#!/usr/bin/env python3
"""
Test suite for MediaVault application components and API endpoints.
"""

import sys
import os
import json
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from core.session_manager import session_manager
from core.instagram_downloader import instagram_downloader
from core.tiktok_downloader import tiktok_downloader
from core.zip_exporter import zip_exporter, DOWNLOADS_DIR
from core.models import InstagramDownloadRequest, TikTokDownloadRequest, MediaTypeFilter


class TestMediaVault(unittest.TestCase):

    def test_instagram_username_extraction(self):
        self.assertEqual(instagram_downloader.extract_username("zuck"), "zuck")
        self.assertEqual(instagram_downloader.extract_username("@zuck"), "zuck")
        self.assertEqual(instagram_downloader.extract_username("https://www.instagram.com/zuck/"), "zuck")
        self.assertEqual(instagram_downloader.extract_username("https://instagram.com/zuck"), "zuck")

    def test_tiktok_username_extraction(self):
        self.assertEqual(tiktok_downloader.extract_username("tiktok"), "tiktok")
        self.assertEqual(tiktok_downloader.extract_username("@tiktok"), "tiktok")
        self.assertEqual(tiktok_downloader.extract_username("https://www.tiktok.com/@tiktok"), "tiktok")

    def test_cookie_string_parser(self):
        cookie_str = "sessionid=12345abcdef; ds_user_id=987654; csrftoken=token123"
        parsed = session_manager.parse_raw_cookie_string(cookie_str)
        self.assertEqual(parsed.get("sessionid"), "12345abcdef")
        self.assertEqual(parsed.get("ds_user_id"), "987654")
        self.assertEqual(parsed.get("csrftoken"), "token123")

    def test_netscape_cookie_parser(self):
        netscape_sample = (
            "# Netscape HTTP Cookie File\n"
            ".instagram.com\tTRUE\t/\tTRUE\t1799999999\tsessionid\tnetscape_session_123\n"
            ".instagram.com\tTRUE\t/\tTRUE\t1799999999\tds_user_id\t11223344\n"
        )
        parsed = session_manager.parse_netscape_cookie_file(netscape_sample)
        self.assertEqual(parsed.get("sessionid"), "netscape_session_123")
        self.assertEqual(parsed.get("ds_user_id"), "11223344")

    def test_json_cookie_parser(self):
        json_sample = json.dumps([
            {"name": "sessionid", "value": "json_sess_abc", "domain": ".instagram.com"},
            {"name": "ds_user_id", "value": "556677", "domain": ".instagram.com"}
        ])
        parsed = session_manager.parse_json_cookie_file(json_sample)
        self.assertEqual(parsed.get("sessionid"), "json_sess_abc")
        self.assertEqual(parsed.get("ds_user_id"), "556677")

    def test_fastapi_endpoints(self):
        from fastapi.testclient import TestClient
        from backend.app import app

        client = TestClient(app)
        
        # Test status endpoint
        resp = client.get("/api/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "online")
        self.assertIn("downloads_dir", data)

        # Test gallery endpoint
        resp_gallery = client.get("/api/gallery")
        self.assertEqual(resp_gallery.status_code, 200)
        self.assertIn("users", resp_gallery.json())

        # Test session status
        resp_session = client.get("/api/session/status")
        self.assertEqual(resp_session.status_code, 200)

        # Test storage endpoint
        resp_storage = client.get("/api/system/storage")
        self.assertEqual(resp_storage.status_code, 200)
        storage_data = resp_storage.json()
        self.assertIn("total_files_count", storage_data)
        self.assertIn("total_size_human", storage_data)

        # Test cookie upload
        fake_cookie_content = "sessionid=upload_test_999; ds_user_id=123"
        resp_upload = client.post(
            "/api/session/upload-cookies",
            data={"platform": "instagram"},
            files={"file": ("cookies.txt", fake_cookie_content.encode("utf-8"), "text/plain")}
        )
        self.assertEqual(resp_upload.status_code, 200)
        self.assertTrue(resp_upload.json().get("success"))

        # Test root endpoint returns HTML
        resp_root = client.get("/")
        self.assertEqual(resp_root.status_code, 200)
        self.assertIn("text/html", resp_root.headers.get("content-type", ""))

    def test_gallery_batch_and_delete_operations(self):
        from fastapi.testclient import TestClient
        from backend.app import app

        client = TestClient(app)

        # Setup test dummy directory
        test_user_dir = DOWNLOADS_DIR / "instagram" / "test_suite_user"
        test_user_dir.mkdir(parents=True, exist_ok=True)
        
        file1 = test_user_dir / "item_1.jpg"
        file1.write_bytes(b"dummy image bytes 1")
        caption1 = test_user_dir / "item_1_caption.txt"
        caption1.write_text("Test caption 1")

        file2 = test_user_dir / "item_2.mp4"
        file2.write_bytes(b"dummy video bytes 2")

        file3 = test_user_dir / "item_3.jpg"
        file3.write_bytes(b"dummy image bytes 3")

        # Test batch ZIP creation
        resp_zip = client.post(
            "/api/gallery/instagram/test_suite_user/batch-zip",
            json={"filenames": ["item_1.jpg", "item_2.mp4"]}
        )
        self.assertEqual(resp_zip.status_code, 200)
        zip_data = resp_zip.json()
        self.assertTrue(zip_data.get("success"))
        self.assertEqual(zip_data.get("items_count"), 2)

        # Test single item deletion
        resp_del_item = client.delete(
            "/api/gallery/instagram/test_suite_user/item?filename=item_1.jpg"
        )
        self.assertEqual(resp_del_item.status_code, 200)
        self.assertFalse(file1.exists())
        self.assertFalse(caption1.exists())  # Matching caption should also be cleaned

        # Test batch deletion
        resp_batch_del = client.post(
            "/api/gallery/instagram/test_suite_user/batch-delete",
            json={"filenames": ["item_2.mp4", "item_3.jpg"]}
        )
        self.assertEqual(resp_batch_del.status_code, 200)
        self.assertEqual(resp_batch_del.json().get("deleted_count"), 2)
        self.assertFalse(file2.exists())
        self.assertFalse(file3.exists())

        # Cleanup test folder
        import shutil
        shutil.rmtree(test_user_dir, ignore_errors=True)

    def test_smart_target_resolver(self):
        from core.job_manager import JobManager
        from core.models import Platform

        # Test URL resolution
        p1, t1 = JobManager.resolve_target("https://www.instagram.com/zuck/")
        self.assertEqual(p1, Platform.INSTAGRAM)
        self.assertIn("zuck", t1)

        p2, t2 = JobManager.resolve_target("https://www.tiktok.com/@khaby.lame")
        self.assertEqual(p2, Platform.TIKTOK)
        self.assertIn("khaby.lame", t2)

        # Test prefix resolution
        p3, t3 = JobManager.resolve_target("ig:natgeo")
        self.assertEqual(p3, Platform.INSTAGRAM)
        self.assertEqual(t3, "natgeo")

        p4, t4 = JobManager.resolve_target("tt:mrbeast")
        self.assertEqual(p4, Platform.TIKTOK)
        self.assertEqual(t4, "mrbeast")

    def test_terminal_command_execution(self):
        from fastapi.testclient import TestClient
        from backend.app import app

        client = TestClient(app)

        # Test help command
        resp_help = client.post("/api/terminal/execute", json={"command": "help"})
        self.assertEqual(resp_help.status_code, 200)
        self.assertTrue(resp_help.json().get("success"))
        self.assertIn("MEDIAVAULT TERMINAL COMMANDS", resp_help.json().get("output"))

        # Test list command
        resp_list = client.post("/api/terminal/execute", json={"command": "list"})
        self.assertEqual(resp_list.status_code, 200)
        self.assertTrue(resp_list.json().get("success"))
        self.assertIn("Downloaded Media Archives", resp_list.json().get("output"))

        # Test storage command
        resp_storage = client.post("/api/terminal/execute", json={"command": "storage"})
        self.assertEqual(resp_storage.status_code, 200)
        self.assertTrue(resp_storage.json().get("success"))
        self.assertIn("Storage Breakdown", resp_storage.json().get("output"))

        # Test jobs command
        resp_jobs = client.post("/api/terminal/execute", json={"command": "jobs"})
        self.assertEqual(resp_jobs.status_code, 200)
        self.assertTrue(resp_jobs.json().get("success"))

        # Test cancel all command
        resp_cancel = client.post("/api/terminal/execute", json={"command": "cancel all"})
        self.assertEqual(resp_cancel.status_code, 200)
        self.assertTrue(resp_cancel.json().get("success"))

    def test_batch_download_api(self):
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from backend.app import app

        client = TestClient(app)

        with patch("core.instagram_downloader.instagram_downloader.download_user", return_value={"success": True, "downloaded_count": 1}), \
             patch("core.tiktok_downloader.tiktok_downloader.download_user", return_value={"success": True, "downloaded_count": 1}):
            
            # Test batch download trigger
            resp_batch = client.post("/api/download/batch", json={
                "targets": ["@zuck", "tt:khaby.lame"],
                "limit": 5
            })
            self.assertEqual(resp_batch.status_code, 200)
            batch_data = resp_batch.json()
            self.assertTrue(batch_data.get("success"))
            self.assertEqual(batch_data.get("count"), 2)
            self.assertEqual(len(batch_data.get("job_ids")), 2)

            # Test cancel-all endpoint
            resp_cancel_all = client.post("/api/jobs/cancel-all")
            self.assertEqual(resp_cancel_all.status_code, 200)
            self.assertTrue(resp_cancel_all.json().get("success"))

    def test_proxy_manager_and_api(self):
        from fastapi.testclient import TestClient
        from backend.app import app
        from core.proxy_manager import proxy_manager

        client = TestClient(app)
        proxy_manager.clear_proxies()

        # 1. Status when empty
        resp = client.get("/api/proxy/status")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("total_count"), 0)

        # 2. Add proxies
        resp_add = client.post("/api/proxy/add", json={"proxies": ["http://proxy1.test:8080", "socks5://proxy2.test:1080"]})
        self.assertEqual(resp_add.status_code, 200)
        self.assertEqual(resp_add.json().get("total"), 2)

        # 3. Rotate proxy
        resp_rotate = client.post("/api/proxy/rotate")
        self.assertEqual(resp_rotate.status_code, 200)
        self.assertTrue(resp_rotate.json().get("success"))

        # 4. Terminal proxy list command
        resp_term = client.post("/api/terminal/execute", json={"command": "proxy list"})
        self.assertEqual(resp_term.status_code, 200)
        self.assertIn("PROXY POOL STATUS", resp_term.json().get("output"))

        # 5. Toggle proxy
        resp_toggle = client.post("/api/proxy/toggle", json={"enabled": False})
        self.assertEqual(resp_toggle.status_code, 200)
        self.assertFalse(resp_toggle.json().get("enabled"))

        # Cleanup
        proxy_manager.clear_proxies()
        proxy_manager.set_enabled(True)


if __name__ == "__main__":
    unittest.main()


