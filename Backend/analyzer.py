import re
from collections import defaultdict, Counter

# Extended keyword mapping
SWOT_KEYWORDS = {
    "Strengths": [
        "innovative", "trusted", "global presence", "scalable", "award-winning",
        "customer satisfaction", "high performance", "market leader", "strong brand", "robust"
    ],
    "Weaknesses": [
        "slow", "expensive", "limited", "complex", "downtime",
        "customer complaints", "outdated", "lagging", "inefficient", "small team"
    ],
    "Opportunities": [
        "AI", "automation", "digital transformation", "cloud adoption", "expansion",
        "emerging market", "green energy", "sustainability", "acquisition", "growth"
    ],
    "Threats": [
        "competition", "cybersecurity", "recession", "regulations", "economic slowdown",
        "supply chain", "data breach", "geopolitical", "market volatility", "inflation"
    ]
}


def extract_sentences(text: str) -> list:
    """Splits text into sentences and cleans them."""
    raw = re.split(r"[.\n]+", text)
    sentences = [s.strip() for s in raw if len(s.strip()) > 25]
    return sentences


def generate_swot(text: str, top_n: int = 5) -> dict:
    """Generates SWOT analysis from raw visible text."""
    swot_result = {
        "Strengths": [],
        "Weaknesses": [],
        "Opportunities": [],
        "Threats": []
    }

    sentences = extract_sentences(text.lower())
    categorized = defaultdict(list)

    for sentence in sentences:
        for category, keywords in SWOT_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in sentence:
                    categorized[category].append(sentence)
                    break  # Avoid double tagging

    # Count frequency and trim results
    for category in swot_result:
        top_sentences = Counter(categorized[category]).most_common(top_n)
        swot_result[category] = [sent.capitalize() for sent, _ in top_sentences]

    return swot_result
