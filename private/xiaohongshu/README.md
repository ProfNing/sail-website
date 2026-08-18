# 小红书草稿（仅本地 / Action 临时文件）

这里的 `digest-*.md` / `latest.md` **不会**推送到 GitHub 或公开网站（已在 `.gitignore`）。

## 本机生成

```bash
python3 scripts/publish_digest.py
```

打开 `latest.md`，复制「标题」和「正文」到小红书 App。

若手改过草稿，在文件头保留 `# hand-edited: true`，同一天的自动任务不会覆盖 `latest.md`。

## 每天发到手机邮箱（推荐）

GitHub Action 在发布公开简报后，会尝试把草稿发到你的邮箱。

在仓库 **Settings → Secrets and variables → Actions** 添加：

| Secret | 示例 |
|--------|------|
| `XHS_EMAIL_TO` | 你手机上能看的邮箱 |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | 你的发信邮箱 |
| `SMTP_PASS` | Gmail **应用专用密码**（不是登录密码） |
| `SMTP_FROM` | 可选，默认等于 `SMTP_USER` |

Gmail：账号 → 安全性 → 开启两步验证 → 应用专用密码。

未配置 `XHS_EMAIL_TO` 时，邮件步骤会自动跳过，不影响网站简报。

本机试发：

```bash
export XHS_EMAIL_TO=you@example.com
export SMTP_HOST=smtp.gmail.com SMTP_PORT=587
export SMTP_USER=you@example.com SMTP_PASS='xxxx'
python3 scripts/email_xhs_draft.py
```
