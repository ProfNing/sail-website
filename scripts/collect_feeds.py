#!/usr/bin/env python3
"""
Collect article headlines from configured RSS/Atom feeds.

Writes js/collected.js for the static site. Does not republish full articles —
only title, short excerpt, source, date, and link to the original.

Usage:
  python3 scripts/collect_feeds.py
"""

from __future__ import annotations

import email.utils
import hashlib
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEEDS_PATH = ROOT / "feeds.json"
OUT_PATH = ROOT / "js" / "collected.js"

UA = "SAIL-collect/1.0 (+https://github.com/ProfNing/sail-website)"


def strip_html(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def truncate(text: str, n: int = 180) -> str:
    text = strip_html(text)
    if len(text) <= n:
        return text
    cut = text[: n - 1].rsplit(" ", 1)[0]
    return (cut or text[: n - 1]).rstrip(".,;:") + "…"


def parse_date(raw: str | None) -> str:
    if not raw:
        return datetime.now(timezone.utc).date().isoformat()
    raw = raw.strip()
    try:
        dt = email.utils.parsedate_to_datetime(raw)
        return dt.astimezone(timezone.utc).date().isoformat()
    except Exception:
        pass
    m = re.search(r"(\d{4}-\d{2}-\d{2})", raw)
    if m:
        return m.group(1)
    try:
        # Atom often uses timezone offsets like +00:00
        cleaned = re.sub(r"([+-]\d{2}):(\d{2})$", r"\1\2", raw)
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+0000"
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
            try:
                return datetime.strptime(cleaned, fmt).date().isoformat()
            except ValueError:
                continue
    except Exception:
        pass
    return datetime.now(timezone.utc).date().isoformat()


def local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def text_of(el: ET.Element | None) -> str:
    if el is None:
        return ""
    return "".join(el.itertext()).strip()


def find_child(parent: ET.Element, names: set[str]) -> ET.Element | None:
    for child in list(parent):
        if local(child.tag) in names:
            return child
    return None


def find_link(entry: ET.Element) -> str:
    # Atom <link href="...">
    for child in list(entry):
        if local(child.tag) == "link":
            href = child.attrib.get("href") or text_of(child)
            rel = child.attrib.get("rel", "alternate")
            if href and rel in ("alternate", "", "self"):
                return href.strip()
    # RSS <link>
    link_el = find_child(entry, {"link"})
    if link_el is not None:
        href = link_el.attrib.get("href") or text_of(link_el)
        if href:
            return href.strip()
    # RSS guid
    guid = find_child(entry, {"guid"})
    if guid is not None:
        t = text_of(guid)
        if t.startswith("http"):
            return t
    return ""


def fetch(url: str) -> bytes:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"})
    with urllib.request.urlopen(req, timeout=25, context=ctx) as resp:
        return resp.read()


def parse_feed(xml_bytes: bytes) -> list[dict]:
    # Some feeds prepend HTML/whitespace/BOM before the XML declaration
    text = xml_bytes.decode("utf-8", errors="replace")
    start = text.find("<?xml")
    if start < 0:
        start = text.find("<rss")
    if start < 0:
        start = text.find("<feed")
    if start > 0:
        text = text[start:]
    root = ET.fromstring(text.encode("utf-8"))
    items = []
    # RSS channel/item
    for el in root.iter():
        if local(el.tag) in {"item", "entry"}:
            title = text_of(find_child(el, {"title"}))
            link = find_link(el)
            summary = text_of(find_child(el, {"description", "summary", "content", "content:encoded"}))
            # content namespaced often as content
            if not summary:
                for child in list(el):
                    if local(child.tag) in {"description", "summary", "content", "encoded"}:
                        summary = text_of(child)
                        break
            date_raw = text_of(find_child(el, {"pubDate", "published", "updated", "date"}))
            if not title or not link:
                continue
            items.append(
                {
                    "title": strip_html(title),
                    "url": link,
                    "excerpt": truncate(summary or title),
                    "date": parse_date(date_raw),
                }
            )
    return items


def item_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def collect() -> list[dict]:
    cfg = json.loads(FEEDS_PATH.read_text(encoding="utf-8"))
    max_items = int(cfg.get("maxItems", 24))
    per_feed = int(cfg.get("perFeed", 6))
    collected: list[dict] = []
    seen = set()

    for feed in cfg.get("feeds", []):
        url = feed["url"]
        name = feed.get("name") or feed.get("id") or url
        topics = feed.get("topics") or []
        print(f"Fetching {name} …")
        try:
            raw = fetch(url)
            entries = parse_feed(raw)[:per_feed]
        except Exception as exc:
            print(f"  skip ({exc})", file=sys.stderr)
            continue
        print(f"  {len(entries)} items")
        for entry in entries:
            u = entry["url"]
            if u in seen:
                continue
            seen.add(u)
            collected.append(
                {
                    "id": item_id(u),
                    "title": entry["title"],
                    "url": u,
                    "excerpt": entry["excerpt"],
                    "date": entry["date"],
                    "source": name,
                    "topics": topics,
                }
            )

    collected.sort(key=lambda x: x["date"], reverse=True)
    return collected[:max_items]


def write_js(items: list[dict]) -> None:
    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "items": items,
    }
    body = "window.SAIL_COLLECTED = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n"
    OUT_PATH.write_text(body, encoding="utf-8")
    print(f"Wrote {OUT_PATH.relative_to(ROOT)} ({len(items)} items)")


def main() -> None:
    items = collect()
    write_js(items)


if __name__ == "__main__":
    main()
