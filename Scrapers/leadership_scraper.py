# scrapers/leadership_scraper.py
import logging
import re
from bs4 import BeautifulSoup, Tag
from typing import List, Dict, Optional, TypedDict

from utils import helpers # For clean_text

# Define a type hint for the output structure
class LeadershipInfo(TypedDict):
    name: Optional[str]
    title: Optional[str]
    bio_snippet: Optional[str]
    source_url: str # URL where the info was found

def extract_leadership_info(html_content: str, url: str) -> List[LeadershipInfo]:
    """
    Attempts to extract leadership/team member information from HTML content.
    This uses heuristics and may not work perfectly on all site structures.

    Args:
        html_content: The full HTML content of the page as a string.
        url: The URL of the page being parsed (for context).

    Returns:
        A list of dictionaries, each representing a potential person found.
    """
    results: List[LeadershipInfo] = []
    if not html_content:
        return results

    logging.info(f"Attempting to extract leadership info from: {url}")

    try:
        soup = BeautifulSoup(html_content, 'lxml')
    except Exception as e:
        logging.error(f"Failed to parse HTML for leadership extraction on {url}: {e}")
        return results

    # --- Heuristic Approaches ---
    # Strategy 1: Look for common container patterns
    # Common class names for team member blocks (add more as observed)
    container_classes = ['team-member', 'leadership-profile', 'person-card', 'bio-item', 'member-info']
    potential_containers: List[Tag] = []
    for class_name in container_classes:
        # Use CSS selector to find elements with these classes
        potential_containers.extend(soup.select(f'div.{class_name}, section.{class_name}, li.{class_name}'))

    logging.debug(f"Found {len(potential_containers)} potential leadership containers using class names.")

    processed_names = set() # Avoid adding the exact same name/title combo multiple times from one page

    if potential_containers:
        for container in potential_containers:
            name: Optional[str] = None
            title: Optional[str] = None
            bio: Optional[str] = None

            # Try finding name (often in h2, h3, h4, strong, or specific class)
            name_tag = container.find(['h2', 'h3', 'h4', 'strong'], class_=lambda x: x != 'title' if x else True) # Avoid title class for name
            if not name_tag: name_tag = container.select_one('.name, .member-name, .profile-name')
            if name_tag: name = helpers.clean_text(name_tag.get_text())

            # Try finding title (often p, div, span with class 'title' or near name)
            title_tag = container.find(['p', 'div', 'span'], class_=re.compile(r'title|position|role', re.I))
            # Fallback: look for a <p> or <span> directly after/inside the name tag's parent? More complex.
            if title_tag: title = helpers.clean_text(title_tag.get_text())

            # Try finding bio (often in a <p> within the container, but not the title)
            bio_paragraphs = container.find_all('p')
            if bio_paragraphs:
                 potential_bios = []
                 for p in bio_paragraphs:
                     p_text = helpers.clean_text(p.get_text())
                     # Avoid using the title paragraph as the bio if they are distinct
                     if title and p_text == title:
                          continue
                     # Avoid very short paragraphs
                     if len(p_text) > 30:
                          potential_bios.append(p_text)
                 if potential_bios:
                      bio = " ".join(potential_bios[:2]) # Join first few relevant paragraphs

            # Basic validation and deduplication
            if name and title and (name, title) not in processed_names:
                logging.debug(f"  Extracted Leader: Name='{name}', Title='{title}'")
                results.append({
                    'name': name,
                    'title': title,
                    'bio_snippet': bio,
                    'source_url': url
                })
                processed_names.add((name, title))
            elif name and not title and name not in processed_names: # Add even if title missing sometimes? Less reliable
                 logging.debug(f"  Extracted Leader (No Title Found): Name='{name}'")
                 results.append({
                    'name': name,
                    'title': None,
                    'bio_snippet': bio,
                    'source_url': url
                 })
                 processed_names.add(name) # Add name only to avoid duplicates if found later with title

    # Strategy 2: Look for specific headings like "Leadership Team" and parse siblings/children (More complex, potentially brittle)
    # Example: Find <h2>Leadership</h2> then look at subsequent <div> elements. Skipped for simplicity here.

    logging.info(f"Extracted {len(results)} potential leadership entries from {url}.")
    return results