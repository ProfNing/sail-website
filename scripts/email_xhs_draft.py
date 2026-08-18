#!/usr/bin/env python3
"""
Email private/xiaohongshu/latest.md to your phone inbox.

Used by GitHub Actions after the daily digest. Skips quietly if secrets
are not configured.

Required env:
  XHS_EMAIL_TO   — your address (phone mail app)
  SMTP_HOST      — e.g. smtp.gmail.com
  SMTP_PORT      — e.g. 587
  SMTP_USER      — SMTP login
  SMTP_PASS      — SMTP password / app password

Optional:
  SMTP_FROM      — From address (defaults to SMTP_USER)
  XHS_DRAFT_PATH — override path to the markdown draft
"""

from __future__ import annotations

import os
import re
import smtplib
import ssl
import sys
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


def main() -> int:
    to_addr = (os.environ.get("XHS_EMAIL_TO") or "").strip()
    if not to_addr:
        print("XHS_EMAIL_TO not set — skip email (add repo secrets to enable)")
        return 0

    host = (os.environ.get("SMTP_HOST") or "").strip()
    user = (os.environ.get("SMTP_USER") or "").strip()
    password = (os.environ.get("SMTP_PASS") or "").strip()
    port_s = (os.environ.get("SMTP_PORT") or "587").strip()
    from_addr = (os.environ.get("SMTP_FROM") or user).strip()

    if not host or not user or not password or not from_addr:
        print(
            "SMTP_HOST / SMTP_USER / SMTP_PASS (and SMTP_FROM) required when XHS_EMAIL_TO is set",
            file=sys.stderr,
        )
        return 1

    draft_path = Path(os.environ.get("XHS_DRAFT_PATH") or DEFAULT_DRAFT)
    if not draft_path.is_file():
        print(f"Draft not found: {draft_path}", file=sys.stderr)
        return 1

    md = draft_path.read_text(encoding="utf-8")
    title, body = parse_title_body(md)
    subject = f"SAIL 小红书｜{title}" if title else "SAIL 小红书草稿"
    if len(subject) > 80:
        subject = subject[:77] + "…"

    plain = ""
    if title:
        plain += f"标题\n{title}\n\n"
    plain += f"正文\n{body}\n"
    plain += "\n——\n复制标题和正文到小红书 App 即可发布。草稿仅发到你的邮箱，不会公开到网站。\n"

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
    print("Email sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
