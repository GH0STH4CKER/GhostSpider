#!/usr/bin/env python3
"""
Ghost-Spider — Silent crawl, visible insights
Author: Generated for Ghost / GhostHacker
Features:
 - Playwright JS execution (headless)
 - Asyncio + semaphore concurrency
 - Rotating lightweight browser fingerprints (UA, viewport, locale)
 - Tor/SOCKS5 proxy support
 - Screenshot capture for each page
 - Sitemap & robots.txt discovery
 - Simple simhash duplicate detection to avoid repeats
 - Sequential URL pattern detection/generation
 - Real-time saving of discovered URLs and metadata
"""

import asyncio
import argparse
import logging
import os
import random
import re
import time
from collections import deque, defaultdict
from hashlib import md5
from pathlib import Path
from urllib.parse import urljoin, urlparse

import aiofiles
import aiohttp
from playwright.async_api import async_playwright
from tqdm.asyncio import tqdm

banner = """                                               
 _____ _           _   _____     _   _         
|   __| |_ ___ ___| |_|   __|___|_|_| |___ ___ 
|  |  |   | . |_ -|  _|__   | . | | . | -_|  _|
|_____|_|_|___|___|_| |_____|  _|_|___|___|_|  
                            |_|                
------------------------------------------------
"""
print(banner)
# ---------------------------
# Configuration / constants
# ---------------------------
DEFAULT_CONCURRENCY = 4
DEFAULT_DELAY = 0.6  # per-page base delay
OUTPUT_DIR = "ghost_spider_out"
SCREENSHOT_DIR = "screenshots"
URLS_FILE = "discovered_urls.txt"
HTML_DIR = "pages_html"

# Minimal UA pool
USER_AGENTS = [
    # desktop
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    # mobile
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]

# Simple list of viewports to rotate
VIEWPORTS = [
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1920, "height": 1080},
    {"width": 1365, "height": 640},
    {"width": 390, "height": 844},  # mobile
]

# Tokenize used by simhash (very lightweight)
TOKEN_RE = re.compile(r"\w+")

# ---------------------------
# Utilities
# ---------------------------
def ensure_dirs(base):
    Path(base).mkdir(parents=True, exist_ok=True)
    Path(base, SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)
    Path(base, HTML_DIR).mkdir(parents=True, exist_ok=True)

def normalize_url(u, base=None):
    if not u:
        return None
    u = u.strip()
    if base:
        u = urljoin(base, u)
    parsed = urlparse(u)
    if parsed.scheme == "":
        u = "http://" + u
        parsed = urlparse(u)
    # strip fragment
    u = parsed._replace(fragment="").geturl().rstrip("/")
    return u

def domain_of(u):
    try:
        return urlparse(u).netloc.lower()
    except:
        return ""

def same_domain(a, b):
    return domain_of(a) == domain_of(b)

def short_hash(text):
    return md5(text.encode("utf-8")).hexdigest()

# ---------------------------
# Simple SimHash implementation
# ---------------------------
def simhash(text, hashbits=64):
    """
    Simple simhash: hash tokens and build bit vector.
    """
    v = [0] * hashbits
    tokens = TOKEN_RE.findall(text.lower())
    if not tokens:
        return 0
    for t in tokens:
        h = int(md5(t.encode()).hexdigest(), 16)
        for i in range(hashbits):
            bit = (h >> i) & 1
            v[i] += (1 if bit else -1)
    fingerprint = 0
    for i, x in enumerate(v):
        if x > 0:
            fingerprint |= 1 << i
    return fingerprint

def hamming(x, y):
    z = x ^ y
    return z.bit_count()

def is_similar(a_text, b_text, threshold=10):
    # smaller threshold = more strict (0 identical)
    a = simhash(a_text)
    b = simhash(b_text)
    return hamming(a, b) <= threshold

# ---------------------------
# GhostSpider core
# ---------------------------
class GhostSpider:
    def __init__(self, start_url, concurrency=DEFAULT_CONCURRENCY, delay=DEFAULT_DELAY,
                 obey_robots=True, tor_proxy=None, mode="stealth", max_pages=1000):
        self.start_url = normalize_url(start_url)
        self.start_domain = domain_of(self.start_url)
        self.concurrency = concurrency
        self.delay = delay
        self.obey_robots = obey_robots
        self.tor_proxy = tor_proxy  # e.g. "socks5://127.0.0.1:9050"
        self.mode = mode
        self.max_pages = max_pages

        # State
        self.to_visit = deque([(self.start_url, 0)])  # (url, depth)
        self.visited = set()
        self.discovered_urls = set()
        self.simhashes = {}  # url -> simhash
        self.sequential_patterns = defaultdict(set)  # prefix->numbers
        self.session = None  # aiohttp session for robots/sitemaps
        self.playwright = None

        # Output
        ensure_dirs(OUTPUT_DIR)
        self.urls_file_path = Path(OUTPUT_DIR) / URLS_FILE
        self.screens_dir = Path(OUTPUT_DIR) / SCREENSHOT_DIR
        self.html_dir = Path(OUTPUT_DIR) / HTML_DIR

        # logging
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
        self.logger = logging.getLogger("ghost-spider")

    async def _write_url(self, url):
        async with aiofiles.open(self.urls_file_path, mode="a", encoding="utf-8") as f:
            await f.write(url + "\n")

    async def fetch_robots_and_sitemaps(self):
        # lightweight robots.txt and sitemap discovery
        try:
            robots_url = urljoin(self.start_url, "/robots.txt")
            async with self.session.get(robots_url, timeout=10) as r:
                if r.status == 200:
                    text = await r.text()
                    # collect sitemap lines
                    for line in text.splitlines():
                        if line.lower().startswith("sitemap:"):
                            s = line.split(":", 1)[1].strip()
                            s = normalize_url(s, self.start_url)
                            if s:
                                self.logger.info(f"Found sitemap in robots: {s}")
                                await self.enqueue_sitemap(s)
        except Exception:
            pass

    async def enqueue_sitemap(self, sitemap_url):
        try:
            async with self.session.get(sitemap_url, timeout=15) as r:
                if r.status == 200:
                    text = await r.text()
                    # naive extract <loc>...</loc>
                    for m in re.findall(r"<loc>(.*?)</loc>", text, flags=re.I):
                        u = normalize_url(m.strip())
                        if u and domain_of(u) == self.start_domain and u not in self.discovered_urls:
                            self.to_visit.append((u, 0))
                            self.discovered_urls.add(u)
                            await self._write_url(u)
        except Exception:
            pass

    def rotate_fingerprint(self):
        ua = random.choice(USER_AGENTS)
        vp = random.choice(VIEWPORTS)
        locale = random.choice(["en-US", "en-GB", "es-ES", "fr-FR", "de-DE"])
        timezone = random.choice(["UTC", "Europe/London", "Asia/Colombo", "America/New_York"])
        return {
            "user_agent": ua,
            "viewport": vp,
            "locale": locale,
            "timezone": timezone
        }

    def extract_links_from_html(self, html, base):
        links = set()
        for m in re.findall(r'href=["\'](.*?)["\']', html, flags=re.I):
            links.add(normalize_url(m, base))
        for m in re.findall(r'src=["\'](.*?)["\']', html, flags=re.I):
            links.add(normalize_url(m, base))
        return {u for u in links if u and u.startswith("http")}

    def detect_sequential(self, u):
        # simplistic pattern that captures trailing number: /item/123 or file-23.html
        m = re.search(r"^(.*?)(\d+)(?:\.\w+)?/?$", u)
        if m:
            prefix = m.group(1)
            num = int(m.group(2))
            self.sequential_patterns[prefix].add(num)

    async def visit_page(self, url, depth, browser):
        # skip if visited or over limit
        if url in self.visited or len(self.visited) >= self.max_pages:
            return
        if not same_domain(url, self.start_url):
            # only index other domains as external records (do not crawl)
            if url not in self.discovered_urls:
                self.discovered_urls.add(url)
                await self._write_url(url)
            return

        self.visited.add(url)
        self.logger.info(f"[{len(self.visited)}] Visiting {url} (depth={depth})")
        fp = self.rotate_fingerprint()

        try:
            context_args = {
                "user_agent": fp["user_agent"],
                "viewport": fp["viewport"],
                "locale": fp["locale"],
                "timezone_id": fp["timezone"],
            }
            if self.tor_proxy:
                context_args["proxy"] = {"server": self.tor_proxy}

            context = await browser.new_context(**context_args)
            page = await context.new_page()

            # navigation with timeout
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
            except Exception:
                # fallback: go with load
                try:
                    await page.goto(url, wait_until="load", timeout=30000)
                except Exception as e:
                    self.logger.warning(f"Failed to load {url}: {e}")
            # small randomized human-like pause
            await asyncio.sleep(self.delay + random.random() * self.delay)

            # get content
            try:
                html = await page.content()
            except Exception:
                html = ""

            # screenshot
            safe_name = short_hash(url)[:12]
            screenshot_path = self.screens_dir / f"{safe_name}.png"
            try:
                await page.screenshot(path=str(screenshot_path), full_page=True)
            except Exception:
                # try viewport screenshot as fallback
                try:
                    await page.screenshot(path=str(screenshot_path), full_page=False)
                except Exception:
                    pass

            # save HTML snapshot
            html_path = self.html_dir / f"{safe_name}.html"
            try:
                async with aiofiles.open(html_path, "w", encoding="utf-8") as f:
                    await f.write(html)
            except Exception:
                pass

            # dedup by simhash
            text_for_hash = " ".join(TOKEN_RE.findall(re.sub(r"\s+", " ", re.sub(r"<.*?>", " ", html or ""))))
            current_hash = simhash(text_for_hash)
            similar_found = False
            for u, h in self.simhashes.items():
                if hamming(current_hash, h) <= 10:
                    similar_found = True
                    break

            if not similar_found:
                self.simhashes[url] = current_hash
            else:
                self.logger.debug(f"Skipped similar content: {url}")
                # optionally still extract links but avoid heavy processing
            # extract links from html and from DOM/network requests
            links = self.extract_links_from_html(html, url)

            # from network requests (fetch/xhr) — attempt to access network logs
            try:
                requests = await page.evaluate(
                    """() => {
                        // This only works if page exposes window.fetch/XHR interception - fallback ignored
                        return [];
                    }"""
                )
            except Exception:
                requests = []

            # consolidate links
            all_links = set(links)
            for r in requests:
                all_links.add(normalize_url(r, url))

            # record discovered urls
            for u in all_links:
                if not u:
                    continue
                if u not in self.discovered_urls:
                    self.discovered_urls.add(u)
                    await self._write_url(u)

                # queue internal domain links for crawling
                if same_domain(u, self.start_url) and u not in self.visited:
                    # basic politeness/limit depth for fast mode
                    if self.mode == "fast" and depth >= 2:
                        continue
                    self.to_visit.append((u, depth + 1))

                # detect sequential patterns
                self.detect_sequential(u)

            # optionally try generated sequential urls
            for prefix, nums in list(self.sequential_patterns.items()):
                if len(nums) >= 3:
                    maxn = max(nums)
                    # generate next few candidates
                    for cand in range(maxn + 1, maxn + 4):
                        cand_url = f"{prefix}{cand}"
                        if domain_of(cand_url) == self.start_domain and cand_url not in self.discovered_urls:
                            self.discovered_urls.add(cand_url)
                            await self._write_url(cand_url)
                            self.to_visit.append((cand_url, depth + 1))

        except Exception as e:
            self.logger.warning(f"Error visiting {url}: {e}")
        finally:
            try:
                await context.close()
            except Exception:
                pass

    async def worker(self, browser, sem):
        while self.to_visit and len(self.visited) < self.max_pages:
            url, depth = self.to_visit.popleft()
            if url in self.visited:
                continue
            async with sem:
                await self.visit_page(url, depth, browser)
            # minor jitter
            await asyncio.sleep(random.random() * self.delay)

    async def run(self):
        # setup http session to fetch robots/sitemaps
        self.session = aiohttp.ClientSession()
        if self.obey_robots:
            await self.fetch_robots_and_sitemaps()

        # start playwright
        self.playwright = await async_playwright().start()
        browser = await self.playwright.chromium.launch(headless=True)

        sem = asyncio.Semaphore(self.concurrency)
        workers = [asyncio.create_task(self.worker(browser, sem)) for _ in range(self.concurrency)]

        # progress display until done
        try:
            await tqdm(asyncio.gather(*workers), desc="Crawlers", total=len(workers))
        except Exception:
            # fallback: wait for all
            await asyncio.gather(*workers, return_exceptions=True)

        await browser.close()
        await self.playwright.stop()
        await self.session.close()

        self.logger.info("Crawl finished")
        # write final discovered urls summary
        # (already appended during crawl) - write additional metadata file
        meta_path = Path(OUTPUT_DIR) / "summary.txt"
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(f"start_url: {self.start_url}\n")
            f.write(f"pages_visited: {len(self.visited)}\n")
            f.write(f"discovered_urls: {len(self.discovered_urls)}\n")
            f.write(f"mode: {self.mode}\n")
            f.write(f"timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

# ---------------------------
# CLI
# ---------------------------
def parse_args():
    p = argparse.ArgumentParser(prog="ghost-spider", description="Ghost-Spider — Silent crawl, visible insights")
    p.add_argument("--start-url", "-u", required=True, help="Start URL")
    p.add_argument("--max-concurrency", "-c", type=int, default=DEFAULT_CONCURRENCY)
    p.add_argument("--delay", "-d", type=float, default=DEFAULT_DELAY)
    p.add_argument("--mode", choices=["fast", "deep", "stealth"], default="stealth")
    p.add_argument("--tor", help="Optional proxy e.g. socks5://127.0.0.1:9050")
    p.add_argument("--max-pages", type=int, default=500)
    return p.parse_args()

async def main():
    args = parse_args()
    ensure_dirs(OUTPUT_DIR)
    # prepare outputs
    if Path(OUTPUT_DIR, URLS_FILE).exists():
        # don't overwrite; append
        pass

    spider = GhostSpider(
        start_url=args.start_url,
        concurrency=args.max_concurrency,
        delay=args.delay,
        obey_robots=True,
        tor_proxy=args.tor,
        mode=args.mode,
        max_pages=args.max_pages
    )
    await spider.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user - exiting.")
