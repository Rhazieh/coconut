"""Unit tests for Velum's XDG configuration persistence."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src" / "velum"
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
                sample_md = Path(td) / "demo.md"
                sample_md.write_text("# Demo\n", encoding="utf-8")

                loaded_default = config.load_config()
                self.assertEqual(loaded_default["font_size"], 18)
                self.assertEqual(loaded_default["theme"], "warm-dark")
                self.assertEqual(loaded_default["language"], "auto")

                loaded_default["font_size"] = 48
                loaded_default["theme"] = "invalid-theme"
                loaded_default["language"] = "es"
                config.add_recent_file(loaded_default, str(sample_md))
                config.add_recent_file(loaded_default, str(sample_md))
                config.save_config(loaded_default)

                reloaded = config.load_config()
                self.assertEqual(reloaded["font_size"], config.MAX_FONT_SIZE)
                self.assertEqual(reloaded["theme"], "warm-dark")
                self.assertEqual(reloaded["language"], "es")
                self.assertEqual(reloaded["recent_files"], [str(sample_md.resolve())])
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


if __name__ == "__main__":
    unittest.main()
