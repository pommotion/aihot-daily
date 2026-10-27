#!/usr/bin/env python3
"""Build RSS 2.0 feed from reports/*.html (stdlib only)."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "reports"
OUTPUT_PATH = ROOT / "feed.xml"
BASE_URL = "https://aihot.1986318.xyz"
CHANNEL_TITLE = "AI DAILY"
CHANNEL_DESCRIPTION = "每日 AI 行业日报"
MAX_ITEMS = 30
DATE_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})\.html$")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
META_DESC_RE = re.compile(
    r'<meta\s+[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)
META_DESC_RE_ALT = re.compile(
    r'<meta\s+[^>]*content=["\'](.*?)["\'][^>]*name=["\']description["\']',
    re.IGNORECASE | re.DOTALL,
)
LEAD_RE = re.compile(
    r'<div\s+class=["\']lead-text["\'][^>]*>(.*?)</div>',
    re.IGNORECASE | re.DOTALL,
)
PARA_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")


def strip_markup(fragment: str) -> str:
    text = TAG_RE.sub("", fragment)
    text = html.unescape(text)
    return " ".join(text.split())


def extract_title(document: str) -> str:
    match = TITLE_RE.search(document)
    if not match:
        return CHANNEL_TITLE
    return strip_markup(match.group(1))


def extract_meta_description(document: str) -> str | None:
    for pattern in (META_DESC_RE, META_DESC_RE_ALT):
        match = pattern.search(document)
        if match:
            text = strip_markup(match.group(1))
            if text:
                return text
    return None


def extract_lead(document: str) -> str | None:
    match = LEAD_RE.search(document)
    if not match:
        return None
    text = strip_markup(match.group(1))
    return text if len(text) >= 10 else None


def extract_first_paragraph(document: str) -> str | None:
    for match in PARA_RE.finditer(document):
        text = strip_markup(match.group(1))
        if len(text) >= 10:
            return text
    return None


def extract_description(document: str) -> str:
    for extractor in (
        extract_meta_description,
        extract_lead,
        extract_first_paragraph,
    ):
        result = extractor(document)
        if result:
            return result
    return CHANNEL_DESCRIPTION


def parse_report_date(filename: str) -> datetime | None:
    match = DATE_PATTERN.match(filename)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


def collect_reports() -> list[tuple[datetime, Path, str]]:
    entries: list[tuple[datetime, Path, str]] = []
    if not REPORTS_DIR.is_dir():
        return entries
    for path in REPORTS_DIR.glob("*.html"):
        report_date = parse_report_date(path.name)
        if report_date is None:
            continue
        entries.append((report_date, path, path.read_text(encoding="utf-8")))
    entries.sort(key=lambda item: item[0], reverse=True)
    return entries[:MAX_ITEMS]


def build_rss(items: list[tuple[datetime, Path, str]]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        "  <channel>",
        f"    <title>{escape(CHANNEL_TITLE)}</title>",
        f"    <link>{escape(BASE_URL)}</link>",
        f"    <description>{escape(CHANNEL_DESCRIPTION)}</description>",
        f"    <language>zh-CN</language>",
    ]
    if items:
        last_build = format_datetime(items[0][0], usegmt=True)
        lines.append(f"    <lastBuildDate>{escape(last_build)}</lastBuildDate>")

    for report_date, path, document in items:
        date_str = report_date.strftime("%Y-%m-%d")
        item_url = f"{BASE_URL}/reports/{date_str}.html"
        title = extract_title(document)
        description = extract_description(document)
        pub_date = format_datetime(report_date, usegmt=True)
        lines.extend(
            [
                "    <item>",
                f"      <title>{escape(title)}</title>",
                f"      <link>{escape(item_url)}</link>",
                f"      <description>{escape(description)}</description>",
                f"      <pubDate>{escape(pub_date)}</pubDate>",
                f'      <guid isPermaLink="true">{escape(item_url)}</guid>',
                "    </item>",
            ]
        )

    lines.extend(["  </channel>", "</rss>", ""])
    return "\n".join(lines)


def main() -> None:
    items = collect_reports()
    OUTPUT_PATH.write_text(build_rss(items), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} with {len(items)} items")


if __name__ == "__main__":
    main()
