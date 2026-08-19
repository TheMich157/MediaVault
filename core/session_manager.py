import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import requests
import instaloader
import yt_dlp.cookies
from http.cookiejar import MozillaCookieJar, Cookie

logger = logging.getLogger(__name__)

SESSION_DIR = Path(__file__).resolve().parent.parent / "data" / "sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

INSTAGRAM_SESSION_FILE = SESSION_DIR / "instagram_session.json"
INSTAGRAM_COOKIES_TXT = SESSION_DIR / "instagram_cookies.txt"
TIKTOK_COOKIES_TXT = SESSION_DIR / "tiktok_cookies.txt"


class SessionManager:
    """Manages Instagram and TikTok authentication sessions and cookies."""

    def __init__(self):
        self.session_dir = SESSION_DIR

    def get_instagram_username(self) -> str:
        """Get saved Instagram username."""
        if INSTAGRAM_SESSION_FILE.exists():
            try:
                with open(INSTAGRAM_SESSION_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("username", "")
            except Exception:
                pass
        return ""

    def get_instagram_cookies(self) -> Dict[str, str]:
        """Load stored Instagram cookies as a dictionary."""
        if INSTAGRAM_SESSION_FILE.exists():
            try:
                with open(INSTAGRAM_SESSION_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("cookies", {})
            except Exception as e:
                logger.error(f"Error loading Instagram session file: {e}")
        return {}

    def save_instagram_cookies(self, cookies: Dict[str, str], username: Optional[str] = None) -> bool:
        """Save Instagram cookies and convert to Netscape cookies.txt."""
        try:
            payload = {
                "username": username or "",
                "cookies": cookies,
                "saved_at": requests.utils.default_user_agent()
            }
            with open(INSTAGRAM_SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)

            # Also generate standard Netscape cookies.txt
            self._write_netscape_cookies(cookies, ".instagram.com", INSTAGRAM_COOKIES_TXT)
            return True
        except Exception as e:
            logger.error(f"Error saving Instagram cookies: {e}")
            return False

    def clear_instagram_session(self) -> bool:
        """Remove stored Instagram session files."""
        try:
            if INSTAGRAM_SESSION_FILE.exists():
                INSTAGRAM_SESSION_FILE.unlink()
            if INSTAGRAM_COOKIES_TXT.exists():
                INSTAGRAM_COOKIES_TXT.unlink()
            return True
        except Exception as e:
            logger.error(f"Error clearing Instagram session: {e}")
            return False

    def parse_raw_cookie_string(self, raw_string: str) -> Dict[str, str]:
        """Parse raw cookie string like 'sessionid=123; ds_user_id=456' or full header."""
        cookies = {}
        # Remove prefix if user pasted 'Cookie: '
        clean_str = raw_string.strip()
        if clean_str.lower().startswith("cookie:"):
            clean_str = clean_str[7:].strip()

        # Split by semicolon or newline
        pairs = [p.strip() for p in clean_str.replace("\n", ";").split(";") if p.strip()]
        for pair in pairs:
            if "=" in pair:
                k, v = pair.split("=", 1)
                k = k.strip()
                v = v.strip()
                if k:
                    cookies[k] = v
        return cookies

    def apply_cookies_to_instaloader(self, L: instaloader.Instaloader) -> Tuple[bool, Optional[str]]:
        """Apply stored Instagram cookies to an Instaloader instance."""
        cookies = self.get_instagram_cookies()
        if not cookies:
            return False, "No stored session cookies found"

        sessionid = cookies.get("sessionid")
        if not sessionid:
            return False, "Missing 'sessionid' in stored cookies"

        # Apply cookies into requests session
        for k, v in cookies.items():
            L.context._session.cookies.set(k, v, domain=".instagram.com")
            L.context._session.cookies.set(k, v, domain="instagram.com")

        # Set username on context so Instaloader knows it is authenticated
        saved_user = self.get_instagram_username() or cookies.get("ds_user_id", "authenticated_user")
        L.context.username = saved_user
        return True, saved_user

    def verify_instagram_session(self, cookies: Dict[str, str]) -> Dict[str, Any]:
        """Verify Instagram cookies against Instagram API and return user profile details."""
        if not cookies or "sessionid" not in cookies:
            return {"valid": False, "error": "Missing 'sessionid' in cookies"}

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "X-IG-App-ID": "936619743392459",
            "Referer": "https://www.instagram.com/",
        }

        session = requests.Session()
        for k, v in cookies.items():
            session.cookies.set(k, v, domain=".instagram.com")

        try:
            # Query web profile info / viewer endpoint
            resp = session.get(
                "https://www.instagram.com/api/v1/users/web_profile_info/?username=instagram",
                headers=headers,
                timeout=10
            )
            
            # Check viewer endpoint or current user if accessible
            status = resp.status_code
            if status in [200, 302]:
                # Valid session!
                ds_user_id = cookies.get("ds_user_id", "Logged in")
                return {
                    "valid": True,
                    "status_code": status,
                    "user_id": ds_user_id,
                    "message": "Session is active and valid!"
                }
            elif status == 401:
                return {"valid": False, "error": "Instagram session is expired or invalid (HTTP 401)."}
            else:
                # Still might be valid despite rate limit / endpoint change
                return {
                    "valid": True,
                    "status_code": status,
                    "message": f"Session loaded (status {status})."
                }
        except Exception as e:
            return {"valid": True, "warning": f"Could not contact verification endpoint: {str(e)}"}

    def auto_extract_from_browser(self, browser_name: str) -> Tuple[bool, Dict[str, Any]]:
        """Extract cookies from a specified browser using yt-dlp cookie engine."""
        supported = [b.lower() for b in yt_dlp.cookies.SUPPORTED_BROWSERS]
        browser_name = browser_name.lower().strip()
        
        if browser_name not in supported:
            return False, {"error": f"Browser '{browser_name}' not supported. Supported: {', '.join(supported)}"}

        try:
            cookie_jar = yt_dlp.cookies.extract_cookies_from_browser(browser_name)
            if not cookie_jar:
                return False, {"error": f"No cookies found in {browser_name.capitalize()}."}

            ig_cookies = {}
            for cookie in cookie_jar:
                domain = getattr(cookie, "domain", "")
                if "instagram.com" in domain:
                    ig_cookies[cookie.name] = cookie.value

            if not ig_cookies or "sessionid" not in ig_cookies:
                return False, {
                    "error": f"No active Instagram login session found in {browser_name.capitalize()}. Please make sure you are logged into instagram.com in {browser_name.capitalize()}."
                }

            # Save the found cookies
            self.save_instagram_cookies(ig_cookies)
            verification = self.verify_instagram_session(ig_cookies)
            return True, {
                "browser": browser_name,
                "cookies_found": len(ig_cookies),
                "has_sessionid": "sessionid" in ig_cookies,
                "ds_user_id": ig_cookies.get("ds_user_id"),
                "verification": verification,
                "message": f"Successfully extracted Instagram session from {browser_name.capitalize()}!"
            }

        except Exception as e:
            err_msg = str(e)
            if "Operation not permitted" in err_msg or "Permission denied" in err_msg:
                return False, {
                    "error": f"macOS security blocked access to {browser_name.capitalize()} cookies. (You can paste cookies directly or grant Full Disk Access to Terminal)."
                }
            elif "could not find" in err_msg.lower():
                return False, {
                    "error": f"No profile database found for {browser_name.capitalize()}."
                }
            return False, {"error": f"Error extracting from {browser_name.capitalize()}: {err_msg}"}

    def scan_all_browsers_for_instagram(self) -> Dict[str, Any]:
        """Scan all installed browsers to find Instagram cookies automatically."""
        browsers_to_try = ["chrome", "brave", "safari", "firefox", "edge", "arc", "opera", "vivaldi", "chromium"]
        results = []
        
        for b in browsers_to_try:
            success, info = self.auto_extract_from_browser(b)
            if success:
                return {
                    "success": True,
                    "browser": b,
                    "details": info
                }
            results.append({"browser": b, "result": info})

        return {
            "success": False,
            "message": "No active Instagram session could be automatically extracted from installed browsers.",
            "attempts": results
        }

    def get_tiktok_cookies(self) -> Dict[str, str]:
        """Load stored TikTok cookies."""
        if TIKTOK_COOKIES_TXT.exists():
            return {"status": "present"}
        return {}

    def save_tiktok_cookies(self, cookies: Dict[str, str]) -> bool:
        """Save TikTok cookies in Netscape cookies.txt format for yt-dlp."""
        try:
            self._write_netscape_cookies(cookies, ".tiktok.com", TIKTOK_COOKIES_TXT)
            return True
        except Exception as e:
            logger.error(f"Error saving TikTok cookies: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Return current session status."""
        cookies = self.get_instagram_cookies()
        has_session = bool(cookies and "sessionid" in cookies)
        return {
            "has_instagram_session": has_session,
            "instagram_user_id": cookies.get("ds_user_id") if has_session else None,
            "cookies_count": len(cookies),
            "cookies_file_exists": INSTAGRAM_COOKIES_TXT.exists(),
            "has_tiktok_session": TIKTOK_COOKIES_TXT.exists(),
        }

    def parse_netscape_cookie_file(self, file_content: str, domain_filter: str = "instagram.com") -> Dict[str, str]:
        """Parse Netscape HTTP Cookie File format into dictionary."""
        cookies = {}
        for line in file_content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 7:
                domain, _, _, _, _, name, value = parts[:7]
                if domain_filter in domain.lower():
                    cookies[name] = value
        return cookies

    def parse_json_cookie_file(self, file_content: str, domain_filter: str = "instagram.com") -> Dict[str, str]:
        """Parse JSON cookies array into dictionary."""
        cookies = {}
        try:
            data = json.loads(file_content)
            if isinstance(data, list):
                for item in data:
                    domain = item.get("domain", "")
                    if domain_filter in domain.lower():
                        name = item.get("name")
                        value = item.get("value")
                        if name and value:
                            cookies[name] = value
            elif isinstance(data, dict):
                # If dictionary of key-values or object containing 'cookies'
                if "cookies" in data and isinstance(data["cookies"], dict):
                    cookies = data["cookies"]
                else:
                    cookies = {k: str(v) for k, v in data.items()}
        except Exception as e:
            logger.warning(f"JSON cookie parse failed: {e}")
        return cookies

    def parse_any_cookie_input(self, raw_input: str, domain_filter: str = "instagram.com") -> Dict[str, str]:
        """Auto-detect format (JSON, Netscape, or key-value string) and parse."""
        trimmed = raw_input.strip()
        if trimmed.startswith("[") or trimmed.startswith("{"):
            parsed = self.parse_json_cookie_file(trimmed, domain_filter)
            if parsed:
                return parsed

        if "\t" in trimmed and ("TRUE" in trimmed or "FALSE" in trimmed):
            parsed = self.parse_netscape_cookie_file(trimmed, domain_filter)
            if parsed:
                return parsed

        return self.parse_raw_cookie_string(trimmed)

    def _write_netscape_cookies(self, cookies: Dict[str, str], domain: str, output_path: Path):
        """Write cookies dictionary in standard Netscape format for yt-dlp/curl."""
        lines = [
            "# Netscape HTTP Cookie File",
            "# http://curl.haxx.se/rfc/cookie_spec.html",
            "# This file was generated by Insta and TikTok Media Downloader",
            ""
        ]
        # Common expiration 1 year from now
        expires = "2147483647"
        for name, val in cookies.items():
            lines.append(f"{domain}\tTRUE\t/\tTRUE\t{expires}\t{name}\t{val}")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")



session_manager = SessionManager()
