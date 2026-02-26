import re
from typing import List, Dict, Any

from bs4 import BeautifulSoup


def extract_engines_from_preferences(html_content: str) -> List[Dict[str, Any]]:
    """
    Extracts engine information from SearXNG preferences HTML.

    Args:
        html_content (str): HTML content of the preferences page

    Returns:
        list: List of dictionaries containing engine information
    """
    soup = BeautifulSoup(html_content, "html.parser")
    engines = []

    engine_rows = soup.find_all("tr", class_="pref-group")

    for row in engine_rows:
        if row.th and row.th.get("colspan") == "2":
            engine_rows_in_category = row.find_next_siblings("tr")

            for engine_row in engine_rows_in_category:
                if engine_row.find("th", class_="name"):
                    engine_entry = _extract_engine_info(engine_row)
                    if engine_entry:
                        engines.append(engine_entry)

    unique_engines = {}
    for engine in engines:
        if engine["name"] not in unique_engines:
            unique_engines[engine["name"]] = engine

    sorted_engines = sorted(unique_engines.values(), key=lambda x: x["name"].lower())

    return sorted_engines


def _extract_engine_info(engine_row: BeautifulSoup) -> Dict[str, Any]:
    """Extract engine information from a single engine row."""
    name_element = engine_row.find("th", class_="name")
    if not name_element:
        return None

    label_element = name_element.find("label")
    engine_name = (
        label_element.text.strip() if label_element and label_element.text else ""
    )

    if not engine_name:
        return None

    engine_url = _extract_engine_url(engine_row)
    bangs = _extract_bangs(engine_row)
    categories = _extract_categories(engine_row)
    reliability, errors = _extract_reliability_and_errors(engine_row)

    return {
        "name": engine_name,
        "url": engine_url,
        "bangs": bangs,
        "categories": categories,
        "reliability": reliability,
        "errors": errors,
    }


def _extract_engine_url(engine_row: BeautifulSoup) -> str:
    """Extract engine URL from tooltip."""
    tooltip = engine_row.find("div", class_="engine-tooltip")
    if not tooltip:
        return ""

    link = tooltip.find("a")
    return link.get("href", "") if link else ""


def _extract_bangs(engine_row: BeautifulSoup) -> List[str]:
    """Extract bang commands from shortcut column."""
    bangs = []
    shortcut_cell = engine_row.find("td", class_="shortcut")
    if not shortcut_cell:
        return bangs

    bang_spans = shortcut_cell.find_all("span", class_="bang")
    for span in bang_spans:
        bang_text = span.text.strip()
        if re.match(r"^![a-zA-Z0-9_]+$", bang_text):
            bangs.append(bang_text)

    return bangs


def _extract_categories(engine_row: BeautifulSoup) -> List[str]:
    """Extract category bangs from tooltip."""
    categories = []
    tooltip = engine_row.find("div", class_="engine-tooltip")
    if not tooltip:
        return categories

    try:
        tooltip_text = tooltip.get_text()
        categories_match = re.search(
            r"!bang for its categories(.*?)(?=!bang|$)", tooltip_text, re.DOTALL
        )
        if categories_match:
            categories_section = categories_match.group(1)
            category_matches = re.findall(r"(![a-zA-Z0-9_]+)", categories_section)
            categories = list(set(category_matches))
    except (AttributeError, re.error):
        pass

    return categories


def _extract_reliability_and_errors(engine_row: BeautifulSoup) -> tuple:
    """Extract reliability score and error messages."""
    reliability = None
    errors = None

    try:
        cells = engine_row.find_all("td")
        if cells:
            reliability_cell = cells[-1]
            reliability_span = reliability_cell.find("span")
            reliability = reliability_span.text.strip() if reliability_span else None

            errors_div = reliability_cell.find("div", class_="engine-tooltip")
            if errors_div:
                paragraphs = errors_div.find_all("p")
                if len(paragraphs) > 1:
                    errors = paragraphs[1].text.strip()
    except (AttributeError, IndexError):
        pass

    return reliability, errors
