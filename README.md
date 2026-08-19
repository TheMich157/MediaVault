<div align="center">

# ⚡ MediaVault • Studio & CLI
### High-Performance Instagram & TikTok Media Archiver, Batch Downloader & Gallery

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)]()
[![Code Style](https://img.shields.io/badge/Code%20Style-Black-000000.svg)](https://github.com/psf/black)

*A studio-grade media archiver and bulk downloader for Instagram and TikTok with real-time UI, interactive terminal shell, automated proxy rotation, smart session management, and local gallery viewer.*

[Features](#-key-features) • [Quick Start](#-quick-start) • [Web Studio](#-web-studio-dashboard) • [CLI Reference](#-command-line-interface-cli) • [Terminal Shell](#-interactive-terminal-console) • [Proxy Engine](#-proxy-pool--evasion-engine) • [Architecture](#-project-architecture) • [Privacy](#-privacy--security-safeguards)

---

</div>

## 🌟 Overview

**MediaVault** is an all-in-one media downloading studio designed for creators, researchers, archivists, and power users. It combines a **modern Glassmorphism Web Dashboard** with a high-throughput **Command-Line Interface (CLI)** and an embedded **Interactive Terminal Shell**.

Whether you want to download an entire Instagram profile with carousels, reels, and story highlights, back up thousands of watermark-free TikTok videos, or concurrently scrape media across multiple targets using rotating proxies, MediaVault handles it cleanly with zero dependencies on third-party cloud services.

---

## 🚀 Key Features

### 📸 Instagram Hub
- **High-Resolution Posts**: Downloads original high-resolution photos and multi-item carousels.
- **Reels & Video Feeds**: Full-length 1080p video reels with audio.
- **Active Stories & Story Highlights**: Archive 24-hour stories and permanent story highlights.
- **Tagged Media**: Download public media where the target user was tagged.
- **Profile Avatars & HD Pictures**: Automatic fetching and proxying of user avatars.
- **Captions & Rich Metadata**: Captions saved as `.txt` and rich metadata saved as structured `.json` (likes, comments, timestamps, hashtags).
- **Date & Count Filtering**: Flexible limits and date range bounds (`--date-from`, `--date-to`).

### 🎵 TikTok Hub
- **Watermark-Free HD Videos**: Direct downloads in original resolution.
- **Photo Slideshows & Carousels**: Full-resolution image extractions from photo posts.
- **Audio Soundtracks**: Extract background audio tracks as standalone MP3 files.
- **Creator Metadata**: Save creator channel information, descriptions, tags, and statistics.

### 🌐 Rotating Proxy Pool & Anti-Block Evasion
- **Auto-Rotation on Rate Limits**: Automatically switches to the next proxy in the pool upon receiving `HTTP 429` (Too Many Requests) or `HTTP 403` (Forbidden).
- **Protocol Flexibility**: Supports `http://`, `https://`, `socks4://`, and `socks5://` (with optional username/password credentials).
- **⚡ 1-Click Free Proxy Auto-Fetch**: Built-in automated scraper and multi-threaded validator that scans public proxy repositories in parallel and activates verified low-latency proxies.

### 🔑 Zero-Password Session & Cookie Management
- **1-Click Auto-Scan**: Automatically scan installed macOS/Windows browsers (**Chrome, Safari, Brave, Firefox, Edge, Arc**) to import Instagram session cookies without entering credentials.
- **1-Click JS Bookmarklet**: A fast 5-second JavaScript console snippet to copy browser session cookies securely.
- **Direct Cookie Header Paste**: Paste cookie strings or raw `sessionid` with real-time session verification.

### 🖼️ Interactive Media Gallery & Archive
- **Organized Platform Browser**: Browse archives categorized by `Platform → Username`.
- **Photo Lightbox**: Fullscreen high-resolution photo viewer with zoom and EXIF metadata.
- **HTML5 Video Player**: Built-in player with playback speed controls (0.5x – 2.0x).
- **1-Click ZIP Exporter**: Package any user's media into an uncompressed or standard ZIP archive.
- **macOS Finder Integration**: Instant "Show in Finder" button to open the local storage directory.
- **Batch Management**: Multi-select deletion, batch ZIP exports, and disk usage breakdowns.

### 💻 Dual Interface: Web Studio + CLI
- **Real-Time Live Progress**: Server-Sent Events (SSE) streaming live download speed, progress bars, active queue drawer, and logs.
- **Embedded Web Terminal**: Interactive terminal shell inside the web browser with history navigation.
- **Standalone CLI (`cli.py`)**: Full command-line tool with rich colored progress bars and headless batch support.

---

## 🛠️ Quick Start

### Prerequisites
- **Python 3.10+**
- **FFmpeg** (Recommended for video and audio processing)
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: `winget install Gyan.FFmpeg`

### 1. Clone & Setup

```bash
# Clone the repository
git clone https://github.com/TheMich157/MediaVault.git
cd MediaVault

# Run the automated launch script (creates virtualenv & installs requirements)
./run.sh
```

> **macOS Users**: You can also simply double-click **`start.command`** in Finder!

The Web Studio will launch automatically at **`http://localhost:3000`**.

---

## 🖥️ Web Studio Dashboard

```text
┌────────────────────────────────────────────────────────────────────────┐
│  MEDIAVAULT • STUDIO              [Storage: 1.2 GB]  [Session: Active] │
├────────────────────────────────────────────────────────────────────────┤
│  [📸 Instagram]   [🎵 TikTok]   [🔗 Direct URLs]   [🖼️ Gallery]       │
│                                                                        │
│  Target Username:  [@zuck                                  ] [Inspect] │
│  Targets:  [x] Posts  [x] Reels  [x] Stories  [x] Highlights  [ ] Tagged│
│  Filters:  Media: [All]   Limit: [30]   From: [YYYY-MM-DD]             │
│                                                                        │
│  [       🚀 START DOWNLOAD       ]                                    │
│                                                                        │
│  ┌─ Live Interactive Terminal Shell ────────────────────────────────┐  │
│  │ Quick: [⚡ Auto-Fetch Free Proxies] [🌐 Proxy Status] [📋 Jobs]   │  │
│  │ mediavault > proxy fetch                                         │  │
│  │ [✓] Activated 5 fast verified proxies into rotation pool.        │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## ⌨️ Command-Line Interface (CLI)

MediaVault includes a full-featured CLI accessible via `cli.py`:

```bash
# Download latest 20 Instagram posts & reels from a user
python3 cli.py -p instagram -u zuck -l 20

# Download Instagram stories and permanent highlights
python3 cli.py -p instagram -u target_user --stories --highlights

# Download TikTok creator videos without watermarks
python3 cli.py -p tiktok -u khaby.lame -l 30

# Extract TikTok audio soundtrack as MP3
python3 cli.py -p tiktok -u creator_name --audio

# Run with automated free proxy rotation
python3 cli.py -p instagram -u zuck --proxies auto

# Download a batch list of handles from a text file
python3 cli.py --batch-file targets.txt -l 50

# Download direct post/reel/video URLs
python3 cli.py -p direct --urls https://www.instagram.com/p/C... https://www.tiktok.com/@user/video/...

# Extract session cookies from Chrome browser
python3 cli.py --extract-cookies chrome

# List downloaded media archives and disk usage
python3 cli.py --list

# Export downloaded profile archive as a ZIP
python3 cli.py --zip instagram zuck
```

---

## 💻 Interactive Terminal Console

When using the Web Studio, open the bottom drawer to access the interactive CLI shell:

| Command | Description | Example |
| :--- | :--- | :--- |
| `ig <user1> [user2...] [-l N]` | Download Instagram profile(s) | `ig zuck leomessi -l 25` |
| `tt <user1> [user2...] [-l N]` | Download TikTok creator(s) | `tt khaby.lame -l 50` |
| `batch <t1> <t2>...` | Multi-target concurrent download | `batch @zuck tt:khaby.lame` |
| `direct <url1> [url2...]` | Download direct media URLs | `direct https://instagram.com/p/...` |
| `proxy fetch` | Auto-scrape & verify fresh free proxies | `proxy fetch` |
| `proxy list` | Show current proxy pool status | `proxy list` |
| `proxy rotate` | Switch to next proxy in pool | `proxy rotate` |
| `proxy add <url>` | Add custom proxy to pool | `proxy add socks5://127.0.0.1:9050` |
| `proxy test [url]` | Test proxy latency & outbound IP | `proxy test` |
| `cookies [browser]` | Auto-extract session cookies | `cookies chrome` |
| `zip <platform> <user>` | Create ZIP archive of user media | `zip instagram zuck` |
| `open` / `finder` | Reveal downloads in macOS Finder | `finder instagram zuck` |
| `jobs` / `ps` | List active and queued download jobs | `jobs` |
| `cancel <id \| all>` | Cancel download task(s) | `cancel all` |
| `storage` / `df` | Display disk usage breakdown | `storage` |
| `clear` / `cls` | Clear terminal output | `clear` |

---

## 🌐 Proxy Pool & Evasion Engine

When downloading large volumes of media, social platforms can issue temporary rate limits (`HTTP 429`) or Cloudflare blocks (`HTTP 403`). MediaVault's proxy engine prevents interruptions:

1. **Automatic Failover**: When a request fails due to rate limits or connection drops, the engine rotates to the next proxy in `data/proxies.json` and retries with backoff.
2. **Auto-Discovery**: Run `proxy fetch` in the terminal or click **`⚡ Auto-Fetch Free Proxies`** in the UI to discover and test working public proxies.
3. **Local Tor Integration**: Run a local Tor SOCKS5 daemon (`brew install tor && tor`) and connect it via:
   ```text
   proxy add socks5://127.0.0.1:9050
   ```

---

## 📁 Project Architecture

```text
MediaVault/
├── backend/
│   ├── app.py                  # FastAPI server, REST API & Media Proxy routes
│   └── sse.py                  # Server-Sent Events (SSE) live progress broadcaster
├── core/
│   ├── instagram_downloader.py # Instagram scraping engine (Instaloader + session)
│   ├── tiktok_downloader.py    # TikTok scraper engine (yt-dlp wrapper)
│   ├── proxy_manager.py        # Rotating proxy pool, validation & auto-fetch
│   ├── session_manager.py      # Cookie extraction, browser vaults & auth
│   ├── job_manager.py          # Background queue, progress tracking & concurrency
│   ├── zip_exporter.py         # ZIP archive bundler
│   └── models.py               # Pydantic data schemas & request models
├── frontend/
│   ├── index.html              # Single-page Glassmorphism studio interface
│   ├── css/
│   │   └── style.css           # Vanilla CSS design system & animations
│   └── js/
│       └── app.js              # State manager, SSE receiver, lightbox & gallery
├── data/                       # [Excluded from git] Local state
│   ├── sessions/               # Active session cookies (Ignored by git)
│   ├── zips/                   # Generated ZIP export archives (Ignored by git)
│   └── proxies.json            # Active proxy pool configuration (Ignored by git)
├── downloads/                  # [Excluded from git] Downloaded media files
│   ├── instagram/              # Downloaded Instagram user folders
│   └── tiktok/                 # Downloaded TikTok user folders
├── cli.py                      # Standalone Command-Line Interface
├── main.py                     # Main application entry point
├── run.sh                      # One-click startup shell script
├── start.command               # macOS Finder double-clickable launcher
├── requirements.txt            # Python package dependencies
├── test_app.py                 # Comprehensive unit & integration test suite
├── .env.example                # Environment variables template
├── .gitignore                  # Strict privacy & security exclusions
└── LICENSE                     # MIT License
```

---

## 🔒 Privacy & Security Safeguards

MediaVault is designed from the ground up to keep your personal data and downloaded content private:

- **100% Local Execution**: All media, metadata, logs, and cookies are stored exclusively on your local machine.
- **Strict `.gitignore` Protections**:
  - `data/sessions/*` is excluded so your private Instagram/TikTok session cookies, tokens, and user IDs are never committed or leaked.
  - `downloads/*` is excluded so downloaded photos, videos, and captions remain private.
  - `data/proxies.json` is excluded to protect private proxy credentials.
- **Credential Masking**: Proxy credentials (passwords, tokens) are masked in all logs and terminal output.

---

## 🧪 Testing

MediaVault comes with a comprehensive test suite covering the API, job queues, session management, proxy rotation, and gallery operations:

```bash
# Run full unit and integration tests
python3 -m unittest test_app.py
```

---

## ⚖️ Legal & Ethical Disclaimer

This software is developed for educational, archival, and personal backup purposes only. 

- Users are responsible for complying with Instagram's and TikTok's Terms of Service.
- Respect the intellectual property rights and privacy of content creators.
- Do not use this tool for unauthorized bulk distribution or commercial exploitation of copyrighted content.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.
