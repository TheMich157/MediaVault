import os
import zipfile
from pathlib import Path
from typing import Optional

DOWNLOADS_DIR = Path(__file__).resolve().parent.parent / "downloads"
ZIP_CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "zips"
ZIP_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class ZipExporter:
    """Creates ZIP archives of downloaded media folders."""

    def __init__(self, downloads_dir: Optional[Path] = None):
        self.downloads_dir = downloads_dir or DOWNLOADS_DIR
        self.zip_cache_dir = ZIP_CACHE_DIR

    def create_user_zip(self, platform: str, username: str) -> Optional[Path]:
        """Create a zip archive of a given user folder and return the zip file path."""
        user_folder = self.downloads_dir / platform / username
        if not user_folder.exists() or not user_folder.is_dir():
            return None

        zip_filename = f"{platform}_{username}_archive.zip"
        zip_path = self.zip_cache_dir / zip_filename

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(user_folder):
                for file in files:
                    file_path = Path(root) / file
                    # Relative archive path
                    arcname = file_path.relative_to(user_folder)
                    zipf.write(file_path, arcname=arcname)

    def create_batch_zip(self, platform: str, username: str, filenames: list[str]) -> Optional[Path]:
        """Create a zip archive of selected files for a user and return the zip file path."""
        user_folder = self.downloads_dir / platform / username
        if not user_folder.exists() or not user_folder.is_dir():
            return None

        import time
        ts = int(time.time())
        zip_filename = f"{platform}_{username}_selection_{ts}.zip"
        zip_path = self.zip_cache_dir / zip_filename

        filenames_set = set(filenames)
        found_count = 0

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(user_folder):
                for file in files:
                    if file in filenames_set:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(user_folder)
                        zipf.write(file_path, arcname=arcname)
                        found_count += 1

        if found_count == 0:
            if zip_path.exists():
                zip_path.unlink()
            return None

        return zip_path


zip_exporter = ZipExporter()

