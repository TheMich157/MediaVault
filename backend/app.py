import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, UploadFile, File, Form, Query
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.models import (
    InstagramDownloadRequest,
    TikTokDownloadRequest,
    DirectUrlDownloadRequest,
    MultiDownloadRequest,
    TerminalCommandRequest,
    TerminalCommandResponse,
    SessionCookieRequest,
    Platform,
    UserProfileGallery,
    MediaItem,
    DeleteItemRequest,
    BatchDeleteRequest,
    BatchZipRequest,
    StorageInfo
)

from core.session_manager import session_manager
from core.proxy_manager import proxy_manager
from core.instagram_downloader import instagram_downloader
from core.tiktok_downloader import tiktok_downloader
from core.job_manager import job_manager
from core.zip_exporter import zip_exporter
from backend.sse import sse_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("media_downloader")

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    job_manager.set_loop(asyncio.get_running_loop())
    logger.info("Server started, job manager event loop registered.")
    yield

app = FastAPI(title="Insta & TikTok Media Downloader", version="1.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------
# System & Event Endpoints
# -------------------------------------------------------------
@app.get("/api/status")
async def get_system_status():
    session_status = session_manager.get_status()
    total_downloads = 0
    if DOWNLOADS_DIR.exists():
        total_downloads = sum(len(files) for _, _, files in os.walk(DOWNLOADS_DIR))
    
    return {
        "status": "online",
        "downloads_dir": str(DOWNLOADS_DIR),
        "total_downloaded_files": total_downloads,
        "session": session_status,
        "active_jobs_count": len([j for j in job_manager.list_jobs().values() if j.status == "running"])
    }


@app.get("/api/system/storage")
async def get_storage_stats():
    """Return disk space, total storage consumed, and platform breakdown."""
    import shutil
    total_bytes = 0
    total_files = 0
    users_set = set()
    breakdowns: List[Dict[str, Any]] = []

    for platform_str in ["instagram", "tiktok"]:
        p_dir = DOWNLOADS_DIR / platform_str
        p_size = 0
        p_count = 0
        if p_dir.exists():
            for root, _, files in os.walk(p_dir):
                for f in files:
                    if f.startswith("."):
                        continue
                    fp = Path(root) / f
                    try:
                        p_size += fp.stat().st_size
                        p_count += 1
                    except Exception:
                        pass
            # Count user folders
            for uf in p_dir.iterdir():
                if uf.is_dir() and not uf.name.startswith("."):
                    users_set.add(f"{platform_str}:{uf.name}")

        breakdowns.append({
            "platform": platform_str,
            "items_count": p_count,
            "size_bytes": p_size,
            "size_human": _human_filesize(p_size)
        })
        total_bytes += p_size
        total_files += p_count

    # Disk usage
    total_disk, used_disk, free_disk = shutil.disk_usage(DOWNLOADS_DIR)

    return {
        "total_size_bytes": total_bytes,
        "total_size_human": _human_filesize(total_bytes),
        "total_files_count": total_files,
        "total_users_count": len(users_set),
        "free_disk_space_bytes": free_disk,
        "free_disk_space_human": _human_filesize(free_disk),
        "platforms": breakdowns
    }



@app.get("/api/events")
async def event_stream(request: Request):
    """Server-Sent Events endpoint for real-time progress and logs."""
    return StreamingResponse(
        sse_manager.event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# -------------------------------------------------------------
# Download Job Triggers & Batch Multi-Profile
# -------------------------------------------------------------
@app.post("/api/download/instagram")
async def start_instagram_download(request: InstagramDownloadRequest):
    raw_target = request.username_or_url.strip()
    if not raw_target:
        raise HTTPException(status_code=400, detail="Username or Profile URL is required.")

    # Check if multiple targets separated by comma, space, or newline
    delimiters = [",", "\n", ";"]
    targets = [raw_target]
    for d in delimiters:
        if d in raw_target:
            targets = [t.strip() for t in raw_target.split(d) if t.strip()]
            break

    if len(targets) > 1:
        job_ids = job_manager.create_batch_jobs(
            targets=targets,
            default_platform=Platform.INSTAGRAM,
            limit=request.limit,
            media_type=request.media_type,
            download_posts=request.download_posts,
            download_reels=request.download_reels,
            download_stories=request.download_stories,
            download_highlights=request.download_highlights,
            download_tagged=request.download_tagged,
            save_captions=request.save_captions,
            save_metadata=request.save_metadata
        )
        return {
            "success": True,
            "job_ids": job_ids,
            "job_id": job_ids[0] if job_ids else None,
            "message": f"Queued {len(job_ids)} Instagram download jobs."
        }

    job_id = job_manager.create_instagram_job(request)
    return {"success": True, "job_id": job_id, "job_ids": [job_id], "message": "Instagram download job queued."}


@app.post("/api/download/tiktok")
async def start_tiktok_download(request: TikTokDownloadRequest):
    raw_target = request.username_or_url.strip()
    if not raw_target:
        raise HTTPException(status_code=400, detail="Username or Profile URL is required.")

    delimiters = [",", "\n", ";"]
    targets = [raw_target]
    for d in delimiters:
        if d in raw_target:
            targets = [t.strip() for t in raw_target.split(d) if t.strip()]
            break

    if len(targets) > 1:
        job_ids = job_manager.create_batch_jobs(
            targets=targets,
            default_platform=Platform.TIKTOK,
            limit=request.limit,
            download_videos=request.download_videos,
            download_slideshows=request.download_slideshows,
            download_audio=request.download_audio,
            save_metadata=request.save_metadata
        )
        return {
            "success": True,
            "job_ids": job_ids,
            "job_id": job_ids[0] if job_ids else None,
            "message": f"Queued {len(job_ids)} TikTok download jobs."
        }

    job_id = job_manager.create_tiktok_job(request)
    return {"success": True, "job_id": job_id, "job_ids": [job_id], "message": "TikTok download job queued."}


@app.post("/api/download/batch")
async def start_batch_download(request: MultiDownloadRequest):
    """Start concurrent downloads across multiple targets (Instagram, TikTok, Direct URLs)."""
    if not request.targets:
        raise HTTPException(status_code=400, detail="At least one target profile or URL is required.")

    job_ids = job_manager.create_batch_jobs(
        targets=request.targets,
        default_platform=request.default_platform,
        limit=request.limit,
        media_type=request.media_type,
        download_posts=request.download_posts,
        download_reels=request.download_reels,
        download_stories=request.download_stories,
        download_highlights=request.download_highlights,
        download_tagged=request.download_tagged,
        download_videos=request.download_videos,
        download_slideshows=request.download_slideshows,
        download_audio=request.download_audio,
        save_captions=request.save_captions,
        save_metadata=request.save_metadata
    )

    return {
        "success": True,
        "job_ids": job_ids,
        "count": len(job_ids),
        "message": f"Successfully queued {len(job_ids)} concurrent download jobs."
    }


@app.post("/api/download/direct")
async def start_direct_download(request: DirectUrlDownloadRequest):
    if not request.urls:
        raise HTTPException(status_code=400, detail="At least one URL is required.")
    job_id = job_manager.create_direct_job(request)
    return {"success": True, "job_id": job_id, "message": "Direct download job queued."}


@app.get("/api/jobs")
async def list_jobs():
    return {job_id: job.model_dump() for job_id, job in job_manager.list_jobs().items()}


@app.get("/api/jobs/{job_id}")
async def get_job_detail(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job.model_dump()


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    success = job_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled or was not found.")
    return {"success": True, "message": "Job cancellation requested."}


@app.post("/api/jobs/cancel-all")
async def cancel_all_jobs():
    count = job_manager.cancel_all_jobs()
    return {"success": True, "cancelled_count": count, "message": f"Cancelled {count} jobs."}


# -------------------------------------------------------------
# Interactive Web Terminal Command Engine
# -------------------------------------------------------------
@app.post("/api/terminal/execute")
async def execute_terminal_command(req: TerminalCommandRequest):
    """Process an interactive command typed into the Web Terminal Console."""
    raw = req.command.strip()
    if not raw:
        return {"success": True, "output": ""}

    parts = raw.split()
    cmd = parts[0].lower()
    args = parts[1:]

    # HELP COMMAND
    if cmd in ["help", "?"]:
        output = (
            "╔══════════════════════════════════════════════════════════════════╗\n"
            "║                  MEDIAVAULT TERMINAL COMMANDS                    ║\n"
            "╚══════════════════════════════════════════════════════════════════╝\n\n"
            "  ig <user1> [user2...] [-l N]  Download Instagram profile(s)\n"
            "  tt <user1> [user2...] [-l N]  Download TikTok creator(s)\n"
            "  batch <target1> <target2>...  Concurrent multi-platform batch\n"
            "  direct <url1> [url2...]       Download specific video/post URLs\n"
            "  list / ls                     List downloaded profiles & files\n"
            "  storage / df                  Show disk usage & space breakdown\n"
            "  jobs / ps                     List active & queued download tasks\n"
            "  cancel <job_id | all>         Cancel a job or all running jobs\n"
            "  proxy [list|add|rotate|test]  Manage rotating proxies & evasion pool\n"
            "  cookies [browser | all]       Extract session cookies from browser\n"
            "  zip <platform> <username>     Export profile media as ZIP archive\n"
            "  open / finder [user]          Reveal downloads folder in Finder\n"
            "  clear / cls                   Clear terminal screen\n"
        )
        return {"success": True, "output": output}

    # INSTAGRAM COMMAND: ig <user1> [user2...] [-l 20]
    elif cmd in ["ig", "instagram"]:
        if not args:
            return {"success": False, "output": "Usage: ig <username1> [username2...] [-l limit]"}
        
        limit = 30
        targets = []
        i = 0
        while i < len(args):
            if args[i] in ["-l", "--limit"] and i + 1 < len(args):
                try:
                    limit = int(args[i + 1])
                except ValueError:
                    pass
                i += 2
            else:
                targets.append(args[i])
                i += 1

        if not targets:
            return {"success": False, "output": "No usernames specified."}

        job_ids = job_manager.create_batch_jobs(
            targets=targets,
            default_platform=Platform.INSTAGRAM,
            limit=limit,
            download_posts=True,
            download_reels=True,
            download_profile_pic=True,
            save_captions=True,
            save_metadata=True
        )
        return {
            "success": True,
            "output": f"🚀 Queued {len(job_ids)} Instagram download job(s) for: {', '.join(targets)} (limit: {limit})\nJob IDs: {', '.join(job_ids)}",
            "action": "refresh_jobs",
            "data": {"job_ids": job_ids}
        }

    # TIKTOK COMMAND: tt <user1> [user2...] [-l 30]
    elif cmd in ["tt", "tiktok"]:
        if not args:
            return {"success": False, "output": "Usage: tt <username1> [username2...] [-l limit]"}
        
        limit = 30
        targets = []
        i = 0
        while i < len(args):
            if args[i] in ["-l", "--limit"] and i + 1 < len(args):
                try:
                    limit = int(args[i + 1])
                except ValueError:
                    pass
                i += 2
            else:
                targets.append(args[i])
                i += 1

        if not targets:
            return {"success": False, "output": "No usernames specified."}

        job_ids = job_manager.create_batch_jobs(
            targets=targets,
            default_platform=Platform.TIKTOK,
            limit=limit,
            download_videos=True,
            download_slideshows=True,
            download_profile_pic=True,
            save_metadata=True
        )
        return {
            "success": True,
            "output": f"🚀 Queued {len(job_ids)} TikTok download job(s) for: {', '.join(targets)} (limit: {limit})\nJob IDs: {', '.join(job_ids)}",
            "action": "refresh_jobs",
            "data": {"job_ids": job_ids}
        }

    # BATCH MULTI-PLATFORM COMMAND: batch <t1> <t2> ...
    elif cmd in ["batch", "multi"]:
        if not args:
            return {"success": False, "output": "Usage: batch <target1> <target2> ... (e.g. batch @zuck tt:khaby.lame ig:natgeo)"}
        job_ids = job_manager.create_batch_jobs(targets=args, limit=30)
        return {
            "success": True,
            "output": f"🚀 Queued {len(job_ids)} concurrent batch job(s).\nJob IDs: {', '.join(job_ids)}",
            "action": "refresh_jobs",
            "data": {"job_ids": job_ids}
        }

    # DIRECT URL COMMAND: direct <url1> [url2...]
    elif cmd in ["direct", "dl"]:
        if not args:
            return {"success": False, "output": "Usage: direct <url1> [url2...]"}
        job_id = job_manager.create_direct_job(DirectUrlDownloadRequest(urls=args, save_metadata=True))
        return {
            "success": True,
            "output": f"🚀 Queued direct download job for {len(args)} URL(s).\nJob ID: {job_id}",
            "action": "refresh_jobs",
            "data": {"job_id": job_id}
        }

    # LIST COMMAND: list / ls
    elif cmd in ["list", "ls"]:
        lines = ["📁 Downloaded Media Archives:\n"]
        total_items = 0
        total_bytes = 0
        for p in ["instagram", "tiktok"]:
            p_dir = DOWNLOADS_DIR / p
            if p_dir.exists():
                users = [d for d in p_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
                lines.append(f"  ● {p.upper()} ({len(users)} profiles):")
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
                    lines.append(f"    - @{u.name:<24} {count:>5} files  ({_human_filesize(size)})")
        lines.append(f"\nTotal: {total_items} files ({_human_filesize(total_bytes)})")
        return {"success": True, "output": "\n".join(lines)}

    # STORAGE COMMAND: storage / df
    elif cmd in ["storage", "df", "stats"]:
        stats = await get_storage_stats()
        out = (
            f"📊 Storage Breakdown:\n"
            f"  - Total Downloaded: {stats['total_size_human']} ({stats['total_files_count']} files across {stats['total_users_count']} profiles)\n"
            f"  - Free Disk Space:  {stats['free_disk_space_human']}\n\n"
            f"Platform Breakdown:\n"
        )
        for p in stats["platforms"]:
            out += f"  - {p['platform'].upper():<12}: {p['items_count']:>5} files ({p['size_human']})\n"
        return {"success": True, "output": out}

    # JOBS COMMAND: jobs / ps
    elif cmd in ["jobs", "ps", "tasks"]:
        all_jobs = job_manager.list_jobs()
        if not all_jobs:
            return {"success": True, "output": "No jobs recorded."}
        lines = ["⚙️ Download Jobs:\n"]
        for jid, j in all_jobs.items():
            lines.append(f"  [{j.status.upper():<9}] {jid:<12} {j.platform.value.upper():<9} {j.target:<20} {j.downloaded_items}/{j.total_items} ({j.progress_percent:.1f}%)")
        return {"success": True, "output": "\n".join(lines)}

    # CANCEL COMMAND: cancel <job_id | all>
    elif cmd in ["cancel", "kill"]:
        if not args:
            return {"success": False, "output": "Usage: cancel <job_id | all>"}
        target = args[0].lower()
        if target in ["all", "*"]:
            count = job_manager.cancel_all_jobs()
            return {"success": True, "output": f"🛑 Cancelled {count} running/queued job(s)."}
        else:
            ok = job_manager.cancel_job(args[0])
            if ok:
                return {"success": True, "output": f"🛑 Job {args[0]} cancelled."}
            return {"success": False, "output": f"Job '{args[0]}' not found or already finished."}

    # COOKIES COMMAND: cookies [browser | all]
    elif cmd in ["cookies", "cookie"]:
        b = args[0].lower() if args else "all"
        if b == "all":
            res = session_manager.scan_all_browsers_for_instagram()
            if res.get("success"):
                return {"success": True, "output": f"✅ Extracted Instagram session from {res.get('browser', '').upper()}!"}
            return {"success": False, "output": "No active Instagram session found in standard browser profiles."}
        else:
            ok, det = session_manager.auto_extract_from_browser(b)
            if ok:
                return {"success": True, "output": f"✅ Extracted session from {b.upper()}!"}
            return {"success": False, "output": det.get("error", "Extraction failed.")}

    # OPEN / FINDER COMMAND: open [platform] [username]
    elif cmd in ["open", "finder"]:
        p = args[0] if len(args) > 0 else None
        u = args[1] if len(args) > 1 else None
        res = await open_in_macos_finder(OpenFinderRequest(platform=p, username=u))
        if res.get("success"):
            return {"success": True, "output": f"📂 Revealed in Finder: {res.get('opened_path')}"}
        return {"success": False, "output": res.get("error", "Could not open folder.")}

    # ZIP EXPORT COMMAND: zip <platform> <username>
    elif cmd == "zip":
        if len(args) < 2:
            return {"success": False, "output": "Usage: zip <platform> <username> (e.g. zip instagram zuck)"}
        p, u = args[0].lower(), args[1]
        zip_path = zip_exporter.create_user_zip(p, u)
        if zip_path and zip_path.exists():
            return {
                "success": True,
                "output": f"📦 ZIP archive created: {zip_path.name} ({_human_filesize(zip_path.stat().st_size)})\nDownload at: /api/zips/{zip_path.name}",
                "action": "download_zip",
                "data": {"zip_url": f"/api/zips/{zip_path.name}"}
            }
        return {"success": False, "output": f"Could not create ZIP archive for @{u}."}

    # PROXY MANAGEMENT COMMAND: proxy [list|add|remove|rotate|test|on|off]
    elif cmd == "proxy":
        sub = args[0].lower() if args else "list"
        if sub in ["list", "ls", "status"]:
            status = proxy_manager.get_status()
            out = f"🌐 PROXY POOL STATUS\n"
            out += f"  Enabled: {'✅ Yes' if status['enabled'] else '❌ No'}\n"
            out += f"  Total Proxies: {status['total_count']}\n"
            out += f"  Active Proxy: {status['current_proxy'] or '(None)'}\n"
            if status['proxies']:
                out += "\nConfigured Proxies:\n"
                for idx, p in enumerate(status['proxies'], 1):
                    is_active = (p == status['current_proxy'])
                    out += f"  {idx}. {p} {'[ACTIVE]' if is_active else ''}\n"
            else:
                out += "\n(No proxies configured. Add one with 'proxy add <url>')\n"
            return {"success": True, "output": out}

        elif sub == "add":
            if len(args) < 2:
                return {"success": False, "output": "Usage: proxy add <http://user:pass@host:port> or <socks5://host:port>"}
            added = 0
            for p in args[1:]:
                if proxy_manager.add_proxy(p):
                    added += 1
            return {"success": True, "output": f"✅ Added {added} proxy/proxies to pool. (Total: {len(proxy_manager.proxies)})"}

        elif sub in ["remove", "rm", "del"]:
            if len(args) < 2:
                return {"success": False, "output": "Usage: proxy remove <proxy_url>"}
            removed = proxy_manager.remove_proxy(args[1])
            return {"success": True, "output": f"✅ Proxy removed." if removed else "❌ Proxy not found in pool."}

        elif sub == "rotate":
            new_p = proxy_manager.rotate_proxy()
            if new_p:
                return {"success": True, "output": f"🔄 Rotated to next proxy: {proxy_manager._mask_proxy(new_p)}"}
            return {"success": False, "output": "No proxies configured in pool to rotate to."}

        elif sub in ["test", "check"]:
            target_p = args[1] if len(args) > 1 else proxy_manager.get_current_proxy()
            if not target_p:
                return {"success": False, "output": "No proxy specified or active to test. Usage: proxy test <url>"}
            ok, msg, lat = proxy_manager.test_proxy(target_p)
            return {
                "success": ok,
                "output": f"🌐 Proxy Test [{proxy_manager._mask_proxy(target_p)}]:\n  Status: {'✅ Online' if ok else '❌ Failed'}\n  Details: {msg}"
            }

        elif sub in ["fetch", "auto", "free", "scrape"]:
            out = "🌐 Fetching and verifying free proxies from public sources in parallel...\n"
            res = proxy_manager.fetch_free_proxies(max_working=8)
            if res.get("success"):
                out += f"✅ Added {res.get('added_new', 0)} fast verified proxies to active pool (Total: {res.get('pool_total')})\n\n"
                out += "Fastest Verified Proxies:\n"
                for idx, p in enumerate(res.get("proxies", []), 1):
                    out += f"  {idx}. {p['url']} (Latency: {p['latency']}s, Outbound: {p.get('origin', 'N/A')})\n"
            else:
                out += f"❌ Could not verify working proxies: {res.get('message', 'Timeout or connectivity error')}"
            return {"success": res.get("success", False), "output": out}

        elif sub in ["on", "enable"]:
            proxy_manager.set_enabled(True)
            return {"success": True, "output": "✅ Proxy routing enabled."}

        elif sub in ["off", "disable"]:
            proxy_manager.set_enabled(False)
            return {"success": True, "output": "⚠️ Proxy routing disabled (direct connection)."}

        else:
            return {
                "success": False,
                "output": "Usage: proxy [list | add <url> | remove <url> | fetch | rotate | test [url] | on | off]"
            }

    # CLEAR COMMAND
    elif cmd in ["clear", "cls"]:
        return {"success": True, "output": "", "action": "clear_screen"}

    else:
        return {
            "success": False,
            "output": f"Unknown command: '{cmd}'. Type 'help' to see all available commands."
        }



# -------------------------------------------------------------
# User Profile Previews & Media Proxy
# -------------------------------------------------------------
@app.get("/api/preview/instagram/{username}")
async def preview_instagram_profile(username: str):
    info = instagram_downloader.fetch_user_info(username)
    return info


@app.get("/api/preview/tiktok/{username}")
async def preview_tiktok_profile(username: str):
    info = tiktok_downloader.fetch_user_info(username)
    return info


@app.get("/api/proxy-image")
async def proxy_remote_image(url: str):
    """Proxy external image URLs (Instagram, TikTok CDN) so browsers don't get blocked by CORS/Hotlinking/Referrer checks."""
    import requests
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required.")
    
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(status_code=400, detail="Invalid URL scheme.")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        }
        
        sess = requests.Session()
        if "cdninstagram.com" in url or "instagram.com" in url or "fbcdn.net" in url:
            cookies = session_manager.get_instagram_cookies()
            for k, v in cookies.items():
                sess.cookies.set(k, v, domain=".instagram.com")
            headers["Referer"] = "https://www.instagram.com/"

        resp = sess.get(url, headers=headers, timeout=12)
        if resp.status_code == 200:
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            return Response(
                content=resp.content,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "Access-Control-Allow-Origin": "*",
                }
            )
        else:
            raise HTTPException(status_code=resp.status_code, detail=f"Image host returned HTTP {resp.status_code}")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Image proxy error for {url}: {e}")
        raise HTTPException(status_code=502, detail=f"Proxy error: {str(e)}")


# -------------------------------------------------------------
# Proxy Pool & Rotation Management
# -------------------------------------------------------------
class ProxyAddRequest(BaseModel):
    proxies: List[str]

class ProxyRemoveRequest(BaseModel):
    proxy: str

class ProxyTestRequest(BaseModel):
    proxy: Optional[str] = None

class ProxyToggleRequest(BaseModel):
    enabled: bool


@app.get("/api/proxy/status")
async def get_proxy_status():
    return proxy_manager.get_status()


@app.post("/api/proxy/add")
async def add_proxies_to_pool(req: ProxyAddRequest):
    added = 0
    for p in req.proxies:
        if proxy_manager.add_proxy(p):
            added += 1
    return {"success": True, "added": added, "total": len(proxy_manager.proxies)}


@app.post("/api/proxy/remove")
async def remove_proxy_from_pool(req: ProxyRemoveRequest):
    ok = proxy_manager.remove_proxy(req.proxy)
    return {"success": ok, "total": len(proxy_manager.proxies)}


@app.post("/api/proxy/rotate")
async def rotate_active_proxy():
    new_p = proxy_manager.rotate_proxy()
    return {"success": bool(new_p), "current_proxy": proxy_manager.get_current_proxy()}


@app.post("/api/proxy/test")
async def test_proxy_endpoint(req: ProxyTestRequest):
    target = req.proxy or proxy_manager.get_current_proxy()
    if not target:
        raise HTTPException(status_code=400, detail="No proxy specified or currently active.")
    ok, msg, lat = proxy_manager.test_proxy(target)
    return {"success": ok, "message": msg, "latency": lat, "proxy": target}


@app.post("/api/proxy/toggle")
async def toggle_proxy_usage(req: ProxyToggleRequest):
    proxy_manager.set_enabled(req.enabled)
    return {"success": True, "enabled": proxy_manager.enabled}


@app.post("/api/proxy/fetch-free")
async def fetch_free_proxies_endpoint():
    """Scrapes public proxy repositories, tests connectivity in parallel, and populates pool."""
    res = proxy_manager.fetch_free_proxies(max_working=8)
    return res


# -------------------------------------------------------------
# Session & Cookie Management
# -------------------------------------------------------------
@app.get("/api/session/status")
async def get_session_status():
    return session_manager.get_status()


@app.post("/api/session/extract-browser")
async def extract_session_from_browser(req: SessionCookieRequest):
    if req.browser:
        success, details = session_manager.auto_extract_from_browser(req.browser)
        return {"success": success, "details": details}
    else:
        # Scan all installed browsers
        res = session_manager.scan_all_browsers_for_instagram()
        return res


@app.post("/api/session/import")
async def import_session_cookies(req: SessionCookieRequest):
    cookies = {}
    if req.raw_cookies:
        cookies = session_manager.parse_raw_cookie_string(req.raw_cookies)
    elif req.session_id:
        cookies["sessionid"] = req.session_id.strip()
        if req.ds_user_id:
            cookies["ds_user_id"] = req.ds_user_id.strip()

    if not cookies or "sessionid" not in cookies:
        raise HTTPException(status_code=400, detail="No valid 'sessionid' found in provided cookies.")

    saved = session_manager.save_instagram_cookies(cookies)
    verification = session_manager.verify_instagram_session(cookies)
    return {
        "success": saved,
        "cookies_saved": len(cookies),
        "verification": verification,
        "message": "Cookies imported and saved successfully!"
    }


@app.post("/api/session/upload-cookies")
async def upload_cookie_file(file: UploadFile = File(...), platform: str = Form("instagram")):
    """Upload cookie file (.txt or .json) and import."""
    try:
        content_bytes = await file.read()
        content_str = content_bytes.decode("utf-8", errors="replace")
        
        domain_filter = "instagram.com" if platform == "instagram" else "tiktok.com"
        cookies = session_manager.parse_any_cookie_input(content_str, domain_filter=domain_filter)

        if not cookies:
            raise HTTPException(status_code=400, detail="Could not parse any valid cookies from uploaded file.")

        if platform == "instagram":
            if "sessionid" not in cookies:
                raise HTTPException(status_code=400, detail="No 'sessionid' cookie found for Instagram in uploaded file.")
            saved = session_manager.save_instagram_cookies(cookies)
            verification = session_manager.verify_instagram_session(cookies)
            return {
                "success": saved,
                "platform": "instagram",
                "cookies_saved": len(cookies),
                "verification": verification,
                "message": f"Successfully imported {len(cookies)} Instagram cookies from {file.filename}!"
            }
        else:
            saved = session_manager.save_tiktok_cookies(cookies)
            return {
                "success": saved,
                "platform": "tiktok",
                "cookies_saved": len(cookies),
                "message": f"Successfully imported {len(cookies)} TikTok cookies from {file.filename}!"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process cookie file: {str(e)}")



@app.post("/api/session/import-tiktok")
async def import_tiktok_cookies(req: SessionCookieRequest):
    cookies = {}
    if req.raw_cookies:
        cookies = session_manager.parse_raw_cookie_string(req.raw_cookies)
    elif req.session_id:
        cookies["sessionid"] = req.session_id.strip()

    if not cookies:
        raise HTTPException(status_code=400, detail="No cookies provided.")

    saved = session_manager.save_tiktok_cookies(cookies)
    return {
        "success": saved,
        "cookies_saved": len(cookies),
        "message": "TikTok cookies saved successfully!"
    }


@app.post("/api/session/clear")
async def clear_session():
    cleared = session_manager.clear_instagram_session()
    return {"success": cleared, "message": "Instagram session cleared."}


# -------------------------------------------------------------
# Gallery & Archive Endpoints
# -------------------------------------------------------------
def _human_filesize(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _get_media_type(suffix: str) -> str:
    s = suffix.lower()
    if s in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic"]:
        return "image"
    elif s in [".mp4", ".mov", ".mkv", ".webm"]:
        return "video"
    elif s in [".mp3", ".m4a", ".aac", ".wav", ".ogg"]:
        return "audio"
    elif s in [".json"]:
        return "json"
    elif s in [".txt"]:
        return "text"
    return "other"


@app.get("/api/gallery")
async def get_gallery_overview():
    """Return all downloaded users and summaries."""
    gallery_data = []

    for platform_str in ["instagram", "tiktok"]:
        platform_dir = DOWNLOADS_DIR / platform_str
        if not platform_dir.exists():
            continue

        for user_folder in sorted(platform_dir.iterdir()):
            if not user_folder.is_dir():
                continue

            username = user_folder.name
            total_size = 0
            items_count = 0
            profile_pic_url = None

            # Check profile picture
            for pic_name in ["profile_pic.jpg", "profile_pic.png", "avatar.jpg"]:
                if (user_folder / pic_name).exists():
                    profile_pic_url = f"/media/{platform_str}/{username}/{pic_name}"
                    break

            for root, _, files in os.walk(user_folder):
                for f in files:
                    if f.startswith("."):
                        continue
                    fpath = Path(root) / f
                    total_size += fpath.stat().st_size
                    ext = fpath.suffix.lower()
                    if ext in [".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm", ".mp3", ".m4a"]:
                        items_count += 1

            gallery_data.append({
                "platform": platform_str,
                "username": username,
                "folder_name": user_folder.name,
                "item_count": items_count,
                "total_size_bytes": total_size,
                "total_size_human": _human_filesize(total_size),
                "profile_pic_url": profile_pic_url
            })

    return {"users": gallery_data}


@app.get("/api/gallery/{platform}/{username}")
async def get_user_gallery_items(platform: str, username: str):
    """Return all individual media items for a specific user."""
    user_folder = DOWNLOADS_DIR / platform / username
    if not user_folder.exists() or not user_folder.is_dir():
        raise HTTPException(status_code=404, detail="User folder not found.")

    items: List[MediaItem] = []
    total_size = 0

    # Load captions/metadata dictionary
    captions_map: Dict[str, str] = {}
    for root, _, files in os.walk(user_folder):
        for f in files:
            if f.endswith("_caption.txt"):
                base_key = f.replace("_caption.txt", "")
                try:
                    with open(Path(root) / f, "r", encoding="utf-8") as capf:
                        captions_map[base_key] = capf.read()
                except Exception:
                    pass

    for root, _, files in os.walk(user_folder):
        for f in sorted(files, reverse=True):
            if f.startswith(".") or f.endswith("_caption.txt") or f.endswith("_meta.json") or f == "user_info.json":
                continue

            fpath = Path(root) / f
            stat = fpath.stat()
            total_size += stat.st_size
            rel_path = str(fpath.relative_to(DOWNLOADS_DIR))
            url_path = f"/media/{rel_path}"
            mtype = _get_media_type(fpath.suffix)

            if mtype in ["image", "video", "audio"]:
                # Check for caption matching prefix
                caption = None
                for k, v in captions_map.items():
                    if k in f:
                        caption = v
                        break

                items.append(MediaItem(
                    filename=f,
                    rel_path=rel_path,
                    full_path=str(fpath),
                    url_path=url_path,
                    media_type=mtype,
                    file_size=stat.st_size,
                    file_size_human=_human_filesize(stat.st_size),
                    created_time=datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    caption=caption
                ))

    profile_pic_url = None
    if (user_folder / "profile_pic.jpg").exists():
        profile_pic_url = f"/media/{platform}/{username}/profile_pic.jpg"

    return {
        "platform": platform,
        "username": username,
        "item_count": len(items),
        "total_size_human": _human_filesize(total_size),
        "profile_pic_url": profile_pic_url,
        "items": [it.model_dump() for it in items]
    }


@app.get("/api/gallery/{platform}/{username}/zip")
async def download_user_as_zip(platform: str, username: str):
    """Download entire user archive as a ZIP file."""
    zip_path = zip_exporter.create_user_zip(platform, username)
    if not zip_path or not zip_path.exists():
        raise HTTPException(status_code=404, detail="Could not create ZIP archive.")

    return FileResponse(
        path=str(zip_path),
        filename=zip_path.name,
        media_type="application/zip"
    )


@app.post("/api/gallery/{platform}/{username}/batch-zip")
async def create_batch_zip(platform: str, username: str, req: BatchZipRequest):
    """Create a ZIP file containing only the selected items."""
    if not req.filenames:
        raise HTTPException(status_code=400, detail="No files specified for batch ZIP.")

    zip_path = zip_exporter.create_batch_zip(platform, username, req.filenames)
    if not zip_path or not zip_path.exists():
        raise HTTPException(status_code=404, detail="Could not create batch ZIP archive.")

    stat = zip_path.stat()
    return {
        "success": True,
        "zip_url": f"/api/zips/{zip_path.name}",
        "filename": zip_path.name,
        "items_count": len(req.filenames),
        "total_size_human": _human_filesize(stat.st_size)
    }


@app.get("/api/zips/{filename}")
async def serve_cached_zip(filename: str):
    """Download a generated ZIP file."""
    from core.zip_exporter import ZIP_CACHE_DIR
    zip_file = ZIP_CACHE_DIR / filename
    if not zip_file.exists():
        raise HTTPException(status_code=404, detail="ZIP archive not found or expired.")

    return FileResponse(
        path=str(zip_file),
        filename=filename,
        media_type="application/zip"
    )


@app.delete("/api/gallery/{platform}/{username}/item")
async def delete_gallery_item(platform: str, username: str, filename: str, include_metadata: bool = True):
    """Delete a single media item from a user folder."""
    user_folder = DOWNLOADS_DIR / platform / username
    if not user_folder.exists():
        raise HTTPException(status_code=404, detail="User folder not found.")

    target_file = None
    # Locate target file recursively
    for root, _, files in os.walk(user_folder):
        if filename in files:
            target_file = Path(root) / filename
            break

    if not target_file or not target_file.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")

    # Remove main file
    target_file.unlink()

    # Clean matching caption or meta if requested
    deleted_extras = []
    if include_metadata:
        stem = target_file.stem
        # Strip trailing index if carousel item
        clean_stem = stem.rsplit("_", 1)[0] if "_" in stem else stem
        for root, _, files in os.walk(user_folder):
            for f in files:
                if (f.startswith(clean_stem) or f.startswith(stem)) and (f.endswith("_caption.txt") or f.endswith("_meta.json")):
                    extra_path = Path(root) / f
                    try:
                        extra_path.unlink()
                        deleted_extras.append(f)
                    except Exception:
                        pass

    return {
        "success": True,
        "filename": filename,
        "deleted_extras": deleted_extras,
        "message": f"Successfully deleted {filename}."
    }


@app.post("/api/gallery/{platform}/{username}/batch-delete")
async def batch_delete_gallery_items(platform: str, username: str, req: BatchDeleteRequest):
    """Delete multiple selected media items from a user folder."""
    user_folder = DOWNLOADS_DIR / platform / username
    if not user_folder.exists():
        raise HTTPException(status_code=404, detail="User folder not found.")

    deleted_count = 0
    to_delete = set(req.filenames)

    for root, _, files in os.walk(user_folder):
        for f in files:
            if f in to_delete:
                file_path = Path(root) / f
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception:
                    pass

    return {
        "success": True,
        "deleted_count": deleted_count,
        "message": f"Successfully deleted {deleted_count} items."
    }


class OpenFinderRequest(BaseModel):
    path: Optional[str] = None
    platform: Optional[str] = None
    username: Optional[str] = None


@app.post("/api/gallery/open-finder")
async def open_in_macos_finder(req: OpenFinderRequest):
    """Open folder in macOS Finder using 'open' command."""
    target_path = DOWNLOADS_DIR
    if req.platform and req.username:
        target_path = DOWNLOADS_DIR / req.platform / req.username
    elif req.path:
        target_path = Path(req.path)

    if not target_path.exists():
        target_path = DOWNLOADS_DIR

    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(target_path)], check=True)
        elif sys.platform == "win32":
            subprocess.run(["explorer", str(target_path)], check=True)
        else:
            subprocess.run(["xdg-open", str(target_path)], check=True)
        return {"success": True, "opened_path": str(target_path)}
    except Exception as e:
        return {"success": False, "error": f"Failed to open in Finder: {str(e)}"}


@app.delete("/api/gallery/{platform}/{username}")
async def delete_user_gallery(platform: str, username: str):
    """Delete a user downloads directory."""
    import shutil
    user_folder = DOWNLOADS_DIR / platform / username
    if user_folder.exists():
        shutil.rmtree(user_folder)
        return {"success": True, "message": f"Deleted folder for {username}."}
    raise HTTPException(status_code=404, detail="Folder not found.")



# -------------------------------------------------------------
# Static and Media Mounting
# -------------------------------------------------------------
app.mount("/media", StaticFiles(directory=str(DOWNLOADS_DIR)), name="media")
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
async def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Insta & TikTok Media Downloader API is running."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="0.0.0.0", port=3000, reload=True)

