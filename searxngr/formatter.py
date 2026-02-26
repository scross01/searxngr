import os
import textwrap
from typing import List, Dict, Any
from urllib.parse import urlparse
from dateutil.parser import parse
from babel.dates import format_date
from html2text import html2text

from .constants import MAX_CONTENT_WORDS, DEBUG, console


def print_results(
    results: List[Dict[str, Any]], count: int, start_at: int = 0, expand: bool = False
) -> None:
    console.print()
    for i, result in enumerate(
        results[start_at:(start_at + count)], start=start_at + 1
    ):
        title = result.get("title", "No title")
        title = textwrap.shorten(title, width=70, placeholder="...")

        url = result.get("url", "")
        domain = ""
        if url:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc

        engine = result.get("engine", None)
        template = result.get("template", None)
        category = result.get("category", None)

        content = result.get("content", "")
        content_text = html2text(content).strip() if content else ""
        content_words = content_text.split(" ") if content_text else []
        content = None
        if len(content_words) > MAX_CONTENT_WORDS:
            content = " ".join(content_words[:MAX_CONTENT_WORDS]) + " ..."
        else:
            content = " ".join(content_words)
        content = textwrap.wrap(content, width=os.get_terminal_size().columns - 5)

        published_date = None
        if result.get("publishedDate"):
            try:
                date_str = result["publishedDate"].strip()
                if date_str:
                    parsed_date = parse(date_str)
                    published_date = format_date(parsed_date)
            except Exception as e:
                if DEBUG:
                    console.print(f"[dim]Error parsing date: {e}[/dim]")

        console.print(
            f" [cyan]{i:>2}.[/cyan] [bold green]{title}[/bold green] [yellow]\\[{domain}][/yellow]",
        )
        if expand:
            console.print(f"     [link={url}]{url}[/link]")
        if content:
            for line in content:
                console.print(f"     {line}", highlight=False)

        if category == "news" and published_date:
            console.print(
                f"     [cyan dim]{published_date}[/cyan dim]", highlight=False
            )
        if category == "images":
            source = result.get("source")
            resolution = result.get("resolution")
            img_src = result.get("img_src")
            if source or resolution:
                console.print(
                    f"     [cyan dim]{resolution if resolution else ''}[/cyan dim] {source if source else ''}"
                )
            console.print(f"     [link={img_src}]{img_src}[/link]", highlight=False)
        if category == "videos":
            author = result.get("author")
            length = result.get("length")
            if isinstance(length, float):
                length = f"{int(length // 60):02}:{int(length % 60):02}"
            if author or length:
                console.print(
                    f"     [cyan dim]{length if length else ''}[/cyan dim] {author if author else ''}"
                )
        if category == "music" and result.get("publishedDate"):
            author = result.get("author")
            length = result.get("length")
            if isinstance(length, float):
                length = f"{int(length // 60):02}:{int(length % 60):02}"
            if author or length:
                console.print(
                    f"     [cyan dim]{length if length else ''}[/cyan dim] {author if author else ''}"
                )
        if category == "map":
            address = result.get("address")
            if address:
                house_number = address.get("house_number")
                road = address.get("road")
                locality = address.get("locality")
                postcode = address.get("postcode")
                country = address.get("country")
                console.print(
                    f"     {house_number + ' ' if house_number else ''}{road if road else ''}\n",
                    f"    {locality if locality else ''}, {postcode if postcode else ''}\n",
                    f"    {country if country else ''}",
                )
            longitude = result.get("longitude")
            latitude = result.get("latitude")
            console.print(f"     [cyan dim]{latitude}, {longitude}[/cyan dim]")
        if category == "it":
            pass
        if category == "science":
            journal = result.get("journal")
            publisher = result.get("publisher")
            console.print(
                f"     [cyan dim][bold]{published_date + ' ' if published_date else ''}[/bold]"
                + f"{journal + ' ' if journal else ''}"
                + f"{publisher + ' ' if publisher else ''}[/cyan dim]",
                highlight=False,
            )
        if category == "files":
            if template == "torrent.html":
                magnet_link = result.get("magnetlink")
                seed = result.get("seed")
                leech = result.get("leech")
                filesize = result.get("filesize")
                console.print(f"     [dim]{magnet_link}[/dim]", highlight=False)
                console.print(
                    f"     [cyan dim]{filesize}[/cyan dim] ↑{seed} seeders, ↓{leech} leechers"
                )
            elif template == "files.html":
                metadata = result.get("metadata")
                size = result.get("size")
                console.print(f"     [cyan dim]{size} {metadata}[/cyan dim]")
        if category == "social media":
            if published_date:
                console.print(f"     [cyan dim]{published_date}[/cyan dim]")

        engines = result.get("engines", [])
        engines.remove(engine) if engine in engines else None
        console.print(
            f"     [dim]\\[[bold]{engine}[/bold]{(', ' + ', '.join(engines)) if len(engines) > 0 else ''}][/dim]"
        )
        console.print()
