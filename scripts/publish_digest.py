#!/usr/bin/env python3
"""
Build a public daily digest from collected feeds (no AI API key).

- Collects RSS headlines
- Writes an extractive summary article in EN / 中文 / 한국어
- Registers it in js/i18n.js
- Locally: also writes a private 小红书 Chinese draft (gitignored)

Usage:
  python3 scripts/publish_digest.py
  python3 scripts/publish_digest.py --date 2026-08-05
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "articles"
I18N = ROOT / "js" / "i18n.js"
XHS_DIR = ROOT / "private" / "xiaohongshu"
SITE_DIGEST_BASE = "https://profning.github.io/sail-website/articles"
sys.path.insert(0, str(ROOT / "scripts"))

from collect_feeds import collect, write_js  # noqa: E402

TOPIC_TAGS = {
    "ai": '<span class="tag tag--ai">AI</span>',
    "sus": '<span class="tag tag--sus">Sustainability</span>',
    "edu": '<span class="tag tag--edu">Learning</span>',
}

SECTION_ORDER = ("ai", "ai_sus", "sus", "edu")

LABELS = {
    "en": {
        "title": "SAIL Daily Digest — {when}",
        "excerpt": "Today’s public-source roundup: {n} headlines — {ai} AI, {sus} sustainability, {edu} learning.",
        "intro": "An automatic digest of headlines SAIL collected from public feeds. Each item links to the original source.",
        "glance": "At a glance",
        "ai": "Artificial Intelligence",
        "ai_sus": "AI for Sustainability",
        "sus": "Sustainability",
        "edu": "Learning",
        "more": "Read original",
        "empty": "No headlines were collected for this day.",
    },
    "zh": {
        "title": "SAIL 每日简报 — {when}",
        "excerpt": "今日公开来源速览：共 {n} 条——人工智能 {ai}、可持续 {sus}、学习 {edu}。",
        "intro": "SAIL 自动汇集的公开信息源摘要。每条均链向原文。",
        "glance": "一览",
        "ai": "人工智能",
        "ai_sus": "人工智能与可持续",
        "sus": "可持续",
        "edu": "学习",
        "more": "阅读原文",
        "empty": "本日暂无采集到的标题。",
    },
    "ko": {
        "title": "SAIL 일일 요약 — {when}",
        "excerpt": "오늘 공개 출처 모음: 헤드라인 {n}건 — AI {ai}, 지속가능성 {sus}, 학습 {edu}.",
        "intro": "SAIL이 공개 피드에서 자동 수집한 헤드라인 요약입니다. 각 항목은 원문으로 연결됩니다.",
        "glance": "한눈에",
        "ai": "인공지능",
        "ai_sus": "AI와 지속가능성",
        "sus": "지속가능성",
        "edu": "학습",
        "more": "원문 보기",
        "empty": "이 날짜에 수집된 헤드라인이 없습니다.",
    },
}


def translate_text(text: str, target: str, source: str = "en") -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if target == source or (target == "zh" and source == "zh-CN"):
        return text

    lang_map = {"en": "en", "ko": "ko", "zh": "zh-CN", "zh-CN": "zh-CN"}
    sl = lang_map.get(source, source)
    tl = lang_map.get(target, target)

    max_len = 1500
    pieces = []
    remaining = text
    while remaining:
        if len(remaining) <= max_len:
            pieces.append(remaining)
            break
        cut = remaining.rfind(". ", 0, max_len)
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
            {"client": "gtx", "sl": sl, "tl": tl, "dt": "t", "q": piece}
        )
        url = "https://translate.googleapis.com/translate_a/single?" + params
        req = urllib.request.Request(url, headers={"User-Agent": "SAIL-digest/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            time.sleep(1.0)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except Exception:
                print(f"translate failed ({target}): {exc}", file=sys.stderr)
                out.append(piece)
                continue
        out.append("".join(part[0] for part in data[0] if part and part[0]))
        if i < len(pieces) - 1:
            time.sleep(0.2)
    return "".join(out)


def bucket_for(item: dict) -> str:
    topics = set(item.get("topics") or [])
    if "ai" in topics and "sus" in topics:
        return "ai_sus"
    if "ai" in topics:
        return "ai"
    if "sus" in topics:
        return "sus"
    if "edu" in topics:
        return "edu"
    return "ai"


def format_when(d: date, lang: str) -> str:
    if lang == "zh":
        return f"{d.year}年{d.month}月{d.day}日"
    if lang == "ko":
        return f"{d.year}년 {d.month}월 {d.day}일"
    return d.strftime("%B %d, %Y").replace(" 0", " ")


def normalize_title(title: str) -> str:
    t = (title or "").lower().strip()
    t = re.sub(r"&amp;", "&", t)
    t = re.sub(r"\s+", " ", t)
    # Drop common site suffixes after em dash / hyphen
    t = re.split(r"\s+[—\-–|]\s+", t, maxsplit=1)[0]
    return t


def titles_too_similar(a: str, b: str) -> bool:
    """Catch near-duplicates with different URLs (same story, different outlets)."""
    if not a or not b:
        return False
    if a == b:
        return True
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if len(shorter) >= 24 and shorter in longer:
        return True
    wa, wb = set(shorter.split()), set(longer.split())
    if len(wa) >= 5 and len(wa & wb) / len(wa) >= 0.75:
        return True
    return False


def urls_from_digest_html(path: Path) -> tuple[set[str], set[str]]:
    """Return (urls, normalized titles) from a published digest page."""
    html_src = path.read_text(encoding="utf-8")
    # Prefer English panel so titles match source language for dedupe
    m = re.search(
        r'data-lang-panel="en">(.*?)</div>\s*<div class="prose" data-lang-panel="zh"',
        html_src,
        re.S,
    )
    block = m.group(1) if m else html_src
    pairs = re.findall(
        r'<a href="([^"]+)"[^>]*>\s*<strong>(.*?)</strong>',
        block,
        re.S,
    )
    urls: set[str] = set()
    titles: set[str] = set()
    for url, title in pairs:
        urls.add(url.strip())
        titles.add(normalize_title(re.sub(r"\s+", " ", title)))
    return urls, titles


def previously_published(exclude_date: date | None = None) -> tuple[set[str], set[str]]:
    """URLs/titles already used in other digest-*.html articles."""
    urls: set[str] = set()
    titles: set[str] = set()
    for path in sorted(ARTICLES.glob("digest-*.html")):
        stamp = path.stem.removeprefix("digest-")
        if exclude_date and stamp == exclude_date.isoformat():
            continue
        try:
            u, t = urls_from_digest_html(path)
        except Exception as exc:
            print(f"warn: could not read {path.name}: {exc}", file=sys.stderr)
            continue
        urls |= u
        titles |= t
    return urls, titles


def select_for_digest(
    items: list[dict],
    per_section: int = 5,
    *,
    exclude_urls: set[str] | None = None,
    exclude_titles: set[str] | None = None,
) -> list[dict]:
    """Pick a fair mix per topic bucket; skip items already in earlier digests."""
    exclude_urls = exclude_urls or set()
    exclude_titles = exclude_titles or set()
    buckets: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        buckets[bucket_for(item)].append(item)
    chosen: list[dict] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    skipped = 0
    for key in SECTION_ORDER:
        for item in buckets.get(key) or []:
            url = item.get("url") or ""
            title_key = normalize_title(item.get("title") or "")
            if url in exclude_urls or url in seen_urls:
                skipped += 1
                continue
            if title_key and (
                title_key in exclude_titles
                or title_key in seen_titles
                or any(titles_too_similar(title_key, prev) for prev in seen_titles)
                or any(titles_too_similar(title_key, prev) for prev in exclude_titles)
            ):
                skipped += 1
                continue
            chosen.append(item)
            seen_urls.add(url)
            if title_key:
                seen_titles.add(title_key)
            if sum(1 for x in chosen if bucket_for(x) == key) >= per_section:
                break
    if skipped:
        print(f"Skipped {skipped} headlines already used in earlier digests")
    return chosen


def counts(items: list[dict]) -> dict[str, int]:
    c = {"ai": 0, "sus": 0, "edu": 0}
    for item in items:
        for t in item.get("topics") or []:
            if t in c:
                c[t] += 1
    return c


def build_lang_html(items: list[dict], day: date, lang: str, translated: dict) -> tuple[str, str, str]:
    """Return title, excerpt, prose html for one language."""
    L = LABELS[lang]
    when = format_when(day, lang)
    c = counts(items)
    title = L["title"].format(when=when)
    excerpt = L["excerpt"].format(n=len(items), ai=c["ai"], sus=c["sus"], edu=c["edu"])

    if not items:
        prose = f"        <p>{html.escape(L['empty'])}</p>"
        return title, excerpt, prose

    parts = [
        f"        <p>{html.escape(L['intro'])}</p>",
        f"        <h2>{html.escape(L['glance'])}</h2>",
        f"        <p>{html.escape(excerpt)}</p>",
    ]

    buckets: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        buckets[bucket_for(item)].append(item)

    per_section = 5
    for key in SECTION_ORDER:
        group = buckets.get(key) or []
        if not group:
            continue
        parts.append(f"        <h2>{html.escape(L[key])}</h2>")
        for item in group[:per_section]:
            t_en = item["title"]
            e_en = item.get("excerpt") or ""
            title_l = translated.get((t_en, lang), t_en)
            excerpt_l = translated.get((e_en, lang), e_en) if e_en else ""
            url = html.escape(item["url"], quote=True)
            source = html.escape(item.get("source") or "")
            line = f'<a href="{url}" target="_blank" rel="noopener noreferrer"><strong>{html.escape(title_l)}</strong></a>'
            if excerpt_l:
                line += f" — {html.escape(excerpt_l)}"
            line += f" <em>({source})</em>"
            parts.append(f"        <p>{line}</p>")

    return title, excerpt, "\n".join(parts)


def render_article(day: date, titles: dict, excerpts: dict, bodies: dict) -> str:
    slug_date = day.isoformat()
    tags = "\n            ".join(TOPIC_TAGS[t] for t in ("ai", "sus", "edu"))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(titles['en'])}</title>
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
        <a href="../topics/ai.html" data-i18n="nav.ai">AI</a>
        <a href="../topics/sustainability.html" data-i18n="nav.sustainability">Sustainability</a>
        <a href="../topics/education.html" data-i18n="nav.education">Learning</a>
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
          <h1 class="display">{html.escape(titles['en'])}</h1>
          <p class="dek">{html.escape(excerpts['en'])}</p>
        </div>
        <div data-lang-panel="zh" hidden>
          <h1 class="display">{html.escape(titles['zh'])}</h1>
          <p class="dek">{html.escape(excerpts['zh'])}</p>
        </div>
        <div data-lang-panel="ko" hidden>
          <h1 class="display">{html.escape(titles['ko'])}</h1>
          <p class="dek">{html.escape(excerpts['ko'])}</p>
        </div>

        <div class="article-meta">
          <span>{slug_date}</span>
          <span>4 <span data-i18n="common.minRead">min read</span></span>
          <span class="tags">
            {tags}
          </span>
        </div>
      </header>

      <div class="prose" data-lang-panel="en">
{bodies['en']}
      </div>

      <div class="prose" data-lang-panel="zh" hidden>
{bodies['zh']}
      </div>

      <div class="prose" data-lang-panel="ko" hidden>
{bodies['ko']}
      </div>
    </article>
  </main>

  <footer class="site-footer">
    <div class="site-footer__inner">
      <div>
        <a class="brand brand--footer" href="../index.html" aria-label="SAIL">
          <svg class="brand__mark" viewBox="0 0 24 24" aria-hidden="true">
          <path fill="#2f7a45" d="M12.2 3.2v12.2H19L12.2 3.2z"/>
          <path fill="#1f6f8b" d="M11.8 5.5v9.9H5.2L11.8 5.5z"/>
          <path stroke="#101c17" stroke-width="1.4" stroke-linecap="round" d="M12 3.2v13.3"/>
          <path fill="#0c1914" d="M3.2 17.2h17.6l-1.8 2.8H5z"/>
          <path fill="none" stroke="#1f6f8b" stroke-width="1.2" stroke-linecap="round" d="M3.5 20.6c2.8-.9 5.6-.9 8.5 0s5.7.9 8.5 0"/>
        </svg>
          <span class="brand__sail">SAIL</span>
        </a>
        <p data-i18n="meta.tagline">Sustainability · AI · Learning</p>
      </div>
      <nav class="footer-nav">
        <a href="index.html" data-i18n="nav.articles">Articles</a>
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


def write_xiaohongshu_draft(
    day: date,
    items: list[dict],
    translated: dict[tuple[str, str], str],
) -> Path | None:
    """
    Private Chinese note for 小红书 — local files only (gitignored).
    Not published to the website or committed by the daily Action.
    """
    if os.environ.get("GITHUB_ACTIONS"):
        print("Skipping 小红书 draft on GitHub Actions (private / local only)")
        return None

    XHS_DIR.mkdir(parents=True, exist_ok=True)
    when = format_when(day, "zh")
    L = LABELS["zh"]
    c = counts(items)
    title = f"SAIL今日简报｜{when}"
    if len(title) > 20:
        title = f"今日简报 {day.month}/{day.day}｜AI·可持续·学习"

    lines: list[str] = [
        f"【SAIL 启航】{when} 公开信息源速览",
        "",
        f"今天整理了 {len(items)} 条：人工智能 {c['ai']} · 可持续 {c['sus']} · 学习 {c['edu']}",
        "",
    ]

    buckets: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        buckets[bucket_for(item)].append(item)

    per_section = 3
    for key in SECTION_ORDER:
        group = buckets.get(key) or []
        if not group:
            continue
        lines.append(f"【{L[key]}】")
        for item in group[:per_section]:
            t_zh = translated.get((item["title"], "zh"), item["title"])
            source = item.get("source") or ""
            lines.append(f"· {t_zh}")
            if source:
                lines.append(f"  （{source}）")
        lines.append("")

    lines.extend(
        [
            "完整中英韩简报（网站）：",
            f"{SITE_DIGEST_BASE}/digest-{day.isoformat()}.html",
            "",
            "#SAIL启航 #人工智能 #可持续 #学习 #每日简报 #AI教育",
        ]
    )

    body = "\n".join(lines).rstrip() + "\n"
    note = (
        f"# 小红书草稿（私密 · 勿公开到网站）\n"
        f"# 生成时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"# 用法：复制下面「标题」和「正文」到小红书 App 发布\n\n"
        f"## 标题\n\n{title}\n\n"
        f"## 正文\n\n{body}"
    )

    dated = XHS_DIR / f"digest-{day.isoformat()}.md"
    latest = XHS_DIR / "latest.md"
    dated.write_text(note, encoding="utf-8")
    latest.write_text(note, encoding="utf-8")
    return dated


def upsert_catalog(day: date, titles: dict, excerpts: dict) -> None:
    slug = f"digest-{day.isoformat()}"
    entry = f"""  {{
    id: {js_str(slug)},
    href: {js_str(slug + ".html")},
    date: {js_str(day.isoformat())},
    minutes: 4,
    topics: ["ai", "sus", "edu"],
    title: {{
      en: {js_str(titles["en"])},
      zh: {js_str(titles["zh"])},
      ko: {js_str(titles["ko"])},
    }},
    excerpt: {{
      en: {js_str(excerpts["en"])},
      zh: {js_str(excerpts["zh"])},
      ko: {js_str(excerpts["ko"])},
    }},
  }}"""

    src = I18N.read_text(encoding="utf-8")
    marker = "window.WEAVE_ARTICLES = ["
    if marker not in src:
        raise SystemExit("WEAVE_ARTICLES not found")

    # Remove existing entry for this slug (match full object by id, not first '}')
    id_pat = re.compile(
        rf"\s*\{{\s*id:\s*{re.escape(js_str(slug))},[\s\S]*?\n  \}},?",
        re.MULTILINE,
    )
    src = id_pat.sub("\n", src, count=1)

    insert_at = src.index(marker) + len(marker)
    src = src[:insert_at] + "\n" + entry + "," + src[insert_at:]
    I18N.write_text(src, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Digest date YYYY-MM-DD (default: today UTC)")
    parser.add_argument("--skip-collect", action="store_true", help="Reuse existing js/collected.js")
    args = parser.parse_args()

    day = date.fromisoformat(args.date) if args.date else datetime.now(timezone.utc).date()

    if args.skip_collect and (ROOT / "js" / "collected.js").exists():
        raw = (ROOT / "js" / "collected.js").read_text(encoding="utf-8")
        payload = json.loads(raw.split("=", 1)[1].strip().rstrip(";"))
        items = payload.get("items") or []
        print(f"Reusing {len(items)} collected items")
    else:
        print("Collecting feeds…")
        items = collect()
        write_js(items)

    items = sorted(items, key=lambda x: x.get("date", ""), reverse=True)
    used_urls, used_titles = previously_published(exclude_date=day)
    if used_urls or used_titles:
        print(f"Excluding {len(used_urls)} URLs / {len(used_titles)} titles from earlier digests")
    digest_items = select_for_digest(
        items,
        exclude_urls=used_urls,
        exclude_titles=used_titles,
    )

    print(f"Digest will include {len(digest_items)} headlines")
    print("Translating headlines (free Google gtx, no API key)…")
    translated: dict[tuple[str, str], str] = {}
    texts: list[str] = []
    for item in digest_items:
        texts.append(item["title"])
        if item.get("excerpt"):
            texts.append(item["excerpt"])
    seen: set[str] = set()
    unique_texts: list[str] = []
    for t in texts:
        if t and t not in seen:
            seen.add(t)
            unique_texts.append(t)

    for text in unique_texts:
        translated[(text, "en")] = text
        translated[(text, "zh")] = translate_text(text, "zh", source="en")
        time.sleep(0.15)
        translated[(text, "ko")] = translate_text(text, "ko", source="en")
        time.sleep(0.15)

    items = digest_items

    titles = {}
    excerpts = {}
    bodies = {}
    for lang in ("en", "zh", "ko"):
        titles[lang], excerpts[lang], bodies[lang] = build_lang_html(items, day, lang, translated)

    # For zh/ko titles/excerpts that are templates, also translate English templates if needed
    # LABELS already has native titles/excerpts

    out = ARTICLES / f"digest-{day.isoformat()}.html"
    out.write_text(render_article(day, titles, excerpts, bodies), encoding="utf-8")
    upsert_catalog(day, titles, excerpts)
    print(f"Wrote {out.relative_to(ROOT)}")
    print(f"Updated {I18N.relative_to(ROOT)}")

    xhs = write_xiaohongshu_draft(day, items, translated)
    if xhs:
        print(f"Wrote private 小红书 draft {xhs.relative_to(ROOT)} (+ latest.md)")


if __name__ == "__main__":
    main()
