# 小红书草稿（仅本地 / Action 临时文件）

这里的 `digest-*.md` / `latest.md` **不会**推送到 GitHub 或公开网站（已在 `.gitignore`）。

## 本机生成

```bash
python3 scripts/publish_digest.py
```

打开 `latest.md`，复制「标题」和「正文」到小红书 App。

若手改过草稿，在文件头保留 `# hand-edited: true`，同一天的自动任务不会覆盖 `latest.md`。

## 每天发到手机邮箱（Outlook）

GitHub Action 在发布公开简报后，会把草稿发到你的邮箱。

在仓库 **Settings → Secrets and variables → Actions** 添加：

| Secret | Outlook 填写 |
|--------|----------------|
| `XHS_EMAIL_TO` | 你手机上能看的邮箱（可同下） |
| `SMTP_HOST` | `smtp.office365.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | 完整 Outlook 地址，如 `you@outlook.com` |
| `SMTP_PASS` | Outlook 登录密码；若开了两步验证，用[应用密码](https://account.microsoft.com/security) |
| `SMTP_FROM` | 与 `SMTP_USER` 相同即可 |

说明：
- 个人 Outlook / Hotmail / Live 一般用 `smtp.office365.com` + `587`（STARTTLS）
- 学校/公司 Microsoft 365：管理员需允许该账号 **Authenticated SMTP**；若仍失败，问 IT 是否禁用了基本验证
- 未配置 `XHS_EMAIL_TO` 时邮件步骤会跳过，不影响网站简报

本机试发：

```bash
export XHS_EMAIL_TO='you@outlook.com'
export SMTP_HOST=smtp.office365.com SMTP_PORT=587
export SMTP_USER='you@outlook.com' SMTP_PASS='your-password-or-app-password'
export SMTP_FROM='you@outlook.com'
python3 scripts/email_xhs_draft.py
```

试通后：GitHub → **Actions** → **Daily public digest** → **Run workflow**。
