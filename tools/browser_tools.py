import webbrowser
from urllib.parse import quote_plus


def open_browser() -> str:
    webbrowser.open("https://www.google.com")
    return "Opening your browser."


def search_google(query: str) -> str:
    url = f"https://www.google.com/search?q={quote_plus(query)}"
    webbrowser.open(url)
    return f"Searching Google for {query}."


def search_youtube(query: str) -> str:
    url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    webbrowser.open(url)
    return f"Searching YouTube for {query}."
