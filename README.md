# 🕷️ GhostSpider

🟡 **Status: Under Development**  
GhostSpider is still being actively developed and optimized. Some features may be incomplete or unstable.

---

**GhostSpider** is a stealth-focused, Playwright-powered web crawler designed for deep link discovery, recon, and visibility analysis.

> *Silent crawl, visible insights.*

---

## ✨ Features

- 🔄 Async & concurrent crawling (asyncio + semaphores)
- 🧠 JavaScript-rendered crawling via Playwright (headless Chromium)
- 🎭 Lightweight browser fingerprint rotation (UA, viewport, locale)
- 🕸️ Internal & external link discovery
- 🧾 robots.txt & sitemap parsing
- 📸 Automatic screenshots for every page
- 💾 HTML snapshot saving
- 🧬 SimHash-based duplicate page detection
- 🔢 Sequential URL pattern detection & generation
- 🧅 Optional SOCKS5 / Tor proxy support
- 🧩 Backend-oriented design (API or service driven)

---

## 🏗️ Architecture (High-Level)

```
Controller / API / Script
          |
          v
     GhostSpider Core
   (Async + Playwright)
          |
          v
   File-based Outputs
```

GhostSpider is **backend-agnostic** — it can be embedded into:
- a custom API
- a web backend
- a CLI wrapper
- or an automation pipeline

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
- Chromium (Playwright)

### Install dependencies

```bash
pip install playwright aiohttp aiofiles tqdm
playwright install chromium
```

---

## ▶️ Usage

GhostSpider can be started from:
- a backend service
- a Python script
- or an API wrapper

Example (programmatic use):

```python
spider = GhostSpider(
    start_url="https://example.com",
    mode="stealth",
    max_pages=500
)
await spider.run()
```

---

## 🧠 Crawl Modes

| Mode | Description |
|-----|-------------|
| `fast` | Shallow crawl, limited depth |
| `stealth` | Human-like delays and fingerprint rotation |
| `deep` | Maximum coverage (experimental) |

---

## 🧅 Proxy / Tor Support

```python
tor_proxy="socks5://127.0.0.1:9050"
```

Routes browser traffic through the specified proxy.

---

## ⚠️ Notes

- GhostSpider does **not bypass authentication**
- Some JS-heavy or protected sites may not work
- Performance tuning is ongoing

---

## 🧩 Known Limitations

- Single crawl instance by default
- Limited JavaScript network introspection
- Not optimized for very large-scale crawling

---

## 🔮 Roadmap

- Performance optimizations
- Improved URL normalization & canonicalization
- Better JS network extraction
- Optional job queue support
- Optional UI/dashboard layer

---

## 🧑‍💻 Author

**GhostSpider**  
Built for research, recon, and visibility analysis.

> Crawl quietly. Observe what’s exposed.

---
