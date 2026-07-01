import os
import requests

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o-mini"


def _key():
    return os.environ.get("OPENAI_API_KEY", "").strip()


def _paste() -> str:
    try:
        import pyperclip
        return (pyperclip.paste() or "").strip()
    except Exception:
        import subprocess
        r = subprocess.run(["powershell", "-command", "Get-Clipboard"],
                           capture_output=True, text=True)
        return r.stdout.strip()


def _copy(text: str):
    try:
        import pyperclip
        pyperclip.copy(text)
    except Exception:
        pass


def _openai(system_msg: str, user_text: str) -> str:
    key = _key()
    if not key:
        return "OpenAI key not set."
    resp = requests.post(
        OPENAI_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user",   "content": user_text},
            ],
            "temperature": 0.3,
        },
        timeout=25,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def read_clipboard() -> str:
    text = _paste()
    if not text:
        return "Your clipboard is empty."
    preview = text[:300]
    return f"Clipboard: {preview}{'...' if len(text) > 300 else ''}"


def summarize_clipboard() -> str:
    text = _paste()
    if not text:
        return "Clipboard is empty — copy some text first."
    return _openai(
        "Summarize the following text in 2-3 concise sentences.",
        text[:6000],
    )


def fix_grammar() -> str:
    text = _paste()
    if not text:
        return "Clipboard is empty — copy some text first."
    result = _openai(
        "Fix grammar, spelling, and punctuation. Return only the corrected text.",
        text,
    )
    _copy(result)
    return f"Grammar fixed and copied to clipboard: {result[:120]}..."


def translate_text(language: str) -> str:
    text = _paste()
    if not text:
        return "Clipboard is empty — copy some text first."
    result = _openai(
        f"Translate the following text to {language}. Return only the translation.",
        text,
    )
    _copy(result)
    return f"Translated to {language} and copied: {result[:120]}..."
