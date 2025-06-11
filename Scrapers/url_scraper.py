# scrapers/url_scraper.py
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException, TimeoutException
import time
import logging
# Add the missing import here too, just in case urlparse is used directly (though unlikely now)
from urllib.parse import urlparse
from typing import Tuple, Optional

# Import models and config
from utils.models import ScrapedPage, HttpUrl
from utils import config, helpers

class UrlScraper:
    """Handles fetching and parsing of a single URL, with retries and dynamic option."""

    def __init__(self):
        """Initializes the scraper with a requests session."""
        self.session = self._create_requests_session()
        logging.info("UrlScraper initialized with retry-enabled requests session.")

    def _create_requests_session(self) -> requests.Session:
        """Creates a requests Session with robust retry logic."""
        session = requests.Session()
        retries = Retry(
            total=config.MAX_RETRIES,
            backoff_factor=config.RETRY_DELAY_SECONDS,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def _scrape_static(self, url_str: str, headers: dict) -> Tuple[ScrapedPage, Optional[str]]:
        """
        Performs static scraping using requests.
        Returns: Tuple of (ScrapedPage object, Full HTML string on success or None).
        """
        logging.info(f"[Static Scraper] Attempting scrape: {url_str}")
        error_message = None
        status_code = None
        soup = None
        raw_html_content = None
        full_html_text = None # To store decoded HTML string
        page_data = {}
        success = False
        request_start_time = time.monotonic()
        final_url_obj = HttpUrl(url_str) # Default to input URL

        try:
            response = self.session.get(
                url_str,
                headers=headers,
                timeout=config.DEFAULT_TIMEOUT,
                allow_redirects=True
                )
            status_code = response.status_code
            final_url_obj = HttpUrl(response.url) # Capture final URL after redirects
            logging.info(f"[Static Scraper] Received status {status_code} from {final_url_obj} in {time.monotonic() - request_start_time:.2f}s")

            content_type = response.headers.get('content-type', '').lower()
            is_html = 'html' in content_type or 'xml' in content_type

            # Raise status for bad responses *after* getting status and final URL
            response.raise_for_status()

            if not is_html and status_code == 200:
                 logging.warning(f"[Static Scraper] Non-HTML/XML content type '{content_type}' for {final_url_obj}.")
                 error_message = f"Non-HTML/XML content type: {content_type}"
            else:
                 raw_html_content = response.content
                 # Try decoding using detected encoding, fallback to utf-8
                 try:
                      full_html_text = response.text # requests usually handles decoding well
                 except UnicodeDecodeError:
                      logging.warning(f"UnicodeDecodeError for {final_url_obj}, trying utf-8 ignore.")
                      full_html_text = raw_html_content.decode('utf-8', errors='ignore')

                 if full_html_text:
                     try:
                         soup = BeautifulSoup(full_html_text, 'lxml')
                         success = True
                     except Exception as parse_err_lxml:
                         logging.warning(f"lxml parse failed for {final_url_obj}, falling back to html.parser: {parse_err_lxml}")
                         try:
                             soup = BeautifulSoup(full_html_text, 'html.parser')
                             success = True
                         except Exception as parse_err_html:
                             logging.error(f"HTML parsing failed completely for {final_url_obj}: {parse_err_html}", exc_info=True)
                             error_message = f"HTML parsing failed: {parse_err_html}"
                 else:
                      error_message = "Failed to decode HTML content."


        except requests.exceptions.Timeout as e:
            logging.error(f"[Static Scraper] Request timed out for {url_str}: {e}")
            error_message = f"Timeout after {config.DEFAULT_TIMEOUT}s"
        except requests.exceptions.TooManyRedirects as e:
             logging.error(f"[Static Scraper] Too many redirects for {url_str}: {e}")
             error_message = f"Too many redirects"
        except requests.exceptions.RequestException as e:
             logging.error(f"[Static Scraper] Request failed for {url_str}: {e}")
             if hasattr(e, 'response') and e.response is not None:
                  status_code = e.response.status_code
                  error_message = f"RequestException (Status: {status_code}): {e}"
             else:
                  error_message = f"RequestException: {e}"
        except Exception as e:
            logging.error(f"[Static Scraper] Unexpected error scraping {url_str}: {e}", exc_info=True)
            error_message = f"Unexpected error: {e}"

        # --- Prepare ScrapedPage object ---
        if soup:
            page_data = helpers.extract_page_content(soup, url_str) # Extract content if parsing succeeded
        # Even if parsing failed, create snippet if we have raw content
        elif full_html_text:
             page_data['raw_html_snippet'] = full_html_text[:helpers.HTML_SNIPPET_LENGTH]
        elif raw_html_content: # Fallback if decoding failed but we have bytes
             page_data['raw_html_snippet'] = raw_html_content.decode('utf-8', errors='ignore')[:helpers.HTML_SNIPPET_LENGTH]

        scraped_page_obj = ScrapedPage(
            url=final_url_obj, # Use final validated URL
            success=success and error_message is None,
            is_dynamic_scrape=False,
            status_code=status_code,
            error_message=error_message,
            **page_data
        )

        # Return the ScrapedPage object and the full HTML text (if successful)
        return scraped_page_obj, full_html_text if success else None


    def _scrape_dynamic(self, url_str: str, headers: dict) -> Tuple[ScrapedPage, Optional[str]]:
        """
        Performs dynamic scraping using Selenium.
        Returns: Tuple of (ScrapedPage object, Full HTML string on success or None).
        """
        logging.info(f"[Dynamic Scraper] Attempting scrape: {url_str}")
        error_message = None
        page_source = None # This will be the full HTML string
        soup = None
        driver = None
        success = False
        page_data = {}
        request_start_time = time.monotonic()
        final_url_obj = HttpUrl(url_str) # Default

        options = ChromeOptions()
        options.add_argument(f"user-agent={headers['User-Agent']}")
        for opt in config.SELENIUM_OPTIONS:
            options.add_argument(opt)

        try:
            logging.debug("Initializing ChromeDriver...")
            service = ChromeService(executable_path=ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(config.DEFAULT_TIMEOUT + 15)

            logging.debug(f"Navigating to {url_str}...")
            driver.get(url_str)
            current_url_str = driver.current_url # Get URL after potential initial redirects
            final_url_obj = HttpUrl(current_url_str) # Validate final URL
            logging.info(f"[Dynamic Scraper] Navigated to {final_url_obj} (final URL)")

            wait_time = config.SELENIUM_DYNAMIC_WAIT_SECONDS
            logging.info(f"[Dynamic Scraper] Waiting {wait_time}s for dynamic content...")
            time.sleep(wait_time)

            logging.debug("Extracting page source...")
            page_source = driver.page_source # Get full HTML source

            if not page_source or len(page_source) < 200:
                logging.warning(f"[Dynamic Scraper] Page source seems empty or minimal for {final_url_obj}.")
                error_message = "Page source empty or minimal after dynamic load"
            else:
                 try:
                    soup = BeautifulSoup(page_source, 'lxml')
                    success = True
                 except Exception as parse_err_lxml:
                    logging.warning(f"lxml parse failed for dynamic content {final_url_obj}, falling back to html.parser: {parse_err_lxml}")
                    try:
                        soup = BeautifulSoup(page_source, 'html.parser')
                        success = True
                    except Exception as parse_err_html:
                        logging.error(f"HTML parsing failed completely for dynamic content {final_url_obj}: {parse_err_html}", exc_info=True)
                        error_message = f"HTML parsing failed: {parse_err_html}"

        except TimeoutException:
            logging.error(f"[Dynamic Scraper] Page load timed out for {url_str}")
            error_message = f"Timeout after {config.DEFAULT_TIMEOUT + 15}s (Selenium)"
        except WebDriverException as e:
            err_str = str(e).lower()
            if "net::err_name_not_resolved" in err_str or "dns probe finished" in err_str:
                 logging.error(f"[Dynamic Scraper] DNS resolution failed for {url_str}: {e}")
                 error_message = "DNS Error: Could not resolve host"
            elif "net::err_connection_refused" in err_str:
                 logging.error(f"[Dynamic Scraper] Connection refused for {url_str}: {e}")
                 error_message = "Connection Refused"
            else:
                 logging.error(f"[Dynamic Scraper] Selenium WebDriver error for {url_str}: {e}")
                 error_message = "WebDriverException: {e}"
        except Exception as e:
            logging.error(f"[Dynamic Scraper] Unexpected error during dynamic scraping {url_str}: {e}", exc_info=True)
            error_message = "Unexpected error: {e}"
        finally:
            if driver:
                try:
                    logging.debug("Closing WebDriver...")
                    driver.quit()
                except Exception as e_quit:
                    logging.error(f"[Dynamic Scraper] Error closing WebDriver: {e_quit}")

        # --- Prepare ScrapedPage object ---
        if soup:
            page_data = helpers.extract_page_content(soup, url_str)
        elif page_source: # Create snippet if parsing failed but source exists
             page_data['raw_html_snippet'] = page_source[:helpers.HTML_SNIPPET_LENGTH]

        scraped_page_obj = ScrapedPage(
            url=final_url_obj, # Use final validated URL
            success=success and error_message is None,
            is_dynamic_scrape=True,
            status_code=None, # Not reliably available from Selenium
            error_message=error_message,
            **page_data
        )

        # Return the ScrapedPage object and the full HTML source (page_source) if successful
        return scraped_page_obj, page_source if success else None

    def fetch_and_parse(self, url, use_dynamic: bool = False) -> Tuple[ScrapedPage, Optional[str]]:
        """
        Fetches and parses a URL, choosing static or dynamic method. Includes a delay.
    
        Args:
            url: The URL string or dictionary to scrape.
            use_dynamic: Whether to use Selenium for dynamic content.
    
        Returns:
            A tuple containing:
            - ScrapedPage object with results/errors.
            - Full HTML source as a string if scrape was successful, otherwise None.
        """
        time.sleep(config.REQUEST_DELAY_SECONDS) # Delay before request
        headers = {'User-Agent': config.get_random_user_agent()}
    
        # Extract URL string if a dictionary was passed
        if isinstance(url, dict) and 'url' in url:
            url_str = str(url['url'])
        else:
            url_str = str(url)
    
        # Basic URL structure check
        try:
            parsed = urlparse(url_str)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL structure")
        except Exception as e:
            logging.error(f"Invalid URL passed to fetch_and_parse: {url_str} - {e}")
            fail_page = ScrapedPage(url=url_str, success=False, is_dynamic_scrape=use_dynamic, 
                                   error_message=f"Invalid URL structure: {e}")
            return fail_page, None
    
        if use_dynamic:
            return self._scrape_dynamic(url_str, headers)
        else:
            return self._scrape_static(url_str, headers)