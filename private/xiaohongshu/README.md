# 小红书草稿（仅本地）

这里的 `digest-*.md` / `latest.md` **不会**推送到 GitHub 或公开网站。

每天在本机生成公开简报时会顺带写出中文小红书文案：

```bash
python3 scripts/publish_digest.py
```

然后打开 `latest.md`，复制「标题」和「正文」到小红书 App 发布。

GitHub Action 只发布网站上的公开简报，不会提交本目录里的草稿。
