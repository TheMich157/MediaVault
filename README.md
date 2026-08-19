# MediaVault • Instagram & TikTok Downloader Studio

A powerful, full-featured media downloader tool that allows you to download all **videos, reels, stories, highlights, photos, and carousels** of any given user from **Instagram** and **TikTok**.

Includes a modern Glassmorphism Web Dashboard, live progress streaming, interactive media gallery viewer, video player, one-click ZIP exporter, Finder integration, and a complete command-line interface (CLI).

---

## Features

- 📸 **Instagram Hub**:
  - Download all posts in original high resolution (single photos & multi-item carousels).
  - Download full-length video reels and IGTV videos.
  - Download active **Stories (24h)** and **Story Highlights**.
  - Download profile picture avatar and biography metadata (`user_info.json`).
  - Filter by media type (All, Photos only, Videos only) and count limits.
  - Save post captions (`.txt`) and metadata (`.json` with likes, comments, hashtags, timestamp).

- 🎵 **TikTok Hub**:
  - Download all user videos in HD without watermarks.
  - Download photo carousels & slideshows.
  - Download background audio soundtracks as MP3.
  - Save video descriptions, titles, tags, and creator metadata.

- 🔗 **Direct URL Batch Downloader**:
  - Paste lists of direct Instagram post/reel URLs or TikTok video URLs for instant batch download.

- 🔑 **Built-in Session & Cookie Manager**:
  - **1-Click Auto-Scan**: Automatically scan installed browsers (Chrome, Safari, Brave, Firefox, Edge) to extract your Instagram session cookie.
  - **1-Click Bookmarklet**: Instant 5-second console snippet to copy your browser cookie without passwords.
  - **Direct Cookie Paste**: Paste `sessionid` or cookie header with real-time validation.

- 🖼️ **Interactive Media Gallery & Archive**:
  - In-browser media explorer organized by Platform → Username.
  - High-res photo lightbox with zoom.
  - HTML5 video player with playback controls.
  - One-click **"Export as ZIP"** for any downloaded profile.
  - **"Open in macOS Finder"** button to jump directly to the local folder.

- 💻 **CLI & macOS Launcher**:
  - Double-clickable `start.command` for macOS Finder.
  - Complete CLI tool (`cli.py`) with rich terminal progress bars.

---

## Quick Start

### 1. Launching the Web Studio

Simply double-click `start.command` in Finder or run in your terminal:

```bash
./run.sh
```

or:

```bash
./venv/bin/python main.py
```

This will launch the Web Studio at `http://0.0.0.0:3000` (accessible locally via `http://localhost:3000` or from other devices on your LAN) and automatically open your default browser.


---

### 2. Using the Command Line Interface (CLI)

Run `cli.py` with flexible parameters:

```bash
# Download latest 20 Instagram posts from a user
./venv/bin/python cli.py -p instagram -u zuck -l 20

# Download Instagram stories & highlights
./venv/bin/python cli.py -p instagram -u username --stories --highlights

# Download TikTok creator videos (latest 30)
./venv/bin/python cli.py -p tiktok -u khaby.lame -l 30

# Extract Instagram session from Chrome browser
./venv/bin/python cli.py --extract-cookies chrome

# Download direct URLs
./venv/bin/python cli.py -p direct --urls https://www.instagram.com/p/C... https://www.tiktok.com/@user/video/...
```

---

## Instagram Stories & Authentication Guide

- **Public Posts & Reels**: Downloadable immediately without logging in or providing any credentials.
- **Stories & Private Profiles You Follow**: Instagram requires an active session cookie to view stories. You can connect your session in the **Session & Cookies** tab:
  1. Click **Auto-Scan All Browsers** to let MediaVault detect your logged-in browser profile.
  2. Or copy the 1-click JavaScript snippet provided in the **Session & Cookies** tab on `instagram.com` and paste your cookie into the box.

---

## Folder Organization

All downloaded media is saved cleanly in the `downloads/` directory:

```
downloads/
├── instagram/
│   └── <username>/
│       ├── profile_pic.jpg
│       ├── user_info.json
│       ├── 20260818_142300_C9xYz123.jpg
│       ├── 20260818_142300_C9xYz123_caption.txt
│       ├── 20260818_142300_C9xYz123_meta.json
│       ├── stories/
│       └── highlights/
└── tiktok/
    └── <username>/
        ├── 20260818_7234567890_video_title.mp4
        └── 20260818_7234567890_video_title.info.json
```
