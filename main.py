#!/usr/bin/env python3
"""
MediaVault • Main Entry Point
Launches the Web Dashboard or CLI.
"""

import os
import sys
import webbrowser
import threading
import time
import argparse
import uvicorn
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))


def open_browser_delayed(url: str, delay: float = 1.2):
    """Open default web browser after server starts."""
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Notice: Could not auto-open browser: {e}")


def run_web_server(host: str = "0.0.0.0", port: int = 3000, auto_open: bool = True):
    display_host = "localhost" if host == "0.0.0.0" else host
    browser_url = f"http://{display_host}:{port}"
    print(f"\n🚀 Starting MediaVault Web Studio on http://{host}:{port} (Local: {browser_url})")
    print("Press Ctrl+C to stop the server.\n")

    if auto_open:
        threading.Thread(target=open_browser_delayed, args=(browser_url,), daemon=True).start()

    uvicorn.run(
        "backend.app:app",
        host=host,
        port=port,
        log_level="info",
        reload=True,
        reload_dirs=[str(BASE_DIR)]
    )



def main():
    parser = argparse.ArgumentParser(description="MediaVault - Instagram & TikTok Media Downloader Studio")
    parser.add_argument("--cli", action="store_true", help="Launch interactive Command-Line Interface instead of Web Studio")
    parser.add_argument("--host", default="0.0.0.0", help="Host address for Web Studio (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=3000, help="Port for Web Studio (default: 3000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser on startup")

    # Pass remaining args to cli if --cli is passed
    args, remaining = parser.parse_known_args()

    if args.cli or len(remaining) > 0:
        import cli
        sys.argv = [sys.argv[0]] + remaining
        cli.main()
    else:
        run_web_server(host=args.host, port=args.port, auto_open=not args.no_browser)



if __name__ == "__main__":
    main()
