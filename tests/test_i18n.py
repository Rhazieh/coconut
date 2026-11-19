"""Unit tests for Velum EN/ES localization and translation language tables."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src" / "velum"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import config  # noqa: E402
import i18n  # noqa: E402


class I18nTests(unittest.TestCase):
    def test_string_key_parity(self) -> None:
        self.assertEqual(set(i18n.STRINGS["en"].keys()), set(i18n.STRINGS["es"].keys()))

    def test_shortcut_action_labels_present(self) -> None:
        for action in config.DEFAULT_SHORTCUTS:
            key = f"sc_{action}"
            self.assertIn(key, i18n.STRINGS["en"])
            self.assertIn(key, i18n.STRINGS["es"])

    def test_translate_language_options(self) -> None:
        en_langs = i18n.get_translate_languages("en")
        es_langs = i18n.get_translate_languages("es")
        self.assertEqual(len(en_langs), len(config.TRANSLATE_LANGUAGES))
        self.assertEqual(len(es_langs), len(config.TRANSLATE_LANGUAGES))
        self.assertEqual(en_langs[0]["code"], "auto")
        self.assertNotEqual(en_langs[1]["label"], es_langs[1]["label"])

    def test_language_resolution(self) -> None:
        self.assertEqual(i18n.resolve_language("es", env={"LANG": "en_US.UTF-8"}), "es")
        self.assertEqual(i18n.resolve_language("en", env={"LANG": "es_AR.UTF-8"}), "en")
        self.assertEqual(i18n.resolve_language("auto", env={"LANG": "es_AR.UTF-8"}), "es")
        self.assertEqual(i18n.resolve_language("auto", env={"LANGUAGE": "es:en"}), "es")
        self.assertEqual(i18n.resolve_language("auto", env={"LANG": "en_US.UTF-8"}), "en")


if __name__ == "__main__":
    unittest.main()
