# 🕷️ GhostSpider

⚠️ **Status: Under Active Development (Alpha)**  
GhostSpider is **not yet fully optimized or production-ready**.  
Features may be incomplete, unstable, or change without notice.

---

**GhostSpider** is a stealth-focused, Playwright-powered web crawler designed for deep link discovery, recon, and visibility analysis.  
It runs heavy scans **silently in the backend** while exposing clean APIs for progress and results.

> *Silent crawl, visible insights.*

---

## 🚧 Development Status

GhostSpider is currently in an **experimental / alpha stage**:

- ❗ Some features may not work as expected
- ❗ Performance is still being optimized
- ❗ Edge cases (JS-heavy sites, anti-bot systems) may fail
- ❗ APIs and internal logic may change

**Do not rely on GhostSpider for critical or production workflows yet.**  
Feedback, testing, and improvements are ongoing.

---

## ✨ Features

- 🔄 **Async & concurrent crawling** (asyncio + semaphores)
- 🎭 **Browser fingerprint rotation** (UA, viewport, locale, timezone)
- 🧠 **JavaScript-rendered crawling** via Playwright (headless Chromium)
- 🕸️ **Internal & external link discovery**
- 🧾 **robots.txt & sitemap parsing**
- 📸 **Automatic screenshots for every page**
- 💾 **HTML snapshot saving**
- 🧬 **SimHash-based duplicate page detection**
- 🔢 **Sequential URL pattern detection & generation**
- 🧅 **Optional Tor / SOCKS5 proxy support**
- 🌐 **Backend-first architecture (Flask API)**

---

## 🏗️ Architecture

```
Client / Frontend
        |
        v
   Flask API
        |
        v
 GhostSpider Core
 (Async + Playwright)
        |
        v
 File Outputs (URLs, HTML, Screenshots)
```

---

## 📁 Output Structure

```
ghost_spider_out/
├── discovered_urls.txt
├── summary.txt
├── screenshots/
│   ├── a1b2c3.png
│   └── ...
└── pages_html/
    ├── a1b2c3.html
    └── ...
```

---

## 🚀 Installation

### Requirements
- Python 3.9+
- Chromium (via Playwright)

### Install dependencies

```bash
pip install flask playwright aiohttp aiofiles tqdm
playwright install chromium
```

---

## ▶️ Running the Backend

```bash
python ghost_spider_backend.py
```

Server starts on:
```
http://localhost:5000
```

---

## 🔌 API Usage

### ▶ Start a crawl

```http
POST /crawl/start
Content-Type: application/json
```

```json
{
  "start_url": "https://example.com",
  "mode": "stealth",
  "concurrency": 4,
  "delay": 0.6,
  "max_pages": 500
}
```

---

### 📊 Crawl status (realtime polling)

```http
GET /crawl/status
```

---

### 📄 Discovered URLs

```http
GET /crawl/results
```

---

### 🧾 Summary

```http
GET /crawl/summary
```

---

## 🧠 Modes

| Mode | Description |
|-----|-------------|
| `fast` | Shallow crawl, limited depth |
| `stealth` | Human-like delays & fingerprint rotation |
| `deep` | Maximum coverage (experimental) |

---

## 🧅 Tor / Proxy Support

```json
{
  "tor": "socks5://127.0.0.1:9050"
}
```

Routes browser traffic through Tor (experimental).

---

## ⚠️ Legal & Ethical Notice

GhostSpider is intended for:
- Personal research
- Educational use
- Testing systems you own or have permission to test

**You are responsible for how you use this tool.**  
The author takes no responsibility for misuse.

---

## 🧩 Known Limitations

- Single crawl job at a time
- Limited JS network interception
- No built-in authentication or rate limiting
- Not optimized for large-scale crawling

---

## 🔮 Roadmap

- [ ] Stability improvements
- [ ] Performance optimizations
- [ ] Multi-job queue
- [ ] WebSocket / SSE live logs
- [ ] Web UI dashboard
- [ ] URL canonicalization engine
- [ ] Pause / resume crawling

---

## 🧑‍💻 Author

**GhostSpider**  
Built for research, recon, and visibility analysis.

> Crawl quietly. Observe everything.

---
