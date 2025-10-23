import re
from typing import List, Dict, Optional, Any

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

    # Find all engine table rows
    engine_rows = soup.find_all("tr", class_="pref-group")

    for row in engine_rows:
        # Skip category headers
        if row.th and row.th.get("colspan") == "2":
            # category_name = row.th.text.strip()
            # Find all engine rows within this category
            engine_rows_in_category = row.find_next_siblings("tr")

            for engine_row in engine_rows_in_category:
                if engine_row.find("th", class_="name"):
                    # Extract just the engine name
                    name_element = engine_row.find("th", class_="name")
                    label_element = name_element.find("label") if name_element else None
                    engine_name = (
                        label_element.text.strip()
                        if label_element and label_element.text
                        else ""
                    )

                    # Extract URL from the tooltip
                    tooltip = engine_row.find("div", class_="engine-tooltip")
                    engine_url = ""
                    if tooltip:
                        # Find the first link in the tooltip
                        link = tooltip.find("a")
                        if link and link.get("href"):
                            engine_url = link.get("href")

                    # Extract bang commands from the shortcut column
                    shortcut_cell = engine_row.find("td", class_="shortcut")
                    bangs = []
                    if shortcut_cell:
                        bang_spans = shortcut_cell.find_all("span", class_="bang")
                        for span in bang_spans:
                            bang_text = span.text.strip()
                            # Only include bangs that start with ! followed by letters/numbers
                            if re.match(r"^![a-zA-Z0-9_]+$", bang_text):
                                bangs.append(bang_text)

                    # Get bang commands from the tooltip
                    # bangs = []
                    # if tooltip:
                    #     tooltip_text = tooltip.get_text()
                    #     # Find the categories section
                    #     bangs_match = re.search(
                    #         r"!bang for this engine(.*?)(?=!bang|$)", tooltip_text
                    #     )
                    #     if bangs_match:
                    #         bangs_section = bangs_match.group(1)
                    #         # Extract engine bangs from this section
                    #         bangs_matches = re.findall(
                    #             r"(![a-zA-Z0-9_]+)", bangs_section
                    #         )
                    #         bangs = list(set(bangs_matches))  # Remove duplicates

                    # Get categories from the tooltip
                    categories = []
                    if tooltip:
                        tooltip_text = tooltip.get_text()
                        # Find the categories section
                        categories_match = re.search(
                            r"!bang for its categories(.*?)(?=!bang|$)", tooltip_text
                        )
                        if categories_match:
                            categories_section = categories_match.group(1)
                            # Extract category bangs from this section
                            category_matches = re.findall(
                                r"(![a-zA-Z0-9_]+)", categories_section
                            )
                            categories = list(
                                set(category_matches)
                            )  # Remove duplicates

                    # Extract reliability from the last table cell
                    reliability = None
                    reliability_cell = engine_row.find_all("td")[-1]
                    if reliability_cell:
                        reliability_span = reliability_cell.find("span")
                        reliability = (
                            reliability_span.text.strip() if reliability_span else None
                        )

                    # Extract errors from the tooltip
                    errors = None
                    if reliability_cell:
                        errors_div = reliability_cell.find("div", class_="engine-tooltip")
                        if errors_div:
                            errors = errors_div.find_all("p")[1].text.strip()

                    # Create engine entry
                    engine_entry = {
                        "name": engine_name,
                        "url": engine_url,
                        "bangs": bangs,
                        "categories": categories,
                        "reliability": reliability,
                        "errors": errors,
                    }

                    engines.append(engine_entry)

    # Remove duplicates by engine name
    unique_engines = {}
    for engine in engines:
        if engine["name"] not in unique_engines:
            unique_engines[engine["name"]] = engine

    # Sort engines by name
    sorted_engines = sorted(unique_engines.values(), key=lambda x: x["name"].lower())

    return sorted_engines


# Example usage:
if __name__ == "__main__":
    # Read the preferences.html file
    with open("preferences.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    # Extract engines
    engines = extract_engines_from_preferences(html_content)

    # Print the result
    import json

    print(json.dumps(engines, indent=2))
