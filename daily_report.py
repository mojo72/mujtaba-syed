#!/usr/bin/env python3
"""
Daily visitor digest for mujtabasyed.goatcounter.com
Sends a summary email to sm.mujtaba72@gmail.com via Gmail API.
Run at 8:00 AM daily.
"""

import json
import urllib.request
import urllib.parse
import smtplib
import ssl
import os
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

GOATCOUNTER_SITE = "mojo"
GOATCOUNTER_TOKEN = os.environ.get("GOATCOUNTER_TOKEN", "")  # set after GoatCounter signup
RECIPIENT = "sm.mujtaba72@gmail.com"
SMTP_USER = os.environ.get("SMTP_USER", "")    # Gmail address used to send
SMTP_PASS = os.environ.get("SMTP_PASS", "")    # Gmail App Password


def gc_get(path, params=None):
    url = f"https://{GOATCOUNTER_SITE}.goatcounter.com/api/v0{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {GOATCOUNTER_TOKEN}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def fetch_stats():
    now = datetime.now(timezone.utc)
    today_start = (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    week_start  = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    now_str     = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Last 24h totals
    hits_24h = gc_get("/stats/total", {"start": today_start, "end": now_str})

    # 7-day daily breakdown
    hits_7d = gc_get("/stats/hits", {
        "start": week_start,
        "end": now_str,
        "daily": "true",
    })

    # Top referrers (last 24h)
    referrers = gc_get("/stats/refs", {"start": today_start, "end": now_str, "limit": 5})

    # Top countries (last 24h)
    countries = gc_get("/stats/countries", {"start": today_start, "end": now_str, "limit": 5})

    # Browsers (last 24h)
    browsers = gc_get("/stats/browsers", {"start": today_start, "end": now_str, "limit": 5})

    return hits_24h, hits_7d, referrers, countries, browsers


def trend_bar(n, max_n, width=20):
    if max_n == 0:
        return "[" + " " * width + "]"
    filled = round((n / max_n) * width)
    return "[" + "█" * filled + "░" * (width - filled) + "]"


def build_email(hits_24h, hits_7d, referrers, countries, browsers):
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%A, %d %B %Y")

    # 24h numbers
    views_24h   = hits_24h.get("total", 0)
    unique_24h  = hits_24h.get("total_unique", 0)

    # 7-day breakdown
    days = hits_7d.get("hits", [])
    if len(days) >= 2:
        max_day = max(d.get("count", 0) for d in days) or 1
        trend_section = "7-DAY TREND\n" + "-" * 45 + "\n"
        for d in days:
            label = d.get("day", "")[:10]
            count = d.get("count", 0)
            trend_section += f"  {label}  {trend_bar(count, max_day, 16)} {count:>4} views\n"
    else:
        # Fewer than 2 days of data: show hourly for yesterday
        trend_section = "HOURLY BREAKDOWN (previous 24h — 7-day data not yet available)\n" + "-" * 45 + "\n"
        hourly = gc_get("/stats/hits", {
            "start": (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end":   now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        hours = hourly.get("hits", [])
        max_h = max((h.get("count", 0) for h in hours), default=1) or 1
        for h in hours:
            label = h.get("hour", "")
            count = h.get("count", 0)
            trend_section += f"  {label}  {trend_bar(count, max_h, 12)} {count:>3}\n"

    # Referrers
    ref_rows = referrers.get("refs", [])[:5]
    ref_section = "TOP REFERRERS (24h)\n" + "-" * 45 + "\n"
    if ref_rows:
        for r in ref_rows:
            ref_section += f"  {r.get('name','(direct)'):<30} {r.get('count',0):>4} visits\n"
    else:
        ref_section += "  No referrer data yet.\n"

    # Countries
    country_rows = countries.get("countries", [])[:5]
    country_section = "TOP COUNTRIES (24h)\n" + "-" * 45 + "\n"
    if country_rows:
        for c in country_rows:
            country_section += f"  {c.get('name','Unknown'):<28} {c.get('count',0):>4} visits\n"
    else:
        country_section += "  No country data yet.\n"

    # Browsers
    browser_rows = browsers.get("browsers", [])[:5]
    browser_section = "BROWSERS (24h)\n" + "-" * 45 + "\n"
    if browser_rows:
        for b in browser_rows:
            browser_section += f"  {b.get('name','Unknown'):<28} {b.get('count',0):>4} visits\n"
    else:
        browser_section += "  No browser data yet.\n"

    body = f"""
MUJTABA SYED PORTFOLIO - DAILY VISITOR DIGEST
{date_str}
{"=" * 45}

LAST 24 HOURS
-----------------------------------------
  Page Views   : {views_24h}
  Unique Visits: {unique_24h}
  Full report  : https://{GOATCOUNTER_SITE}.goatcounter.com

{"=" * 45}

{trend_section}
{"=" * 45}

{ref_section}
{"=" * 45}

{country_section}
{"=" * 45}

{browser_section}
{"=" * 45}

View your full live dashboard: https://{GOATCOUNTER_SITE}.goatcounter.com
Portfolio URL: https://mojo72.github.io/mujtaba-syed/

-- Automated digest. Delivered daily at 8:00 AM IST.
""".strip()

    return body


def send_email(subject, body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SMTP_USER
    msg["To"]      = RECIPIENT
    msg.attach(MIMEText(body, "plain"))

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as server:
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, RECIPIENT, msg.as_string())
    print(f"Email sent to {RECIPIENT}")


if __name__ == "__main__":
    if not GOATCOUNTER_TOKEN:
        print("ERROR: GOATCOUNTER_TOKEN not set. Export it before running.")
        raise SystemExit(1)
    if not SMTP_PASS:
        print("ERROR: SMTP_PASS not set. Export your Gmail App Password.")
        raise SystemExit(1)

    hits_24h, hits_7d, refs, countries, browsers = fetch_stats()
    body    = build_email(hits_24h, hits_7d, refs, countries, browsers)
    subject = f"Portfolio Digest - {datetime.now(timezone.utc).strftime('%d %b %Y')} | {hits_24h.get('total', 0)} views today"
    send_email(subject, body)
