import os
import re
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List, Generator
import requests
import instaloader
import yt_dlp

from core.models import InstagramDownloadRequest, MediaTypeFilter, Platform
from core.session_manager import session_manager, INSTAGRAM_COOKIES_TXT
from core.proxy_manager import proxy_manager

logger = logging.getLogger(__name__)


DOWNLOADS_DIR = Path(__file__).resolve().parent.parent / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)


class InstagramDownloader:
    """Downloader engine for Instagram media (posts, reels, stories, highlights, profile pic)."""

    def __init__(self, base_download_dir: Optional[Path] = None):
        self.base_dir = base_download_dir or DOWNLOADS_DIR
        self.ig_dir = self.base_dir / "instagram"
        self.ig_dir.mkdir(parents=True, exist_ok=True)

    def extract_username(self, input_str: str) -> str:
        """Clean username or extract username from URL."""
        s = input_str.strip()
        # Remove trailing slash
        s = s.rstrip("/")
        # If full URL
        if "instagram.com" in s:
            # Handle post / reel URLs
            match = re.search(r"instagram\.com/([^/?#]+)", s)
            if match:
                extracted = match.group(1)
                if extracted not in ["p", "reel", "reels", "stories", "tv", "explore"]:
                    return extracted
        # If starts with @
        if s.startswith("@"):
            return s[1:].strip()
        # If contains path or query
        if "/" in s:
            parts = [p for p in s.split("/") if p and "instagram.com" not in p]
            if parts:
                return parts[-1]
        return s

    def get_instaloader_instance(self) -> instaloader.Instaloader:
        """Create a fresh configured Instaloader instance with session and proxies loaded if available."""
        L = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            quiet=True,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        # Apply proxies if configured
        proxies = proxy_manager.get_requests_proxies()
        if proxies:
            L.context._session.proxies.update(proxies)

        # Apply cookies if present
        session_manager.apply_cookies_to_instaloader(L)
        return L

    def fetch_user_info(self, username_or_url: str) -> Dict[str, Any]:
        """Fetch profile information for preview."""
        username = self.extract_username(username_or_url)
        L = self.get_instaloader_instance()
        try:
            profile = instaloader.Profile.from_username(L.context, username)
            
            # Fast profile pic URL without slow extra API calls
            pic_url = ""
            if hasattr(profile, "_node") and isinstance(profile._node, dict):
                pic_url = profile._node.get("profile_pic_url_hd") or profile._node.get("profile_pic_url") or ""
            if not pic_url:
                try:
                    pic_url = profile.profile_pic_url
                except Exception:
                    pass

            local_pic = self.ig_dir / username / "profile_pic.jpg"
            if local_pic.exists():
                display_avatar_url = f"/media/instagram/{username}/profile_pic.jpg"
            elif pic_url:
                display_avatar_url = f"/api/proxy-image?url={requests.utils.quote(pic_url, safe='')}"
            else:
                display_avatar_url = ""

            return {
                "success": True,
                "username": profile.username,
                "full_name": profile.full_name,
                "biography": profile.biography,
                "followers": profile.followers,
                "followees": profile.followees,
                "mediacount": profile.mediacount,
                "is_private": profile.is_private,
                "is_verified": profile.is_verified,
                "profile_pic_url": display_avatar_url,
                "raw_profile_pic_url": pic_url,
                "external_url": profile.external_url,
                "has_highlight_reels": profile.has_highlight_reels,
            }
        except instaloader.exceptions.ProfileNotExistsException:
            return {"success": False, "error": f"Instagram profile '@{username}' does not exist."}
        except instaloader.exceptions.ConnectionException as ce:
            return {"success": False, "error": f"Instagram connection error: {str(ce)}"}
        except Exception as e:
            return {"success": False, "error": f"Failed to fetch profile: {str(e)}"}

    def download_url_to_file(self, url: str, dest_path: Path, session: Optional[requests.Session] = None) -> bool:
        """Download remote URL directly to destination file."""
        try:
            sess = session or requests.Session()
            if not session:
                proxies = proxy_manager.get_requests_proxies()
                if proxies:
                    sess.proxies.update(proxies)
            resp = sess.get(url, stream=True, timeout=30)
            if resp.status_code == 200:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with open(dest_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                return True
            else:
                logger.error(f"Download failed with status {resp.status_code} for URL {url}")
                return False
        except Exception as e:
            logger.error(f"Error writing file {dest_path}: {e}")
            return False

    def download_user(
        self,
        request: InstagramDownloadRequest,
        progress_callback: Optional[Callable[[int, int, str, float], None]] = None,
        log_callback: Optional[Callable[[str, str], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        """Download all selected media from given user."""
        username = self.extract_username(request.username_or_url)
        target_dir_name = request.custom_subfolder or username
        user_folder = self.ig_dir / target_dir_name
        user_folder.mkdir(parents=True, exist_ok=True)

        def log(level: str, msg: str):
            if log_callback:
                log_callback(level, msg)
            logger.info(f"[{level.upper()}] {msg}")

        def check_cancel():
            if is_cancelled and is_cancelled():
                log("warning", "Download cancelled by user.")
                raise InterruptedError("Download was cancelled.")

        def notify_progress(d_count: int, total: int, curr_item: str, pct: Optional[float] = None):
            if progress_callback:
                tot = max(total, d_count, 1)
                calculated_pct = pct if pct is not None else ((d_count / tot) * 100.0)
                progress_callback(d_count, tot, curr_item, min(calculated_pct, 100.0))

        log("info", f"Starting Instagram download for @{username}...")
        notify_progress(0, 0, f"Scanning @{username}...", 0.0)

        L = self.get_instaloader_instance()

        try:
            profile = instaloader.Profile.from_username(L.context, username)
        except Exception as e:
            log("error", f"Could not load profile @{username}: {str(e)}")
            return {"success": False, "error": str(e), "downloaded_count": 0}

        log("info", f"Profile found: {profile.full_name} ({profile.mediacount} total posts, {'Private' if profile.is_private else 'Public'})")

        # Handle private profiles not followed by current session
        if profile.is_private and not profile.followed_by_viewer:
            logged_in_user = session_manager.get_instagram_username() or "your account"
            log("warning", f"Account @{username} is private and not followed by {logged_in_user}.")
            
            downloaded_count = 0
            # Save profile avatar if requested
            if request.download_profile_pic:
                pic_path = user_folder / "profile_pic.jpg"
                if not pic_path.exists():
                    if self.download_url_to_file(profile.profile_pic_url, pic_path, L.context._session):
                        downloaded_count = 1
                else:
                    downloaded_count = 1
                notify_progress(downloaded_count, 1, "profile_pic.jpg", 100.0)

            log("info", f"Instagram servers do not send posts or stories for private accounts unless the follow request is accepted.")
            return {
                "success": True,
                "username": username,
                "downloaded_count": downloaded_count,
                "folder": str(user_folder),
                "message": f"Profile @{username} is private. Follow the account with @{logged_in_user} to unlock posts and stories."
            }

        downloaded_count = 0
        failed_count = 0
        total_estimated = profile.mediacount or 0
        if request.limit:
            total_estimated = min(total_estimated, request.limit)

        # 1. Download Profile Picture & Bio
        if request.download_profile_pic:
            try:
                log("info", "Saving profile avatar and metadata...")
                pic_path = user_folder / "profile_pic.jpg"
                if not pic_path.exists():
                    if self.download_url_to_file(profile.profile_pic_url, pic_path, L.context._session):
                        downloaded_count += 1
                else:
                    downloaded_count += 1

                notify_progress(downloaded_count, max(total_estimated, downloaded_count), "profile_pic.jpg")

                # Save user metadata json only if requested
                if request.save_metadata:
                    user_info = {
                        "username": profile.username,
                        "full_name": profile.full_name,
                        "biography": profile.biography,
                        "followers": profile.followers,
                        "followees": profile.followees,
                        "mediacount": profile.mediacount,
                        "is_private": profile.is_private,
                        "is_verified": profile.is_verified,
                        "external_url": profile.external_url,
                        "download_date": datetime.now().isoformat()
                    }
                    with open(user_folder / "user_info.json", "w", encoding="utf-8") as f:
                        json.dump(user_info, f, indent=2, ensure_ascii=False)
            except Exception as e:
                log("warning", f"Could not save profile info: {e}")

        # Date range filters
        date_from_dt = None
        date_to_dt = None
        if request.date_from:
            try:
                date_from_dt = datetime.fromisoformat(request.date_from)
            except Exception:
                pass
        if request.date_to:
            try:
                date_to_dt = datetime.fromisoformat(request.date_to)
            except Exception:
                pass

        # 2. Download Stories (if requested)
        if request.download_stories:
            check_cancel()
            log("info", "Checking for active stories...")
            try:
                stories_folder = user_folder / "stories"
                stories_folder.mkdir(exist_ok=True)
                stories_downloaded = 0
                
                # Try direct API first
                session_headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                    'X-IG-App-ID': '936619743392459',
                    'Referer': f'https://www.instagram.com/{username}/',
                }
                
                resp = L.context._session.get(
                    f"https://www.instagram.com/api/v1/feed/reels_media/?reel_ids={profile.userid}",
                    headers=session_headers,
                    timeout=15
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    reels_media = data.get("reels_media", [])
                    for reel in reels_media:
                        for it in reel.get("items", []):
                            check_cancel()
                            is_vid = bool(it.get("video_versions"))
                            if request.media_type == MediaTypeFilter.PHOTOS and is_vid:
                                continue
                            if request.media_type == MediaTypeFilter.VIDEOS and not is_vid:
                                continue
                            
                            url = it["video_versions"][0]["url"] if is_vid else it["image_versions2"]["candidates"][0]["url"]
                            taken_at = it.get("taken_at")
                            date_str = datetime.fromtimestamp(taken_at).strftime("%Y%m%d_%H%M%S") if taken_at else "story"
                            ext = ".mp4" if is_vid else ".jpg"
                            story_file = stories_folder / f"story_{date_str}_{it.get('id')}{ext}"
                            
                            if not story_file.exists():
                                if self.download_url_to_file(url, story_file, L.context._session):
                                    stories_downloaded += 1
                                    downloaded_count += 1
                                    log("success", f"Downloaded story: {story_file.name}")
                            else:
                                stories_downloaded += 1
                                downloaded_count += 1
                            
                            notify_progress(downloaded_count, max(total_estimated, downloaded_count), story_file.name)
                
                if stories_downloaded == 0:
                    log("info", "No active stories currently available (stories expire after 24h).")
                else:
                    log("success", f"Downloaded {stories_downloaded} active stories.")
            except Exception as e:
                log("warning", f"Stories download notice: {str(e)}")

        # 3. Download Highlights (if requested)
        if request.download_highlights:
            check_cancel()
            log("info", "Checking highlights...")
            try:
                highlights_folder = user_folder / "highlights"
                highlights_folder.mkdir(exist_ok=True)
                hl_count = 0
                
                session_headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                    'X-IG-App-ID': '936619743392459',
                    'Referer': f'https://www.instagram.com/{username}/',
                }
                
                # Fetch highlights tray
                resp = L.context._session.get(
                    f"https://www.instagram.com/api/v1/highlights/{profile.userid}/highlights_tray/",
                    headers=session_headers,
                    timeout=15
                )
                
                if resp.status_code == 200:
                    tray = resp.json().get("tray", [])
                    log("info", f"Found {len(tray)} highlight reels for @{username}...")
                    tray_total = sum(t.get("media_count", 0) for t in tray)
                    if tray_total > 0:
                        total_estimated += tray_total
                    
                    for reel_summary in tray:
                        check_cancel()
                        reel_id = reel_summary.get("id")
                        title = reel_summary.get("title", "")
                        clean_name = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip()
                        hl_title = clean_name if clean_name else f"highlight_{reel_id.replace('highlight:', '')}"
                        hl_subfolder = highlights_folder / hl_title
                        hl_subfolder.mkdir(parents=True, exist_ok=True)
                        
                        # Fetch items for this reel
                        reel_resp = L.context._session.get(
                            f"https://www.instagram.com/api/v1/feed/reels_media/?reel_ids={reel_id}",
                            headers=session_headers,
                            timeout=15
                        )
                        
                        if reel_resp.status_code == 200:
                            reels_media = reel_resp.json().get("reels_media", [])
                            for reel in reels_media:
                                for it in reel.get("items", []):
                                    check_cancel()
                                    is_vid = bool(it.get("video_versions"))
                                    if request.media_type == MediaTypeFilter.PHOTOS and is_vid:
                                        continue
                                    if request.media_type == MediaTypeFilter.VIDEOS and not is_vid:
                                        continue
                                    
                                    url = it["video_versions"][0]["url"] if is_vid else it["image_versions2"]["candidates"][0]["url"]
                                    taken_at = it.get("taken_at")
                                    date_str = datetime.fromtimestamp(taken_at).strftime("%Y%m%d_%H%M%S") if taken_at else "hl"
                                    ext = ".mp4" if is_vid else ".jpg"
                                    hl_file = hl_subfolder / f"hl_{date_str}_{it.get('id')}{ext}"
                                    
                                    if not hl_file.exists():
                                        if self.download_url_to_file(url, hl_file, L.context._session):
                                            hl_count += 1
                                            downloaded_count += 1
                                            log("success", f"Saved highlight [{hl_title}]: {hl_file.name}")
                                    else:
                                        hl_count += 1
                                        downloaded_count += 1

                                    notify_progress(downloaded_count, max(total_estimated, downloaded_count), hl_file.name)
                    
                    log("success", f"Downloaded {hl_count} items from highlights.")
                else:
                    log("warning", f"Could not retrieve highlights tray (HTTP {resp.status_code}).")
            except Exception as e:
                log("warning", f"Highlights download notice: {str(e)}")

        # 4. Download Posts & Reels
        if request.download_posts or request.download_reels:
            log("info", f"Fetching posts for @{username} (Limit: {request.limit or 'All'})...")
            posts_processed = 0
            
            session_headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'X-IG-App-ID': '936619743392459',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': f'https://www.instagram.com/{username}/',
            }

            max_id = ""
            has_more = True

            while has_more:
                check_cancel()
                if request.limit and posts_processed >= request.limit:
                    break

                req_url = f"https://www.instagram.com/api/v1/feed/user/{profile.userid}/"
                if max_id:
                    req_url += f"?max_id={max_id}"

                try:
                    feed_resp = L.context._session.get(req_url, headers=session_headers, timeout=15)
                    if feed_resp.status_code != 200:
                        log("warning", f"Feed endpoint returned HTTP {feed_resp.status_code}")
                        break

                    feed_data = feed_resp.json()
                    items = feed_data.get("items", [])
                    if not items:
                        if posts_processed == 0:
                            log("info", f"No feed posts found for @{username}.")
                        break

                    for it in items:
                        check_cancel()
                        if request.limit and posts_processed >= request.limit:
                            break

                        taken_at = it.get("taken_at")
                        post_date = datetime.fromtimestamp(taken_at) if taken_at else datetime.now()

                        if date_from_dt and post_date < date_from_dt:
                            has_more = False
                            break
                        if date_to_dt and post_date > date_to_dt:
                            continue

                        code = it.get("code") or str(it.get("pk", "item"))
                        media_type = it.get("media_type")  # 1=photo, 2=video, 8=carousel
                        is_video = media_type == 2
                        date_prefix = post_date.strftime("%Y%m%d_%H%M%S")
                        posts_processed += 1

                        # Save caption only if requested
                        caption_text = it.get("caption", {}).get("text", "") if it.get("caption") else ""
                        if request.save_captions and caption_text:
                            cap_file = user_folder / f"{date_prefix}_{code}_caption.txt"
                            if not cap_file.exists():
                                with open(cap_file, "w", encoding="utf-8") as f:
                                    f.write(caption_text)

                        # Handle Carousel
                        if media_type == 8:
                            carousel_media = it.get("carousel_media", [])
                            for idx, sub in enumerate(carousel_media, 1):
                                check_cancel()
                                sub_is_vid = bool(sub.get("video_versions"))
                                if request.media_type == MediaTypeFilter.PHOTOS and sub_is_vid:
                                    continue
                                if request.media_type == MediaTypeFilter.VIDEOS and not sub_is_vid:
                                    continue

                                sub_url = sub["video_versions"][0]["url"] if sub_is_vid else sub["image_versions2"]["candidates"][0]["url"]
                                ext = ".mp4" if sub_is_vid else ".jpg"
                                media_filename = f"{date_prefix}_{code}_{idx}{ext}"
                                dest_file = user_folder / media_filename

                                if not dest_file.exists():
                                    if self.download_url_to_file(sub_url, dest_file, L.context._session):
                                        downloaded_count += 1
                                        log("success", f"Saved carousel item: {media_filename}")
                                    else:
                                        failed_count += 1
                                else:
                                    downloaded_count += 1

                                notify_progress(downloaded_count, max(total_estimated, downloaded_count), media_filename)
                        else:
                            # Single photo or video
                            if request.media_type == MediaTypeFilter.PHOTOS and is_video:
                                continue
                            if request.media_type == MediaTypeFilter.VIDEOS and not is_video:
                                continue

                            url = it["video_versions"][0]["url"] if is_video else it["image_versions2"]["candidates"][0]["url"]
                            ext = ".mp4" if is_video else ".jpg"
                            media_filename = f"{date_prefix}_{code}{ext}"
                            dest_file = user_folder / media_filename

                            if not dest_file.exists():
                                if self.download_url_to_file(url, dest_file, L.context._session):
                                    downloaded_count += 1
                                    log("success", f"Saved post: {media_filename}")
                                else:
                                    failed_count += 1
                            else:
                                downloaded_count += 1

                            notify_progress(downloaded_count, max(total_estimated, downloaded_count), media_filename)

                        time.sleep(0.1)

                    max_id = feed_data.get("next_max_id")
                    has_more = bool(feed_data.get("more_available") and max_id)

                except Exception as fe:
                    log("warning", f"Feed notice: {str(fe)}")
                    break

        # 5. Download Tagged Posts (if requested)
        if request.download_tagged:
            check_cancel()
            log("info", f"Checking tagged posts for @{username}...")
            try:
                tagged_folder = user_folder / "tagged"
                tagged_folder.mkdir(exist_ok=True)
                tagged_count = 0

                session_headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                    'X-IG-App-ID': '936619743392459',
                    'Referer': f'https://www.instagram.com/{username}/',
                }

                resp = L.context._session.get(
                    f"https://www.instagram.com/api/v1/usertags/{profile.userid}/feed/",
                    headers=session_headers,
                    timeout=15
                )

                if resp.status_code == 200:
                    tagged_items = resp.json().get("items", [])
                    for it in tagged_items:
                        check_cancel()
                        code = it.get("code") or str(it.get("pk", "tagged"))
                        is_vid = bool(it.get("video_versions"))
                        if request.media_type == MediaTypeFilter.PHOTOS and is_vid:
                            continue
                        if request.media_type == MediaTypeFilter.VIDEOS and not is_vid:
                            continue

                        url = it["video_versions"][0]["url"] if is_vid else it["image_versions2"]["candidates"][0]["url"]
                        taken_at = it.get("taken_at")
                        date_str = datetime.fromtimestamp(taken_at).strftime("%Y%m%d_%H%M%S") if taken_at else "tagged"
                        ext = ".mp4" if is_vid else ".jpg"
                        tagged_file = tagged_folder / f"tagged_{date_str}_{code}{ext}"

                        if not tagged_file.exists():
                            if self.download_url_to_file(url, tagged_file, L.context._session):
                                tagged_count += 1
                                downloaded_count += 1
                                log("success", f"Saved tagged post: {tagged_file.name}")
                        else:
                            tagged_count += 1
                            downloaded_count += 1

                        notify_progress(downloaded_count, max(total_estimated, downloaded_count), tagged_file.name)

                    if tagged_count > 0:
                        log("success", f"Downloaded {tagged_count} tagged posts.")
                    else:
                        log("info", "No public tagged posts found or available.")
                else:
                    log("info", f"Tagged feed returned HTTP {resp.status_code}.")
            except Exception as e:
                log("warning", f"Tagged posts notice: {str(e)}")

        if downloaded_count == 0 and profile.mediacount == 0:
            if profile.has_highlight_reels and not request.download_highlights:
                log("info", f"Note: @{username} has Highlights available. Enable 'Highlights' to download them.")

        notify_progress(downloaded_count, max(total_estimated, downloaded_count, 1), "Completed", 100.0)
        log("success", f"Completed Instagram download for @{username}! Total files saved: {downloaded_count}")
        return {
            "success": True,
            "username": username,
            "downloaded_count": downloaded_count,
            "failed_count": failed_count,
            "folder": str(user_folder)
        }

    def download_direct_post(
        self,
        url_or_shortcode: str,
        dest_folder: Optional[Path] = None,
        save_metadata: bool = True
    ) -> Dict[str, Any]:
        """Download a single Instagram post or reel from direct URL with multi-engine fallback."""
        # Extract shortcode or format URL
        match = re.search(r"instagram\.com/(?:p|reel|reels|tv)/([^/?#]+)", url_or_shortcode)
        shortcode = match.group(1) if match else url_or_shortcode.strip()
        direct_url = url_or_shortcode if url_or_shortcode.startswith("http") else f"https://www.instagram.com/p/{shortcode}/"
        
        target_dir = dest_folder or (self.ig_dir / "direct_downloads")
        target_dir.mkdir(parents=True, exist_ok=True)

        L = self.get_instaloader_instance()
        try:
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            date_prefix = post.date_utc.strftime("%Y%m%d_%H%M%S")
            saved_files = []

            if post.typename == "GraphSidecar":
                idx = 1
                for node in post.get_sidecar_nodes():
                    ext = ".mp4" if node.is_video else ".jpg"
                    fname = f"{date_prefix}_{shortcode}_{idx}{ext}"
                    dest = target_dir / fname
                    url = node.video_url if node.is_video else node.display_url
                    if self.download_url_to_file(url, dest, L.context._session):
                        saved_files.append(str(dest))
                    idx += 1
            else:
                ext = ".mp4" if post.is_video else ".jpg"
                fname = f"{date_prefix}_{shortcode}{ext}"
                dest = target_dir / fname
                url = post.video_url if post.is_video else post.url
                if self.download_url_to_file(url, dest, L.context._session):
                    saved_files.append(str(dest))

            if save_metadata:
                meta_file = target_dir / f"{date_prefix}_{shortcode}_meta.json"
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "shortcode": shortcode,
                        "owner": post.owner_username,
                        "date_utc": post.date_utc.isoformat(),
                        "caption": post.caption or "",
                        "likes": post.likes,
                        "comments": post.comments,
                    }, f, indent=2, ensure_ascii=False)

            return {"success": True, "saved_files": saved_files, "shortcode": shortcode}
        except Exception as instaloader_err:
            logger.warning(f"Instaloader engine notice for {shortcode}: {instaloader_err}. Trying yt-dlp fallback...")
            # Fallback to yt-dlp engine
            try:
                outtmpl = str(target_dir / "%(upload_date>%Y%m%d)s_%(id)s_%(title).50B.%(ext)s")
                ydl_opts = {
                    'outtmpl': outtmpl,
                    'format': 'bestvideo+bestaudio/best',
                    'writedescription': save_metadata,
                    'writeinfojson': save_metadata,
                    'quiet': True,
                    'no_warnings': True,
                }
                if INSTAGRAM_COOKIES_TXT.exists():
                    ydl_opts['cookiefile'] = str(INSTAGRAM_COOKIES_TXT)

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(direct_url, download=True)
                    return {
                        "success": True,
                        "title": info.get("title") or shortcode,
                        "id": info.get("id") or shortcode,
                        "folder": str(target_dir),
                        "shortcode": shortcode,
                        "engine": "yt-dlp"
                    }
            except Exception as ytdl_err:
                return {
                    "success": False,
                    "error": f"Download failed (Instaloader: {str(instaloader_err)} | Fallback: {str(ytdl_err)})"
                }


instagram_downloader = InstagramDownloader()

