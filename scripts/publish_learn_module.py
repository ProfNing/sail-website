#!/usr/bin/env python3
"""
Draft a SAIL weekly practice module from a daily digest page.

Writes/updates an entry in js/learn-modules.js. Machine draft — edit insights
and quiz quality before teaching use.

Usage:
  python3 scripts/publish_learn_module.py articles/digest-2026-08-13.html
  python3 scripts/publish_learn_module.py --date 2026-08-13
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "articles"
MODULES = ROOT / "js" / "learn-modules.js"

sys.path.insert(0, str(ROOT / "scripts"))
from publish_digest import translate_text  # noqa: E402
import time


def js_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def extract_en_headlines(html: str) -> list[str]:
    m = re.search(
        r'data-lang-panel="en">(.*?)</div>\s*<div class="prose" data-lang-panel="zh"',
        html,
        re.S,
    )
    block = m.group(1) if m else html
    titles = []
    for _, title in re.findall(
        r'<a href="([^"]+)"[^>]*>\s*<strong>(.*?)</strong>',
        block,
        re.S,
    ):
        t = re.sub(r"\s+", " ", title).strip()
        t = t.replace("&amp;", "&").replace("&#x27;", "'")
        titles.append(t)
    return titles


def trilang(text: str) -> dict[str, str]:
    en = text.strip()
    zh = translate_text(en, "zh", source="en")
    time.sleep(0.12)
    ko = translate_text(en, "ko", source="en")
    time.sleep(0.12)
    return {"en": en, "zh": zh, "ko": ko}


def build_module(day: date, headlines: list[str]) -> dict:
    leads = headlines[:3] or ["No headlines available for this digest."]
    while len(leads) < 3:
        leads.append(leads[-1])

    title = trilang(f"SAIL practice — {day.isoformat()}")
    excerpt = trilang(
        "Draft module from today’s digest. Edit insights and quiz items before classroom use."
    )
    insights = [trilang(h) for h in leads]

    # Simple scaffold questions (edit before publishing to learners)
    questions = []
    for i, h in enumerate(leads):
        questions.append(
            {
                "prompt": trilang(
                    f"Which statement best captures a literacy takeaway from: “{h[:90]}”?"
                ),
                "choices": [
                    trilang("Ask who benefits, what evidence is missing, and what skill it demands."),
                    trilang("Treat the headline as settled fact with no further questions."),
                    trilang("Ignore education and sustainability angles entirely."),
                ],
                "answer": 0,
                "explain": trilang(
                    "SAIL practice trains judgment: stakes, evidence, and skill—not headline acceptance."
                ),
            }
        )
    # pad to 5
    while len(questions) < 5:
        questions.append(
            {
                "prompt": trilang(
                    "A responsible next step after reading an AI×education headline is to:"
                ),
                "choices": [
                    trilang("Connect it to classroom use, evaluation, or energy/society impact."),
                    trilang("Share it without checking the source."),
                    trilang("Assume AI always improves learning outcomes."),
                ],
                "answer": 0,
                "explain": trilang(
                    "Link news to practice: classroom use, evaluation, or sustainability stakes."
                ),
            }
        )

    ethics = trilang(
        "Pick one headline from this digest. Who should disclose AI use, and what would fair assessment look like in a class or workplace? Write 3–5 sentences."
    )

    return {
        "id": day.isoformat(),
        "date": day.isoformat(),
        "minutes": 8,
        "digestHref": f"../articles/digest-{day.isoformat()}.html",
        "skills": ["evaluate", "classroom-use", "energy-society"],
        "sdgs": ["4", "13"],
        "title": title,
        "excerpt": excerpt,
        "insights": insights,
        "questions": questions[:5],
        "ethics": ethics,
        "_draft": True,
    }


def module_to_js(mod: dict) -> str:
    # Strip internal flag from emitted object
    data = {k: v for k, v in mod.items() if not k.startswith("_")}
    return json.dumps(data, ensure_ascii=False, indent=2)


def upsert_modules(mod: dict) -> None:
    if not MODULES.exists():
        MODULES.write_text(
            "/* SAIL weekly practice modules — generated/edited from digests */\n"
            "window.WEAVE_LEARN_MODULES = [\n];\n",
            encoding="utf-8",
        )
    src = MODULES.read_text(encoding="utf-8")
    marker = "window.WEAVE_LEARN_MODULES = ["
    if marker not in src:
        raise SystemExit("WEAVE_LEARN_MODULES not found")

    # Remove existing id block via JSON parse of array contents is hard;
    # use regex on "id": "DATE"
    mid = mod["id"]
    src = re.sub(
        rf"\s*\{{\s*\"id\":\s*{re.escape(js_str(mid))}[\s\S]*?\}}\s*,?",
        "\n",
        src,
        count=1,
    )
    entry = module_to_js(mod)
    # indent entry
    entry_indented = "\n  " + entry.replace("\n", "\n  ") + ","
    insert_at = src.index(marker) + len(marker)
    note = "\n  /* draft: edit quiz/insights before learner use */"
    src = src[:insert_at] + note + entry_indented + src[insert_at:]
    MODULES.write_text(src, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("digest", nargs="?", help="Path to digest HTML")
    parser.add_argument("--date", help="YYYY-MM-DD (uses articles/digest-DATE.html)")
    args = parser.parse_args()

    if args.date:
        day = date.fromisoformat(args.date)
        path = ARTICLES / f"digest-{day.isoformat()}.html"
    elif args.digest:
        path = Path(args.digest)
        if not path.is_absolute():
            path = ROOT / path
        m = re.search(r"digest-(\d{4}-\d{2}-\d{2})", path.name)
        if not m:
            raise SystemExit("Could not parse date from digest filename")
        day = date.fromisoformat(m.group(1))
    else:
        raise SystemExit("Provide digest path or --date")

    if not path.exists():
        raise SystemExit(f"Missing {path}")

    headlines = extract_en_headlines(path.read_text(encoding="utf-8"))
    print(f"Found {len(headlines)} headlines in {path.name}")
    print("Building draft module (translating)…")
    mod = build_module(day, headlines)
    upsert_modules(mod)
    print(f"Updated {MODULES.relative_to(ROOT)} with id={mod['id']}")
    print("Edit insights/questions, then open /learn/")


if __name__ == "__main__":
    main()
