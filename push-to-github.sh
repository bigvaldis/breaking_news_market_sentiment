#!/bin/bash
# Push to GitHub using token from auth-token.txt (no typing needed)
cd "$(dirname "$0")"

if [ ! -f auth-token.txt ]; then
  echo "Create auth-token.txt with your GitHub Personal Access Token (one line, token only)"
  echo "Get one at: https://github.com/settings/tokens"
  exit 1
fi

TOKEN=$(cat auth-token.txt | tr -d '[:space:]')
if [ "$TOKEN" = "PASTE_YOUR_GITHUB_TOKEN_HERE" ] || [ -z "$TOKEN" ]; then
  echo "Replace the placeholder in auth-token.txt with your actual GitHub token"
  exit 1
fi
git push https://ShaonINT:${TOKEN}@github.com/ShaonINT/breaking_news_market_sentiment.git main
