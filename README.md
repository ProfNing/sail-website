# SAIL 启航

**Sustainability · AI · Learning**

Languages: Chinese (中文) · English · Korean (한국어)

## Preview

```bash
cd /home/nancy/workdir/website
python3 -m http.server 8080
```

Open http://localhost:8080

## Collect articles from the web (automatic)

SAIL pulls **headlines + short excerpts + source links** from RSS feeds (not full republished articles).

Sources are listed in `feeds.json`. Edit that file to add/remove feeds.

### Run locally

```bash
python3 scripts/collect_feeds.py
```

This updates `js/collected.js`. Review on the home page (**Collected**) or `/collected/`.

### Run automatically on GitHub

A GitHub Action (`.github/workflows/collect-feeds.yml`) runs **daily** and on demand:

1. Open the repo → **Actions** → **Collect feeds** → **Run workflow**
2. Or wait for the daily schedule

After it commits, GitHub Pages refreshes with the new headlines.

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
topics: [ai, sus, edu]    # any of: ai, sus, edu
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
