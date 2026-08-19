from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class Platform(str, Enum):
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    DIRECT = "direct"


class MediaTypeFilter(str, Enum):
    ALL = "all"
    PHOTOS = "photos"
    VIDEOS = "videos"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InstagramDownloadRequest(BaseModel):
    username_or_url: str
    download_posts: bool = True
    download_reels: bool = True
    download_stories: bool = False
    download_highlights: bool = False
    download_profile_pic: bool = True
    download_tagged: bool = False
    media_type: MediaTypeFilter = MediaTypeFilter.ALL
    limit: Optional[int] = Field(default=None, description="Max number of posts to download (None for all)")
    date_from: Optional[str] = Field(default=None, description="ISO format YYYY-MM-DD")
    date_to: Optional[str] = Field(default=None, description="ISO format YYYY-MM-DD")
    save_metadata: bool = False
    save_captions: bool = False
    custom_subfolder: Optional[str] = None


class TikTokDownloadRequest(BaseModel):
    username_or_url: str
    download_videos: bool = True
    download_slideshows: bool = True
    download_audio: bool = False
    download_profile_pic: bool = True
    limit: Optional[int] = Field(default=None, description="Max number of items (None for all)")
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    save_metadata: bool = False
    custom_subfolder: Optional[str] = None


class DirectUrlDownloadRequest(BaseModel):
    urls: List[str]
    save_metadata: bool = False
    custom_subfolder: Optional[str] = None


class LogMessage(BaseModel):
    timestamp: str
    level: str  # "info", "success", "warning", "error"
    message: str


class JobProgress(BaseModel):
    job_id: str
    platform: Platform
    target: str
    status: JobStatus
    total_items: int = 0
    downloaded_items: int = 0
    failed_items: int = 0
    current_item_name: str = ""
    current_file_path: Optional[str] = None
    progress_percent: float = 0.0
    speed: str = ""
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    logs: List[LogMessage] = Field(default_factory=list)


class MediaItem(BaseModel):
    filename: str
    rel_path: str
    full_path: str
    url_path: str
    media_type: str  # "image", "video", "audio", "json", "text"
    file_size: int
    file_size_human: str
    created_time: str
    caption: Optional[str] = None
    dimensions: Optional[str] = None
    thumbnail_url: Optional[str] = None


class UserProfileGallery(BaseModel):
    platform: Platform
    username: str
    folder_name: str
    item_count: int
    total_size_human: str
    total_size_bytes: int
    profile_pic_url: Optional[str] = None
    items: List[MediaItem] = Field(default_factory=list)


class SessionCookieRequest(BaseModel):
    browser: Optional[str] = None  # chrome, brave, safari, firefox, edge, etc.
    raw_cookies: Optional[str] = None  # e.g., sessionid=... or cookie header
    session_id: Optional[str] = None
    ds_user_id: Optional[str] = None
    platform: Platform = Platform.INSTAGRAM


class DeleteItemRequest(BaseModel):
    filename: str
    include_metadata: bool = True


class BatchDeleteRequest(BaseModel):
    filenames: List[str]
    include_metadata: bool = True


class BatchZipRequest(BaseModel):
    filenames: List[str]


class BatchZipResponse(BaseModel):
    success: bool
    zip_url: str
    filename: str
    items_count: int
    total_size_human: str


class StoragePlatformBreakdown(BaseModel):
    platform: str
    items_count: int
    size_bytes: int
    size_human: str


class StorageInfo(BaseModel):
    total_size_bytes: int
    total_size_human: str
    total_files_count: int
    total_users_count: int
    free_disk_space_bytes: int
    free_disk_space_human: str
    platforms: List[StoragePlatformBreakdown]


class BatchTargetItem(BaseModel):
    platform: Platform
    target: str
    limit: Optional[int] = None


class MultiDownloadRequest(BaseModel):
    targets: List[str]  # handles, URLs, or prefixed targets like ig:user or tt:creator
    default_platform: Optional[Platform] = None
    limit: Optional[int] = 30
    media_type: MediaTypeFilter = MediaTypeFilter.ALL
    download_posts: bool = True
    download_reels: bool = True
    download_stories: bool = False
    download_highlights: bool = False
    download_tagged: bool = False
    download_videos: bool = True
    download_slideshows: bool = True
    download_audio: bool = False
    save_captions: bool = True
    save_metadata: bool = True
    concurrency: int = 3


class TerminalCommandRequest(BaseModel):
    command: str


class TerminalCommandResponse(BaseModel):
    success: bool
    output: str
    action: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


