# 小红书草稿（仅本地 / Action 临时文件）

这里的 `digest-*.md` / `latest.md` **不会**推送到 GitHub 或公开网站（已在 `.gitignore`）。

## 为什么以前标题总撞车？

旧逻辑用固定模板（如「课堂与考试在变，气候账本也在逼近」）+ 每天相同的「看点/提醒」套话，所以会：

- 标题几乎不变  
- 正文大段重复  

现已改为：

1. **推荐：LLM 润色**（有 API key 时）——按你的手改风格写新标题与三点观察  
2. **兜底：启发式**——从当日中文标题抽钩子生成标题，去掉固定套话，并避开近日用过的标题  

## 提高质量（推荐）

在仓库 **Settings → Secrets → Actions** 添加：

| Secret | 说明 |
|--------|------|
| `XHS_LLM_API_KEY` | OpenAI 兼容接口的 key（也可用 `OPENAI_API_KEY`） |
| `XHS_LLM_BASE_URL` | 可选，默认 `https://api.openai.com/v1` |
| `XHS_LLM_MODEL` | 可选，默认 `gpt-4o-mini` |

用 DeepSeek / Groq / Azure 等亦可，只要兼容 Chat Completions。

本地试跑：

```bash
export XHS_LLM_API_KEY='sk-...'
python3 scripts/publish_digest.py --date 2026-08-24 --skip-collect
# 看 private/xiaohongshu/latest.md
```

手改过的稿件请保留文件头 `# hand-edited: true`，同日自动任务不会覆盖 `latest.md`。

## 每天发到手机（Resend → Outlook）

| Secret | 填什么 |
|--------|--------|
| `XHS_EMAIL_TO` | 你的 Outlook 地址 |
| `RESEND_API_KEY` | Resend API key |
| `EMAIL_FROM` | 已验证发件人（测试可用 `SAIL <onboarding@resend.dev>`） |

未配置 LLM 时仍会发启发式草稿；配上 LLM 后邮件质量会接近你的手改版。
