#!/usr/bin/env python3
"""
MediaVault • Instagram & TikTok Media Downloader CLI
Command-line interface for downloading user media.
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from core.models import (
    InstagramDownloadRequest,
    TikTokDownloadRequest,
    DirectUrlDownloadRequest,
    MediaTypeFilter,
    Platform
)
from core.instagram_downloader import instagram_downloader
from core.tiktok_downloader import tiktok_downloader
from core.session_manager import session_manager


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_banner():
    banner = f"""
{Colors.HEADER}{Colors.BOLD}╔════════════════════════════════════════════════════════════════╗
║             MediaVault • Insta & TikTok Downloader             ║
╚════════════════════════════════════════════════════════════════╝{Colors.END}
"""
    print(banner)


def cli_log(level: str, msg: str):
    if level == "success":
        print(f"{Colors.GREEN}[✓] {msg}{Colors.END}")
    elif level == "error":
        print(f"{Colors.RED}[✗] {msg}{Colors.END}")
    elif level == "warning":
        print(f"{Colors.YELLOW}[!] {msg}{Colors.END}")
    else:
        print(f"{Colors.CYAN}[i] {msg}{Colors.END}")


def cli_progress(downloaded: int, total: int, filename: str, percent: float):
    bar_len = 30
    filled_len = int(bar_len * (percent / 100))
    bar = '=' * filled_len + '-' * (bar_len - filled_len)
    sys.stdout.write(f"\r{Colors.BLUE}[{bar}] {percent:.1f}% ({downloaded}/{total}) - {filename[:30]}{Colors.END}")
    sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(
        description="MediaVault - Download all photos, reels, videos & stories from Instagram and TikTok users."
    )

    parser.add_argument("-p", "--platform", choices=["instagram", "tiktok", "direct"], help="Platform to download from")
    parser.add_argument("-u", "--user", nargs="+", help="One or more usernames/URLs (e.g. -u zuck leomessi natgeo)")
    parser.add_argument("--batch-file", help="Path to text file containing target usernames/URLs (one per line)")
    parser.add_argument("-l", "--limit", type=int, default=None, help="Max number of items to download per user (default: all)")
    parser.add_argument("-m", "--media-type", choices=["all", "photos", "videos"], default="all", help="Media filter (Instagram)")
    parser.add_argument("--stories", action="store_true", help="Download Instagram stories (requires login session)")
    parser.add_argument("--highlights", action="store_true", help="Download Instagram story highlights")
    parser.add_argument("--tagged", action="store_true", help="Download Instagram posts where user is tagged")
    parser.add_argument("--audio", action="store_true", help="Download TikTok audio soundtrack as MP3")
    parser.add_argument("--date-from", help="Filter items newer than date (YYYY-MM-DD)")
    parser.add_argument("--date-to", help="Filter items older than date (YYYY-MM-DD)")
    parser.add_argument("--extract-cookies", help="Extract Instagram cookies from browser (chrome, safari, brave, firefox, edge, arc, all)")
    parser.add_argument("--open-folder", action="store_true", help="Open downloaded folder in macOS Finder upon completion")
    parser.add_argument("--urls", nargs="+", help="List of direct URLs to download")
    parser.add_argument("--list", action="store_true", help="List all downloaded user profiles and storage stats")
    parser.add_argument("--zip", nargs=2, metavar=("PLATFORM", "USER"), help="Export a downloaded user archive as a ZIP file")
    parser.add_argument("--proxy", "--proxies", nargs="*", help="Use custom proxy URL(s) or 'auto' to auto-fetch free proxies")

    args = parser.parse_args()
    print_banner()

    # Handle proxy configuration
    if args.proxy is not None:
        from core.proxy_manager import proxy_manager
        if len(args.proxy) == 0 or "auto" in args.proxy:
            cli_log("info", "Auto-fetching and verifying free public proxies...")
            res = proxy_manager.fetch_free_proxies(max_working=5)
            if res.get("success"):
                cli_log("success", f"Activated {res.get('verified_working')} free proxies in rotation pool.")
            else:
                cli_log("warning", "Could not fetch free proxies. Proceeding with direct connection.")
        else:
            for p in args.proxy:
                proxy_manager.add_proxy(p)
            proxy_manager.set_enabled(True)
            cli_log("success", f"Configured {len(args.proxy)} proxy/proxies in rotation pool.")

    # Handle batch file input
    targets = []
    if args.batch_file:
        b_path = Path(args.batch_file)
        if b_path.exists():
            targets = [line.strip() for line in b_path.read_text().splitlines() if line.strip()]
            cli_log("info", f"Loaded {len(targets)} targets from {args.batch_file}")
        else:
            cli_log("error", f"Batch file '{args.batch_file}' not found.")
            return
    elif args.user:
        targets = args.user

    # Handle listing downloads
    if args.list:
        from core.zip_exporter import DOWNLOADS_DIR
        print(f"{Colors.BOLD}📁 Downloaded Media Archives:{Colors.END}\n")
        total_items = 0
        total_bytes = 0
        for p in ["instagram", "tiktok"]:
            p_dir = DOWNLOADS_DIR / p
            if p_dir.exists():
                users = [d for d in p_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
                print(f"  {Colors.CYAN}● {p.upper()} ({len(users)} profiles):{Colors.END}")
                for u in sorted(users, key=lambda x: x.name.lower()):
                    count = 0
                    size = 0
                    for root, _, files in os.walk(u):
                        for f in files:
                            if not f.startswith("."):
                                count += 1
                                size += (Path(root) / f).stat().st_size
                    total_items += count
                    total_bytes += size
                    size_mb = size / (1024 * 1024)
                    print(f"    - @{u.name:<25} {count:>5} files  ({size_mb:>6.1f} MB)")
        print(f"\n{Colors.GREEN}Total Archive: {total_items} files ({total_bytes / (1024*1024):.1f} MB){Colors.END}")
        return

    # Handle ZIP creation
    if args.zip:
        from core.zip_exporter import zip_exporter
        p, u = args.zip
        cli_log("info", f"Generating ZIP for {p.upper()} @{u}...")
        zip_path = zip_exporter.create_user_zip(p.lower(), u)
        if zip_path and zip_path.exists():
            cli_log("success", f"ZIP archive created: {zip_path}")
            if sys.platform == "darwin":
                subprocess.run(["open", "-R", str(zip_path)])
        else:
            cli_log("error", f"Could not create ZIP for @{u}.")
        return

    # Handle cookie extraction first if requested
    if args.extract_cookies:
        browser = args.extract_cookies.lower()
        if browser == "all":
            cli_log("info", "Scanning all installed browsers for Instagram session cookies...")
            res = session_manager.scan_all_browsers_for_instagram()
            if res.get("success"):
                cli_log("success", f"Successfully extracted session from {res.get('browser').upper()}!")
            else:
                cli_log("warning", "Could not find active session in browser profiles.")
        else:
            cli_log("info", f"Extracting cookies from {browser.upper()}...")
            success, details = session_manager.auto_extract_from_browser(browser)
            if success:
                cli_log("success", details.get("message", "Cookies extracted!"))
            else:
                cli_log("error", details.get("error", "Extraction failed."))
        if not args.platform and not targets:
            return

    # Interactive prompt if parameters missing
    platform = args.platform
    if not platform and not targets:
        print(f"{Colors.BOLD}Select Platform:{Colors.END}")
        print("  1) Instagram")
        print("  2) TikTok")
        print("  3) Direct Links")
        choice = input(f"{Colors.CYAN}Enter choice (1-3) [1]: {Colors.END}").strip() or "1"
        if choice == "2":
            platform = "tiktok"
        elif choice == "3":
            platform = "direct"
        else:
            platform = "instagram"

    if platform in ["instagram", "tiktok"] and not targets:
        raw_in = input(f"{Colors.CYAN}Enter {platform.capitalize()} username(s) (space-separated): {Colors.END}").strip()
        if not raw_in:
            cli_log("error", "Username cannot be empty.")
            return
        targets = raw_in.split()

    # Execute Download for each target
    dest_folder = None
    if platform == "instagram" or (not platform and targets):
        mtype = MediaTypeFilter.ALL
        if args.media_type == "photos":
            mtype = MediaTypeFilter.PHOTOS
        elif args.media_type == "videos":
            mtype = MediaTypeFilter.VIDEOS

        for user_item in targets:
            # Auto-detect if user_item is tiktok or direct
            actual_plat, actual_target = job_manager.resolve_target(user_item, Platform.INSTAGRAM if platform != "tiktok" else Platform.TIKTOK)
            
            if actual_plat == Platform.TIKTOK:
                cli_log("info", f"Starting TikTok download for @{actual_target}...")
                req = TikTokDownloadRequest(
                    username_or_url=actual_target,
                    download_videos=not args.audio,
                    download_slideshows=True,
                    download_audio=args.audio,
                    download_profile_pic=True,
                    limit=args.limit,
                    save_metadata=True
                )
                res = tiktok_downloader.download_user(
                    request=req,
                    progress_callback=cli_progress,
                    log_callback=cli_log
                )
            else:
                cli_log("info", f"Starting Instagram download for @{actual_target}...")
                req = InstagramDownloadRequest(
                    username_or_url=actual_target,
                    download_posts=True,
                    download_reels=True,
                    download_stories=args.stories,
                    download_highlights=args.highlights,
                    download_tagged=args.tagged,
                    download_profile_pic=True,
                    media_type=mtype,
                    limit=args.limit,
                    date_from=args.date_from,
                    date_to=args.date_to,
                    save_captions=True,
                    save_metadata=True
                )
                res = instagram_downloader.download_user(
                    request=req,
                    progress_callback=cli_progress,
                    log_callback=cli_log
                )

            print()
            if res.get("success"):
                dest_folder = res.get("folder")
                cli_log("success", f"Completed @{actual_target}! Saved {res.get('downloaded_count')} files in {dest_folder}")
            else:
                cli_log("error", f"Failed @{actual_target}: {res.get('error')}")

    elif platform == "tiktok":
        for user_item in targets:
            cli_log("info", f"Starting TikTok download for @{user_item}...")
            req = TikTokDownloadRequest(
                username_or_url=user_item,
                download_videos=not args.audio,
                download_slideshows=True,
                download_audio=args.audio,
                download_profile_pic=True,
                limit=args.limit,
                save_metadata=True
            )

            res = tiktok_downloader.download_user(
                request=req,
                progress_callback=cli_progress,
                log_callback=cli_log
            )
            print()
            if res.get("success"):
                dest_folder = res.get("folder")
                cli_log("success", f"Finished! Total files downloaded: {res.get('downloaded_count')}")
                cli_log("info", f"Files saved in: {dest_folder}")
            else:
                cli_log("error", f"Download failed: {res.get('error')}")


    elif platform == "direct":
        urls = args.urls
        if not urls:
            raw_urls = input(f"{Colors.CYAN}Enter URLs separated by space: {Colors.END}").strip()
            urls = raw_urls.split()

        if not urls:
            cli_log("error", "No URLs provided.")
            return

        for u in urls:
            cli_log("info", f"Downloading {u}...")
            if "instagram.com" in u:
                res = instagram_downloader.download_direct_post(u)
            else:
                res = tiktok_downloader.download_direct_url(u)

            if res.get("success"):
                cli_log("success", f"Saved: {u}")
            else:
                cli_log("error", f"Failed ({u}): {res.get('error')}")

    # Open Finder if requested
    if args.open_folder and dest_folder:
        if sys.platform == "darwin":
            subprocess.run(["open", str(dest_folder)])


if __name__ == "__main__":
    main()
