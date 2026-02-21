"""Fear & Greed Index from Alternative.me (Crypto). Free API, no auth required."""

import urllib.request
import json


FNG_URL = "https://api.alternative.me/fng/?limit=1"


def fetch_fear_greed() -> dict:
    """
    Fetch current Fear & Greed Index from Alternative.me.
    Returns dict with value (0-100), classification, timestamp, or error.
    """
    try:
        req = urllib.request.Request(FNG_URL, headers={"User-Agent": "BreakingNews/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e), "value": None, "classification": None}

    if not data.get("data"):
        return {"error": "no_data", "value": None, "classification": None}

    item = data["data"][0]
    try:
        value = int(item.get("value", 0))
    except (TypeError, ValueError):
        value = 0

    return {
        "value": value,
        "classification": item.get("value_classification", "Unknown"),
        "timestamp": item.get("timestamp"),
    }
