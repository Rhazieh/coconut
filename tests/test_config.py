"""Unit tests for Coconut's XDG configuration, extensions, customization settings, and translate URLs."""

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
                self.assertEqual(loaded["reading_width"], "medium")
                self.assertEqual(loaded["line_height"], "comfortable")
                self.assertTrue(loaded["show_line_numbers"])
                self.assertEqual(loaded["accent_color"], "default")
                self.assertEqual(loaded["code_style"], "card")
                self.assertEqual(loaded["enabled_extensions"], ["txt"])
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
                loaded["reading_width"] = "wide"
                loaded["line_height"] = "spacious"
                loaded["show_line_numbers"] = False
                loaded["accent_color"] = "sage"
                loaded["code_style"] = "contrast"
                loaded["enabled_extensions"] = ["epub", ".py", "typescript", "invalid_ext", "py"]
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
                self.assertEqual(reloaded["reading_width"], "wide")
                self.assertEqual(reloaded["line_height"], "spacious")
                self.assertFalse(reloaded["show_line_numbers"])
                self.assertEqual(reloaded["accent_color"], "sage")
                self.assertEqual(reloaded["code_style"], "contrast")
                self.assertEqual(reloaded["enabled_extensions"], ["epub", "ts", "py"])
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

    def test_invalid_customization_choices_fallback_to_defaults(self) -> None:
        sanitized = config._sanitize_config({
            "reading_width": "huge",
            "line_height": "tiny",
            "accent_color": "neon-pink",
            "code_style": "3d",
            "enabled_extensions": "not-a-list",
        })
        self.assertEqual(sanitized["reading_width"], "medium")
        self.assertEqual(sanitized["line_height"], "comfortable")
        self.assertEqual(sanitized["accent_color"], "default")
        self.assertEqual(sanitized["code_style"], "card")
        self.assertEqual(sanitized["enabled_extensions"], ["txt"])

    def test_extensions_catalog_and_file_support_filters(self) -> None:
        required_suffixes = {
            ".txt",
            ".epub",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".py",
            ".java",
            ".html",
            ".css",
            ".json",
            ".yaml",
            ".yml",
            ".sh",
            ".sql",
            ".c",
            ".cpp",
            ".rs",
            ".go",
            ".xml",
        }
        all_known = config.get_all_known_file_extensions()
        for ext in required_suffixes:
            self.assertIn(ext, all_known, f"Missing support for {ext}")

        cfg = dict(config.DEFAULT_CONFIG)
        cfg["enabled_extensions"] = ["epub", "py", "js"]

        self.assertTrue(config.is_file_supported("README.md", cfg))
        self.assertTrue(config.is_file_supported("book.epub", cfg))
        self.assertTrue(config.is_file_supported("script.py", cfg))
        self.assertTrue(config.is_file_supported("Component.jsx", cfg))
        self.assertFalse(config.is_file_supported("main.rs", cfg))
        self.assertFalse(config.is_file_supported("notes.txt", cfg))

        filter_en = config.build_file_dialog_filter(cfg, "en")
        self.assertIn("*.epub", filter_en)
        self.assertIn("*.py", filter_en)
        self.assertIn("*.jsx", filter_en)
        self.assertNotIn("*.rs", filter_en)

        filter_es = config.build_file_dialog_filter(cfg, "es")
        self.assertIn("Archivos compatibles", filter_es)
        self.assertIn("Libros EPUB (*.epub)", filter_es)

        cat_es = config.get_extension_catalog("es", cfg["enabled_extensions"])
        by_id = {item["id"]: item for item in cat_es}
        self.assertTrue(by_id["epub"]["enabled"])
        self.assertTrue(by_id["py"]["enabled"])
        self.assertFalse(by_id["rs"]["enabled"])

    def test_recent_files_capped_at_max(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cfg = dict(config.DEFAULT_CONFIG)
            for idx in range(config.MAX_RECENT_FILES + 4):
                p = Path(td) / f"doc-{idx}.md"
                p.write_text("# Doc\n", encoding="utf-8")
                config.add_recent_file(cfg, str(p))
            self.assertEqual(len(cfg["recent_files"]), config.MAX_RECENT_FILES)
            self.assertTrue(cfg["recent_files"][0].endswith(f"doc-{config.MAX_RECENT_FILES + 3}.md"))

    def test_auto_enable_extensions_and_folder_scan_order(self) -> None:
        cfg = dict(config.DEFAULT_CONFIG)
        cfg["enabled_extensions"] = ["txt"]
        added = config.ensure_extensions_enabled_for_paths(
            cfg, [Path("app.py"), Path("book.epub"), Path("index.tsx"), Path("README.md")]
        )
        self.assertEqual(added, ["py", "epub", "ts"])
        self.assertIn("py", cfg["enabled_extensions"])
        self.assertIn("epub", cfg["enabled_extensions"])
        self.assertIn("ts", cfg["enabled_extensions"])
        # Calling again returns empty list
        self.assertEqual(config.ensure_extensions_enabled_for_paths(cfg, [Path("app.py")]), [])

        self.assertEqual(config.clamp_sidebar_width(50), config.MIN_SIDEBAR_WIDTH)
        self.assertEqual(config.clamp_sidebar_width(999), config.MAX_SIDEBAR_WIDTH)
        self.assertEqual(config.clamp_sidebar_width(310), 310)

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "beta.py").write_text("print(1)\n", encoding="utf-8")
            (root / "alpha.md").write_text("# A\n", encoding="utf-8")
            (root / "ignore.bin").write_bytes(b"\x00\x01")
            sub = root / "src"
            sub.mkdir()
            (sub / "main.rs").write_text("fn main() {}\n", encoding="utf-8")
            git_dir = root / ".git"
            git_dir.mkdir()
            (git_dir / "config.json").write_text("{}\n", encoding="utf-8")

            tree, discovered = config.scan_folder_tree(root)
            discovered_names = {p.name for p in discovered}
            self.assertEqual(discovered_names, {"beta.py", "alpha.md", "main.rs"})
            self.assertEqual([c["name"] for c in tree["children"]], ["src", "alpha.md", "beta.py"])

            # Custom drag-and-drop order respected
            custom = {str(root.resolve()): [str((root / "beta.py").resolve()), str((root / "alpha.md").resolve())]}
            ordered_tree, _ = config.scan_folder_tree(root, custom_order=custom)
            self.assertEqual([c["name"] for c in ordered_tree["children"]], ["beta.py", "alpha.md", "src"])

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
