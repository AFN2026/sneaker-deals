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

_PRICE_GBP_RE = re.compile(r'£\s*\d[\d,.]*')
_PRICE_USD_RE = re.compile(r'\$\s*\d[\d,.]*')

# HotUKDeals /rss returns the top-30 hot deals as valid XML.
# Slickdeals popular-deals RSS is the equivalent US feed.
# DealNews Shoes RSS targets the footwear category directly (USD).
# All feeds are filtered client-side for sneaker-related entries.
FEEDS = [
    {
        "source":   "HotUKDeals",
        "url":      "https://www.hotukdeals.com/rss",
        "currency": "GBP",
        "price_re": _PRICE_GBP_RE,
    },
    {
        "source":   "Slickdeals",
        "url":      "https://slickdeals.net/newsearch.php?mode=popdeals&searcharea=deals&q=&rss=1",
        "currency": "USD",
        "price_re": _PRICE_USD_RE,
    },
    {
        "source":   "DealNews",
        "url":      "https://www.dealnews.com/c280/Clothing-Accessories/Shoes/?rss=1",
        "currency": "USD",
        "price_re": _PRICE_USD_RE,
    },
]

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

_TAG_RE = re.compile(r'<[^>]+>')


def _strip_html(text: str) -> str:
    return html.unescape(_TAG_RE.sub(' ', text or ''))


def _extract_price(text: str, price_re: re.Pattern) -> str:
    """Return the first price matching price_re found in raw HTML or plain text."""
    m = price_re.search(text or "")
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

    for feed_cfg in FEEDS:
        source   = feed_cfg["source"]
        url      = feed_cfg["url"]
        currency = feed_cfg["currency"]
        price_re = feed_cfg["price_re"]

        print(f"  Fetching {source}…")
        try:
            feed = feedparser.parse(url, agent=_UA)
        except Exception as exc:
            print(f"    [!] Error: {exc}")
            continue

        status = feed.get("status", 200)
        if status >= 400:
            print(f"    [!] HTTP {status} from {url}")
            continue

        total = len(feed.entries)
        print(f"    Got {total} entries — filtering for sneaker keywords…")

        source_count = 0
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
            price = _extract_price(title, price_re) or _extract_price(summary, price_re)

            try:
                pp = entry.published_parsed
                date_str = datetime(
                    pp.tm_year, pp.tm_mon, pp.tm_mday,
                    pp.tm_hour, pp.tm_min, tzinfo=timezone.utc,
                ).strftime("%Y-%m-%d %H:%M")
            except Exception:
                date_str = entry.get("published", "")

            deals.append({
                "title":    title,
                "price":    price,
                "link":     link,
                "date":     date_str,
                "source":   source,
                "currency": currency,
                "keyword":  matched,
            })
            source_count += 1

        print(f"    Matched {source_count} sneaker deal(s) out of {total}")

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
