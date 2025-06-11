# backend/analyzer.py
def generate_swot(text):
    """
    Simple mock SWOT generator using keyword heuristics.
    Replace with LLM integration if needed.
    """
    return {
        "Strengths": ["Strong online presence", "Clear product messaging"],
        "Weaknesses": ["Limited technical documentation"],
        "Opportunities": ["Expand to international markets", "Add AI-based features"],
        "Threats": ["High competition", "Regulatory uncertainty"]
    }

def find_leaders(soup):
    """
    Searches for common leadership role indicators in text.
    """
    candidates = set()
    keywords = ["CEO", "Founder", "Co-Founder", "CTO", "Director"]
    for tag in soup.find_all(text=True):
        line = tag.strip()
        if any(keyword in line for keyword in keywords):
            candidates.add(line)
    return list(candidates)

def detect_tech_stack(html):
    """
    Detect technologies used based on script/link/content hints.
    """
    stack = []
    if 'gtag' in html or 'GoogleAnalyticsObject' in html:
        stack.append("Google Analytics")
    if 'ReactDOM' in html or 'react' in html.lower():
        stack.append("React")
    if 'wp-content' in html:
        stack.append("WordPress")
    if 'shopify' in html.lower():
        stack.append("Shopify")
    if 'bootstrap' in html.lower():
        stack.append("Bootstrap")
    if 'cloudflare' in html.lower():
        stack.append("Cloudflare")
    return stack
