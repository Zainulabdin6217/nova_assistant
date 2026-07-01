import json
import os
import requests

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
MODEL      = "gpt-4o-mini"

SYSTEM_PROMPT = """You are NOVA, a friendly and capable Windows desktop voice assistant.
When the user wants a system action, call the appropriate function.
For greetings, casual chat, or general questions, reply naturally (1-3 sentences).
Be warm, helpful, and concise. Never make up information."""

# ── Tool definitions ──────────────────────────────────────────────────────────
TOOLS = [
    # Apps
    {"type":"function","function":{"name":"open_notepad","description":"Open Windows Notepad","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"open_calculator","description":"Open Windows Calculator","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"open_file_explorer","description":"Open Windows File Explorer","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"open_browser","description":"Open the default web browser","parameters":{"type":"object","properties":{},"required":[]}}},

    # Web search
    {"type":"function","function":{"name":"search_google","description":"Search Google","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type":"function","function":{"name":"search_youtube","description":"Search YouTube for videos","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},

    # AI platform search
    {"type":"function","function":{"name":"search_chatgpt","description":"Open ChatGPT with a query (copies query to clipboard)","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type":"function","function":{"name":"search_gemini","description":"Open Google Gemini with a query","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type":"function","function":{"name":"search_perplexity","description":"Search Perplexity AI — great for factual/research questions","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type":"function","function":{"name":"search_claude","description":"Open Claude AI with a query","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type":"function","function":{"name":"search_copilot","description":"Search Microsoft Copilot","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type":"function","function":{"name":"search_grok","description":"Open Grok AI by xAI with a query","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type":"function","function":{"name":"search_phind","description":"Search Phind — great for coding questions","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},

    # System stats
    {"type":"function","function":{"name":"show_cpu","description":"Show CPU usage","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"show_ram","description":"Show RAM usage","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"show_battery","description":"Show battery level","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"show_time","description":"Show current time and date","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"take_screenshot","description":"Take a screenshot","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"get_network_info","description":"Show IP address and network usage","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"get_disk_usage","description":"Show disk space for all drives","parameters":{"type":"object","properties":{},"required":[]}}},

    # Basic file ops
    {"type":"function","function":{"name":"create_folder","description":"Create a folder in workspace","parameters":{"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}}},
    {"type":"function","function":{"name":"create_file","description":"Create a new empty text file","parameters":{"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}}},
    {"type":"function","function":{"name":"read_file","description":"Read a text file","parameters":{"type":"object","properties":{"name":{"type":"string"},"location":{"type":"string","description":"workspace, desktop, downloads, or documents","default":"workspace"}},"required":["name"]}}},
    {"type":"function","function":{"name":"list_files","description":"List files in a folder","parameters":{"type":"object","properties":{"location":{"type":"string","description":"workspace, desktop, downloads, or documents","default":"workspace"}},"required":[]}}},
    {"type":"function","function":{"name":"delete_file","description":"Delete a file (asks for confirmation)","parameters":{"type":"object","properties":{"name":{"type":"string"},"location":{"type":"string","default":"workspace"}},"required":["name"]}}},

    # Advanced file ops
    {"type":"function","function":{"name":"write_to_file","description":"Write specific content to a file, creating it if needed","parameters":{"type":"object","properties":{"name":{"type":"string","description":"filename"},"content":{"type":"string","description":"text to write"}},"required":["name","content"]}}},
    {"type":"function","function":{"name":"append_to_file","description":"Append text to the end of an existing file","parameters":{"type":"object","properties":{"name":{"type":"string"},"content":{"type":"string"}},"required":["name","content"]}}},
    {"type":"function","function":{"name":"move_file","description":"Move a file from one location to another. Locations: workspace, desktop, downloads, documents","parameters":{"type":"object","properties":{"name":{"type":"string","description":"filename to move"},"source":{"type":"string","description":"source location","default":"workspace"},"destination":{"type":"string","description":"destination location"}},"required":["name","destination"]}}},
    {"type":"function","function":{"name":"copy_file","description":"Copy a file from one location to another","parameters":{"type":"object","properties":{"name":{"type":"string"},"source":{"type":"string","default":"workspace"},"destination":{"type":"string"}},"required":["name","destination"]}}},
    {"type":"function","function":{"name":"rename_file","description":"Rename a file in the workspace","parameters":{"type":"object","properties":{"old_name":{"type":"string"},"new_name":{"type":"string"}},"required":["old_name","new_name"]}}},
    {"type":"function","function":{"name":"search_in_files","description":"Search for a word or phrase inside workspace text files","parameters":{"type":"object","properties":{"keyword":{"type":"string"}},"required":["keyword"]}}},

    # Notes
    {"type":"function","function":{"name":"create_note","description":"Save a note or reminder","parameters":{"type":"object","properties":{"content":{"type":"string"}},"required":["content"]}}},
    {"type":"function","function":{"name":"show_notes","description":"Show all saved notes","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"delete_note","description":"Delete most recent note (asks confirmation)","parameters":{"type":"object","properties":{},"required":[]}}},

    # Volume
    {"type":"function","function":{"name":"volume_up","description":"Increase volume by 10%","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"volume_down","description":"Decrease volume by 10%","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"volume_mute","description":"Mute system volume","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"volume_unmute","description":"Unmute system volume","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"get_volume","description":"Show current volume level","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"set_volume","description":"Set volume to a specific percentage","parameters":{"type":"object","properties":{"level":{"type":"integer","description":"0 to 100"}},"required":["level"]}}},

    # Power
    {"type":"function","function":{"name":"lock_computer","description":"Lock the Windows screen","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"sleep_computer","description":"Put the computer to sleep","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"shutdown_computer","description":"Shut down the computer (asks confirmation)","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"restart_computer","description":"Restart the computer (asks confirmation)","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"cancel_shutdown","description":"Cancel a pending shutdown or restart","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"kill_process","description":"Force close an app by name (asks confirmation)","parameters":{"type":"object","properties":{"name":{"type":"string","description":"process name e.g. chrome, notepad"}},"required":["name"]}}},

    # Clipboard & AI processing
    {"type":"function","function":{"name":"read_clipboard","description":"Read what is currently in the clipboard","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"summarize_clipboard","description":"Summarize the text in the clipboard using AI","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"fix_grammar","description":"Fix grammar and spelling of clipboard text","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"translate_text","description":"Translate clipboard text to another language","parameters":{"type":"object","properties":{"language":{"type":"string","description":"e.g. Urdu, French, Arabic, Spanish"}},"required":["language"]}}},

    # Information
    {"type":"function","function":{"name":"get_weather","description":"Show current weather for a city","parameters":{"type":"object","properties":{"city":{"type":"string","description":"city name, default Lahore"}},"required":[]}}},
    {"type":"function","function":{"name":"get_wikipedia","description":"Get a Wikipedia summary about any topic","parameters":{"type":"object","properties":{"topic":{"type":"string"}},"required":["topic"]}}},

    # Timer
    {"type":"function","function":{"name":"set_timer","description":"Start a countdown timer","parameters":{"type":"object","properties":{"duration":{"type":"string","description":"e.g. '5 minutes', '30 seconds', '1 hour 30 minutes'"}},"required":["duration"]}}},

    # Controls
    {"type":"function","function":{"name":"stop_speaking","description":"Stop NOVA from speaking","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"clear_chat","description":"Clear the conversation window","parameters":{"type":"object","properties":{},"required":[]}}},
]

# ── Conversation history ──────────────────────────────────────────────────────
_history: list[dict] = []
MAX_HISTORY = 10

# Multi-arg tools — packed as JSON in the args string
MULTI_ARG_TOOLS = {
    "move_file", "copy_file", "rename_file", "write_to_file",
    "append_to_file", "read_file", "list_files", "delete_file",
}


def _get_key() -> str:
    return os.environ.get("OPENAI_API_KEY", "").strip()


def is_ready() -> bool:
    return bool(_get_key())


def clear_history():
    global _history
    _history = []


def _extract_args(fn_name: str, fn_args: dict) -> str | None:
    if fn_name in MULTI_ARG_TOOLS:
        return json.dumps(fn_args)
    if fn_name == "set_volume":
        return str(fn_args.get("level", 50))
    return (
        fn_args.get("query")
        or fn_args.get("name")
        or fn_args.get("content")
        or fn_args.get("topic")
        or fn_args.get("city")
        or fn_args.get("keyword")
        or fn_args.get("language")
        or fn_args.get("duration")
        or None
    )


def classify(user_text: str) -> dict:
    key = _get_key()
    if not key:
        return {
            "intent": "chat", "args": None,
            "reply": "Please add OPENAI_API_KEY to your .env file and restart NOVA.",
            "ok": False,
        }

    _history.append({"role": "user", "content": user_text})
    if len(_history) > MAX_HISTORY:
        del _history[:-MAX_HISTORY]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + _history

    try:
        resp = requests.post(
            OPENAI_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": messages, "tools": TOOLS,
                  "tool_choice": "auto", "temperature": 0.2},
            timeout=25,
        )
        resp.raise_for_status()
        message = resp.json()["choices"][0]["message"]

        if message.get("tool_calls"):
            tc      = message["tool_calls"][0]
            fn_name = tc["function"]["name"]
            fn_args = json.loads(tc["function"]["arguments"] or "{}")
            args    = _extract_args(fn_name, fn_args)
            _history.append({"role": "assistant", "content": f"[Called: {fn_name}]"})
            return {"intent": fn_name, "args": args, "reply": None, "ok": True}

        reply = message.get("content") or "I'm here — what would you like me to do?"
        _history.append({"role": "assistant", "content": reply})
        return {"intent": "chat", "args": None, "reply": reply, "ok": True}

    except requests.exceptions.ConnectionError:
        _history.pop()
        return {"intent": "chat", "args": None,
                "reply": "No internet connection — check your network.", "ok": False}

    except requests.exceptions.HTTPError as e:
        _history.pop()
        code = e.response.status_code if e.response is not None else 0
        if code == 401:
            msg = "Invalid OpenAI API key. Check your .env file."
        elif code == 429:
            msg = "OpenAI rate limit. Wait a moment and try again."
        else:
            msg = f"OpenAI error (HTTP {code}). Try again."
        return {"intent": "chat", "args": None, "reply": msg, "ok": False}

    except Exception:
        _history.pop()
        return {"intent": "chat", "args": None,
                "reply": "Something went wrong — could you try again?", "ok": False}
