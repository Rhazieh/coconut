"""Unit tests for Coconut's Markdown renderer and HTML sanitizer."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SRC_DIR = Path(__file__).resolve().parent.parent / "src" / "coconut"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import renderer  # noqa: E402


class RendererTests(unittest.TestCase):
    def test_frontmatter_stripped_but_leading_hr_kept(self) -> None:
        md_with_fm = "---\ntitle: Note\ntags: [linux]\n---\n\n# Heading\n\nBody text.\n"
        doc = renderer.render_markdown_text(md_with_fm, filename="note.md")
        self.assertNotIn("tags:", doc["html"])
        self.assertIn("<h1 id=\"heading\">Heading</h1>", doc["html"])
        self.assertEqual(doc["title"], "Heading")

        md_with_hr = "---\n\n# After Rule\n\nStill visible.\n"
        doc2 = renderer.render_markdown_text(md_with_hr, filename="rule.md")
        self.assertIn("<hr", doc2["html"])
        self.assertIn("After Rule", doc2["html"])

    def test_gfm_features_tables_tasklists_strikethrough_code(self) -> None:
        md = (
            "# Spec\n\n"
            "Text with ~~removed~~ and https://example.org autolink.\n\n"
            "- [x] Done\n"
            "- [ ] Pending\n"
            "  ```python\n"
            "  print(42)\n"
            "  ```\n\n"
            "| Key | Value |\n"
            "|-----|-------|\n"
            "| A   | 1     |\n"
        )
        doc = renderer.render_markdown_text(md, filename="spec.md")
        html = doc["html"]
        self.assertIn("<del>removed</del>", html)
        self.assertIn('href="https://example.org"', html)
        self.assertIn('type="checkbox"', html)
        self.assertIn("checked", html)
        self.assertIn('<div class="table-wrap"><table>', html)
        self.assertIn('data-lang="python"', html)

    def test_heading_slugs_accents_duplicates_and_toc(self) -> None:
        md = (
            "# Guía Rápida\n"
            "## Sección\n"
            "## Sección\n"
            "### Detalle Técnico\n"
            "#### Ignorado en TOC\n"
        )
        doc = renderer.render_markdown_text(md, filename="guia.md")
        self.assertEqual(
            doc["toc"],
            [
                {"level": 1, "id": "guia-rapida", "text": "Guía Rápida"},
                {"level": 2, "id": "seccion", "text": "Sección"},
                {"level": 2, "id": "seccion-2", "text": "Sección"},
                {"level": 3, "id": "detalle-tecnico", "text": "Detalle Técnico"},
            ],
        )
        self.assertIn('<h4 id="ignorado-en-toc">', doc["html"])

    def test_relative_links_and_images_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            md = "[Guide](docs/sub.md#intro) and ![Pic](./img/chart.png)"
            doc = renderer.render_markdown_text(md, base_dir=base, filename="index.md")
            expected_doc = (base / "docs" / "sub.md").resolve().as_uri() + "#intro"
            expected_img = (base / "img" / "chart.png").resolve().as_uri()
            self.assertIn(f'href="{expected_doc}"', doc["html"])
            self.assertIn(f'src="{expected_img}"', doc["html"])

    def test_xss_sanitization(self) -> None:
        md = (
            '<script>alert("xss")</script>\n'
            '<SCRIPT>alert(2)</SCRIPT>\n'
            '<iframe src="https://evil.example"></iframe>\n'
            '<object data="evil.swf">bad</object>\n'
            '<img src="ok.png" onerror="alert(1)">\n'
            '<svg onload="alert(3)"><circle cx="5" cy="5" r="5"/></svg>\n\n'
            '<a href="javascript:alert(1)">raw</a>\n\n'
            '[bad](javascript:alert(1)) '
            '[data-html](data:text/html;base64,PHNjcmlwdD4=)\n'
        )
        doc = renderer.render_markdown_text(md, base_dir=Path("/tmp"), filename="xss.md")
        low = doc["html"].lower()
        self.assertNotIn("<script", low)
        self.assertNotIn("<iframe", low)
        self.assertNotIn("<object", low)
        self.assertNotIn("onerror", low)
        self.assertNotIn("onload", low)
        self.assertNotIn("javascript:", low)
        self.assertNotIn("data:text/html", low)

    def test_python_markdown_fallback(self) -> None:
        md = "# Fallback\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n```sh\necho ok\n```\n"
        with mock.patch.object(renderer, "_init_cmark_gfm", return_value=False):
            doc = renderer.render_markdown_text(md, filename="fb.md")
        self.assertEqual(doc["title"], "Fallback")
        self.assertIn('<div class="table-wrap"><table>', doc["html"])
        self.assertIn('data-lang="sh"', doc["html"])

    def test_render_markdown_file_utf8_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "sample.md"
            f.write_bytes(b"# Title\n\nValid text " + b"\xff\xfe" + b" end\n")
            doc = renderer.render_markdown_file(f)
            self.assertEqual(doc["filename"], "sample.md")
            self.assertEqual(doc["title"], "Title")
            self.assertIn("Valid text", doc["html"])


if __name__ == "__main__":
    unittest.main()
