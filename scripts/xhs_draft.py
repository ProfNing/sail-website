#!/usr/bin/env python3
"""
Build a private 小红书 observation draft from digest headlines.

Quality path (recommended): set XHS_LLM_API_KEY (OpenAI-compatible) so a model
writes a fresh title + 3-point note in SAIL's hand-edited style.

Fallback: heuristic draft that varies titles from today's headlines and avoids
copy-pasting the same stock paragraphs every day.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XHS_DIR = ROOT / "private" / "xiaohongshu"
SITE_DIGEST_BASE = "https://profning.github.io/sail-website/articles"

STYLE_PROMPT = """你是 SAIL 启航小红书编辑。根据今日公开新闻标题，写一条「每日观察」中文稿。

硬性要求：
1. 标题：≤20字，具体、有张力，必须扣住今天条目里的独特事实（专有名词/事件），禁止套话如「课堂与考试在变」「今日观察」「气候账本也在逼近」。
2. 正文结构固定：
   - 首行：【SAIL 启航 · 每日观察】M月D日（周X）
   - 一句引导：不堆新闻，只挑跟「可持续 · 人工智能 · 学习」真正相关的变化。
   - 用 —— 分隔
   - 正好三个小节：一、二、三、；侧重点在人工智能与可持续；学习最多一句带过或放进某一节末尾。
   - 每节先用自己的话点破含义，再可点到具体新闻，不要只罗列标题。
   - 禁止每天重复的空话，例如「能力分层、检测/隐私」「算力有碳账，应用也可能减灾节能——关键是谁在测」。
   - 结尾给网站链接占位：COMPLETE_URL
3. 不要使用 Markdown 加粗（不要 **）。
4. 口吻冷静、锋利，像观察评论，不像公关稿或新闻播报。
5. 输出严格 JSON（不要其它文字）：
{"title":"...","body":"..."}
"""


def _weekday_zh(d: date) -> str:
    return ("周一", "周二", "周三", "周四", "周五", "周六", "周日")[d.weekday()]


def _bucket_for(item: dict) -> str:
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


def _counts(items: list[dict]) -> dict[str, int]:
    c = {"ai": 0, "sus": 0, "edu": 0}
    for item in items:
        topics = set(item.get("topics") or [])
        if "ai" in topics:
            c["ai"] += 1
        if "sus" in topics:
            c["sus"] += 1
        if "edu" in topics:
            c["edu"] += 1
    return c


def _zh_title(item: dict, translated: dict[tuple[str, str], str]) -> str:
    return translated.get((item["title"], "zh"), item["title"]).strip()


def _recent_titles(limit: int = 10) -> list[str]:
    if not XHS_DIR.is_dir():
        return []
    files = sorted(XHS_DIR.glob("digest-*.md"), reverse=True)[:limit]
    out: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        m = re.search(r"##\s*标题\s*\n+(.+)", text)
        if m:
            out.append(m.group(1).strip())
    return out


def _clip_title(title: str, max_len: int = 20) -> str:
    title = re.sub(r"\s+", "", title.strip())
    title = title.replace("**", "")
    if len(title) > max_len:
        # Prefer cutting at punctuation if possible
        cut = title[:max_len]
        for sep in ("，", "：", "、", "—", "-"):
            i = cut.rfind(sep)
            if i >= 8:
                return cut[:i]
        return cut
    return title


def _headline_hook(zh: str) -> str:
    """Short concrete hook from a Chinese headline (keep ≤8 chars for titles)."""
    s = re.sub(r"\s+", "", zh)
    s = re.sub(r"[《》【】\[\]（）()“”\"']", "", s)
    s = re.split(r"[-—|:：]", s)[0]
    # Prefer a run of CJK characters so mixed EN tokens don't get half-cut
    m = re.search(r"[\u4e00-\u9fff]{2,8}", s)
    if m:
        return m.group(0)
    if len(s) > 8:
        s = s[:8]
    return s


def _llm_draft(
    day: date,
    items: list[dict],
    translated: dict[tuple[str, str], str],
) -> tuple[str, str] | None:
    api_key = (
        os.environ.get("XHS_LLM_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    ).strip()
    if not api_key:
        return None

    base = (
        os.environ.get("XHS_LLM_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
        or "https://api.openai.com/v1"
    ).rstrip("/")
    model = os.environ.get("XHS_LLM_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"

    buckets: dict[str, list[str]] = defaultdict(list)
    for item in items:
        buckets[_bucket_for(item)].append(_zh_title(item, translated))

    recent = _recent_titles()
    payload_headlines = {
        "date": day.isoformat(),
        "weekday": _weekday_zh(day),
        "ai": buckets.get("ai", [])[:5],
        "ai_sus": buckets.get("ai_sus", [])[:3],
        "sus": buckets.get("sus", [])[:3],
        "edu": buckets.get("edu", [])[:2],
        "avoid_titles": recent,
    }
    url_placeholder = f"{SITE_DIGEST_BASE}/digest-{day.isoformat()}.html"
    system = STYLE_PROMPT.replace("COMPLETE_URL", url_placeholder)
    user = (
        "今日材料（JSON）：\n"
        + json.dumps(payload_headlines, ensure_ascii=False, indent=2)
        + "\n\n请写标题与正文。标题不要与 avoid_titles 相似。"
    )

    body = {
        "model": model,
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "SAIL-xhs-draft/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        title = _clip_title(str(parsed.get("title") or ""))
        text = str(parsed.get("body") or "").replace("**", "").strip()
        if not title or not text:
            return None
        if url_placeholder not in text:
            text = text.rstrip() + "\n\n完整中英韩版简报：\n" + url_placeholder
        print(f"小红书 draft via LLM ({model})")
        return title, text + "\n"
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, json.JSONDecodeError, TimeoutError) as exc:
        print(f"LLM 小红书 draft failed, using heuristic: {exc}")
        return None


def _heuristic_draft(
    day: date,
    items: list[dict],
    translated: dict[tuple[str, str], str],
) -> tuple[str, str]:
    """Better-than-template fallback: titles/comments anchored to today's headlines."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        buckets[_bucket_for(item)].append(item)

    def pick(key: str, n: int = 2) -> list[str]:
        return [_zh_title(it, translated) for it in (buckets.get(key) or [])[:n]]

    ai = pick("ai", 3)
    sus = pick("ai_sus", 2) + pick("sus", 2)
    edu = pick("edu", 1)
    c = _counts(items)
    when = f"{day.month}月{day.day}日（{_weekday_zh(day)}）"
    url = f"{SITE_DIGEST_BASE}/digest-{day.isoformat()}.html"
    recent = set(_recent_titles())

    hooks = [_headline_hook(t) for t in (ai + sus) if t]
    hooks = [h for h in hooks if len(h) >= 4]

    title_patterns = [
        lambda: f"{hooks[0]}，规则跟得上吗" if hooks else "",
        lambda: f"{hooks[0]}背后的账单" if hooks else "",
        lambda: f"别只看：{hooks[0]}" if hooks else "",
        lambda: f"{hooks[0]}×气候账" if hooks else "",
        lambda: f"{hooks[0]}，谁在担责" if hooks else "",
    ]
    title = ""
    seed = day.toordinal() % len(title_patterns)
    for i in range(len(title_patterns)):
        cand = _clip_title(title_patterns[(seed + i) % len(title_patterns)]())
        if cand and cand not in recent:
            title = cand
            break
    if not title:
        title = _clip_title(f"SAIL观察｜{day.month}/{day.day}")

    sections: list[str] = []
    if ai:
        lead = ai[0]
        extra = "；".join(ai[1:3]) if len(ai) > 1 else ""
        para = f"一、人工智能\n今日焦点落在：{lead}"
        if extra:
            para += f"。相关还有：{extra}"
        para += "。别停在标题党——问清谁在部署、数据从哪来、责任归谁。"
        sections.append(para)
    if sus:
        lead = sus[0]
        extra = "；".join(sus[1:3]) if len(sus) > 1 else ""
        para = f"{'二' if sections else '一'}、可持续\n{lead}"
        if extra:
            para += f"。另见：{extra}"
        para += "。把「叙事」和「可核验的减排/资源账」分开看，才谈得上可持续。"
        sections.append(para)
    # Keep learning light — only if we still need a third beat
    if len(sections) < 3 and edu:
        sections.append(
            "学习（一点）\n"
            f"{edu[0]}。课堂规则会跟着工具变，但判断力训练不能外包给模型。"
        )
    elif len(sections) < 3 and ai and sus:
        sections.append(
            "交叉提醒\n"
            "算力扩张与气候约束会越来越撞车：公开测法与碳账，比口号更能区分负责任的 AI。"
        )
    elif len(sections) < 3:
        sections.append(
            "今日收束\n"
            f"公开源共 {len(items)} 条（AI {c['ai']} · 可持续 {c['sus']} · 学习 {c['edu']}）。"
            "发布前请再改一版标题，避免与近日撞车。"
        )

    # Renumber 一、二、三、
    labeled: list[str] = []
    for i, sec in enumerate(sections[:3]):
        body = re.sub(r"^[一二三四五]、", "", sec, count=1)
        labeled.append(f"{'一二三'[i]}、{body}")

    text = "\n".join(
        [
            f"【SAIL 启航 · 每日观察】{when}",
            "",
            "不堆新闻，只挑跟「可持续 · 人工智能 · 学习」真正相关的变化。",
            "",
            "——",
            "",
            "\n\n".join(labeled),
            "",
            "——",
            "",
            "（自动草稿 · 建议发布前再改标题）",
            "",
            "完整中英韩版简报：",
            url,
            "",
            "#SAIL启航 #人工智能 #可持续 #每日观察",
            "",
        ]
    )
    print("小红书 draft via heuristic (no LLM key)")
    return title, text


def write_xiaohongshu_draft(
    day: date,
    items: list[dict],
    translated: dict[tuple[str, str], str],
) -> Path | None:
    XHS_DIR.mkdir(parents=True, exist_ok=True)

    llm = _llm_draft(day, items, translated)
    title, body = llm if llm else _heuristic_draft(day, items, translated)

    note = (
        f"# 小红书草稿（私密 · 勿公开到网站）\n"
        f"# hand-edited: false\n"
        f"# 生成时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"# 用法：复制下面「标题」和「正文」到小红书 App 发布\n\n"
        f"## 标题\n\n{title}\n\n"
        f"## 正文\n\n{body}"
    )

    dated = XHS_DIR / f"digest-{day.isoformat()}.md"
    latest = XHS_DIR / "latest.md"
    dated.write_text(note, encoding="utf-8")

    skip_latest = False
    if latest.exists():
        head = latest.read_text(encoding="utf-8")[:400]
        if "hand-edited: true" in head and f"{day.month}月{day.day}日" in head:
            skip_latest = True
            print("Keeping hand-edited latest.md (not overwritten)")
    if not skip_latest:
        latest.write_text(note, encoding="utf-8")
    return dated
