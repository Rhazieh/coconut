"""Unit tests for Coconut's XDG configuration, session persistence, and translate URLs."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src" / "coconut"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import config  # noqa: E402


class ConfigTests(unittest.TestCase):
    def test_defaults_and_clamping(self) -> None:
        self.assertEqual(config.clamp_font_size(4), config.MIN_FONT_SIZE)
        self.assertEqual(config.clamp_font_size(99), config.MAX_FONT_SIZE)
        self.assertEqual(config.clamp_font_size("bad"), config.DEFAULT_FONT_SIZE)
        self.assertEqual(config.clamp_font_size(22), 22)

    def test_xdg_roundtrip_and_sanitization(self) -> None:
        prev = os.environ.get("XDG_CONFIG_HOME")
        with tempfile.TemporaryDirectory() as td:
            os.environ["XDG_CONFIG_HOME"] = td
            try:
                doc_a = Path(td) / "alpha.md"
                doc_b = Path(td) / "beta.md"
                doc_a.write_text("# Alpha\n", encoding="utf-8")
                doc_b.write_text("# Beta\n", encoding="utf-8")

                loaded = config.load_config()
                self.assertEqual(loaded["font_size"], 18)
                self.assertEqual(loaded["theme"], "warm-dark")
                self.assertEqual(loaded["language"], "auto")
                self.assertTrue(loaded["show_progress_bar"])
                self.assertTrue(loaded["auto_reload"])
                self.assertTrue(loaded["restore_session"])
                self.assertTrue(loaded["translate_enabled"])
                self.assertEqual(loaded["translate_source"], "auto")
                self.assertEqual(loaded["translate_target"], "es")
                self.assertEqual(loaded["shortcuts"], config.DEFAULT_SHORTCUTS)

                loaded["font_size"] = 48
                loaded["theme"] = "invalid-theme"
                loaded["language"] = "es"
                loaded["show_progress_bar"] = False
                loaded["translate_source"] = "bad-code"
                loaded["translate_target"] = "auto"  # invalid target
                loaded["open_files"] = [str(doc_a), str(doc_b), "/nonexistent/ghost.md", str(doc_a)]
                loaded["active_file"] = str(doc_b)
                loaded["collapsed_folders"] = ["/tmp/docs", "/tmp/docs"]
                loaded["shortcuts"] = {"open_file": "Ctrl+Shift+O", "unknown_action": "Ctrl+Z"}
                config.add_recent_file(loaded, str(doc_a))
                config.save_config(loaded)

                reloaded = config.load_config()
                self.assertEqual(reloaded["font_size"], config.MAX_FONT_SIZE)
                self.assertEqual(reloaded["theme"], "warm-dark")
                self.assertEqual(reloaded["language"], "es")
                self.assertFalse(reloaded["show_progress_bar"])
                self.assertEqual(reloaded["translate_source"], "auto")
                self.assertEqual(reloaded["translate_target"], "es")
                self.assertEqual(
                    reloaded["open_files"],
                    [str(doc_a.resolve()), str(doc_b.resolve())],
                )
                self.assertEqual(reloaded["active_file"], str(doc_b.resolve()))
                self.assertEqual(reloaded["collapsed_folders"], ["/tmp/docs"])
                self.assertEqual(reloaded["shortcuts"]["open_file"], "Ctrl+Shift+O")
                self.assertNotIn("unknown_action", reloaded["shortcuts"])
                self.assertEqual(reloaded["recent_files"], [str(doc_a.resolve())])
            finally:
                if prev is None:
                    os.environ.pop("XDG_CONFIG_HOME", None)
                else:
                    os.environ["XDG_CONFIG_HOME"] = prev

    def test_recent_files_capped_at_max(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cfg = dict(config.DEFAULT_CONFIG)
            for idx in range(config.MAX_RECENT_FILES + 4):
                p = Path(td) / f"doc-{idx}.md"
                p.write_text("# Doc\n", encoding="utf-8")
                config.add_recent_file(cfg, str(p))
            self.assertEqual(len(cfg["recent_files"]), config.MAX_RECENT_FILES)
            self.assertTrue(cfg["recent_files"][0].endswith(f"doc-{config.MAX_RECENT_FILES + 3}.md"))

    def test_build_translate_url_encoding_and_truncation(self) -> None:
        url = config.build_translate_url("hello world & linux", source="en", target="es")
        self.assertEqual(
            url,
            "https://translate.google.com/?sl=en&tl=es&text=hello%20world%20%26%20linux&op=translate",
        )
        long_url = config.build_translate_url("a" * 6000, source="bad", target="auto", max_chars=100)
        self.assertIn("sl=auto&tl=es", long_url)
        self.assertIn("text=" + ("a" * 100) + "&op=translate", long_url)


if __name__ == "__main__":
    unittest.main()
