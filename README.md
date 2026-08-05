# SAIL 启航

**Sustainability · AI · Learning**

Languages: Chinese (中文) · English · Korean (한국어)

## Preview

```bash
cd /home/nancy/workdir/website
python3 -m http.server 8080
```

Open http://localhost:8080

## Private visitor stats (you only)

The public site does **not** show visitor numbers. Stats go to [GoatCounter](https://www.goatcounter.com) (privacy-friendly, free for personal use).

1. Sign up at https://www.goatcounter.com
2. Create a site with code **`sail-website`** (must match `SAIL_GOATCOUNTER` in `js/main.js`)
3. In settings, set **Dashboard viewable by** → **logged in users only**
4. View daily visitors at https://sail-website.goatcounter.com while signed in

Shortcut on the site (not in the public menu): https://profning.github.io/sail-website/stats/

Localhost previews are not counted.

## Private collection (local only)

Headlines are collected for **you only**. `js/collected.js` is gitignored and is **not** published to GitHub Pages.

Feeds (edit `feeds.json`):
- **AI news** — MIT News, TechCrunch, The Verge
- **Learning** — AI education, MIS education, AI in business schools (Google News queries), Campus Technology, TechCrunch EdTech, Poets&Quants, MIT Sloan Review, MIS Quarterly
- **AI × Sustainability** — Google News (AI for sustainability / green AI / climate tech), TechCrunch Climate
- **Stanford Doerr School of Sustainability** — Google News coverage of the school

```bash
python3 scripts/collect_feeds.py
python3 -m http.server 8080
```

Then open http://localhost:8080/collected/ — not linked from the public site.

## Public daily digest (no API key)

Publishes a trilingual extractive roundup to `articles/digest-YYYY-MM-DD.html` and the articles catalog. Uses free Google Translate (gtx) — no API key.

```bash
python3 scripts/publish_digest.py
```

GitHub Action (`.github/workflows/daily-digest.yml`) runs this daily and commits only the public digest files — never `js/collected.js`.

### Private 小红书 draft (local only)

When you run `publish_digest.py` **on your machine**, it also writes a Chinese note ready to paste into 小红书:

- `private/xiaohongshu/latest.md`
- `private/xiaohongshu/digest-YYYY-MM-DD.md`

These files are gitignored and are **not** on the public site. Open `latest.md`, copy 标题 + 正文 into the app. GitHub Actions skips this step.

## Write an article (Chinese → auto EN / KO)

1. Copy the sample draft and edit in Chinese:

```bash
cp drafts/sample-green-campus.md drafts/my-article.md
```

2. Front matter fields:

```yaml
---
slug: my-article          # becomes articles/my-article.html
date: 2026-07-31
topics: [ai, sus, edu]    # any of: ai, sus, edu (edu = Learning)
minutes: 5
title: 中文标题
excerpt: 中文摘要（列表里显示）
---

正文。用空行分段。

## 小标题

> 引用
```

3. Publish (translates title, excerpt, and body into English & Korean):

```bash
python3 scripts/publish_article.py drafts/my-article.md
```

4. Review at `articles/my-article.html` — switch 启航 / SAIL / 출항 (or the language buttons) and edit the EN/KO panels if you want finer wording.

Machine translation is a draft. Keep the Chinese as source of truth; tweak EN/KO when needed.
