#!/usr/bin/env python3
"""Fetch sneaker deal RSS feeds and save to deals.json + deals.js."""

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import feedparser

# Brand terms are checked against title + summary (brand names are unlikely
# to appear incidentally in unrelated product descriptions).
BRAND_KEYWORDS = [
    "nike",
    "adidas",
    "jordan",
    "new balance",
    "puma",
    "reebok",
    "vans",
    "converse",
]

# Generic footwear terms are checked against the title only — they appear too
# often in unrelated product summaries (e.g. "pairs well with trainers").
TITLE_ONLY_KEYWORDS = [
    "trainers",
    "sneakers",
]

# HotUKDeals /rss/search was removed; /rss returns the top-30 hot deals as
# valid XML. We filter client-side for sneaker-related entries.
FEED_SOURCE = "HotUKDeals"
FEED_URL    = "https://www.hotukdeals.com/rss"

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

_TAG_RE   = re.compile(r'<[^>]+>')
_PRICE_RE = re.compile(r'£\s*\d[\d,.]*')


def _strip_html(text: str) -> str:
    return html.unescape(_TAG_RE.sub(' ', text or ''))


def _extract_price(text: str) -> str:
    """Return the first GBP price found in raw HTML or plain text."""
    m = _PRICE_RE.search(text or "")
    return m.group(0).strip() if m else ""


def _first_match(title: str, summary_html: str) -> str | None:
    """Return the first keyword matched, or None if the entry is not a sneaker deal.

    Brand names are matched against title + summary; generic terms (trainers,
    sneakers) are matched against the title only to avoid false positives from
    styling suggestions in product descriptions (e.g. "pairs with trainers").
    """
    title_lower   = title.lower()
    summary_lower = _strip_html(summary_html).lower()
    full_lower    = title_lower + " " + summary_lower

    for kw in BRAND_KEYWORDS:
        if kw in full_lower:
            return kw
    for kw in TITLE_ONLY_KEYWORDS:
        if kw in title_lower:
            return kw
    return None


def fetch_all() -> list[dict]:
    deals: list[dict] = []
    seen:  set[str]   = set()

    print(f"  Fetching {FEED_SOURCE}…")
    try:
        feed = feedparser.parse(FEED_URL, agent=_UA)
    except Exception as exc:
        print(f"    [!] Error: {exc}")
        return deals

    status = feed.get("status", 200)
    if status >= 400:
        print(f"    [!] HTTP {status} from {FEED_URL}")
        return deals

    total = len(feed.entries)
    print(f"    Got {total} entries from top-30 feed — filtering for sneaker keywords…")

    for entry in feed.entries:
        link = entry.get("link", "")
        if not link or link in seen:
            continue

        title   = entry.get("title", "").strip()
        summary = entry.get("summary", "")

        matched = _first_match(title, summary)
        if not matched:
            continue

        seen.add(link)
        price = _extract_price(title) or _extract_price(summary)

        try:
            pp = entry.published_parsed
            date_str = datetime(
                pp.tm_year, pp.tm_mon, pp.tm_mday,
                pp.tm_hour, pp.tm_min, tzinfo=timezone.utc,
            ).strftime("%Y-%m-%d %H:%M")
        except Exception:
            date_str = entry.get("published", "")

        deals.append({
            "title":   title,
            "price":   price,
            "link":    link,
            "date":    date_str,
            "source":  FEED_SOURCE,
            "keyword": matched,
        })

    print(f"    Matched {len(deals)} sneaker deal(s) out of {total}")
    deals.sort(key=lambda d: d["date"], reverse=True)
    return deals


if __name__ == "__main__":
    print("Fetching deals…\n")
    deals = fetch_all()

    Path("deals.json").write_text(
        json.dumps(deals, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    # deals.js lets index.html load data without a local server (no CORS issues)
    Path("deals.js").write_text(
        "window.DEALS = " + json.dumps(deals, indent=2, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )

    print(f"\nDone — {len(deals)} deals saved to deals.json and deals.js.")
