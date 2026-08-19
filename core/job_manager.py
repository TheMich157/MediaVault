import asyncio
import uuid
import logging
from datetime import datetime
from typing import Dict, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor

from core.models import (
    JobProgress,
    JobStatus,
    Platform,
    LogMessage,
    InstagramDownloadRequest,
    TikTokDownloadRequest,
    DirectUrlDownloadRequest
)
from core.instagram_downloader import instagram_downloader
from core.tiktok_downloader import tiktok_downloader
from backend.sse import sse_manager

logger = logging.getLogger(__name__)


class JobManager:
    """Manages background download jobs, status tracking, cancellation, and event broadcasting."""

    def __init__(self, max_workers: int = 4):
        self.jobs: Dict[str, JobProgress] = {}
        self.cancellation_flags: Dict[str, bool] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def get_job(self, job_id: str) -> Optional[JobProgress]:
        return self.jobs.get(job_id)

    def list_jobs(self) -> Dict[str, JobProgress]:
        return self.jobs

    def cancel_job(self, job_id: str) -> bool:
        if job_id in self.jobs and self.jobs[job_id].status in [JobStatus.QUEUED, JobStatus.RUNNING]:
            self.cancellation_flags[job_id] = True
            self.jobs[job_id].status = JobStatus.CANCELLED
            self._emit_event("job_cancelled", self.jobs[job_id].model_dump())
            return True
        return False

    def cancel_all_jobs(self) -> int:
        """Cancel all running or queued jobs."""
        cancelled_count = 0
        for job_id, job in self.jobs.items():
            if job.status in [JobStatus.QUEUED, JobStatus.RUNNING]:
                self.cancellation_flags[job_id] = True
                job.status = JobStatus.CANCELLED
                self._emit_event("job_cancelled", job.model_dump())
                cancelled_count += 1
        return cancelled_count

    def is_cancelled(self, job_id: str) -> bool:
        return self.cancellation_flags.get(job_id, False)

    def _emit_event(self, event_type: str, data: dict):
        """Thread-safe event broadcast to SSE clients."""
        try:
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    sse_manager.broadcast(event_type, data),
                    self.loop
                )
        except Exception as e:
            logger.error(f"Error broadcasting event {event_type}: {e}")

    def create_instagram_job(self, request: InstagramDownloadRequest) -> str:
        job_id = f"ig_{uuid.uuid4().hex[:8]}"
        job = JobProgress(
            job_id=job_id,
            platform=Platform.INSTAGRAM,
            target=request.username_or_url,
            status=JobStatus.QUEUED,
            created_at=datetime.now().isoformat(),
        )
        self.jobs[job_id] = job
        self.cancellation_flags[job_id] = False

        # Submit background task
        self.executor.submit(self._run_instagram_job, job_id, request)
        self._emit_event("job_created", job.model_dump())
        return job_id

    def create_tiktok_job(self, request: TikTokDownloadRequest) -> str:
        job_id = f"tt_{uuid.uuid4().hex[:8]}"
        job = JobProgress(
            job_id=job_id,
            platform=Platform.TIKTOK,
            target=request.username_or_url,
            status=JobStatus.QUEUED,
            created_at=datetime.now().isoformat(),
        )
        self.jobs[job_id] = job
        self.cancellation_flags[job_id] = False

        # Submit background task
        self.executor.submit(self._run_tiktok_job, job_id, request)
        self._emit_event("job_created", job.model_dump())
        return job_id

    def create_direct_job(self, request: DirectUrlDownloadRequest) -> str:
        job_id = f"dir_{uuid.uuid4().hex[:8]}"
        job = JobProgress(
            job_id=job_id,
            platform=Platform.DIRECT,
            target=f"{len(request.urls)} direct URLs",
            status=JobStatus.QUEUED,
            created_at=datetime.now().isoformat(),
        )
        self.jobs[job_id] = job
        self.cancellation_flags[job_id] = False

        # Submit background task
        self.executor.submit(self._run_direct_job, job_id, request)
        self._emit_event("job_created", job.model_dump())
        return job_id

    @staticmethod
    def resolve_target(raw: str, default_platform: Optional[Platform] = None) -> tuple[Platform, str]:
        """Resolve a raw target string (e.g. '@zuck', 'tiktok.com/@foo', 'ig:bar') to (Platform, clean_target)."""
        raw = raw.strip()
        lower = raw.lower()

        if "instagram.com" in lower or lower.startswith("ig:") or lower.startswith("instagram:"):
            target = raw.split(":", 1)[1].strip() if ":" in raw and not raw.startswith("http") else raw
            return Platform.INSTAGRAM, target

        if "tiktok.com" in lower or lower.startswith("tt:") or lower.startswith("tiktok:"):
            target = raw.split(":", 1)[1].strip() if ":" in raw and not raw.startswith("http") else raw
            return Platform.TIKTOK, target

        if default_platform:
            return default_platform, raw

        # Default heuristic: if starts with @ or plain text, default to Instagram unless specified
        return Platform.INSTAGRAM, raw

    def create_batch_jobs(self, targets: list[str], default_platform: Optional[Platform] = None, **kwargs) -> list[str]:
        """Spawn background download jobs for a list of targets across Instagram and TikTok."""
        created_job_ids = []
        for raw in targets:
            clean = raw.strip()
            if not clean:
                continue

            platform, target = self.resolve_target(clean, default_platform)

            if platform == Platform.INSTAGRAM:
                ig_req = InstagramDownloadRequest(
                    username_or_url=target,
                    limit=kwargs.get("limit", 30),
                    media_type=kwargs.get("media_type", "all"),
                    download_posts=kwargs.get("download_posts", True),
                    download_reels=kwargs.get("download_reels", True),
                    download_stories=kwargs.get("download_stories", False),
                    download_highlights=kwargs.get("download_highlights", False),
                    download_tagged=kwargs.get("download_tagged", False),
                    download_profile_pic=True,
                    save_captions=kwargs.get("save_captions", True),
                    save_metadata=kwargs.get("save_metadata", True),
                )
                job_id = self.create_instagram_job(ig_req)
                created_job_ids.append(job_id)

            elif platform == Platform.TIKTOK:
                tt_req = TikTokDownloadRequest(
                    username_or_url=target,
                    limit=kwargs.get("limit", 30),
                    download_videos=kwargs.get("download_videos", True),
                    download_slideshows=kwargs.get("download_slideshows", True),
                    download_audio=kwargs.get("download_audio", False),
                    download_profile_pic=True,
                    save_metadata=kwargs.get("save_metadata", True),
                )
                job_id = self.create_tiktok_job(tt_req)
                created_job_ids.append(job_id)

            else:
                dir_req = DirectUrlDownloadRequest(
                    urls=[target],
                    save_metadata=kwargs.get("save_metadata", True)
                )
                job_id = self.create_direct_job(dir_req)
                created_job_ids.append(job_id)

        return created_job_ids


    def _append_log(self, job_id: str, level: str, message: str):
        if job_id in self.jobs:
            log_item = LogMessage(
                timestamp=datetime.now().strftime("%H:%M:%S"),
                level=level,
                message=message
            )
            self.jobs[job_id].logs.append(log_item)
            self._emit_event("job_log", {
                "job_id": job_id,
                "log": log_item.model_dump()
            })

    def _update_progress(self, job_id: str, downloaded: int, total: int, filename: str, percent: float):
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job.downloaded_items = downloaded
            job.total_items = max(total, downloaded)
            job.current_item_name = filename
            job.progress_percent = round(percent, 1)
            self._emit_event("job_progress", job.model_dump())

    def _run_instagram_job(self, job_id: str, request: InstagramDownloadRequest):
        job = self.jobs[job_id]
        job.status = JobStatus.RUNNING
        self._emit_event("job_started", job.model_dump())
        self._append_log(job_id, "info", f"Starting download for Instagram user '{request.username_or_url}'...")

        try:
            res = instagram_downloader.download_user(
                request=request,
                progress_callback=lambda d, t, f, p: self._update_progress(job_id, d, t, f, p),
                log_callback=lambda lvl, msg: self._append_log(job_id, lvl, msg),
                is_cancelled=lambda: self.is_cancelled(job_id)
            )

            if self.is_cancelled(job_id):
                job.status = JobStatus.CANCELLED
                self._append_log(job_id, "warning", "Instagram download task was cancelled.")
                self._emit_event("job_cancelled", job.model_dump())
            elif res.get("success"):
                job.status = JobStatus.COMPLETED
                job.downloaded_items = res.get("downloaded_count", job.downloaded_items)
                job.total_items = max(job.total_items, job.downloaded_items)
                job.progress_percent = 100.0
                job.completed_at = datetime.now().isoformat()
                self._append_log(job_id, "success", f"Completed! Successfully downloaded {job.downloaded_items} files.")
                self._emit_event("job_completed", job.model_dump())
            else:
                job.status = JobStatus.FAILED
                job.error_message = res.get("error", "Unknown error")
                self._append_log(job_id, "error", f"Download failed: {job.error_message}")
                self._emit_event("job_failed", job.model_dump())

        except InterruptedError:
            job.status = JobStatus.CANCELLED
            self._append_log(job_id, "warning", "Download cancelled.")
            self._emit_event("job_cancelled", job.model_dump())
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            self._append_log(job_id, "error", f"Unexpected error: {str(e)}")
            self._emit_event("job_failed", job.model_dump())

    def _run_tiktok_job(self, job_id: str, request: TikTokDownloadRequest):
        job = self.jobs[job_id]
        job.status = JobStatus.RUNNING
        self._emit_event("job_started", job.model_dump())
        self._append_log(job_id, "info", f"Starting download for TikTok user '{request.username_or_url}'...")

        try:
            res = tiktok_downloader.download_user(
                request=request,
                progress_callback=lambda d, t, f, p: self._update_progress(job_id, d, t, f, p),
                log_callback=lambda lvl, msg: self._append_log(job_id, lvl, msg),
                is_cancelled=lambda: self.is_cancelled(job_id)
            )

            if self.is_cancelled(job_id):
                job.status = JobStatus.CANCELLED
                self._append_log(job_id, "warning", "TikTok download task was cancelled.")
                self._emit_event("job_cancelled", job.model_dump())
            elif res.get("success"):
                job.status = JobStatus.COMPLETED
                job.downloaded_items = res.get("downloaded_count", job.downloaded_items)
                job.total_items = max(job.total_items, job.downloaded_items)
                job.progress_percent = 100.0
                job.completed_at = datetime.now().isoformat()
                self._append_log(job_id, "success", f"Completed! Successfully downloaded {job.downloaded_items} files.")
                self._emit_event("job_completed", job.model_dump())
            else:
                job.status = JobStatus.FAILED
                job.error_message = res.get("error", "Unknown error")
                self._append_log(job_id, "error", f"Download failed: {job.error_message}")
                self._emit_event("job_failed", job.model_dump())

        except InterruptedError:
            job.status = JobStatus.CANCELLED
            self._append_log(job_id, "warning", "Download cancelled.")
            self._emit_event("job_cancelled", job.model_dump())
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            self._append_log(job_id, "error", f"Unexpected error: {str(e)}")
            self._emit_event("job_failed", job.model_dump())

    def _run_direct_job(self, job_id: str, request: DirectUrlDownloadRequest):
        job = self.jobs[job_id]
        job.status = JobStatus.RUNNING
        job.total_items = len(request.urls)
        self._emit_event("job_started", job.model_dump())

        downloaded = 0
        for i, url in enumerate(request.urls):
            if self.is_cancelled(job_id):
                job.status = JobStatus.CANCELLED
                break

            self._append_log(job_id, "info", f"Processing URL ({i+1}/{len(request.urls)}): {url}")
            if "instagram.com" in url:
                res = instagram_downloader.download_direct_post(url, save_metadata=request.save_metadata)
            elif "tiktok.com" in url:
                res = tiktok_downloader.download_direct_url(url, save_metadata=request.save_metadata)
            else:
                # Default to yt-dlp direct download
                res = tiktok_downloader.download_direct_url(url, save_metadata=request.save_metadata)

            if res.get("success"):
                downloaded += 1
                self._append_log(job_id, "success", f"Downloaded: {url}")
            else:
                self._append_log(job_id, "warning", f"Failed ({url}): {res.get('error')}")

            pct = ((i + 1) / len(request.urls)) * 100
            self._update_progress(job_id, downloaded, len(request.urls), url, pct)

        if not self.is_cancelled(job_id):
            job.status = JobStatus.COMPLETED
            job.progress_percent = 100.0
            job.completed_at = datetime.now().isoformat()
            self._append_log(job_id, "success", f"Direct download batch complete! {downloaded}/{len(request.urls)} saved.")
            self._emit_event("job_completed", job.model_dump())


job_manager = JobManager()
