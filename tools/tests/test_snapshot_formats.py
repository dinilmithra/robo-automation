"""Check environment flags and the files produced by actual snapshot methods."""
import ast
import itertools
import json
import logging
import os
from pathlib import Path
import re
import runpy
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

PROJECT = Path(__file__).resolve().parents[2]
WORKSPACE = PROJECT.parent
SnapshotConfig = runpy.run_path(str(PROJECT / "robo_automation/config.py"))["SnapshotConfig"]


def snapshot_classes():
    path = PROJECT / "robo_automation/snapshot_evidence.py"
    tree = ast.parse(path.read_text())
    selected = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in {"_token", "SnapshotWriter", "SnapshotService"}]
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    ns = dict(Path=Path, re=re, time=time, json=json, os=os, threading=threading,
              logger=logging.getLogger("snapshot-format-test"), _raw_page=lambda value: value,
              current_correlation=lambda: {"process_id": "case1"},
              FailureCoverage=lambda *args: SimpleNamespace(process_id=args[0], error_type=args[1], error_text=args[2]))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future, *selected], type_ignores=[])), str(path), "exec"), ns)
    return ns["SnapshotWriter"], ns["SnapshotService"]


Writer, Service = snapshot_classes()


class SnapshotFormatTests(unittest.TestCase):
    def page(self):
        class Page:
            def goto(self, url):
                if self.failure:
                    raise self.failure
                return "navigated"
        page = Page()
        page.url, page.failure = "https://example.invalid/", None
        page.is_closed = Mock(return_value=False)
        page.content = Mock(return_value="<html><body>Snapshot DOM</body></html>")
        def screenshot(**kwargs):
            Path(kwargs["path"]).write_bytes(b"test screenshot")
        page.screenshot = Mock(side_effect=screenshot)
        return page

    def test_defaults_keep_both_formats_without_enabling_capture(self):
        with patch.dict(os.environ, {}, clear=True):
            config = SnapshotConfig.from_env()
        self.assertTrue(config.images_enabled and config.html_enabled)
        self.assertFalse(config.enabled)

    def test_flags_parse_independently(self):
        for images, html in itertools.product(("Y", "N"), repeat=2):
            with self.subTest(images=images, html=html), patch.dict(os.environ, {
                "CAPTURE_SNAPSHOT_IMAGES": images, "CAPTURE_SNAPSHOT_HTML": html,
                "CAPTURE_ACTION_SNAPSHOTS": "N", "CAPTURE_FAILURE_SNAPSHOTS": "Y"}, clear=True):
                config = SnapshotConfig.from_env()
                self.assertEqual(config.images_enabled, images == "Y")
                self.assertEqual(config.html_enabled, html == "Y")
                self.assertFalse(config.action_enabled)
                self.assertTrue(config.failure_enabled)

    def test_blank_flags_keep_compatibility_defaults(self):
        with patch.dict(os.environ, {"CAPTURE_SNAPSHOT_IMAGES": "", "CAPTURE_SNAPSHOT_HTML": " "}, clear=True):
            config = SnapshotConfig.from_env()
        self.assertTrue(config.images_enabled and config.html_enabled)

    def assert_files(self, root, page, images, html, count):
        self.assertEqual(len(list(root.rglob("*.png"))), count if images else 0)
        self.assertEqual(len(list(root.rglob("*.html"))), count if html else 0)
        self.assertEqual(len(list(root.rglob("*.json"))), count)
        self.assertEqual(page.screenshot.call_count, count if images else 0)
        self.assertEqual(page.content.call_count, count if html else 0)
        self.assertEqual((root / "screenshots").exists(), images)
        self.assertEqual((root / "html").exists(), html)
        for file in root.rglob("*.json"):
            self.assertEqual(json.loads(file.read_text())["process_id"], "case1")
        for file in root.rglob("*.html"):
            self.assertIn("Snapshot DOM", file.read_text())

    def test_writer_all_format_combinations_create_only_enabled_artifacts(self):
        for images, html in itertools.product((True, False), repeat=2):
            with self.subTest(images=images, html=html), tempfile.TemporaryDirectory() as folder:
                root, page = Path(folder), self.page()
                writer = Writer(root, "gw1", full_page=True, images_enabled=images, html_enabled=html)
                self.assertTrue(writer.capture(page, stem="example", metadata={"process_id": "case1"}))
                self.assert_files(root, page, images, html, 1)
                if images:
                    self.assertTrue(page.screenshot.call_args.kwargs["full_page"])

    def test_action_snapshots_share_format_policy_for_before_and_after(self):
        for images, html in itertools.product((True, False), repeat=2):
            with self.subTest(images=images, html=html), tempfile.TemporaryDirectory() as folder:
                root, page = Path(folder), self.page()
                service = Service(SnapshotConfig(action_enabled=True, images_enabled=images, html_enabled=html), SimpleNamespace(action_snapshots=root), worker_id="gw1")
                service._patch(type(page), "goto", "page")
                try:
                    self.assertEqual(page.goto("https://example.invalid/next"), "navigated")
                finally:
                    service.stop()
                self.assert_files(root, page, images, html, 2)
                phases = {json.loads(f.read_text())["phase"] for f in root.rglob("*.json")}
                self.assertEqual(phases, {"before", "after"})

    def test_failure_snapshots_share_independent_format_policy(self):
        for images, html in itertools.product((True, False), repeat=2):
            with self.subTest(images=images, html=html), tempfile.TemporaryDirectory() as folder:
                root, page = Path(folder), self.page()
                service = Service(SnapshotConfig(failure_enabled=True, images_enabled=images, html_enabled=html), SimpleNamespace(action_snapshots=root), worker_id="gw1")
                self.assertTrue(service.capture_failure(page, nodeid="case", phase="call", details="failed"))
                self.assert_files(root, page, images, html, 1)
                self.assertEqual(json.loads(next(root.rglob("*.json")).read_text())["status"], "failed")

    def test_metadata_only_preserves_action_failure_and_deduplication(self):
        with tempfile.TemporaryDirectory() as folder:
            root, page = Path(folder), self.page()
            service = Service(SnapshotConfig(action_enabled=True, failure_enabled=True, images_enabled=False, html_enabled=False), SimpleNamespace(action_snapshots=root), worker_id="gw1")
            page.failure = ValueError("business action failed")
            service._patch(type(page), "goto", "page")
            try:
                with self.assertRaisesRegex(ValueError, "business action failed"):
                    page.goto("https://example.invalid/next")
            finally:
                service.stop()
            self.assertFalse(service.capture_failure(page, nodeid="case", phase="call", details="business action failed"))
            self.assert_files(root, page, False, False, 2)
            payloads = [json.loads(f.read_text()) for f in root.rglob("*.json")]
            self.assertTrue(any(p.get("error") == "business action failed" for p in payloads))

    def test_disabled_failure_policy_does_not_capture_even_if_formats_enabled(self):
        with tempfile.TemporaryDirectory() as folder:
            root, page = Path(folder), self.page()
            service = Service(SnapshotConfig(), SimpleNamespace(action_snapshots=root), worker_id="gw1")
            self.assertFalse(service.capture_failure(page, nodeid="case", phase="call"))
            self.assertEqual(list(root.iterdir()), [])
            page.screenshot.assert_not_called()
            page.content.assert_not_called()

    def test_existing_artifacts_are_preserved_when_formats_disabled(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            png, html = root / "screenshots/old.png", root / "html/old.html"
            for file in (png, html):
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text("prior run")
            writer = Writer(root, "gw1", images_enabled=False, html_enabled=False)
            self.assertTrue(writer.capture(self.page(), stem="new", metadata={"process_id": "case1"}))
            self.assertEqual(png.read_text(), "prior run")
            self.assertEqual(html.read_text(), "prior run")

    def test_metadata_without_browser_still_works_with_formats_disabled(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            service = Service(SnapshotConfig(failure_enabled=True, images_enabled=False, html_enabled=False), SimpleNamespace(action_snapshots=root), worker_id="gw1")
            self.assertTrue(service.capture_failure(None, nodeid="case", phase="setup"))
            self.assertEqual(len(list(root.rglob("*.json"))), 1)
            self.assertFalse((root / "screenshots").exists())
            self.assertFalse((root / "html").exists())

    def test_core_env_and_jenkins_expose_both_flags(self):
        core = WORKSPACE / "core-automation"
        for name in (".env.uat", ".env.test", ".env.test-onm"):
            text = (core / name).read_text()
            for flag in ("CAPTURE_SNAPSHOT_IMAGES", "CAPTURE_SNAPSHOT_HTML"):
                self.assertEqual(text.count(flag + "=Y"), 1)
        for name in ("Jenkinsfile", "Jenkinsfile.uat", "Jenkinsfile.test", "Jenkinsfile.test-onm"):
            text = (core / "scripts/jenkin" / name).read_text()
            for flag in ("CAPTURE_SNAPSHOT_IMAGES", "CAPTURE_SNAPSHOT_HTML"):
                self.assertIn(f"name: '{flag}'", text)
                self.assertIn('${params.' + flag + " ? 'Y' : 'N'}", text)


if __name__ == "__main__":
    unittest.main()
