"""Unit tests for Coconut's Markdown, Code, Plain-Text, and EPUB renderers."""

from __future__ import annotations

import base64
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

SRC_DIR = Path(__file__).resolve().parent.parent / "src" / "coconut"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import renderer  # noqa: E402


def _build_sample_epub(epub_path: Path) -> None:
    """Create a valid minimal EPUB archive with container.xml, OPF, NCX, 2 chapters, and an image."""
    tiny_png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    content_opf = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Coconut Field Guide</dc:title>
    <dc:creator>Maximiliano Cano</dc:creator>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="ch1" href="text/ch1.xhtml" media-type="application/xhtml+xml"/>
    <item id="ch2" href="text/ch2.xhtml" media-type="application/xhtml+xml"/>
    <item id="cover" href="images/dot.png" media-type="image/png"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="ch1"/>
    <itemref idref="ch2"/>
  </spine>
</package>
"""
    toc_ncx = """<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <navMap>
    <navPoint id="navPoint-1" playOrder="1">
      <navLabel><text>1. Calm Typography</text></navLabel>
      <content src="text/ch1.xhtml"/>
    </navPoint>
    <navPoint id="navPoint-2" playOrder="2">
      <navLabel><text>2. Offline Architecture</text></navLabel>
      <content src="text/ch2.xhtml"/>
    </navPoint>
  </navMap>
</ncx>
"""
    ch1_xhtml = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 1</title><script>alert('bad')</script></head>
<body>
  <h1>1. Calm Typography</h1>
  <p>Reading comfort on Linux with <a href="ch2.xhtml">Next Chapter</a>.</p>
  <img src="../images/dot.png" alt="Dot" onerror="alert(1)"/>
  <h2>Sub-heading Detail</h2>
  <p>More content here.</p>
</body>
</html>
"""
    ch2_xhtml = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 2</title></head>
<body>
  <p>Local-first and fast without bloated dependencies.</p>
</body>
</html>
"""
    with zipfile.ZipFile(epub_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr("META-INF/container.xml", container_xml)
        zf.writestr("OEBPS/content.opf", content_opf)
        zf.writestr("OEBPS/toc.ncx", toc_ncx)
        zf.writestr("OEBPS/text/ch1.xhtml", ch1_xhtml)
        zf.writestr("OEBPS/text/ch2.xhtml", ch2_xhtml)
        zf.writestr("OEBPS/images/dot.png", tiny_png)


class RendererTests(unittest.TestCase):
    def test_frontmatter_stripped_but_leading_hr_kept(self) -> None:
        md_with_fm = "---\ntitle: Note\ntags: [linux]\n---\n\n# Heading\n\nBody text.\n"
        doc = renderer.render_markdown_text(md_with_fm, filename="note.md")
        self.assertNotIn("tags:", doc["html"])
        self.assertIn("<h1 id=\"heading\">Heading</h1>", doc["html"])
        self.assertEqual(doc["title"], "Heading")
        self.assertTrue(doc["editable"])

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

    def test_render_code_files_and_symbol_outline(self) -> None:
        py_src = (
            "class ReaderEngine:\n"
            "    def render_page(self, text: str) -> str:\n"
            "        return text\n\n"
            "async def main_loop():\n"
            "    pass\n"
        )
        doc = renderer.render_code_text(py_src, filename="engine.py")
        self.assertTrue(doc["is_code"])
        self.assertTrue(doc["editable"])
        self.assertEqual(doc["language"], "python")
        self.assertIn('data-code-file="true"', doc["html"])
        self.assertIn("class ReaderEngine:", doc["html"])
        toc_texts = [item["text"] for item in doc["toc"]]
        self.assertIn("ReaderEngine", toc_texts)
        self.assertIn("render_page", toc_texts)
        self.assertIn("main_loop", toc_texts)

        with tempfile.TemporaryDirectory() as td:
            ts_file = Path(td) / "app.tsx"
            ts_file.write_text(
                "export interface Props { title: string; }\n"
                "export function Header(p: Props) { return <h1>{p.title}</h1>; }\n",
                encoding="utf-8",
            )
            ts_doc = renderer.render_document_file(ts_file)
            self.assertEqual(ts_doc["language"], "tsx")
            self.assertTrue(ts_doc["is_code"])
            self.assertIn("&lt;h1&gt;", ts_doc["html"])
            ts_toc = [item["text"] for item in ts_doc["toc"]]
            self.assertIn("Props", ts_toc)
            self.assertIn("Header", ts_toc)

    def test_render_plain_text_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            txt_file = Path(td) / "notes.txt"
            txt_file.write_text(
                "INTRODUCTION\nWelcome to plain text.\n\nCONFIGURATION\nLine 2 <escaped>.\n",
                encoding="utf-8",
            )
            doc = renderer.render_document_file(txt_file)
            self.assertEqual(doc["format"], "text")
            self.assertTrue(doc["editable"])
            self.assertIn("&lt;escaped&gt;", doc["html"])
            self.assertEqual(len(doc["toc"]), 2)
            self.assertEqual(doc["toc"][0]["text"], "Introduction")

    def test_render_epub_file_chapters_toc_images_and_sanitization(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            epub_path = Path(td) / "guide.epub"
            _build_sample_epub(epub_path)

            doc = renderer.render_document_file(epub_path)
            self.assertTrue(doc["is_epub"])
            self.assertFalse(doc["editable"])
            self.assertEqual(doc["title"], "Coconut Field Guide")
            self.assertEqual(doc["author"], "Maximiliano Cano")
            self.assertEqual(doc["chapter_count"], 2)

            toc_titles = [item["text"] for item in doc["toc"]]
            self.assertIn("1. Calm Typography", toc_titles)
            self.assertIn("2. Offline Architecture", toc_titles)
            self.assertIn("Sub-heading Detail", toc_titles)

            html_out = doc["html"]
            self.assertIn('id="epub-chapter-1"', html_out)
            self.assertIn('id="epub-chapter-2"', html_out)
            self.assertIn('href="#epub-chapter-2"', html_out)
            self.assertIn("data:image/png;base64,", html_out)
            self.assertNotIn("<script", html_out.lower())
            self.assertNotIn("onerror", html_out.lower())


if __name__ == "__main__":
    unittest.main()
