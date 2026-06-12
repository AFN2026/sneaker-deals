#!/usr/bin/env python3
"""Fetch sneaker deal RSS feeds and save to deals.json + deals.js."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import feedparser

KEYWORDS = [
    "Nike trainers",
    "Adidas sneakers",
    "Jordan shoes",
    "New Balance sneakers",
    "Puma trainers",
]

FEEDS = [
    ("HotUKDeals", "https://www.hotukdeals.com/rss/search?q={query}"),
]

# GBP-only: entries with prices in other currencies are stored without a price
_PRICE_RE = re.compile(r'£\s*\d[\d,.]*')


def _extract_price(text: str) -> str:
    m = _PRICE_RE.search(text or "")
    return m.group(0).strip() if m else ""


def fetch_all() -> list[dict]:
    deals: list[dict] = []
    seen: set[str] = set()

    for keyword in KEYWORDS:
        query = keyword.replace(" ", "+")
        for source, template in FEEDS:
            url = template.format(query=query)
            print(f"  Fetching {source} for '{keyword}'…")
            try:
                feed = feedparser.parse(url)
            except Exception as exc:
                print(f"    [!] Error: {exc}")
                continue

            for entry in feed.entries:
                link = entry.get("link", "")
                if not link or link in seen:
                    continue
                seen.add(link)

                title   = entry.get("title", "").strip()
                summary = entry.get("summary", "")
                price   = _extract_price(title) or _extract_price(summary)

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
                    "source":  source,
                    "keyword": keyword,
                })

    deals.sort(key=lambda d: d["date"], reverse=True)
    return deals


if __name__ == "__main__":
    print("Fetching deals…\n")
    deals = fetch_all()

    Path("deals.json").write_text(
        json.dumps(deals, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    # deals.js lets dashboard.html load data without a local server (no CORS issues)
    Path("deals.js").write_text(
        "window.DEALS = " + json.dumps(deals, indent=2, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )

    print(f"\nDone — {len(deals)} deals saved to deals.json and deals.js.")
