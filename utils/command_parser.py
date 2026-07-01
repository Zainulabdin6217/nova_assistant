import re

INTENTS = [
    ("open_notepad",       [r"open notepad"]),
    ("open_calculator",    [r"open calculator"]),
    ("open_file_explorer", [r"open file explorer", r"open explorer"]),
    ("open_browser",       [r"open browser"]),
    ("search_youtube",     [r"search youtube for (.+)", r"youtube (.+)"]),
    ("search_google",      [r"search google for (.+)", r"google (.+)"]),
    ("show_cpu",           [r"show cpu", r"cpu usage"]),
    ("show_ram",           [r"show ram", r"ram usage", r"memory usage"]),
    ("show_battery",       [r"show battery", r"battery"]),
    ("show_time",          [r"what time", r"show time", r"current time"]),
    ("take_screenshot",    [r"take screenshot", r"screenshot"]),
    ("create_folder",      [r"create folder (.+)"]),
    ("create_note",        [r"create note saying (.+)", r"add note (.+)"]),
    ("show_notes",         [r"show my notes", r"show notes"]),
    ("delete_note",        [r"delete note"]),
    ("delete_file",        [r"delete file (.+)"]),
    ("stop_speaking",      [r"stop speaking", r"stop talking", r"be quiet"]),
    ("clear_chat",         [r"clear chat"]),
]

RISKY_INTENTS = {
    "delete_file", "delete_note",
    "shutdown_computer", "restart_computer", "kill_process",
}


def parse_command(text: str) -> dict:
    cleaned = text.strip().lower()
    cleaned = re.sub(r"[.!?]+$", "", cleaned)
    for intent, patterns in INTENTS:
        for pattern in patterns:
            match = re.search(pattern, cleaned)
            if match:
                args = match.group(1).strip() if match.groups() else None
                return {"intent": intent, "args": args, "raw": text}
    return {"intent": "unknown", "args": None, "raw": text}


def needs_confirmation(intent: str) -> bool:
    return intent in RISKY_INTENTS
