import requests
from bs4 import BeautifulSoup
from utils.helpers import extract_basic_info
import logging
from .base_scraper import BaseScraper # Import the base class

# Headers defined here or could be in BaseScraper __init__
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
}

# Inherit from BaseScraper
class BasicUrlScraper(BaseScraper):

    # Implement the abstract 'scrape' method
    def scrape(self, url: str, **kwargs) -> dict | None:
        """
        Scrapes a URL using requests and BeautifulSoup for static content.
        Overrides BaseScraper.scrape.
        """
        self._log_start(url) # Use helper log method
        try:
            # Allow overriding timeout via kwargs if needed
            timeout = kwargs.get('timeout', 20)
            response = requests.get(url, headers=HEADERS, timeout=timeout)
            response.raise_for_status()

            content_type = response.headers.get('content-type', '').lower()
            if 'html' not in content_type and 'xml' not in content_type:
                logging.warning(f"Non-HTML content type '{content_type}' for {url}. Skipping parsing.")
                # Return consistent error format potentially
                return {
                    'url': url, 'source': self.__class__.__name__, 'error': f"Non-HTML content type: {content_type}",
                    'title': None, 'meta_description': None, 'h1_headings': [], 'paragraphs': [], 'combined_text': ''
                }

            try:
                soup = BeautifulSoup(response.content, 'lxml')
            except Exception:
                soup = BeautifulSoup(response.content, 'html.parser')

            data = extract_basic_info(soup)
            data['url'] = url
            data['source'] = self.__class__.__name__ # Use class name for source

            self._log_success(url) # Use helper log method
            return data

        except requests.exceptions.Timeout:
            self._log_error(url, "Request timed out") # Use helper log method
            return None
        except requests.exceptions.TooManyRedirects:
            self._log_error(url, "Too many redirects")
            return None
        except requests.exceptions.RequestException as e:
            self._log_error(url, e)
            return None
        except Exception as e:
            self._log_error(url, f"Unexpected error: {e}")
            return None

# --- Optional: Keep standalone function for direct use if needed ---
# --- Or modify main.py to instantiate and call BasicUrlScraper().scrape() ---

def scrape_static_url(url: str) -> dict | None:
     """Wrapper to maintain original function signature if needed elsewhere"""
     scraper = BasicUrlScraper()
     return scraper.scrape(url)