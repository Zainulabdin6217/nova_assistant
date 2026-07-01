import webbrowser
from urllib.parse import quote_plus


def _copy_to_clipboard(text: str) -> bool:
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        return False


def search_chatgpt(query: str) -> str:
    _copy_to_clipboard(query)
    webbrowser.open("https://chat.openai.com/")
    return f"Opened ChatGPT. Your query '{query}' has been copied to clipboard — just paste it."


def search_gemini(query: str) -> str:
    _copy_to_clipboard(query)
    webbrowser.open("https://gemini.google.com/app")
    return f"Opened Google Gemini. Your query has been copied — paste it to search."


def search_perplexity(query: str) -> str:
    url = f"https://www.perplexity.ai/search?q={quote_plus(query)}"
    webbrowser.open(url)
    return f"Searching Perplexity for '{query}'."


def search_claude(query: str) -> str:
    _copy_to_clipboard(query)
    webbrowser.open("https://claude.ai/new")
    return f"Opened Claude.ai. Your query has been copied — paste it to start."


def search_copilot(query: str) -> str:
    url = f"https://copilot.microsoft.com/?q={quote_plus(query)}"
    webbrowser.open(url)
    return f"Searching Microsoft Copilot for '{query}'."


def search_grok(query: str) -> str:
    url = f"https://x.com/i/grok?text={quote_plus(query)}"
    webbrowser.open(url)
    return f"Opening Grok with your query."


def search_phind(query: str) -> str:
    url = f"https://www.phind.com/search?q={quote_plus(query)}"
    webbrowser.open(url)
    return f"Searching Phind for '{query}'."
