"""
LLM Brain — supports two providers:
  1. OpenAI (gpt-4o-mini)  — used when OPENAI_API_KEY is set in .env
  2. Ollama (llama3.2:3b)  — used automatically when no OpenAI key is set (FREE, offline)

Nothing else in the project needs to change — workflow.py calls classify() either way.
"""
import json
import os
import time
import requests

OPENAI_URL  = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4o-mini"

OLLAMA_URL  = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"

SYSTEM_PROMPT = """You are NOVA, a friendly and capable Windows desktop voice assistant.
When the user wants a system action, call the matching function.
For greetings, questions, or general conversation reply naturally in 1-3 sentences.
Be warm, helpful, and concise. Never make up information."""

# ── Tool definitions (same for both providers) ────────────────────────────────
TOOLS = [
    # Apps
    {"type":"function","function":{"name":"open_notepad","description":"Open Windows Notepad","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"open_calculator","description":"Open Windows Calculator","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"open_file_explorer","description":"Open Windows File Explorer","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"open_browser","description":"Open the default web browser","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"open_application","description":"Open any general Windows application (e.g. Microsoft Word, Excel, Chrome, Spotify) and optionally type text into it. CRITICAL: Use this if the user asks to open an app and write something IN IT, or if they ask to write something 'in Word', 'in Notepad', etc.","parameters":{"type":"object","properties":{"name":{"type":"string"},"text_to_type":{"type":"string"}},"required":["name"]}}},
    {"type":"function","function":{"name":"write_text_to_window","description":"Type specific text into the currently active window. CRITICAL: Use this if the user asks to 'actually write' or 'type' into an OPENED application like Word or Notepad, or says 'write X in Word' when Word is already open.","parameters":{"type":"object","properties":{"text":{"type":"string"}},"required":["text"]}}},
    # Web/AI search
    {"type":"function","function":{"name":"search_google","description":"Search Google","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type":"function","function":{"name":"search_youtube","description":"Open YouTube search results (does NOT play video automatically)","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type":"function","function":{"name":"play_youtube","description":"Find and PLAY the first YouTube video for a query immediately — use when user says play, watch, listen to, or wants a video to start","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type":"function","function":{"name":"search_chatgpt","description":"Open ChatGPT with a query","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type":"function","function":{"name":"search_gemini","description":"Open Google Gemini","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type":"function","function":{"name":"search_perplexity","description":"Search Perplexity AI","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type":"function","function":{"name":"search_claude","description":"Open Claude AI","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type":"function","function":{"name":"search_copilot","description":"Search Microsoft Copilot","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type":"function","function":{"name":"search_grok","description":"Open Grok AI","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type":"function","function":{"name":"search_phind","description":"Search Phind for coding questions","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    # System stats
    {"type":"function","function":{"name":"get_system_specs","description":"Get COMPLETE system specifications — CPU model name and generation, total RAM size and speed, GPU model, storage drives, OS version, motherboard, BIOS. Use this for ANY question about hardware specs, system info, computer model, processor details, RAM amount etc.","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"show_cpu","description":"Show CURRENT CPU usage percentage (how busy the CPU is RIGHT NOW — not the CPU model)","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"show_ram","description":"Show CURRENT RAM usage percentage (how much memory is used RIGHT NOW — not the total RAM size)","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"show_battery","description":"Show battery level and charging status","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"show_time","description":"Show current time and date","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"take_screenshot","description":"Take a screenshot","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"get_network_info","description":"Show IP address and network usage","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"get_disk_usage","description":"Show disk space for all drives","parameters":{"type":"object","properties":{},"required":[]}}},
    # Files — work on REAL Windows paths (desktop, downloads, documents, pictures, videos, music)
    {"type":"function","function":{"name":"generate_and_save_file","description":"Use AI to generate long-form text and save it silently as a background file on the disk. DO NOT use this if the user asks to open Microsoft Word or another app to write it.","parameters":{"type":"object","properties":{"filename":{"type":"string","description":"filename e.g. essay_on_my_father"},"topic":{"type":"string","description":"full writing prompt e.g. Write a 400-word heartfelt essay about my father"},"location":{"type":"string","description":"desktop downloads documents pictures videos music","default":"desktop"}},"required":["filename","topic"]}}},
    {"type":"function","function":{"name":"create_folder","description":"Create a folder on desktop or any real Windows location","parameters":{"type":"object","properties":{"name":{"type":"string"},"location":{"type":"string","default":"desktop"}},"required":["name"]}}},
    {"type":"function","function":{"name":"create_file","description":"Create an empty text file on desktop or any Windows location","parameters":{"type":"object","properties":{"name":{"type":"string"},"location":{"type":"string","default":"desktop"}},"required":["name"]}}},
    {"type":"function","function":{"name":"read_file","description":"Read a text file from desktop downloads documents etc.","parameters":{"type":"object","properties":{"name":{"type":"string"},"location":{"type":"string","default":"desktop"}},"required":["name"]}}},
    {"type":"function","function":{"name":"list_files","description":"List files in desktop downloads documents pictures videos music or any folder","parameters":{"type":"object","properties":{"location":{"type":"string","default":"desktop"}},"required":[]}}},
    {"type":"function","function":{"name":"delete_file","description":"Delete a file from desktop or any location","parameters":{"type":"object","properties":{"name":{"type":"string"},"location":{"type":"string","default":"desktop"}},"required":["name"]}}},
    {"type":"function","function":{"name":"save_text_to_file","description":"Write specific text to a background file on the disk. DO NOT use this to type text into an application like Word, Notepad, or Excel.","parameters":{"type":"object","properties":{"name":{"type":"string"},"content":{"type":"string"},"location":{"type":"string","default":"desktop"}},"required":["name","content"]}}},
    {"type":"function","function":{"name":"append_to_file","description":"Add text to end of a file","parameters":{"type":"object","properties":{"name":{"type":"string"},"content":{"type":"string"},"location":{"type":"string","default":"desktop"}},"required":["name","content"]}}},
    {"type":"function","function":{"name":"open_with_app","description":"Open any file PDF Word image video audio text with its default Windows application","parameters":{"type":"object","properties":{"name":{"type":"string"},"location":{"type":"string","default":"desktop"}},"required":["name"]}}},
    {"type":"function","function":{"name":"open_folder","description":"Open a folder in Windows File Explorer e.g. open desktop folder open downloads","parameters":{"type":"object","properties":{"location":{"type":"string","default":"desktop"}},"required":[]}}},
    {"type":"function","function":{"name":"move_file","description":"Move a file between real Windows locations desktop downloads documents pictures etc.","parameters":{"type":"object","properties":{"name":{"type":"string"},"source":{"type":"string","default":"desktop"},"destination":{"type":"string"}},"required":["name","destination"]}}},
    {"type":"function","function":{"name":"copy_file","description":"Copy a file to another real Windows location","parameters":{"type":"object","properties":{"name":{"type":"string"},"source":{"type":"string","default":"desktop"},"destination":{"type":"string"}},"required":["name","destination"]}}},
    {"type":"function","function":{"name":"rename_file","description":"Rename a file on desktop or any location","parameters":{"type":"object","properties":{"old_name":{"type":"string"},"new_name":{"type":"string"},"location":{"type":"string","default":"desktop"}},"required":["old_name","new_name"]}}},
    {"type":"function","function":{"name":"search_in_files","description":"Search for a word inside text files on desktop or any location","parameters":{"type":"object","properties":{"keyword":{"type":"string"},"location":{"type":"string","default":"desktop"}},"required":["keyword"]}}},
    # Notes
    {"type":"function","function":{"name":"create_note","description":"Save a note","parameters":{"type":"object","properties":{"content":{"type":"string"}},"required":["content"]}}},
    {"type":"function","function":{"name":"show_notes","description":"Show all notes","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"delete_note","description":"Delete most recent note","parameters":{"type":"object","properties":{},"required":[]}}},
    # Volume
    {"type":"function","function":{"name":"volume_up","description":"Increase volume","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"volume_down","description":"Decrease volume","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"volume_mute","description":"Mute volume","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"volume_unmute","description":"Unmute volume","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"get_volume","description":"Show current volume","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"set_volume","description":"Set volume to a percentage","parameters":{"type":"object","properties":{"level":{"type":"integer"}},"required":["level"]}}},
    # Power
    {"type":"function","function":{"name":"lock_computer","description":"Lock the screen","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"sleep_computer","description":"Sleep the computer","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"shutdown_computer","description":"Shut down the computer","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"restart_computer","description":"Restart the computer","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"cancel_shutdown","description":"Cancel a pending shutdown","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"kill_process","description":"Force close an app","parameters":{"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}}},
    # Clipboard
    {"type":"function","function":{"name":"read_clipboard","description":"Read clipboard text","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"summarize_clipboard","description":"Summarize clipboard text with AI","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"fix_grammar","description":"Fix grammar of clipboard text","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"translate_text","description":"Translate clipboard text","parameters":{"type":"object","properties":{"language":{"type":"string"}},"required":["language"]}}},
    # Info
    {"type":"function","function":{"name":"get_weather","description":"Show current weather","parameters":{"type":"object","properties":{"city":{"type":"string"}},"required":[]}}},
    {"type":"function","function":{"name":"get_wikipedia","description":"Get Wikipedia summary","parameters":{"type":"object","properties":{"topic":{"type":"string"}},"required":["topic"]}}},
    # Timer
    {"type":"function","function":{"name":"set_timer","description":"Start a countdown timer","parameters":{"type":"object","properties":{"duration":{"type":"string"}},"required":["duration"]}}},
    # Startup
    {"type":"function","function":{"name":"enable_startup","description":"Make NOVA start with Windows","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"disable_startup","description":"Stop NOVA from auto-starting","parameters":{"type":"object","properties":{},"required":[]}}},
    # Controls
    {"type":"function","function":{"name":"stop_speaking","description":"Stop NOVA speaking","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"clear_chat","description":"Clear the chat window","parameters":{"type":"object","properties":{},"required":[]}}},
]

# ── Ollama intent prompt (used instead of function calling for local model) ───
OLLAMA_INTENT_PROMPT = """You are NOVA, a Windows desktop assistant. Classify the user message into ONE intent.
For greetings or conversation use intent "chat" and write a short friendly reply.

Intents: open_notepad, open_calculator, open_file_explorer, open_browser, open_application, write_text_to_window,
search_google, search_youtube, play_youtube, search_chatgpt, search_gemini, search_perplexity,
search_claude, search_copilot, search_grok, search_phind,
get_system_specs, show_cpu, show_ram, show_battery, show_time, take_screenshot,
get_network_info, get_disk_usage,
create_folder, create_file, read_file, list_files, delete_file,
save_text_to_file, append_to_file, move_file, copy_file, rename_file, search_in_files,
create_note, show_notes, delete_note,
volume_up, volume_down, volume_mute, volume_unmute, get_volume, set_volume,
lock_computer, sleep_computer, shutdown_computer, restart_computer, cancel_shutdown, kill_process,
read_clipboard, summarize_clipboard, fix_grammar, translate_text,
get_weather, get_wikipedia, set_timer,
enable_startup, disable_startup, stop_speaking, clear_chat, chat

Reply ONLY with valid JSON:
{"intent":"<name>","args":"<string or null>","reply":"<only for chat intent>"}

Examples:
"hey open notepad" -> {"intent":"open_notepad","args":null,"reply":null}
"Show CPUs usage" -> {"intent":"show_cpu","args":null,"reply":null}
"open microsoft word and write a letter" -> {"intent":"open_application","args":"{\"name\":\"Microsoft Word\",\"text_to_type\":\"Dear Sir/Madam,\"}","reply":null}
"write hi in word" -> {"intent":"open_application","args":"{\"name\":\"Word\",\"text_to_type\":\"hi\"}","reply":null}
"type hello world" -> {"intent":"write_text_to_window","args":"hello world","reply":null}
"write some text in the word" -> {"intent":"write_text_to_window","args":"some text","reply":null}
"search youtube for python tutorials" -> {"intent":"search_youtube","args":"python tutorials","reply":null}
"play peaceful songs on youtube" -> {"intent":"play_youtube","args":"peaceful songs","reply":null}
"play despacito" -> {"intent":"play_youtube","args":"despacito","reply":null}
"move test.txt from workspace to desktop" -> {"intent":"move_file","args":"{\\"name\\":\\"test.txt\\",\\"source\\":\\"workspace\\",\\"destination\\":\\"desktop\\"}","reply":null}
"write hello world to notes.txt" -> {"intent":"save_text_to_file","args":"{\"name\":\"notes.txt\",\"content\":\"hello world\"}","reply":null}
"rename old.txt to new.txt" -> {"intent":"rename_file","args":"{\\"old_name\\":\\"old.txt\\",\\"new_name\\":\\"new.txt\\"}","reply":null}
"set volume to 60" -> {"intent":"set_volume","args":"60","reply":null}
"translate to Urdu" -> {"intent":"translate_text","args":"Urdu","reply":null}
"set a 5 minute timer" -> {"intent":"set_timer","args":"5 minutes","reply":null}
"hello how are you" -> {"intent":"chat","args":null,"reply":"I'm doing great! How can I help you?"}
"""

# ── Conversation history ──────────────────────────────────────────────────────
_history: list[dict] = []
MAX_HISTORY = 10

MULTI_ARG_TOOLS = {
    "move_file", "copy_file", "rename_file",
    "save_text_to_file", "append_to_file",
    "read_file", "list_files", "delete_file",
    "open_application", "generate_and_save_file"
}


def _get_openai_key() -> str:
    return os.environ.get("OPENAI_API_KEY", "").strip()


def is_ollama_running() -> bool:
    try:
        return requests.get("http://localhost:11434/api/tags", timeout=2).status_code == 200
    except Exception:
        return False


def active_provider() -> str:
    if _get_openai_key():
        return "openai"
    if is_ollama_running():
        return "ollama"
    return "none"


def is_ready() -> bool:
    return active_provider() != "none"


def clear_history():
    global _history
    _history = []


def _extract_args(fn_name: str, fn_args: dict) -> str | None:
    if fn_name in MULTI_ARG_TOOLS:
        return json.dumps(fn_args)
    if fn_name == "set_volume":
        return str(fn_args.get("level", 50))
    return (
        fn_args.get("query") or fn_args.get("name") or fn_args.get("content")
        or fn_args.get("topic") or fn_args.get("city") or fn_args.get("keyword")
        or fn_args.get("language") or fn_args.get("duration") or fn_args.get("text") or None
    )


# ── OpenAI provider ───────────────────────────────────────────────────────────
def _classify_openai(user_text: str, key: str) -> dict:
    _history.append({"role": "user", "content": user_text})
    if len(_history) > MAX_HISTORY:
        del _history[:-MAX_HISTORY]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + _history

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            resp = requests.post(
                OPENAI_URL,
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json"},
                json={"model": OPENAI_MODEL, "messages": messages,
                      "tools": TOOLS, "tool_choice": "auto", "temperature": 0.2},
                timeout=30,
            )
            resp.raise_for_status()

            try:
                data = resp.json()
            except Exception:
                _history.pop()
                return {"intent":"chat","args":None,
                        "reply":"OpenAI returned an unreadable response.","ok":False}

            if not data.get("choices"):
                _history.pop()
                return {"intent":"chat","args":None,
                        "reply":"OpenAI returned an empty response.","ok":False}

            message = data["choices"][0]["message"]

            if message.get("tool_calls"):
                tc      = message["tool_calls"][0]
                fn_name = tc["function"]["name"]
                fn_args = json.loads(tc["function"]["arguments"] or "{}")
                args    = _extract_args(fn_name, fn_args)
                _history.append({"role":"assistant","content":f"[Called:{fn_name}]"})
                return {"intent":fn_name,"args":args,"reply":None,"ok":True}

            reply = message.get("content") or "I'm here — what would you like me to do?"
            _history.append({"role":"assistant","content":reply})
            return {"intent":"chat","args":None,"reply":reply,"ok":True}

        except requests.exceptions.ConnectionError:
            _history.pop()
            return {"intent":"chat","args":None,
                    "reply":"No internet connection.","ok":False}
        except requests.exceptions.Timeout:
            _history.pop()
            return {"intent":"chat","args":None,
                    "reply":"OpenAI took too long. Try again.","ok":False}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else 0
            if code == 429:
                if attempt < max_attempts:
                    time.sleep(2 ** attempt)
                    continue
                _history.pop()
                return {"intent":"chat","args":None,
                        "reply":"OpenAI rate limit — wait 20 seconds and try again. "
                                "Free tier allows only 3 requests per minute.","ok":False}
            elif code == 401:
                _history.pop()
                return {"intent":"chat","args":None,
                        "reply":"Invalid OpenAI API key. Check your .env file.","ok":False}
            else:
                _history.pop()
                return {"intent":"chat","args":None,
                        "reply":f"OpenAI error (HTTP {code}). Try again.","ok":False}
        except Exception as e:
            _history.pop()
            return {"intent":"chat","args":None,
                    "reply":f"Unexpected error: {type(e).__name__}: {e}","ok":False}

    _history.pop()
    return {"intent":"chat","args":None,
            "reply":"Could not reach OpenAI after several retries.","ok":False}


# ── Ollama provider ───────────────────────────────────────────────────────────
def _classify_ollama(user_text: str) -> dict:
    prompt = f'{OLLAMA_INTENT_PROMPT}\nUser: "{user_text}"\n'
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt,
                  "format": "json", "stream": False,
                  "options": {"temperature": 0.2}},
            timeout=30,
        )
        resp.raise_for_status()
        raw  = resp.json().get("response", "").strip()
        data = json.loads(raw)

        intent = data.get("intent", "chat")
        args   = data.get("args")
        reply  = data.get("reply")

        if intent == "chat":
            return {"intent":"chat","args":None,
                    "reply": reply or "I'm here — what would you like me to do?",
                    "ok":True}

        return {"intent":intent,"args":args,"reply":None,"ok":True}

    except requests.exceptions.ConnectionError:
        return {"intent":"chat","args":None,
                "reply":"Cannot reach Ollama. Run 'ollama serve' in a terminal.","ok":False}
    except json.JSONDecodeError:
        return {"intent":"chat","args":None,
                "reply":"Could not understand the local model's response. Try again.","ok":False}
    except Exception as e:
        return {"intent":"chat","args":None,
                "reply":f"Ollama error: {e}","ok":False}


# ── Public entry point ────────────────────────────────────────────────────────
def classify(user_text: str) -> dict:
    """
    Routes to OpenAI if OPENAI_API_KEY is set, otherwise uses local Ollama.
    Called by graph/workflow.py — the rest of the app never needs to know which.
    """
    key = _get_openai_key()
    if key:
        return _classify_openai(user_text, key)
    return _classify_ollama(user_text)
