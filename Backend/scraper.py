from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from analyzer import generate_swot
from bs4 import BeautifulSoup
import time
import re


def init_driver():
    options = Options()
    options.headless = True
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(25)
        return driver
    except Exception as e:
        print("[ERROR] Failed to initialize driver:", e)
        return None


def scrape_company_data(url: str) -> dict:
    driver = init_driver()
    if not driver:
        return {"error": "Selenium driver could not be initialized."}

    try:
        visited_urls = set()
        base_url = url.rstrip("/")
        all_text = ""
        all_html = ""

        # Crawl homepage
        driver.get(url)
        time.sleep(3)
        visited_urls.add(url)
        all_html += driver.page_source
        all_text += driver.find_element(By.TAG_NAME, "body").text + "\n"

        # Visit known useful subpages
        fallback_paths = ["/about", "/team", "/leadership", "/management", "/contact"]
        for path in fallback_paths:
            full_url = base_url + path
            if full_url in visited_urls:
                continue
            try:
                driver.get(full_url)
                time.sleep(2)
                visited_urls.add(full_url)
                all_html += driver.page_source
                all_text += driver.find_element(By.TAG_NAME, "body").text + "\n"
            except Exception:
                continue

        return {
            "url": url,
            "links": extract_internal_links(driver, base_url),
            "contacts": extract_contact_info(all_html),
            "leadership": extract_leadership_info(all_html),
            "tech_stack": detect_tech_stack(all_html),
            "swot": generate_swot(all_text[:6000])  # Increased for richer analysis
        }

    except TimeoutException:
        return {"error": "Timed out while loading the page."}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
    finally:
        driver.quit()


def extract_internal_links(driver, base_url: str) -> list:
    anchors = driver.find_elements(By.TAG_NAME, "a")
    links = {a.get_attribute("href") for a in anchors if a.get_attribute("href") and base_url in a.get_attribute("href")}
    return sorted(links)


def extract_contact_info(html: str) -> list:
    emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", html)
    phones = re.findall(r"\b(?:\+91|0)?[6-9]\d{9}\b", html)
    valid_phones = [p for p in phones if not all(ch == p[0] for ch in p)]
    return sorted(set(emails + valid_phones))


def extract_leadership_info(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    leadership_data = []
    seen_blocks = set()

    keywords = [
        "CEO", "CTO", "CFO", "COO", "Chief Executive", "Chief Technology",
        "Chief Operating", "Managing Director", "Founder", "President",
        "Executive Officer", "Board Member", "Vice President", "IT Director"
    ]

    banned = [
        "cookie", "preference", "background", "retail", "sector",
        "submit", "media", "semiconductor"
    ]

    for tag in soup.find_all(["div", "p", "span", "li", "h2", "h3", "h4"]):
        text = tag.get_text(" ", strip=True)

        if not (10 < len(text) < 250):
            continue
        if any(bad in text.lower() for bad in banned):
            continue
        if not any(k.lower() in text.lower() for k in keywords):
            continue
        if text in seen_blocks:
            continue

        seen_blocks.add(text)

        # Try to get LinkedIn link
        linkedin = None
        link_tag = tag.find("a", href=True)
        if link_tag and "linkedin.com" in link_tag["href"]:
            linkedin = link_tag["href"]
        else:
            parent = tag.find_parent()
            if parent:
                link = parent.find("a", href=True)
                if link and "linkedin.com" in link["href"]:
                    linkedin = link["href"]

        leadership_data.append({
            "profile": text,
            "linkedin": linkedin
        })

    return leadership_data[:10]


def detect_tech_stack(html: str) -> list:
    stack = []
    if "wp-content" in html:
        stack.append("WordPress")
    if "googletagmanager" in html or "gtag(" in html:
        stack.append("Google Analytics")
    if "react" in html or "ReactDOM" in html:
        stack.append("React")
    if "shopify" in html:
        stack.append("Shopify")
    if "cdn.jsdelivr.net/npm/bootstrap" in html:
        stack.append("Bootstrap")
    return stack
