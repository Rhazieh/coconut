"""Fast, safe GitHub-Flavored Markdown, Code, Plain-Text, and EPUB renderer for Coconut."""

from __future__ import annotations

import base64
import ctypes
import ctypes.util
import html
import posixpath
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from config import CORE_MD_EXTENSIONS, SUFFIX_TO_LANGUAGE

_CMARK_INIT_DONE = False
_CMARK: Any = None
_LIBC: Any = None

_CMARK_OPT_SMART = 1 << 10
_CMARK_OPT_UNSAFE = 1 << 17

_FRONTMATTER_RE = re.compile(r"\A---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)")
_YAML_KEY_RE = re.compile(r"^[A-Za-z0-9_.-]+\s*:")
_WORD_RE = re.compile(r"\S+")
_BODY_RE = re.compile(r"<body\b[^>]*>([\s\S]*?)</body>", re.IGNORECASE)
_TITLE_RE = re.compile(r"<title\b[^>]*>([\s\S]*?)</title>", re.IGNORECASE)
_TAG_STRIP_RE = re.compile(r"<[^>]+>")

_VOID_ELEMENTS = frozenset({
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
})

_DROP_WITH_CONTENT = frozenset({
    "script",
    "style",
    "iframe",
    "object",
    "embed",
    "applet",
    "form",
    "noscript",
    "template",
    "textarea",
    "xmp",
    "plaintext",
    "noembed",
    "noframes",
    "svg",
})

_DROP_TAG_ONLY = frozenset({"meta", "base", "link", "title", "button", "select", "option"})

_SAFE_IMAGE_DATA_RE = re.compile(
    r"^data:image/(?:png|jpeg|jpg|gif|webp|avif);base64,[A-Za-z0-9+/=]+$",
    re.IGNORECASE,
)

_EPUB_IMAGE_MIMES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".avif": "image/avif",
}

_CODE_SYMBOL_PATTERNS: list[tuple[re.Pattern[str], int]] = [
    (re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:pub(?:\([^)]*\))?\s+)?(?:abstract\s+)?(?:class|interface|struct|enum|trait|type)\s+([A-Za-z_][A-Za-z0-9_]*)"), 1),
    (re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:def|fn|func|function)\s+(?:\([^)]*\)\s*)?([A-Za-z_][A-Za-z0-9_]*)"), 2),
    (re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_][A-Za-z0-9_]*)\s*=>"), 2),
    (re.compile(r"^\s*(?:public|private|protected|static|final|synchronized|\s)+[A-Za-z0-9_<>\[\], ?]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^;]*\)\s*\{"), 2),
    (re.compile(r"^\s*CREATE\s+(?:OR\s+REPLACE\s+)?(?:TEMPORARY\s+)?(TABLE|VIEW|FUNCTION|PROCEDURE|INDEX|TRIGGER)\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z0-9_.\"`]+)", re.IGNORECASE), 1),
    (re.compile(r"^([A-Za-z_][A-Za-z0-9_.-]*)\s*:\s*(?:#.*)?$"), 1),
    (re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*\(\)\s*\{"), 2),
]


def _find_shared_lib(stem: str) -> str:
    """Locate a shared library across Debian, Ubuntu, Fedora, and Arch layouts."""
    found = ctypes.util.find_library(stem)
    if found:
        return found
    for base in (
        Path("/usr/lib/x86_64-linux-gnu"),
        Path("/usr/lib/aarch64-linux-gnu"),
        Path("/usr/lib64"),
        Path("/usr/lib"),
    ):
        if base.is_dir():
            matches = sorted(base.glob(f"lib{stem}.so*"))
            if matches:
                return str(matches[0])
    return f"lib{stem}.so"


def _init_cmark_gfm() -> bool:
    """Lazily initialize libcmark-gfm + extensions via ctypes."""
    global _CMARK_INIT_DONE, _CMARK, _LIBC
    if _CMARK_INIT_DONE:
        return _CMARK is not None
    _CMARK_INIT_DONE = True

    try:
        cmark_name = _find_shared_lib("cmark-gfm")
        ext_name = _find_shared_lib("cmark-gfm-extensions")
        cmark = ctypes.CDLL(cmark_name)
        ext = ctypes.CDLL(ext_name)
        libc = ctypes.CDLL(None)

        ext.cmark_gfm_core_extensions_ensure_registered.argtypes = []
        ext.cmark_gfm_core_extensions_ensure_registered.restype = None
        ext.cmark_gfm_core_extensions_ensure_registered()

        cmark.cmark_parser_new.argtypes = [ctypes.c_int]
        cmark.cmark_parser_new.restype = ctypes.c_void_p

        cmark.cmark_find_syntax_extension.argtypes = [ctypes.c_char_p]
        cmark.cmark_find_syntax_extension.restype = ctypes.c_void_p

        cmark.cmark_parser_attach_syntax_extension.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        cmark.cmark_parser_attach_syntax_extension.restype = ctypes.c_int

        cmark.cmark_parser_feed.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
        cmark.cmark_parser_feed.restype = None

        cmark.cmark_parser_finish.argtypes = [ctypes.c_void_p]
        cmark.cmark_parser_finish.restype = ctypes.c_void_p

        cmark.cmark_parser_free.argtypes = [ctypes.c_void_p]
        cmark.cmark_parser_free.restype = None

        cmark.cmark_parser_get_syntax_extensions.argtypes = [ctypes.c_void_p]
        cmark.cmark_parser_get_syntax_extensions.restype = ctypes.c_void_p

        cmark.cmark_render_html.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        cmark.cmark_render_html.restype = ctypes.c_void_p

        cmark.cmark_node_free.argtypes = [ctypes.c_void_p]
        cmark.cmark_node_free.restype = None

        libc.free.argtypes = [ctypes.c_void_p]
        libc.free.restype = None

        _CMARK = cmark
        _LIBC = libc
        return True
    except Exception:
        _CMARK = None
        _LIBC = None
        return False


def _strip_frontmatter(text: str) -> str:
    """Remove leading YAML frontmatter block if present."""
    if text.startswith("\ufeff"):
        text = text[1:]
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return text
    body = m.group(1)
    lines = [ln.strip() for ln in body.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if not lines or any(_YAML_KEY_RE.match(ln) for ln in lines):
        return text[m.end():]
    return text


def _render_cmark_gfm(text: str) -> str:
    """Render GFM markdown to HTML via libcmark-gfm."""
    opts = _CMARK_OPT_SMART | _CMARK_OPT_UNSAFE
    data = text.encode("utf-8")
    parser = _CMARK.cmark_parser_new(opts)
    if not parser:
        raise RuntimeError("cmark_parser_new returned NULL")
    doc = None
    try:
        for ext_name in (b"table", b"strikethrough", b"autolink", b"tasklist", b"tagfilter"):
            ext_ptr = _CMARK.cmark_find_syntax_extension(ext_name)
            if ext_ptr:
                _CMARK.cmark_parser_attach_syntax_extension(parser, ext_ptr)
        _CMARK.cmark_parser_feed(parser, data, len(data))
        doc = _CMARK.cmark_parser_finish(parser)
        if not doc:
            raise RuntimeError("cmark_parser_finish returned NULL")
        exts = _CMARK.cmark_parser_get_syntax_extensions(parser)
        html_ptr = _CMARK.cmark_render_html(doc, opts, exts)
        if not html_ptr:
            raise RuntimeError("cmark_render_html returned NULL")
        try:
            return ctypes.string_at(html_ptr).decode("utf-8", errors="replace")
        finally:
            _LIBC.free(html_ptr)
    finally:
        if doc:
            _CMARK.cmark_node_free(doc)
        _CMARK.cmark_parser_free(parser)


def _render_python_markdown(text: str) -> str:
    """Fallback renderer using python-markdown."""
    import markdown

    return markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "sane_lists", "smarty"],
    )


def _slugify(text: str, used: dict[str, int]) -> str:
    """Create a unique, ASCII-clean heading ID compatible with CSS/JS selectors."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    if not slug:
        slug = "section"
    count = used.get(slug, 0) + 1
    used[slug] = count
    if count > 1:
        return f"{slug}-{count}"
    return slug


def _resolve_url(raw_url: str, base_dir: Path | None, is_image: bool) -> str | None:
    """Sanitize URLs and resolve relative paths to file:// URIs."""
    url = raw_url.strip()
    if not url:
        return ""
    if url.startswith("#"):
        return url

    parsed = urlsplit(url)
    scheme = parsed.scheme.lower()

    if scheme:
        if scheme in ("http", "https", "file"):
            return url
        if scheme == "mailto" and not is_image:
            return url
        if scheme == "data":
            if is_image and _SAFE_IMAGE_DATA_RE.match(url):
                return url
            return None
        return None

    if url.startswith("//"):
        return f"https:{url}"

    frag = f"#{parsed.fragment}" if parsed.fragment else ""
    path_part = unquote(parsed.path)
    if not path_part:
        return frag or ""

    candidate = Path(path_part)
    if candidate.is_absolute():
        return candidate.resolve().as_uri() + frag
    if base_dir is not None:
        return (base_dir / candidate).resolve().as_uri() + frag
    return url


def _format_attrs(attrs: list[tuple[str, str | None]]) -> str:
    if not attrs:
        return ""
    parts: list[str] = []
    for key, val in attrs:
        if val is None or val == "":
            parts.append(key)
        else:
            parts.append(f'{key}="{html.escape(val, quote=True)}"')
    return " " + " ".join(parts)


class _PostProcessor(HTMLParser):
    """Sanitize HTML, extract TOC headings with IDs, resolve URLs, wrap tables."""

    def __init__(
        self,
        base_dir: Path | None,
        used_slugs: dict[str, int] | None = None,
        url_resolver: Any = None,
    ) -> None:
        super().__init__(convert_charrefs=True)
        self.base_dir = base_dir
        self.url_resolver = url_resolver
        self.out: list[str] = []
        self.toc: list[dict[str, Any]] = []
        self.first_h1: str | None = None
        self._used_slugs: dict[str, int] = used_slugs if used_slugs is not None else {}
        self._drop_depth = 0
        self._in_pre = False
        self._heading_level: int | None = None
        self._heading_attrs: list[tuple[str, str | None]] = []
        self._heading_inner: list[str] = []
        self._heading_text: list[str] = []

    def _emit(self, chunk: str) -> None:
        if self._heading_level is not None:
            self._heading_inner.append(chunk)
        else:
            self.out.append(chunk)

    def _filter_attrs(self, tag: str, attrs: list[tuple[str, str | None]]) -> list[tuple[str, str | None]] | None:
        """Filter unsafe attributes; return None if the whole tag should be skipped."""
        cleaned: list[tuple[str, str | None]] = []
        attr_map = {k.lower(): (v or "") for k, v in attrs if k}

        if tag == "input":
            if attr_map.get("type", "").lower() != "checkbox":
                return None
            cleaned.append(("type", "checkbox"))
            cleaned.append(("disabled", ""))
            if "checked" in attr_map:
                cleaned.append(("checked", ""))
            return cleaned

        lang_found: str | None = None
        for raw_key, raw_val in attrs:
            if not raw_key:
                continue
            key = raw_key.lower()
            if key.startswith("on") or key in ("srcdoc", "formaction", "style"):
                continue
            val = raw_val if raw_val is not None else ""
            if key in ("href", "src", "poster"):
                if self.url_resolver is not None:
                    safe_url = self.url_resolver(val, is_image=(tag == "img"))
                else:
                    safe_url = _resolve_url(val, self.base_dir, is_image=(tag == "img"))
                if safe_url is None:
                    continue
                val = safe_url
            if tag == "code" and key == "class":
                for cls in val.split():
                    if cls.startswith("language-") and len(cls) > 9:
                        lang_found = cls[9:]
                        break
            cleaned.append((key, val))

        if tag == "code" and self._in_pre and lang_found and "data-lang" not in attr_map:
            cleaned.append(("data-lang", lang_found))
        if tag == "img" and "loading" not in attr_map:
            cleaned.append(("loading", "lazy"))
        return cleaned

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self._drop_depth > 0:
            if tag not in _VOID_ELEMENTS:
                self._drop_depth += 1
            return

        if tag in _DROP_WITH_CONTENT:
            if tag not in _VOID_ELEMENTS:
                self._drop_depth = 1
            return

        if tag in _DROP_TAG_ONLY:
            return

        filtered = self._filter_attrs(tag, attrs)
        if filtered is None:
            return

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6") and self._heading_level is None:
            self._heading_level = int(tag[1])
            self._heading_attrs = [(k, v) for k, v in filtered if k != "id"]
            self._heading_inner = []
            self._heading_text = []
            return

        if tag == "pre":
            self._in_pre = True

        if tag == "table":
            self._emit('<div class="table-wrap"><table>')
            return

        self._emit(f"<{tag}{_format_attrs(filtered)}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self._drop_depth > 0 or tag in _DROP_WITH_CONTENT or tag in _DROP_TAG_ONLY:
            return
        filtered = self._filter_attrs(tag, attrs)
        if filtered is None:
            return
        self._emit(f"<{tag}{_format_attrs(filtered)}>")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._drop_depth > 0:
            if tag not in _VOID_ELEMENTS:
                self._drop_depth -= 1
            return
        if tag in _VOID_ELEMENTS or tag in _DROP_TAG_ONLY:
            return

        if self._heading_level is not None and tag == f"h{self._heading_level}":
            level = self._heading_level
            plain = " ".join("".join(self._heading_text).split()).strip()
            inner_html = "".join(self._heading_inner)
            slug = _slugify(plain, self._used_slugs)

            if level == 1 and self.first_h1 is None and plain:
                self.first_h1 = plain
            if level <= 3 and plain:
                self.toc.append({"level": level, "id": slug, "text": plain})

            attrs = [("id", slug), *self._heading_attrs]
            self._heading_level = None
            self._heading_attrs = []
            self._heading_inner = []
            self._heading_text = []
            self.out.append(f"<h{level}{_format_attrs(attrs)}>{inner_html}</h{level}>")
            return

        if tag == "pre":
            self._in_pre = False
        if tag == "table":
            self._emit("</table></div>")
            return

        self._emit(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if self._drop_depth > 0:
            return
        if self._heading_level is not None:
            self._heading_text.append(data)
        self._emit(html.escape(data, quote=False))


def _read_text_with_fallback(path: Path) -> str:
    """Read UTF-8 text from disk with graceful fallback for non-UTF8 bytes."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def render_markdown_text(text: str, base_dir: Path | None = None, filename: str = "") -> dict[str, Any]:
    """Render raw Markdown string into clean HTML + TOC metadata."""
    cleaned = _strip_frontmatter(text)
    word_count = len(_WORD_RE.findall(cleaned))
    read_minutes = max(1, round(word_count / 220)) if word_count else 0

    if _init_cmark_gfm():
        try:
            raw_html = _render_cmark_gfm(cleaned)
        except Exception:
            raw_html = _render_python_markdown(cleaned)
    else:
        raw_html = _render_python_markdown(cleaned)

    processor = _PostProcessor(base_dir)
    processor.feed(raw_html)
    processor.close()

    fallback_title = Path(filename).stem if filename else "Coconut"
    title = processor.first_h1 or fallback_title
    return {
        "title": title,
        "filename": filename or fallback_title,
        "path": "",
        "html": "".join(processor.out),
        "toc": processor.toc,
        "word_count": word_count,
        "read_minutes": read_minutes,
        "editable": True,
        "format": "markdown",
        "raw_text": text,
    }


def render_markdown_file(path: Path) -> dict[str, Any]:
    """Read a Markdown file from disk and render it."""
    resolved = path.expanduser().resolve()
    text = _read_text_with_fallback(resolved)
    doc = render_markdown_text(text, base_dir=resolved.parent, filename=resolved.name)
    doc["path"] = str(resolved)
    return doc


def render_plain_text(text: str, filename: str = "") -> dict[str, Any]:
    """Render plain text (.txt, .log) into clean HTML paragraphs + optional outline."""
    if text.startswith("\ufeff"):
        text = text[1:]
    word_count = len(_WORD_RE.findall(text))
    read_minutes = max(1, round(word_count / 220)) if word_count else 0

    lines = text.splitlines()
    used_slugs: dict[str, int] = {}
    toc: list[dict[str, Any]] = []
    out_lines: list[str] = []

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        is_heading = False
        heading_text = ""
        heading_level = 2

        if stripped.startswith("#"):
            m = re.match(r"^(#{1,3})\s+(.+)$", stripped)
            if m:
                is_heading = True
                heading_level = len(m.group(1))
                heading_text = m.group(2).strip()
        elif (
            3 <= len(stripped) <= 72
            and stripped.isupper()
            and any(ch.isalpha() for ch in stripped)
            and (idx == 1 or not lines[idx - 2].strip())
        ):
            is_heading = True
            heading_level = 2
            heading_text = stripped.title()

        if is_heading and heading_text:
            slug = _slugify(heading_text, used_slugs)
            toc.append({"level": heading_level, "id": slug, "text": heading_text})
            out_lines.append(
                f'<span id="{slug}" class="txt-heading">{html.escape(line, quote=False)}</span>'
            )
        else:
            out_lines.append(html.escape(line, quote=False))

    body_html = f'<pre class="plain-text-pre">{chr(10).join(out_lines)}</pre>'
    fallback_title = Path(filename).stem if filename else "Coconut"
    title = toc[0]["text"] if toc and toc[0]["level"] == 1 else fallback_title

    return {
        "title": title,
        "filename": filename or fallback_title,
        "path": "",
        "html": body_html,
        "toc": toc,
        "word_count": word_count,
        "read_minutes": read_minutes,
        "editable": True,
        "format": "text",
        "raw_text": text,
    }


def render_text_file(path: Path) -> dict[str, Any]:
    """Read a plain text file from disk and render it."""
    resolved = path.expanduser().resolve()
    text = _read_text_with_fallback(resolved)
    doc = render_plain_text(text, filename=resolved.name)
    doc["path"] = str(resolved)
    return doc


def _extract_code_toc(text: str, lang: str) -> list[dict[str, Any]]:
    """Extract top-level symbols (classes, functions, declarations) for code outline."""
    toc: list[dict[str, Any]] = []
    lines = text.splitlines()

    if lang in ("html", "xml"):
        tag_re = re.compile(r"<(h[1-3]|section|article|main|nav|header|footer)\b([^>]*)>", re.IGNORECASE)
        id_re = re.compile(r'\bid=["\']([^"\']+)["\']', re.IGNORECASE)
        for lineno, line in enumerate(lines, start=1):
            m = tag_re.search(line)
            if m:
                tag_name = m.group(1).lower()
                id_match = id_re.search(m.group(2))
                label = f"<{tag_name}#{id_match.group(1)}>" if id_match else f"<{tag_name}> (L{lineno})"
                toc.append({"level": 1 if tag_name == "h1" else 2, "id": f"L{lineno}", "text": label})
                if len(toc) >= 80:
                    break
        return toc

    if lang == "css":
        sel_re = re.compile(r"^([@#.:A-Za-z0-9_\-\[\]=\"' >+~,]+)\s*\{")
        for lineno, line in enumerate(lines, start=1):
            m = sel_re.match(line.strip())
            if m:
                label = " ".join(m.group(1).split())[:60]
                if label:
                    toc.append({"level": 1 if label.startswith("@") else 2, "id": f"L{lineno}", "text": label})
                if len(toc) >= 80:
                    break
        return toc

    if lang == "json":
        key_re = re.compile(r'^\s{1,4}"([^"]+)"\s*:')
        for lineno, line in enumerate(lines, start=1):
            m = key_re.match(line)
            if m:
                toc.append({"level": 1, "id": f"L{lineno}", "text": m.group(1)})
                if len(toc) >= 80:
                    break
        return toc

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//", "/*", "*", "--")):
            continue
        for pattern, level in _CODE_SYMBOL_PATTERNS:
            m = pattern.match(line)
            if m:
                if m.lastindex and m.lastindex >= 2:
                    sym = f"{m.group(1).upper()} {m.group(2)}"
                else:
                    sym = m.group(1)
                indent = len(line) - len(line.lstrip())
                eff_level = 2 if indent >= 2 and level == 1 else level
                toc.append({"level": eff_level, "id": f"L{lineno}", "text": sym})
                break
        if len(toc) >= 100:
            break
    return toc


def render_code_text(text: str, filename: str = "", lang: str | None = None) -> dict[str, Any]:
    """Render a source code file with syntax language metadata and symbol outline."""
    if text.startswith("\ufeff"):
        text = text[1:]

    suffix = Path(filename).suffix.lower() if filename else ""
    resolved_lang = (lang or SUFFIX_TO_LANGUAGE.get(suffix) or suffix.lstrip(".") or "plaintext").lower()

    word_count = len(_WORD_RE.findall(text))
    read_minutes = max(1, round(word_count / 200)) if word_count else 0
    toc = _extract_code_toc(text, resolved_lang)

    escaped_code = html.escape(text, quote=False)
    safe_lang = html.escape(resolved_lang, quote=True)
    html_out = (
        f'<div class="code-document" data-lang="{safe_lang}">'
        f'<pre class="code-file-pre" data-lang="{safe_lang}">'
        f'<code class="language-{safe_lang}" data-lang="{safe_lang}" data-code-file="true">{escaped_code}</code>'
        f"</pre></div>"
    )

    fallback_title = filename or "Code"
    return {
        "title": fallback_title,
        "filename": fallback_title,
        "path": "",
        "html": html_out,
        "toc": toc,
        "word_count": word_count,
        "read_minutes": read_minutes,
        "editable": True,
        "is_code": True,
        "language": resolved_lang,
        "format": "code",
        "raw_text": text,
    }


def render_code_file(path: Path) -> dict[str, Any]:
    """Read a source code file from disk and render it."""
    resolved = path.expanduser().resolve()
    text = _read_text_with_fallback(resolved)
    doc = render_code_text(text, filename=resolved.name)
    doc["path"] = str(resolved)
    return doc


def _local_tag(tag: str) -> str:
    """Strip XML namespace from an ElementTree tag name."""
    if "}" in tag:
        return tag.split("}", 1)[1].lower()
    return tag.lower()


def _norm_zip_path(base_dir: str, href: str) -> str:
    """Normalize a relative href inside an EPUB zip archive."""
    raw_path = unquote(urlsplit(href.strip()).path)
    if not raw_path:
        return ""
    joined = posixpath.normpath(posixpath.join(base_dir, raw_path)) if base_dir else posixpath.normpath(raw_path)
    return joined.lstrip("/")


def _parse_epub_toc_ncx(ncx_bytes: bytes, ncx_dir: str) -> dict[str, str]:
    """Extract href -> chapter title mapping from an EPUB 2 NCX document."""
    mapping: dict[str, str] = {}
    try:
        root = ET.fromstring(ncx_bytes)
    except ET.ParseError:
        return mapping

    for elem in root.iter():
        if _local_tag(elem.tag) != "navpoint":
            continue
        label_text = ""
        content_src = ""
        for child in elem:
            ctag = _local_tag(child.tag)
            if ctag == "navlabel":
                for sub in child.iter():
                    if _local_tag(sub.tag) == "text" and sub.text:
                        label_text = " ".join(sub.text.split()).strip()
                        break
            elif ctag == "content":
                content_src = child.attrib.get("src", "").strip()
        if label_text and content_src:
            norm = _norm_zip_path(ncx_dir, content_src)
            if norm and norm not in mapping:
                mapping[norm] = label_text
    return mapping


def _parse_epub_toc_nav(nav_bytes: bytes, nav_dir: str) -> dict[str, str]:
    """Extract href -> chapter title mapping from an EPUB 3 Navigation Document."""
    mapping: dict[str, str] = {}
    try:
        root = ET.fromstring(nav_bytes)
    except ET.ParseError:
        a_re = re.compile(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>', re.IGNORECASE)
        for m in a_re.finditer(nav_bytes.decode("utf-8", errors="replace")):
            href = m.group(1)
            text = " ".join(_TAG_STRIP_RE.sub("", m.group(2)).split()).strip()
            norm = _norm_zip_path(nav_dir, href)
            if norm and text and norm not in mapping:
                mapping[norm] = text
        return mapping

    for elem in root.iter():
        if _local_tag(elem.tag) == "a":
            href = elem.attrib.get("href", "").strip()
            text = " ".join("".join(elem.itertext()).split()).strip()
            if href and text:
                norm = _norm_zip_path(nav_dir, href)
                if norm and norm not in mapping:
                    mapping[norm] = text
    return mapping


def parse_epub_archive(zf: zipfile.ZipFile, filename: str = "") -> dict[str, Any]:
    """Parse an open EPUB ZipFile into clean multi-chapter HTML + sidebar TOC."""
    names = set(zf.namelist())
    opf_path = ""

    if "META-INF/container.xml" in names:
        try:
            container_root = ET.fromstring(zf.read("META-INF/container.xml"))
            for elem in container_root.iter():
                if _local_tag(elem.tag) == "rootfile":
                    cand = elem.attrib.get("full-path", "").strip()
                    if cand in names:
                        opf_path = cand
                        break
        except Exception:
            pass

    if not opf_path:
        for name in sorted(names):
            if name.lower().endswith(".opf"):
                opf_path = name
                break

    opf_dir = posixpath.dirname(opf_path) if opf_path else ""
    book_title = Path(filename).stem if filename else "EPUB Book"
    book_author = ""

    manifest: dict[str, dict[str, str]] = {}
    spine_ids: list[str] = []
    ncx_id = ""
    nav_href = ""

    if opf_path and opf_path in names:
        try:
            opf_root = ET.fromstring(zf.read(opf_path))
            for elem in opf_root.iter():
                tag = _local_tag(elem.tag)
                if tag == "title" and elem.text and elem.text.strip():
                    book_title = " ".join(elem.text.split()).strip()
                elif tag == "creator" and elem.text and elem.text.strip() and not book_author:
                    book_author = " ".join(elem.text.split()).strip()
                elif tag == "item":
                    item_id = elem.attrib.get("id", "").strip()
                    href = elem.attrib.get("href", "").strip()
                    mtype = elem.attrib.get("media-type", "").strip().lower()
                    props = elem.attrib.get("properties", "").strip().lower()
                    if item_id and href:
                        manifest[item_id] = {
                            "href": href,
                            "zip_path": _norm_zip_path(opf_dir, href),
                            "media_type": mtype,
                            "properties": props,
                        }
                        if "nav" in props.split() and not nav_href:
                            nav_href = _norm_zip_path(opf_dir, href)
                        if mtype == "application/x-dtbncx+xml" and not ncx_id:
                            ncx_id = item_id
                elif tag == "spine":
                    toc_attr = elem.attrib.get("toc", "").strip()
                    if toc_attr and not ncx_id:
                        ncx_id = toc_attr
                elif tag == "itemref":
                    idref = elem.attrib.get("idref", "").strip()
                    if idref:
                        spine_ids.append(idref)
        except Exception:
            pass

    toc_titles: dict[str, str] = {}
    if nav_href and nav_href in names:
        toc_titles.update(_parse_epub_toc_nav(zf.read(nav_href), posixpath.dirname(nav_href)))
    if ncx_id and ncx_id in manifest:
        ncx_zp = manifest[ncx_id]["zip_path"]
        if ncx_zp in names:
            for k, v in _parse_epub_toc_ncx(zf.read(ncx_zp), posixpath.dirname(ncx_zp)).items():
                toc_titles.setdefault(k, v)

    chapter_paths: list[str] = []
    for idref in spine_ids:
        item = manifest.get(idref)
        if item and item["zip_path"] in names:
            mtype = item["media_type"]
            if "html" in mtype or "xml" in mtype or item["zip_path"].lower().endswith((".xhtml", ".html", ".htm")):
                chapter_paths.append(item["zip_path"])

    if not chapter_paths:
        for name in sorted(names):
            low = name.lower()
            if low.endswith((".xhtml", ".html", ".htm")) and not low.endswith("nav.xhtml"):
                chapter_paths.append(name)

    chapter_anchor_by_path: dict[str, str] = {
        cpath: f"epub-chapter-{idx}"
        for idx, cpath in enumerate(chapter_paths, start=1)
    }

    used_slugs: dict[str, int] = {}
    toc: list[dict[str, Any]] = []
    chapters_html: list[str] = []
    total_words = 0

    for idx, cpath in enumerate(chapter_paths, start=1):
        try:
            raw_bytes = zf.read(cpath)
        except KeyError:
            continue
        raw_text = raw_bytes.decode("utf-8", errors="replace")
        cdir = posixpath.dirname(cpath)
        chapter_id = chapter_anchor_by_path[cpath]

        body_match = _BODY_RE.search(raw_text)
        body_fragment = body_match.group(1) if body_match else raw_text

        title_match = _TITLE_RE.search(raw_text)
        doc_html_title = (
            " ".join(_TAG_STRIP_RE.sub("", title_match.group(1)).split()).strip()
            if title_match
            else ""
        )

        def _resolve_epub_url(raw_url: str, is_image: bool, _cdir: str = cdir) -> str | None:
            u = raw_url.strip()
            if not u:
                return ""
            if u.startswith("#"):
                return u
            parsed = urlsplit(u)
            scheme = parsed.scheme.lower()
            if scheme:
                if scheme in ("http", "https", "mailto") and not is_image:
                    return u
                if scheme == "data" and is_image and _SAFE_IMAGE_DATA_RE.match(u):
                    return u
                return None

            target_zip_path = _norm_zip_path(_cdir, parsed.path)
            if is_image:
                if target_zip_path in names:
                    ext = posixpath.splitext(target_zip_path)[1].lower()
                    mime = _EPUB_IMAGE_MIMES.get(ext)
                    if mime:
                        try:
                            img_bytes = zf.read(target_zip_path)
                            if len(img_bytes) <= 4 * 1024 * 1024:
                                b64 = base64.b64encode(img_bytes).decode("ascii")
                                return f"data:{mime};base64,{b64}"
                        except Exception:
                            pass
                return None

            if target_zip_path in chapter_anchor_by_path:
                return f"#{chapter_anchor_by_path[target_zip_path]}"
            if parsed.fragment:
                return f"#{parsed.fragment}"
            return None

        proc = _PostProcessor(base_dir=None, used_slugs=used_slugs, url_resolver=_resolve_epub_url)
        proc.feed(body_fragment)
        proc.close()

        chapter_inner = "".join(proc.out).strip()
        plain_words = _WORD_RE.findall(_TAG_STRIP_RE.sub(" ", chapter_inner))
        if not chapter_inner and not plain_words:
            continue
        total_words += len(plain_words)

        first_heading = proc.toc[0]["text"] if proc.toc else ""
        chapter_title = (
            toc_titles.get(cpath)
            or first_heading
            or (doc_html_title if doc_html_title and doc_html_title.lower() != book_title.lower() else "")
            or f"Chapter {idx}"
        )

        toc.append({"level": 1, "id": chapter_id, "text": chapter_title})
        for sub in proc.toc:
            if sub["text"] == chapter_title and sub["level"] == 1:
                continue
            toc.append({
                "level": min(3, sub["level"] + 1),
                "id": sub["id"],
                "text": sub["text"],
            })

        heading_injected = ""
        if not first_heading:
            heading_injected = f'<h2 class="epub-chapter-title">{html.escape(chapter_title)}</h2>'

        chapters_html.append(
            f'<section id="{chapter_id}" class="epub-chapter" data-chapter="{idx}">'
            f"{heading_injected}{chapter_inner}</section>"
        )

    header_meta = ""
    if book_author:
        header_meta = f'<p class="epub-author">{html.escape(book_author)}</p>'
    book_header = (
        f'<header class="epub-book-header">'
        f'<h1 id="epub-book-top">{html.escape(book_title)}</h1>'
        f"{header_meta}</header>"
    )

    read_minutes = max(1, round(total_words / 220)) if total_words else 0
    return {
        "title": book_title,
        "author": book_author,
        "filename": filename or f"{book_title}.epub",
        "path": "",
        "html": book_header + "\n".join(chapters_html),
        "toc": toc,
        "word_count": total_words,
        "read_minutes": read_minutes,
        "editable": False,
        "is_epub": True,
        "format": "epub",
        "chapter_count": len(chapters_html),
        "raw_text": "",
    }


def render_epub_file(path: Path) -> dict[str, Any]:
    """Read an .epub file from disk using native zipfile + xml.etree and render chapters."""
    resolved = path.expanduser().resolve()
    with zipfile.ZipFile(resolved, "r") as zf:
        doc = parse_epub_archive(zf, filename=resolved.name)
    doc["path"] = str(resolved)
    return doc


def render_document_file(path: Path) -> dict[str, Any]:
    """Dispatch file rendering based on file extension (.md, .epub, .txt, or code)."""
    resolved = path.expanduser().resolve()
    suffix = resolved.suffix.lower()

    if suffix == ".epub":
        return render_epub_file(resolved)
    if suffix in CORE_MD_EXTENSIONS:
        return render_markdown_file(resolved)
    if suffix in (".txt", ".text", ".log"):
        return render_text_file(resolved)
    if suffix in SUFFIX_TO_LANGUAGE:
        return render_code_file(resolved)
    return render_markdown_file(resolved)
