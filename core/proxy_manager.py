import os
import json
import logging
import random
import time
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
import requests

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PROXIES_FILE = DATA_DIR / "proxies.json"


class ProxyManager:
    """Manages proxy pool, validation, automatic rotation on rate limits / blocks, and format conversion."""

    def __init__(self):
        self.proxies: List[str] = []
        self.current_index: int = 0
        self.enabled: bool = True
        self.failed_proxies: Dict[str, float] = {}  # proxy -> timestamp
        self._load_proxies()

    def _load_proxies(self):
        """Load proxies from data/proxies.json or environment."""
        if PROXIES_FILE.exists():
            try:
                with open(PROXIES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.proxies = [p.strip() for p in data if p and isinstance(p, str)]
                    elif isinstance(data, dict):
                        self.proxies = data.get("proxies", [])
                        self.enabled = data.get("enabled", True)
            except Exception as e:
                logger.error(f"Failed to load proxies from {PROXIES_FILE}: {e}")

        # Also check environment variable PROXY_POOL or HTTP_PROXY
        env_pool = os.environ.get("PROXY_POOL", "")
        if env_pool:
            for p in env_pool.split(","):
                clean = p.strip()
                if clean and clean not in self.proxies:
                    self.proxies.append(clean)

    def _save_proxies(self):
        """Save current proxy list to data/proxies.json."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(PROXIES_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "enabled": self.enabled,
                    "proxies": self.proxies,
                    "count": len(self.proxies)
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save proxies: {e}")

    def add_proxy(self, proxy_url: str) -> bool:
        """Add a proxy to the pool (format: http://host:port, socks5://host:port, http://user:pass@host:port)."""
        clean = proxy_url.strip()
        if not clean:
            return False
        if not (clean.startswith("http://") or clean.startswith("https://") or clean.startswith("socks5://") or clean.startswith("socks4://")):
            clean = f"http://{clean}"
        if clean not in self.proxies:
            self.proxies.append(clean)
            self._save_proxies()
            return True
        return False

    def remove_proxy(self, proxy_url: str) -> bool:
        """Remove a proxy from the pool."""
        clean = proxy_url.strip()
        if clean in self.proxies:
            self.proxies.remove(clean)
            self._save_proxies()
            return True
        return False

    def clear_proxies(self):
        """Clear all proxies."""
        self.proxies = []
        self._save_proxies()

    def set_enabled(self, enabled: bool):
        """Enable or disable proxy usage."""
        self.enabled = enabled
        self._save_proxies()

    def get_current_proxy(self) -> Optional[str]:
        """Get the current active proxy from the pool if available and enabled."""
        if not self.enabled or not self.proxies:
            return None
        return self.proxies[self.current_index % len(self.proxies)]

    def rotate_proxy(self) -> Optional[str]:
        """Rotate to the next proxy in the pool and return it."""
        if not self.proxies:
            return None
        self.current_index = (self.current_index + 1) % len(self.proxies)
        current = self.proxies[self.current_index]
        logger.info(f"Rotated to proxy: {self._mask_proxy(current)} ({self.current_index + 1}/{len(self.proxies)})")
        return current

    def mark_failed(self, proxy_url: str):
        """Mark a proxy as failed and automatically rotate to the next one."""
        self.failed_proxies[proxy_url] = time.time()
        logger.warning(f"Proxy marked failed: {self._mask_proxy(proxy_url)}. Auto-rotating...")
        self.rotate_proxy()

    def get_requests_proxies(self) -> Optional[Dict[str, str]]:
        """Return proxy dictionary formatted for requests.Session (or None if no proxy)."""
        proxy = self.get_current_proxy()
        if not proxy:
            return None
        return {
            "http": proxy,
            "https": proxy
        }

    def get_ytdl_proxy(self) -> Optional[str]:
        """Return proxy string formatted for yt-dlp."""
        return self.get_current_proxy()

    def test_proxy(self, proxy_url: str, timeout: int = 6) -> Tuple[bool, str, Optional[float]]:
        """Test a proxy against public IP echo endpoints."""
        clean = proxy_url.strip()
        if not (clean.startswith("http://") or clean.startswith("https://") or clean.startswith("socks5://") or clean.startswith("socks4://")):
            clean = f"http://{clean}"

        proxies = {"http": clean, "https": clean}
        t0 = time.time()
        try:
            resp = requests.get("https://api.ipify.org?format=json", proxies=proxies, timeout=timeout)
            duration = round(time.time() - t0, 2)
            if resp.status_code == 200:
                ip = resp.json().get("ip", "unknown")
                return True, f"Working (IP: {ip}, Latency: {duration}s)", duration
            return False, f"HTTP {resp.status_code}", None
        except Exception as e:
            return False, str(e), None

    def fetch_free_proxies(self, max_working: int = 8, timeout: int = 3) -> Dict[str, Any]:
        """Scrape public proxy aggregators and verify candidates in parallel."""
        from concurrent.futures import ThreadPoolExecutor
        
        sources = [
            ("http", "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"),
            ("socks5", "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt"),
            ("http", "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt"),
            ("socks5", "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt"),
            ("http", "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt"),
            ("socks5", "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt"),
        ]

        candidates = []
        for proto, u in sources:
            try:
                r = requests.get(u, timeout=4)
                if r.status_code == 200:
                    lines = [l.strip() for l in r.text.splitlines() if l.strip() and not l.startswith("#")]
                    for l in lines[:80]:
                        formatted = l if "://" in l else f"{proto}://{l}"
                        if formatted not in candidates:
                            candidates.append(formatted)
            except Exception as e:
                logger.warning(f"Failed to fetch proxy list from {u}: {e}")

        if not candidates:
            return {"success": False, "message": "No proxy candidates could be fetched from public sources.", "added": 0}

        random.shuffle(candidates)

        def _check_candidate(p: str):
            try:
                t0 = time.time()
                r = requests.get("http://httpbin.org/ip", proxies={"http": p, "https": p}, timeout=timeout)
                if r.status_code == 200:
                    lat = round(time.time() - t0, 2)
                    return True, p, lat, r.json().get("origin")
            except Exception:
                pass
            return False, p, None, None

        verified = []
        with ThreadPoolExecutor(max_workers=25) as ex:
            for ok, p, lat, ip in ex.map(_check_candidate, candidates[:120]):
                if ok:
                    verified.append({"url": p, "latency": lat, "origin": ip})
                    if len(verified) >= max_working:
                        break

        verified.sort(key=lambda x: x["latency"])
        
        added = 0
        for item in verified:
            if self.add_proxy(item["url"]):
                added += 1

        self.set_enabled(True)

        return {
            "success": len(verified) > 0,
            "found_candidates": len(candidates),
            "verified_working": len(verified),
            "added_new": added,
            "pool_total": len(self.proxies),
            "proxies": verified
        }

    def get_status(self) -> Dict[str, Any]:
        """Get summary of proxy pool status."""
        current = self.get_current_proxy()
        return {
            "enabled": self.enabled,
            "total_count": len(self.proxies),
            "current_proxy": self._mask_proxy(current) if current else None,
            "proxies": [self._mask_proxy(p) for p in self.proxies],
            "raw_proxies": self.proxies
        }

    @staticmethod
    def _mask_proxy(proxy_url: str) -> str:
        """Mask credentials in proxy URL for display."""
        if not proxy_url:
            return ""
        if "@" in proxy_url:
            prefix, rest = proxy_url.split("@", 1)
            scheme = prefix.split("://")[0] if "://" in prefix else "http"
            return f"{scheme}://***:***@{rest}"
        return proxy_url


proxy_manager = ProxyManager()
