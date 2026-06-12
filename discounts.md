# Sneaker Deals — Data Source Notes

## Source

**HotUKDeals** (`https://www.hotukdeals.com/rss`)

The RSS feed returns the current **top 30 hot deals** across all categories — it is not keyword-searchable. `fetch_deals.py` filters these entries locally using two keyword sets:

- **Brand names** (nike, adidas, jordan, new balance, puma, reebok, vans, converse) — matched against title **or** summary text.
- **Generic footwear terms** (trainers, sneakers) — matched against the **title only**, to avoid false positives from product descriptions that mention sneakers incidentally (e.g. "pairs well with trainers").

## Limitation

Results depend entirely on whether sneaker deals happen to appear in today's top 30. On days with no sneaker entries in the hot list, `deals.json` will be empty. Running the fetch more frequently (e.g. every few hours via the scheduled job) increases the chance of catching deals as they trend.

## Why not the search RSS?

HotUKDeals previously offered `https://www.hotukdeals.com/rss/search?q=...` for keyword-filtered feeds. This endpoint was removed (returns 404 as of June 2026). The main `/rss` feed is the only working XML endpoint they expose.
