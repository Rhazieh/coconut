# Designing Comfortable Long-Form Reading on Linux

> **Local-first · Viewer-only · Zero distractions.**  
> Built for hours of calm reading across technical guides, architecture notes, and documentation without raw Markdown syntax cluttering the page.

---

## 1. Typography & Single-Font Hierarchy

Instead of forcing your eyes to jump between incompatible serif, sans, and harsh monospace fonts, **Coconut** renders the entire interface and document in **Atkinson Hyperlegible Next**:

- Unambiguous glyphs (`1`, `l`, `I` and `0`, `O`) eliminate micro-decoding strain in paths like `/etc/systemd/system` or commands like `ip -br addr`.
- Generous `1.72` line height and an adaptive `68ch` line measure keep paragraphs scannable regardless of whether you read at `16 px` or `24 px`.
- Calm inline code pills such as `systemctl status ssh` and `kubectl get pods` blend effortlessly into prose.

### Quick Terminal Setup

```bash
git clone https://github.com/Rhazieh/coconut.git
cd coconut
./install.sh
coco docs/demo.md
```

---

## 2. Eye-Comfort Palettes

Pure `#FFFFFF` on `#000000` (21:1 contrast) triggers **halation**—a faint glow around letters that tires the eyes over multi-hour sessions. Coconut pairs a dark roasted shell with soft cream interiors (~12.4:1 contrast):

| Palette | Canvas | Body Text | Accent | Best Environment |
| :--- | :--- | :--- | :--- | :--- |
| **Warm Night** | `#191817` | `#DCD7CE` | `#D4A373` | Night & dim rooms |
| **Paper Sepia** | `#F3ECDC` | `#352F28` | `#9A5B25` | Warm indoor lighting |
| **Soft Stone** | `#F4F3EE` | `#2A2926` | `#3E6B89` | Bright daylight |

---

## 3. Reading Checklist

- [x] Native Linux support on **Wayland** and **X11**
- [x] Instant local rendering via `libcmark-gfm` (`< 15 ms`)
- [x] Customizable text size (`Ctrl++` / `Ctrl+-` / `Ctrl+Wheel`)
- [x] Live auto-reload when the file updates on disk
- [ ] Enjoy uninterrupted deep reading
