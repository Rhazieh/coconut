"""Fast, safe GitHub-Flavored Markdown renderer for Velum."""

from __future__ import annotations

import ctypes
import ctypes.util
import html
import re
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

_CMARK_INIT_DONE = False
_CMARK: Any = None
_LIBC: Any = None

_CMARK_OPT_SMART = 1 << 10
_CMARK_OPT_UNSAFE = 1 << 17

_FRONTMATTER_RE = re.compile(r"\A---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)")
_YAML_KEY_RE = re.compile(r"^[A-Za-z0-9_.-]+\s*:")
_WORD_RE = re.compile(r"\S+")

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

    def __init__(self, base_dir: Path | None) -> None:
        super().__init__(convert_charrefs=True)
        self.base_dir = base_dir
        self.out: list[str] = []
        self.toc: list[dict[str, Any]] = []
        self.first_h1: str | None = None
        self._used_slugs: dict[str, int] = {}
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
            if key.startswith("on") or key in ("srcdoc", "formaction"):
                continue
            val = raw_val if raw_val is not None else ""
            if key in ("href", "src", "poster"):
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

    fallback_title = Path(filename).stem if filename else "Velum"
    title = processor.first_h1 or fallback_title
    return {
        "title": title,
        "filename": filename or fallback_title,
        "path": "",
        "html": "".join(processor.out),
        "toc": processor.toc,
        "word_count": word_count,
        "read_minutes": read_minutes,
    }


def render_markdown_file(path: Path) -> dict[str, Any]:
    """Read a Markdown file from disk and render it."""
    resolved = path.expanduser().resolve()
    try:
        text = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = resolved.read_text(encoding="utf-8", errors="replace")

    doc = render_markdown_text(text, base_dir=resolved.parent, filename=resolved.name)
    doc["path"] = str(resolved)
    return doc
