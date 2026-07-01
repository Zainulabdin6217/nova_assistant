import re
import webbrowser
import requests
from urllib.parse import quote_plus

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def open_browser() -> str:
    webbrowser.open("https://www.google.com")
    return "Opening your browser."


def search_google(query: str) -> str:
    webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")
    return f"Searching Google for {query}."


def search_youtube(query: str) -> str:
    """Open YouTube search results page."""
    webbrowser.open(f"https://www.youtube.com/results?search_query={quote_plus(query)}")
    return f"Opened YouTube search for {query}."


def play_youtube(query: str) -> str:
    """
    Find the first real video result for the query and open it directly —
    so the video starts playing immediately, not just a search page.
    """
    search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"

    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=8)
        resp.raise_for_status()

        # YouTube embeds all video data as JSON in the page HTML.
        # The videoId appears repeatedly — first unique occurrence is the top result.
        ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', resp.text)
        unique_ids = list(dict.fromkeys(ids))  # preserve order, remove duplicates

        if unique_ids:
            video_id  = unique_ids[0]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            webbrowser.open(video_url)
            return f"Playing '{query}' on YouTube."

    except Exception:
        pass

    # Fallback: open search page if scraping fails
    webbrowser.open(search_url)
    return f"Opened YouTube search for '{query}' — select a video to play."
