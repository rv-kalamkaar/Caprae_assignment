# scrapers/tech_analyzer.py
import logging
import builtwith
from typing import Optional
import urllib.parse

from utils.models import TechnologyInfo

# Suppress builtwith's internal logging if too verbose, or configure logging level
# logging.getLogger('builtwith').setLevel(logging.WARNING)

def guess_technologies(url: str) -> TechnologyInfo:
    """
    Uses the 'builtwith' library to guess technologies used by a website.

    Args:
        url: The URL string to analyze.

    Returns:
        A TechnologyInfo object containing results or error information.
    """
    logging.info(f"Attempting technology stack guess for: {url}")
    tech_results: Optional[dict] = None
    error_message: Optional[str] = None

    try:
        # Builtwith requires a scheme (http/https)
        parsed_url = urllib.parse.urlparse(url)
        if not parsed_url.scheme:
            url_with_scheme = 'http://' + url # Default to http if scheme missing
            logging.debug(f"Assuming http scheme for builtwith analysis: {url_with_scheme}")
        else:
            url_with_scheme = url

        # The builtwith.parse() function can sometimes hang or take a long time.
        # Consider running it in a separate thread/process with a timeout
        # for a truly robust implementation, but that adds complexity.
        tech_results = builtwith.parse(url_with_scheme)

        if not tech_results:
            logging.info(f"Builtwith analysis completed but found no specific technologies for {url}")
            # Return empty dict to indicate success but no findings
            tech_results = {}
        else:
            logging.info(f"Builtwith analysis successful for {url}.")
            logging.debug(f"Technologies found: {tech_results}")

    except ImportError:
         logging.error("The 'builtwith' library is not installed. Cannot guess technologies.", exc_info=True)
         error_message = "Builtwith library not installed."
    except Exception as e:
        # Catch potential errors during builtwith parsing (network, parsing errors)
        logging.error(f"Builtwith failed to parse {url}: {e}", exc_info=True)
        error_message = f"Builtwith library error: {e}"
        tech_results = None # Ensure results are None on error

    return TechnologyInfo(
        guessed_technologies=tech_results,
        error_message=error_message
    )