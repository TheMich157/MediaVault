import os
import re
import json
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime
import yt_dlp

from core.models import TikTokDownloadRequest
from core.session_manager import TIKTOK_COOKIES_TXT
from core.proxy_manager import proxy_manager

logger = logging.getLogger(__name__)

DOWNLOADS_DIR = Path(__file__).resolve().parent.parent / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)


class TikTokDownloader:
    """Downloader engine for TikTok media (videos, photo slideshows, audio, metadata)."""

    def __init__(self, base_download_dir: Optional[Path] = None):
        self.base_dir = base_download_dir or DOWNLOADS_DIR
        self.tiktok_dir = self.base_dir / "tiktok"
        self.tiktok_dir.mkdir(parents=True, exist_ok=True)

    def extract_username(self, input_str: str) -> str:
        """Clean username or extract username from URL."""
        s = input_str.strip().rstrip("/")
        if "tiktok.com" in s:
            match = re.search(r"tiktok\.com/@([^/?#]+)", s)
            if match:
                return match.group(1)
        if s.startswith("@"):
            return s[1:].strip()
        if "/" in s:
            parts = [p for p in s.split("/") if p and "tiktok.com" not in p]
            if parts:
                return parts[-1].replace("@", "")
        return s

    def fetch_user_info(self, username_or_url: str) -> Dict[str, Any]:
        """Fetch profile info using yt-dlp flat extraction."""
        username = self.extract_username(username_or_url)
        url = f"https://www.tiktok.com/@{username}"

        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'extract_flat': True,
            'playlist_items': '1-1',
            'no_warnings': True,
        }

        if TIKTOK_COOKIES_TXT.exists():
            ydl_opts['cookiefile'] = str(TIKTOK_COOKIES_TXT)

        proxy = proxy_manager.get_ytdl_proxy()
        if proxy:
            ydl_opts['proxy'] = proxy

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return {"success": False, "error": f"Could not find TikTok user @{username}"}
                
                thumbnails = info.get("thumbnails", [])
                avatar_url = thumbnails[-1].get("url") if thumbnails else None

                import requests
                local_pic = self.tiktok_dir / username / "profile_pic.jpg"
                if local_pic.exists():
                    display_avatar = f"/media/tiktok/{username}/profile_pic.jpg"
                elif avatar_url:
                    display_avatar = f"/api/proxy-image?url={requests.utils.quote(avatar_url, safe='')}"
                else:
                    display_avatar = ""

                return {
                    "success": True,
                    "username": username,
                    "display_name": info.get("uploader") or info.get("channel") or username,
                    "channel_id": info.get("channel_id"),
                    "webpage_url": url,
                    "description": info.get("description") or "",
                    "avatar_url": display_avatar,
                    "raw_avatar_url": avatar_url,
                }
        except Exception as e:
            return {"success": False, "error": f"Failed to fetch TikTok profile: {str(e)}"}

    def download_url_to_file(self, url: str, dest_path: Path) -> bool:
        """Download a direct remote media URL to destination file."""
        import requests
        try:
            resp = requests.get(url, stream=True, timeout=20)
            if resp.status_code == 200:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with open(dest_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                return True
        except Exception as e:
            logger.warning(f"Failed to download URL {url} to {dest_path}: {e}")
        return False

    def download_user(
        self,
        request: TikTokDownloadRequest,
        progress_callback: Optional[Callable[[int, int, str, float], None]] = None,
        log_callback: Optional[Callable[[str, str], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        """Download all videos/slideshows from given TikTok user."""
        username = self.extract_username(request.username_or_url)
        target_dir_name = request.custom_subfolder or username
        user_folder = self.tiktok_dir / target_dir_name
        user_folder.mkdir(parents=True, exist_ok=True)

        def log(level: str, msg: str):
            if log_callback:
                log_callback(level, msg)
            logger.info(f"[{level.upper()}] {msg}")

        def check_cancel():
            if is_cancelled and is_cancelled():
                log("warning", "TikTok download cancelled by user.")
                raise InterruptedError("Download was cancelled.")

        log("info", f"Starting TikTok download for @{username}...")
        url = f"https://www.tiktok.com/@{username}"

        # Fetch profile info for avatar
        if request.download_profile_pic:
            try:
                prof_info = self.fetch_user_info(username)
                if prof_info.get("success"):
                    if prof_info.get("avatar_url"):
                        pic_file = user_folder / "profile_pic.jpg"
                        if not pic_file.exists():
                            self.download_url_to_file(prof_info["avatar_url"], pic_file)

                    if request.save_metadata:
                        user_info_file = user_folder / "user_info.json"
                        with open(user_info_file, "w", encoding="utf-8") as uf:
                            json.dump({
                                "username": username,
                                "display_name": prof_info.get("display_name"),
                                "description": prof_info.get("description"),
                                "webpage_url": prof_info.get("webpage_url"),
                                "download_date": datetime.now().isoformat()
                            }, uf, indent=2, ensure_ascii=False)
            except Exception as pe:
                logger.warning(f"TikTok avatar fetch notice: {pe}")

        # Setup yt-dlp options
        outtmpl = str(user_folder / "%(upload_date>%Y%m%d)s_%(id)s_%(title).60B.%(ext)s")
        
        # Determine format
        if request.download_audio and not request.download_videos:
            fmt = "bestaudio/best"
        else:
            fmt = "bestvideo+bestaudio/best"


        downloaded_count = 0
        total_items = 0

        class YTDLLogger:
            def debug(self, msg):
                if "[download]" in msg and "Destination" in msg:
                    log("info", msg)
                elif "Downloading item" in msg:
                    log("info", msg)

            def info(self, msg):
                if msg.strip():
                    log("info", msg)

            def warning(self, msg):
                log("warning", msg)

            def error(self, msg):
                log("error", msg)

        def ytdl_progress_hook(d):
            nonlocal downloaded_count
            check_cancel()

            if d['status'] == 'downloading':
                curr_file = Path(d.get('filename', '')).name
                speed = d.get('_speed_str', '')
                eta = d.get('_eta_str', '')
                pct_str = d.get('_percent_str', '0%').replace('%', '').strip()
                try:
                    pct = float(pct_str)
                except ValueError:
                    pct = 0.0

                if progress_callback:
                    progress_callback(downloaded_count, total_items or 1, curr_file, pct)

            elif d['status'] == 'finished':
                downloaded_count += 1
                curr_file = Path(d.get('filename', '')).name
                log("success", f"Downloaded: {curr_file}")
                if progress_callback:
                    progress_callback(downloaded_count, total_items or downloaded_count, curr_file, 100.0)

        ydl_opts: Dict[str, Any] = {
            'outtmpl': outtmpl,
            'format': fmt,
            'writedescription': request.save_metadata,
            'writeinfojson': request.save_metadata,
            'logger': YTDLLogger(),
            'progress_hooks': [ytdl_progress_hook],
            'ignoreerrors': True,
            'no_color': True,
            'retries': 5,
        }

        if request.limit:
            ydl_opts['playlist_items'] = f"1-{request.limit}"

        if request.date_from or request.date_to:
            date_filter = ""
            if request.date_from:
                date_filter += f"upload_date >= {request.date_from.replace('-', '')}"
            if request.date_to:
                if date_filter:
                    date_filter += " & "
                date_filter += f"upload_date <= {request.date_to.replace('-', '')}"
            if date_filter:
                ydl_opts['match_filter'] = yt_dlp.utils.match_filter_func(date_filter)

        if TIKTOK_COOKIES_TXT.exists():
            ydl_opts['cookiefile'] = str(TIKTOK_COOKIES_TXT)

        proxy = proxy_manager.get_ytdl_proxy()
        if proxy:
            ydl_opts['proxy'] = proxy

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                log("info", "Extracting TikTok video feed...")
                # First extract entries count
                info = ydl.extract_info(url, download=False)
                if info and 'entries' in info:
                    entries = list(info['entries'])
                    total_items = len(entries)
                    if request.limit:
                        total_items = min(total_items, request.limit)
                    log("info", f"Found {total_items} items to download.")
                
                # Perform download
                ydl.download([url])

            # Clean non-media files if save_metadata is False
            if not request.save_metadata:
                media_exts = {'.mp4', '.mov', '.mkv', '.webm', '.jpg', '.jpeg', '.png', '.webp', '.mp3', '.m4a'}
                for root, _, files in os.walk(user_folder):
                    for f in files:
                        fpath = Path(root) / f
                        if fpath.suffix.lower() not in media_exts:
                            try:
                                fpath.unlink()
                            except Exception:
                                pass

            log("success", f"TikTok download complete for @{username}! Files saved in: {user_folder.name}")
            return {
                "success": True,
                "username": username,
                "downloaded_count": downloaded_count,
                "folder": str(user_folder)
            }

        except InterruptedError:
            log("warning", "Download was stopped by user.")
            return {"success": False, "cancelled": True, "downloaded_count": downloaded_count}
        except Exception as e:
            log("error", f"TikTok download error: {str(e)}")
            return {"success": False, "error": str(e), "downloaded_count": downloaded_count}

    def download_direct_url(
        self,
        url: str,
        dest_folder: Optional[Path] = None,
        save_metadata: bool = True
    ) -> Dict[str, Any]:
        """Download single TikTok video or slideshow from direct URL."""
        target_dir = dest_folder or (self.tiktok_dir / "direct_downloads")
        target_dir.mkdir(parents=True, exist_ok=True)
        outtmpl = str(target_dir / "%(upload_date>%Y%m%d)s_%(id)s_%(title).50B.%(ext)s")

        ydl_opts = {
            'outtmpl': outtmpl,
            'format': 'bestvideo+bestaudio/best',
            'writedescription': save_metadata,
            'writeinfojson': save_metadata,
            'quiet': True,
            'no_warnings': True,
        }

        if TIKTOK_COOKIES_TXT.exists():
            ydl_opts['cookiefile'] = str(TIKTOK_COOKIES_TXT)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return {
                    "success": True,
                    "title": info.get("title"),
                    "id": info.get("id"),
                    "uploader": info.get("uploader"),
                    "folder": str(target_dir)
                }
        except Exception as e:
            return {"success": False, "error": f"Failed to download TikTok URL: {str(e)}"}


tiktok_downloader = TikTokDownloader()
