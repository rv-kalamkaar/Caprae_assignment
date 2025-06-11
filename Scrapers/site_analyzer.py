import logging
import time
import random
from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import RatelimitException, DuckDuckGoSearchException
from typing import List, Optional, Dict

from utils import config, helpers
from utils.models import ReviewSnippet, HttpUrl

def search_single_query(ddgs_instance: DDGS, search_query: str, site_key: str, delay: float = config.REVIEW_SEARCH_DELAY_SECONDS) -> List[ReviewSnippet]:
    """Performs a single DuckDuckGo search and returns validated review snippets."""
    snippets: List[ReviewSnippet] = []
    logging.info(f"Querying DDG for {site_key}: '{search_query}'")
    
    # Add jitter to the delay to make the pattern less predictable
    jittered_delay = delay * (1 + random.uniform(-0.2, 0.5))
    time.sleep(jittered_delay)
    
    # Get site-specific max results or use default
    site_config = config.REVIEW_SITES_CONFIG.get(site_key, {})
    max_results = site_config.get('max_results', config.MAX_REVIEW_RESULTS_PER_SITE)

    try:
        # Add a different user-agent for each request
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0"
        ]
        
        # Configure DDGS with a random user agent
        ddgs_instance.headers.update({"User-Agent": random.choice(user_agents)})
        
        results = list(ddgs_instance.text(
            search_query,
            max_results=max_results,
            region='wt-wt'  # Worldwide results
        ))

        if not results:
            logging.info(f"No results found for query: '{search_query}'")
            return []

        for r in results:
            if isinstance(r, dict) and r.get('href') and r.get('title'):
                link_str = r.get('href')
                title_str = r.get('title')
                try:
                    link_url = HttpUrl(link_str)  # Validate URL
                    snippet = ReviewSnippet(
                        title=helpers.clean_text(title_str),
                        link=link_url,
                        source_site=site_key,
                        query_used=search_query
                    )
                    snippets.append(snippet)
                    logging.debug(f"Found: '{snippet.title}' -> {snippet.link_str}")
                except Exception as e:
                    logging.warning(f"Skipping invalid URL: '{link_str}' - {e}")
            else:
                logging.warning(f"Skipping malformed result: {r}")

        logging.info(f"Found {len(snippets)} valid result(s) for query: '{search_query}'")

    except RatelimitException:
        logging.error(f"Rate limit hit for query: '{search_query}'")
        raise  # Re-raise to halt further searches
    except DuckDuckGoSearchException as e:
        logging.error(f"Search error for query '{search_query}': {e}")
    except Exception as e:
        logging.error(f"Unexpected error for query '{search_query}': {e}", exc_info=True)

    return snippets

def search_review_sites(company_name: str, location: Optional[str] = None, delay: float = config.REVIEW_SEARCH_DELAY_SECONDS) -> List[ReviewSnippet]:
    """Searches configured review sites for company reviews, optionally with location."""
    all_snippets_map: Dict[str, ReviewSnippet] = {}
    total_results = 0

    if not company_name:
        logging.warning("Company name is empty; no search performed.")
        return []

    logging.info(f"Starting review search for '{company_name}' (Location: {location or 'N/A'})")

    # Sort sites by priority (lower number = higher priority)
    sorted_sites = sorted(
        config.REVIEW_SITES_CONFIG.items(),
        key=lambda x: x[1].get('priority', 999)
    )
    
    # Add proxy rotation if available
    proxies = getattr(config, 'PROXIES', None)
    
    # Implement exponential backoff for rate limits
    max_retries = 3
    base_backoff = 60  # seconds
    
    try:
        with DDGS(timeout=20) as ddgs:
            for site_key, site_config in sorted_sites:
                # Check if we've reached the total results limit
                if total_results >= getattr(config, 'MAX_TOTAL_REVIEW_RESULTS', float('inf')):
                    logging.info(f"Reached maximum total review results ({total_results}). Stopping search.")
                    break
                    
                domain = site_config.get('domain')
                query_suffix = site_config.get('query_suffix', '')
                
                if not domain:
                    continue

                # Base query without location
                base_query = f'site:{domain} "{company_name}"{query_suffix}'
                
                # Try with exponential backoff for rate limits
                for attempt in range(max_retries):
                    try:
                        # If we have proxies, rotate them
                        if proxies and len(proxies) > 0:
                            current_proxy = random.choice(proxies)
                            ddgs.proxies = {"http": current_proxy, "https": current_proxy}
                        
                        # Use a longer delay on retry attempts
                        current_delay = delay * (2 ** attempt)
                        results = search_single_query(ddgs, base_query, site_key, current_delay)
                        
                        for snippet in results:
                            all_snippets_map[snippet.link_str] = snippet
                            total_results += 1
                        
                        # If successful, break the retry loop
                        break
                        
                    except RatelimitException:
                        if attempt < max_retries - 1:
                            backoff_time = base_backoff * (2 ** attempt)
                            logging.warning(f"Rate limit hit for {site_key}. Backing off for {backoff_time} seconds before retry {attempt+1}/{max_retries}")
                            time.sleep(backoff_time)
                        else:
                            logging.error(f"Rate limit persisted after {max_retries} retries for {site_key}. Skipping.")
                            break
                    except Exception as e:
                        logging.error(f"Error in base query for {site_key}: {e}")
                        break

                # Location-specific query if provided
                if location:
                    location_query = f'site:{domain} "{company_name}" "{location}"{query_suffix}'
                    if location_query != base_query:
                        # Similar retry logic for location-specific query
                        for attempt in range(max_retries):
                            try:
                                # If we have proxies, rotate them
                                if proxies and len(proxies) > 0:
                                    current_proxy = random.choice(proxies)
                                    ddgs.proxies = {"http": current_proxy, "https": current_proxy}
                                
                                current_delay = delay * (2 ** attempt)
                                results = search_single_query(ddgs, location_query, site_key, current_delay)
                                
                                for snippet in results:
                                    if snippet.link_str not in all_snippets_map:
                                        all_snippets_map[snippet.link_str] = snippet
                                        total_results += 1
                                
                                # If successful, break the retry loop
                                break
                                
                            except RatelimitException:
                                if attempt < max_retries - 1:
                                    backoff_time = base_backoff * (2 ** attempt)
                                    logging.warning(f"Rate limit hit for {site_key} location query. Backing off for {backoff_time} seconds before retry {attempt+1}/{max_retries}")
                                    time.sleep(backoff_time)
                                else:
                                    logging.error(f"Rate limit persisted after {max_retries} retries for {site_key} location query. Skipping.")
                                    break
                            except Exception as e:
                                logging.error(f"Error in location query for {site_key}: {e}")
                                break

    except Exception as e:
        logging.error(f"DDGS context error: {e}", exc_info=True)
        return []

    final_snippets = list(all_snippets_map.values())
    logging.info(f"Found {len(final_snippets)} unique snippets.")
    return final_snippets