#!/usr/bin/env bash
set -euo pipefail

# Install feedparser if missing
python -c "import feedparser" 2>/dev/null || {
  echo "Installing feedparser…"
  pip install feedparser -q
}

echo "==> Fetching deals…"
python fetch_deals.py

echo "==> Opening dashboard…"
python -c "
import pathlib, webbrowser
url = pathlib.Path('dashboard.html').resolve().as_uri()
print('Opening:', url)
webbrowser.open(url)
"
