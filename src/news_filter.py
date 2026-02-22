"""Filter and rank news before sentiment analysis.

Only financial and political news from preferred sources are analyzed.
Preferred: CNBC, Bloomberg, Schwab Network, CNN, BBC, ABC News.
Jim Cramer content (Mad Money) and Trump-related content get higher weight.
"""

import re

import pandas as pd


# Preferred sources (higher = more preferred). Used for ranking.
PREFERRED_SOURCES = {
    "CNBC": 10,
    "CNBC Top News": 10,
    "Bloomberg": 10,
    "Bloomberg Markets": 10,
    "Schwab Network": 10,
    "Charles Schwab": 10,
    "Trump (Truth Social)": 10,
    "Trump (X)": 10,
    "CNN": 9,
    "BBC": 9,
    "ABC News": 9,
    "Dow Jones": 7,
    "Reuters": 7,
    "Yahoo Finance": 6,
}

# Keywords that indicate financial news
FINANCIAL_KEYWORDS = re.compile(
    r"\b(stock|market|economy|fed|federal reserve|inflation|recession|"
    r"earnings|trading|invest|investment|wall street|nasdaq|s&p|dow|"
    r"bond|treasury|interest rate|gdp|unemployment|bank|finance|"
    r"sec|ipo|merger|acquisition|dividend|bull|bear)\b",
    re.I,
)

# Keywords that indicate political news (policy, elections, regulation)
POLITICAL_KEYWORDS = re.compile(
    r"\b(trump|biden|congress|senate|house|election|vote|"
    r"policy|regulation|tariff|trade war|white house|"
    r"federal|government|legislation|bill|law)\b",
    re.I,
)

# Jim Cramer / Mad Money content (boost priority)
CRAMER_KEYWORDS = re.compile(r"\b(cramer|mad money)\b", re.I)

# Trump tweet / social content (boost when available)
TRUMP_KEYWORDS = re.compile(r"\b(trump|trump's|trump tweet)\b", re.I)

# Truth Social posts are high-volume (~20-30/day); only keep market-moving topics
TRUTH_SOCIAL_KEYWORDS = re.compile(
    r"\b(tariff|tariffs|trade war|trade deal|import|export|duties|"
    r"war|attack|military|missile|bomb|strike|conflict|defense|"
    r"politic|congress|senate|legislation|executive order|"
    r"geopolit|nato|ally|allies|sanction|"
    r"china|chinese|beijing|xi jinping|"
    r"india|modi|"
    r"iran|iranian|tehran|"
    r"greenland|arctic|"
    r"europe|european|eu\b|brussels|"
    r"uk\b|britain|british|london|"
    r"epstein|"
    r"midterm|mid-term|election|vote|ballot|"
    r"fed\b|federal reserve|interest rate|powell|fed chair|"
    r"crypto|bitcoin|btc|digital asset|"
    r"rare earth|mineral|lithium|cobalt)\b",
    re.I,
)


def _is_relevant_truth_social(text: str) -> bool:
    """Truth Social posts must match specific high-impact topics."""
    if not text or not isinstance(text, str):
        return False
    return bool(TRUTH_SOCIAL_KEYWORDS.search(text))


# News type classification for supervised learning labels
# Priority order: region/topic-specific first, then broad categories last
_TYPE_PATTERNS = [
    ("Trump Post", re.compile(r"truth social|trump \(", re.I)),
    ("China", re.compile(
        r"\b(china|chinese|beijing|xi jinping|ccp|taiwan|south china sea|"
        r"hong kong|huawei|tiktok|byd)\b", re.I)),
    ("Middle East", re.compile(
        r"\b(iran|iranian|tehran|israel|gaza|saudi|opec|oil price|"
        r"iraq|syria|yemen|hezbollah|hamas|lebanon)\b", re.I)),
    ("India", re.compile(r"\b(india|indian|modi|mumbai|nifty|sensex|rupee)\b", re.I)),
    ("Europe", re.compile(
        r"\b(europe|european|eu\b|brussels|ecb|germany|france|italy|spain|"
        r"eurozone|euro\b|uk\b|britain|british|london|boe\b|bank of england)\b", re.I)),
    ("Tariff / Trade", re.compile(
        r"\b(tariff|tariffs|trade war|trade deal|import duty|export ban|"
        r"duties|customs|trade deficit|trade surplus|sanctions?)\b", re.I)),
    ("War / Military", re.compile(
        r"\b(war|attack|military|missile|bomb|strike|conflict|defense|invasion|"
        r"troops|soldier|nato|battlefield|ceasefire|airstrike|drone strike|nuclear)\b", re.I)),
    ("Crypto", re.compile(
        r"\b(crypto|bitcoin|btc|ethereum|eth|blockchain|defi|"
        r"digital asset|stablecoin|altcoin|binance|coinbase)\b", re.I)),
    ("Fed / Monetary", re.compile(
        r"\b(fed\b|federal reserve|interest rate|rate cut|rate hike|"
        r"powell|fed chair|fomc|quantitative|inflation|cpi|ppi|"
        r"monetary policy|yield curve)\b", re.I)),
    ("Political", re.compile(
        r"\b(biden|congress|senate|house|election|vote|midterm|"
        r"republican|democrat|legislation|executive order|white house|"
        r"supreme court|impeach|gop|dnc|rnc|ballot|epstein)\b", re.I)),
    ("Financial", re.compile(
        r"\b(stock|market|economy|earnings|trading|invest|wall street|"
        r"nasdaq|s&p|dow|bond|treasury|gdp|unemployment|bank|"
        r"sec\b|ipo|merger|acquisition|dividend|recession|"
        r"bull|bear|rally|sell-off|crash)\b", re.I)),
    ("US Local", re.compile(
        r"\b(domestic|local|state|governor|mayor|county|sheriff|"
        r"immigration|border|fema|homeland|social security|medicare|"
        r"medicaid|obamacare|student loan|housing)\b", re.I)),
]


def classify_news_type(title: str, summary: str, source: str = "") -> str:
    """Classify an article into a news type for supervised learning labels.

    Returns the most specific matching type. Articles can match multiple
    patterns; the first match in priority order wins (most specific first).
    """
    text = f"{title or ''} {summary or ''}"
    source_lower = (source or "").lower()

    # Trump posts detected by source name
    if "truth social" in source_lower or "trump (x)" in source_lower:
        return "Trump Post"

    for label, pattern in _TYPE_PATTERNS:
        if label == "Trump Post":
            continue
        if pattern.search(text):
            return label

    return "General"


def classify_news_types_multi(title: str, summary: str, source: str = "") -> list:
    """Classify an article into ALL matching news types (multi-label).

    Returns list of matching type strings for multi-label supervised learning.
    """
    text = f"{title or ''} {summary or ''}"
    source_lower = (source or "").lower()
    types = []

    if "truth social" in source_lower or "trump (x)" in source_lower:
        types.append("Trump Post")

    for label, pattern in _TYPE_PATTERNS:
        if label == "Trump Post":
            continue
        if pattern.search(text):
            types.append(label)

    return types if types else ["General"]


def _is_relevant(text: str) -> bool:
    """Check if text is financial or political."""
    if not text or not isinstance(text, str):
        return False
    combined = f"{text} "
    return bool(FINANCIAL_KEYWORDS.search(combined) or POLITICAL_KEYWORDS.search(combined))


def _source_priority(source: str) -> int:
    """Get priority score for source (0 = not preferred)."""
    if not source:
        return 0
    for key, score in PREFERRED_SOURCES.items():
        if key.lower() in str(source).lower():
            return score
    return 1  # Other sources get low priority but not excluded


def _content_boost(title: str, summary: str) -> int:
    """Extra boost for Jim Cramer or Trump content (0, 1, or 2)."""
    combined = f"{title or ''} {summary or ''}"
    boost = 0
    if CRAMER_KEYWORDS.search(combined):
        boost += 2
    if TRUMP_KEYWORDS.search(combined):
        boost += 1
    return boost


def filter_and_rank_news(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter to financial/political news only, prefer specified sources.
    Returns sorted DataFrame (highest priority first).
    """
    if df.empty:
        return df

    df = df.copy()

    def _relevance(row):
        text = f"{row.get('title', '')} {row.get('summary', '')}"
        return _is_relevant(text)

    df["_relevant"] = df.apply(_relevance, axis=1)
    df = df[df["_relevant"]].drop(columns=["_relevant"], errors="ignore")

    # Truth Social posts: only keep those matching high-impact topic keywords
    truth_mask = df["source"].str.contains("Truth Social", case=False, na=False)
    if truth_mask.any():
        truth_relevant = df[truth_mask].apply(
            lambda r: _is_relevant_truth_social(f"{r.get('title', '')} {r.get('summary', '')}"),
            axis=1,
        )
        df = df[~truth_mask | truth_relevant]

    if df.empty:
        return df

    df["_source_priority"] = df["source"].map(_source_priority)
    df["_content_boost"] = df.apply(
        lambda r: _content_boost(r.get("title", ""), r.get("summary", "")), axis=1
    )
    df["_rank"] = df["_source_priority"] + df["_content_boost"]

    df = df.sort_values("_rank", ascending=False).drop(
        columns=["_source_priority", "_content_boost", "_rank"], errors="ignore"
    )

    # Add news_type classification for supervised learning
    df["news_type"] = df.apply(
        lambda r: classify_news_type(r.get("title", ""), r.get("summary", ""), r.get("source", "")),
        axis=1,
    )

    return df.reset_index(drop=True)
