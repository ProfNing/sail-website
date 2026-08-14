#!/usr/bin/env python3
"""
Publish a Chinese draft as a trilingual SAIL article.

Usage:
  python3 scripts/publish_article.py drafts/my-article.md

The draft is Chinese Markdown with YAML front matter. English and Korean
are generated automatically and written into articles/<slug>.html, then
registered in js/i18n.js.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAFTS = ROOT / "drafts"
ARTICLES = ROOT / "articles"
I18N = ROOT / "js" / "i18n.js"

TOPIC_TAGS = {
    "ai": '<span class="tag tag--ai">AI</span>',
    "sus": '<span class="tag tag--sus">Sustainability</span>',
    "edu": '<span class="tag tag--edu">Learning</span>',
}


def translate_text(text: str, target: str) -> str:
    """Translate Chinese text via Google's public gtx endpoint (no API key)."""
    import urllib.parse
    import urllib.request

    text = text.strip()
    if not text:
        return ""

    lang_map = {"en": "en", "ko": "ko", "zh": "zh-CN"}
    tl = lang_map.get(target, target)

    # Keep requests small
    max_len = 1800
    pieces = []
    remaining = text
    while remaining:
        if len(remaining) <= max_len:
            pieces.append(remaining)
            break
        cut = remaining.rfind("。", 0, max_len)
        if cut < max_len // 3:
            cut = remaining.rfind(" ", 0, max_len)
        if cut < max_len // 3:
            cut = max_len
        pieces.append(remaining[: cut + 1])
        remaining = remaining[cut + 1 :]

    out = []
    for i, piece in enumerate(pieces):
        if not piece.strip():
            out.append(piece)
            continue
        params = urllib.parse.urlencode(
            {
                "client": "gtx",
                "sl": "zh-CN",
                "tl": tl,
                "dt": "t",
                "q": piece,
            }
        )
        url = "https://translate.googleapis.com/translate_a/single?" + params
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "SAIL-publish/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            time.sleep(1.2)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except Exception:
                raise SystemExit(f"Translation failed ({target}): {exc}") from exc

        # Response shape: [[[translated, original, ...], ...], ...]
        translated = "".join(part[0] for part in data[0] if part and part[0])
        out.append(translated)
        if i < len(pieces) - 1:
            time.sleep(0.25)
    return "".join(out)


def ensure_translator() -> None:
    # Network translator; nothing to install.
    return


def parse_draft(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        raise SystemExit(f"{path}: missing YAML front matter (start with ---)")
    parts = raw.split("---", 2)
    if len(parts) < 3:
        raise SystemExit(f"{path}: invalid front matter")
    meta_raw = parts[1].strip()
    body = parts[2].strip()

    meta: dict = {}
    for line in meta_raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key == "topics":
            inner = val.strip("[]")
            meta["topics"] = [t.strip().strip('"').strip("'") for t in inner.split(",") if t.strip()]
        elif key == "minutes":
            meta["minutes"] = int(val)
        else:
            meta[key] = val

    for required in ("slug", "title", "excerpt"):
        if not meta.get(required):
            raise SystemExit(f"{path}: front matter needs `{required}`")

    topics = meta.get("topics") or ["ai"]
    for t in topics:
        if t not in TOPIC_TAGS:
            raise SystemExit(f"{path}: unknown topic `{t}` (use ai, sus, edu)")

    meta.setdefault("date", date.today().isoformat())
    meta.setdefault("minutes", max(1, round(len(body) / 400)))
    meta["body"] = body
    meta["topics"] = topics
    return meta


def split_blocks(markdown: str) -> list[tuple[str, str]]:
    """Return list of (kind, text) where kind in p|h2|quote."""
    blocks = []
    for chunk in re.split(r"\n\s*\n", markdown.strip()):
        chunk = chunk.strip()
        if not chunk:
            continue
        if chunk.startswith("> "):
            lines = [re.sub(r"^>\s?", "", ln) for ln in chunk.splitlines()]
            blocks.append(("quote", "\n".join(lines).strip()))
        elif chunk.startswith("## "):
            blocks.append(("h2", chunk[3:].strip()))
        elif chunk.startswith("# "):
            blocks.append(("h2", chunk[2:].strip()))
        else:
            blocks.append(("p", chunk.replace("\n", " ").strip()))
    return blocks


def blocks_to_html(blocks: list[tuple[str, str]]) -> str:
    parts = []
    for kind, text in blocks:
        safe = html.escape(text)
        if kind == "h2":
            parts.append(f"        <h2>{safe}</h2>")
        elif kind == "quote":
            parts.append(f"        <blockquote>{safe}</blockquote>")
        else:
            parts.append(f"        <p>{safe}</p>")
    return "\n".join(parts)


def translate_blocks(blocks: list[tuple[str, str]], target: str) -> list[tuple[str, str]]:
    # Translate each block separately for structure safety
    out = []
    for kind, text in blocks:
        translated = translate_text(text, target) if text else ""
        out.append((kind, translated))
        time.sleep(0.2)
    return out


def render_article(meta: dict, zh_blocks, en_blocks, ko_blocks, titles, excerpts) -> str:
    tags = "\n            ".join(TOPIC_TAGS[t] for t in meta["topics"])
    title_en, title_zh, title_ko = titles
    dek_en, dek_zh, dek_ko = excerpts

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title_en)}</title>
  <link rel="stylesheet" href="../css/styles.css" />
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Cpath fill='%232f7a45' d='M16.2 4v16h9L16.2 4z'/%3E%3Cpath fill='%231f6f8b' d='M15.8 7v13H7L15.8 7z'/%3E%3Cpath stroke='%23101c17' stroke-width='1.6' d='M16 4v17'/%3E%3Cpath fill='%230c1914' d='M5 22.5h22l-2.2 3.5H7.2z'/%3E%3C/svg%3E" />
</head>
<body>
  <header class="site-header">
    <div class="site-header__inner">
      <div class="brand">
        <a class="brand__logo" href="../index.html" aria-label="Home"><svg class="brand__mark" viewBox="0 0 24 24" aria-hidden="true">
          <path fill="#2f7a45" d="M12.2 3.2v12.2H19L12.2 3.2z"/>
          <path fill="#1f6f8b" d="M11.8 5.5v9.9H5.2L11.8 5.5z"/>
          <path stroke="#101c17" stroke-width="1.4" stroke-linecap="round" d="M12 3.2v13.3"/>
          <path fill="#0c1914" d="M3.2 17.2h17.6l-1.8 2.8H5z"/>
          <path fill="none" stroke="#1f6f8b" stroke-width="1.2" stroke-linecap="round" d="M3.5 20.6c2.8-.9 5.6-.9 8.5 0s5.7.9 8.5 0"/>
        </svg></a>
        <a class="brand__sail" href="../index.html?lang=en" lang="en">SAIL</a>
        <a class="brand__qi" href="../index.html?lang=zh" lang="zh-Hans">启航</a>
        <a class="brand__ko" href="../index.html?lang=ko" lang="ko">출항</a>
      </div>
      <button class="menu-toggle" type="button" aria-expanded="false" data-i18n-aria="nav.menu" aria-label="Menu">
        <span></span><span></span><span></span>
      </button>
      <nav class="nav" aria-label="Primary">
        <a href="../index.html" data-i18n="nav.home">Home</a>
        <a href="index.html" data-i18n="nav.articles">Articles</a>
        <a href="../learn/index.html" data-i18n="nav.practice">Practice</a>
        <a href="../about.html" data-i18n="nav.about">About</a>
        <div class="lang-switch" role="group" aria-label="Language">
          <button type="button" data-lang="zh">中文</button>
          <button type="button" data-lang="en">EN</button>
          <button type="button" data-lang="ko">한국어</button>
        </div>
      </nav>
    </div>
  </header>

  <main class="wrap article-layout">
    <article>
      <header class="article-header">
        <p class="eyebrow"><a href="index.html" data-i18n="common.backArticles">← All articles</a></p>

        <div data-lang-panel="en">
          <h1 class="display">{html.escape(title_en)}</h1>
          <p class="dek">{html.escape(dek_en)}</p>
        </div>
        <div data-lang-panel="zh" hidden>
          <h1 class="display">{html.escape(title_zh)}</h1>
          <p class="dek">{html.escape(dek_zh)}</p>
        </div>
        <div data-lang-panel="ko" hidden>
          <h1 class="display">{html.escape(title_ko)}</h1>
          <p class="dek">{html.escape(dek_ko)}</p>
        </div>

        <div class="article-meta">
          <span>{html.escape(meta["date"])}</span>
          <span>{meta["minutes"]} <span data-i18n="common.minRead">min read</span></span>
          <span class="tags">
            {tags}
          </span>
        </div>
      </header>

      <div class="prose" data-lang-panel="en">
{blocks_to_html(en_blocks)}
      </div>

      <div class="prose" data-lang-panel="zh" hidden>
{blocks_to_html(zh_blocks)}
      </div>

      <div class="prose" data-lang-panel="ko" hidden>
{blocks_to_html(ko_blocks)}
      </div>
    </article>
  </main>

  <footer class="site-footer">
    <div class="site-footer__inner">
      <div>
        <a class="brand brand--footer" href="../index.html" aria-label="SAIL 启航 출항">
          <svg class="brand__mark" viewBox="0 0 24 24" aria-hidden="true">
          <path fill="#2f7a45" d="M12.2 3.2v12.2H19L12.2 3.2z"/>
          <path fill="#1f6f8b" d="M11.8 5.5v9.9H5.2L11.8 5.5z"/>
          <path stroke="#101c17" stroke-width="1.4" stroke-linecap="round" d="M12 3.2v13.3"/>
          <path fill="#0c1914" d="M3.2 17.2h17.6l-1.8 2.8H5z"/>
          <path fill="none" stroke="#1f6f8b" stroke-width="1.2" stroke-linecap="round" d="M3.5 20.6c2.8-.9 5.6-.9 8.5 0s5.7.9 8.5 0"/>
        </svg>
        </a>
        <p data-i18n="meta.tagline">Sustainability · AI · Learning</p>
      </div>
      <nav class="footer-nav">
        <a href="index.html" data-i18n="nav.articles">Articles</a>
        <a href="../learn/index.html" data-i18n="nav.practice">Practice</a>
        <a href="../about.html" data-i18n="nav.about">About</a>
      </nav>
    </div>
  </footer>

  <script src="../js/i18n.js"></script>
  <script src="../js/main.js"></script>
</body>
</html>
"""


def js_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def upsert_catalog(meta: dict, titles: tuple[str, str, str], excerpts: tuple[str, str, str]) -> None:
    title_en, title_zh, title_ko = titles
    dek_en, dek_zh, dek_ko = excerpts
    slug = meta["slug"]
    topics_js = json.dumps(meta["topics"])

    entry = f"""  {{
    id: {js_str(slug)},
    href: {js_str(slug + ".html")},
    date: {js_str(meta["date"])},
    minutes: {meta["minutes"]},
    topics: {topics_js},
    title: {{
      en: {js_str(title_en)},
      zh: {js_str(title_zh)},
      ko: {js_str(title_ko)},
    }},
    excerpt: {{
      en: {js_str(dek_en)},
      zh: {js_str(dek_zh)},
      ko: {js_str(dek_ko)},
    }},
  }}"""

    src = I18N.read_text(encoding="utf-8")
    marker = "window.WEAVE_ARTICLES = ["
    if marker not in src:
        raise SystemExit("js/i18n.js: WEAVE_ARTICLES not found")

    # Remove existing entry with same id
    src = re.sub(
        rf"\s*\{{\s*id:\s*{re.escape(js_str(slug))}[\s\S]*?\}}\s*,?",
        "\n",
        src,
        count=1,
    )

    insert_at = src.index(marker) + len(marker)
    src = src[:insert_at] + "\n" + entry + "," + src[insert_at:]
    I18N.write_text(src, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish Chinese draft → EN/KO article")
    parser.add_argument("draft", type=Path, help="Path to Chinese Markdown draft")
    parser.add_argument("--skip-translate", action="store_true", help="Reuse zh for en/ko (debug)")
    args = parser.parse_args()

    draft = args.draft
    if not draft.is_file():
        draft = DRAFTS / draft
    if not draft.is_file():
        raise SystemExit(f"Draft not found: {args.draft}")

    ensure_translator()
    meta = parse_draft(draft)
    zh_blocks = split_blocks(meta["body"])

    print(f"Translating “{meta['title']}” → English & Korean…")
    if args.skip_translate:
        title_en = title_ko = meta["title"]
        dek_en = dek_ko = meta["excerpt"]
        en_blocks = ko_blocks = zh_blocks
    else:
        title_en = translate_text(meta["title"], "en")
        title_ko = translate_text(meta["title"], "ko")
        dek_en = translate_text(meta["excerpt"], "en")
        dek_ko = translate_text(meta["excerpt"], "ko")
        en_blocks = translate_blocks(zh_blocks, "en")
        ko_blocks = translate_blocks(zh_blocks, "ko")

    titles = (title_en, meta["title"], title_ko)
    excerpts = (dek_en, meta["excerpt"], dek_ko)

    out = ARTICLES / f"{meta['slug']}.html"
    out.write_text(
        render_article(meta, zh_blocks, en_blocks, ko_blocks, titles, excerpts),
        encoding="utf-8",
    )
    upsert_catalog(meta, titles, excerpts)

    print(f"Wrote {out.relative_to(ROOT)}")
    print(f"Updated {I18N.relative_to(ROOT)}")
    print("Open articles/index.html and switch language to review translations.")


if __name__ == "__main__":
    main()
