#!/usr/bin/env python3
"""
Email private/xiaohongshu/latest.md to your phone inbox.

Used by GitHub Actions after the daily digest. Skips quietly if no
mail secrets are configured.

Option A — Resend (recommended; works when Outlook blocks basic SMTP):
  RESEND_API_KEY   — from https://resend.com
  XHS_EMAIL_TO     — inbox on your phone (Outlook OK as *recipient*)
  EMAIL_FROM       — must be a verified sender/domain in Resend
                     (or Resend's onboarding from-address)

Option B — SMTP (Gmail app password, etc.):
  XHS_EMAIL_TO, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS
  SMTP_FROM optional (defaults to SMTP_USER)

Note: Personal Outlook often rejects SMTP password login
("basic authentication is disabled"). Prefer Resend, and keep
Outlook only as XHS_EMAIL_TO.
"""

from __future__ import annotations

import json
import os
import re
import smtplib
import ssl
import sys
import urllib.error
import urllib.request
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DRAFT = ROOT / "private" / "xiaohongshu" / "latest.md"


def parse_title_body(md: str) -> tuple[str, str]:
    title_m = re.search(r"##\s*标题\s*\n+(.+?)(?:\n\s*\n|\n##)", md, re.S)
    body_m = re.search(r"##\s*正文\s*\n+(.*)\Z", md, re.S)
    title = (title_m.group(1).strip() if title_m else "").strip()
    body = (body_m.group(1).strip() if body_m else md.strip()).strip()
    return title, body


def build_plain(title: str, body: str) -> str:
    plain = ""
    if title:
        plain += f"标题\n{title}\n\n"
    plain += f"正文\n{body}\n"
    plain += (
        "\n——\n"
        "复制标题和正文到小红书 App 即可发布。"
        "草稿仅发到你的邮箱，不会公开到网站。\n"
    )
    return plain


def send_resend(to_addr: str, subject: str, plain: str) -> None:
    api_key = (os.environ.get("RESEND_API_KEY") or "").strip()
    from_addr = (os.environ.get("EMAIL_FROM") or "").strip()
    if not api_key or not from_addr:
        raise SystemExit(
            "RESEND_API_KEY and EMAIL_FROM are required for Resend sending"
        )
    payload = {
        "from": from_addr,
        "to": [to_addr],
        "subject": subject,
        "text": plain,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            # Cloudflare (in front of Resend) rejects bare Python-urllib UA (error 1010).
            "User-Agent": "SAIL-digest/1.0 (+https://github.com/ProfNing/sail-website)",
        },
    )
    print(f"Sending 小红书 draft to {to_addr} via Resend …")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            print(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Resend HTTP {exc.code}: {detail}") from exc
    print("Email sent (Resend).")


def send_smtp(to_addr: str, subject: str, plain: str) -> None:
    host = (os.environ.get("SMTP_HOST") or "").strip()
    user = (os.environ.get("SMTP_USER") or "").strip()
    password = (os.environ.get("SMTP_PASS") or "").strip()
    port_s = (os.environ.get("SMTP_PORT") or "587").strip()
    from_addr = (os.environ.get("SMTP_FROM") or user).strip()

    if not host or not user or not password or not from_addr:
        raise SystemExit(
            "SMTP_HOST / SMTP_USER / SMTP_PASS required when using SMTP"
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(plain)

    port = int(port_s)
    context = ssl.create_default_context()
    print(f"Sending 小红书 draft to {to_addr} via {host}:{port} …")
    with smtplib.SMTP(host, port, timeout=60) as smtp:
        smtp.ehlo()
        if port != 25:
            smtp.starttls(context=context)
            smtp.ehlo()
        smtp.login(user, password)
        smtp.send_message(msg)
    print("Email sent (SMTP).")


def main() -> int:
    to_addr = (os.environ.get("XHS_EMAIL_TO") or "").strip()
    if not to_addr:
        print("XHS_EMAIL_TO not set — skip email")
        return 0

    draft_path = Path(os.environ.get("XHS_DRAFT_PATH") or DEFAULT_DRAFT)
    if not draft_path.is_file():
        print(f"Draft not found: {draft_path}", file=sys.stderr)
        return 1

    md = draft_path.read_text(encoding="utf-8")
    title, body = parse_title_body(md)
    subject = f"SAIL 小红书｜{title}" if title else "SAIL 小红书草稿"
    if len(subject) > 80:
        subject = subject[:77] + "…"
    plain = build_plain(title, body)

    if (os.environ.get("RESEND_API_KEY") or "").strip():
        send_resend(to_addr, subject, plain)
        return 0

    if (os.environ.get("SMTP_HOST") or "").strip():
        send_smtp(to_addr, subject, plain)
        return 0

    print(
        "No RESEND_API_KEY or SMTP_HOST — skip email. "
        "Outlook often blocks SMTP passwords; Resend is recommended.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
