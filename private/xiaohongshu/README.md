# 小红书草稿（仅本地 / Action 临时文件）

这里的 `digest-*.md` / `latest.md` **不会**推送到 GitHub 或公开网站（已在 `.gitignore`）。

## 每天发到手机（推荐：Resend → 你的 Outlook）

Outlook 个人/许多学校账号会禁用 SMTP「密码登录」（报错
`basic authentication is disabled`）。所以：

- **收件箱**继续用 Outlook（手机上看信）
- **发信**用 [Resend](https://resend.com)（Actions 友好）

### 设置

1. 注册 Resend，创建 API key  
2. 仓库 **Settings → Secrets and variables → Actions** 添加：

| Secret | 填什么 |
|--------|--------|
| `XHS_EMAIL_TO` | 你的 Outlook 地址 |
| `RESEND_API_KEY` | Resend API key |
| `EMAIL_FROM` | Resend 已验证发件人。测试可用 `SAIL <onboarding@resend.dev>`（仅能发到你注册 Resend 的邮箱）；长期请验证自己的域名 |

3. **Actions → Daily public digest → Run workflow** 测一次  

邮件步骤失败时**不会**再把整个简报任务标红（`continue-on-error`）。

### 可选：SMTP（Gmail 应用专用密码等）

若不用 Resend，可设 `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASS`。  
Outlook SMTP 密码登录通常不可用，勿再依赖。
