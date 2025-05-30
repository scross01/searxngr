import json
import requests
import sys
from rich import print
import textwrap
import os

# Set the SearXNG instance URL
# TODO get server settings from a .config file of env variable
SEARXNG_URL = "UPDATE ME WITH YOUR SEARXNG URL"
# TODO set result count from command line
RESULT_COUNT = 10


# print search results to the terminal 
def print_results(results, count):
    print()
    for i, result in enumerate(results[0:count], start=1):
        title = result.get("title", "No title")
        # truncate the title to 70 characters if it's too long
        title = textwrap.shorten(title, width=70, placeholder="...")
        url = result.get("url", "No URL")
        # extract just the domain name from the URL
        domain = url.split("//")[1].split("/")[0]
        content = result.get("content", "No content")
        # wrap the content to the terminal width with indentation
        content = textwrap.wrap(content, width=os.get_terminal_size().columns - 5)

        print(f" [cyan]{i:>2}.[/cyan] [bold green]{title}[/bold green] [yellow]\\[{domain}][/yellow]")
        # print(f"URL: [link={url}]{url}[/link]")
        for line in content:
            print(f"     {line}")
        print()


def searxng_search(query, searxng_url, count):
    # searxng does not have a limit option, we will always a fixed number of
    # results per page depending on the searxng instance e.g. 20
    # TODO if the count > page max we need to get multiple pages
    url = f"{searxng_url}/?q={query}&format=json"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        if data and "results" in data:
            print_results(data["results"], count)
        else:
            print("No results found.")

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
    except json.JSONDecodeError:
        print("Error: Could not decode JSON response.")


def main():
    if len(sys.argv) > 1:
        search_query = sys.argv[1:]
        searxng_search(search_query, SEARXNG_URL, RESULT_COUNT)
    else:
        print("Usage: python main.py <search_query>")


if __name__ == "__main__":
    main()
