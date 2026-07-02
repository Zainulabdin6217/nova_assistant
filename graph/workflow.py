import json
import re
from langgraph.graph import StateGraph, END

from graph.state import NovaState
from utils.command_parser import needs_confirmation
from utils import llm_brain
from database.database import db

from utils.startup import enable_startup, disable_startup
from tools import (
    application_tools, browser_tools, system_tools,
    file_tools, note_tools, power_tools, info_tools,
    clipboard_tools, ai_tools,
)

CONFIRM_MARKER = "__NEEDS_CONFIRMATION__"
TIMER_MARKER   = "__TIMER__"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_args(args: str | None) -> dict:
    """Parse a JSON-packed args string. Returns {} on failure."""
    if not args:
        return {}
    try:
        return json.loads(args)
    except Exception:
        return {}


def _parse_duration(text: str) -> int:
    """Convert '5 minutes', '30 seconds', '1 hour 10 minutes' → total seconds."""
    text = (text or "").lower()
    total = 0
    for pattern, mult in [(r"(\d+)\s*h", 3600), (r"(\d+)\s*m", 60), (r"(\d+)\s*s", 1)]:
        m = re.search(pattern, text)
        if m:
            total += int(m.group(1)) * mult
    return total or 60  # default 60 s if nothing parsed


# ── Nodes ─────────────────────────────────────────────────────────────────────

def receive_input(state: NovaState) -> dict:
    return {"raw_input": state["raw_input"]}


def classify_intent(state: NovaState) -> dict:
    if state.get("skip_classify") and state.get("intent"):
        return {"intent": state["intent"], "args": state.get("args"), "is_chat": False}

    result = llm_brain.classify(state["raw_input"])

    if result["intent"] == "chat":
        return {
            "intent": "chat", "args": None, "is_chat": True,
            "response": result.get("reply") or "I'm here — what would you like me to do?",
            "success": True,
        }

    return {"intent": result["intent"], "args": result.get("args"), "is_chat": False}


def check_confirmation(state: NovaState) -> dict:
    return {"needs_confirm": needs_confirmation(state["intent"])}


def ask_confirmation(state: NovaState) -> dict:
    intent = state["intent"]
    a = _parse_args(state.get("args"))
    if intent == "delete_note":
        target = "your most recent note"
    elif intent == "shutdown_computer":
        target = "your computer (shutdown)"
    elif intent == "restart_computer":
        target = "your computer (restart)"
    elif intent == "kill_process":
        target = a.get("name") or state.get("args") or "that process"
    else:
        target = a.get("name") or state.get("args") or "this item"

    marker = CONFIRM_MARKER + json.dumps({"intent": intent, "target": target,
                                           "args": state.get("args")})
    return {"response": marker, "success": False}


def execute_tool(state: NovaState) -> dict:
    intent = state["intent"]
    args   = state.get("args")
    a      = _parse_args(args)  # for multi-arg tools

    try:
        # ── Apps ─────────────────────────────────────────────
        if intent == "open_notepad":
            response = application_tools.open_notepad()
        elif intent == "open_calculator":
            response = application_tools.open_calculator()
        elif intent == "open_file_explorer":
            response = application_tools.open_file_explorer()
        elif intent == "open_browser":
            response = browser_tools.open_browser()
        elif intent == "open_application":
            response = application_tools.open_application(a.get("name") or args or "", a.get("text_to_type"))
        elif intent == "write_text_to_window":
            response = application_tools.type_text(a.get("text") or args or "")

        # ── Web/AI search ────────────────────────────────────
        elif intent == "search_google":
            response = browser_tools.search_google(args or "")
        elif intent == "search_youtube":
            response = browser_tools.search_youtube(args or "")
        elif intent == "play_youtube":
            response = browser_tools.play_youtube(args or "")
        elif intent == "search_chatgpt":
            response = ai_tools.search_chatgpt(args or "")
        elif intent == "search_gemini":
            response = ai_tools.search_gemini(args or "")
        elif intent == "search_perplexity":
            response = ai_tools.search_perplexity(args or "")
        elif intent == "search_claude":
            response = ai_tools.search_claude(args or "")
        elif intent == "search_copilot":
            response = ai_tools.search_copilot(args or "")
        elif intent == "search_grok":
            response = ai_tools.search_grok(args or "")
        elif intent == "search_phind":
            response = ai_tools.search_phind(args or "")

        # ── System stats ─────────────────────────────────────
        elif intent == "get_system_specs":
            response = system_tools.get_system_specs()
        elif intent == "show_cpu":
            response = system_tools.get_cpu_usage()
        elif intent == "show_ram":
            response = system_tools.get_ram_usage()
        elif intent == "show_battery":
            response = system_tools.get_battery()
        elif intent == "show_time":
            response = system_tools.get_time()
        elif intent == "take_screenshot":
            response = system_tools.take_screenshot()
        elif intent == "get_network_info":
            response = info_tools.get_network_info()
        elif intent == "get_disk_usage":
            response = info_tools.get_disk_usage()

        # ── File ops — real Windows paths ────────────────────────────
        elif intent == "generate_and_save_file":
            response = file_tools.generate_and_write_file(
                a.get("filename") or args or "document",
                a.get("topic") or "",
                a.get("location", "desktop"),
            )
        elif intent == "create_folder":
            response = file_tools.create_folder(a.get("name") or args or "New Folder", a.get("location", "desktop"))
        elif intent == "create_file":
            response = file_tools.create_text_file(a.get("name") or args or "untitled", a.get("location", "desktop"))
        elif intent == "read_file":
            response = file_tools.read_text_file(a.get("name") or args or "", a.get("location", "desktop"))
        elif intent == "list_files":
            response = file_tools.list_files(a.get("location", "desktop"))
        elif intent == "delete_file":
            response = file_tools.delete_file(a.get("name") or args or "", a.get("location", "desktop"))
        elif intent == "save_text_to_file":
            response = file_tools.write_to_file(a.get("name") or "", a.get("content") or "", a.get("location", "desktop"))
        elif intent == "append_to_file":
            response = file_tools.append_to_file(a.get("name") or "", a.get("content") or "", a.get("location", "desktop"))
        elif intent == "open_with_app":
            response = file_tools.open_with_app(a.get("name") or args or "", a.get("location", "desktop"))
        elif intent == "open_folder":
            response = file_tools.open_folder(a.get("location", "desktop"))
        elif intent == "move_file":
            response = file_tools.move_file(a.get("name") or "", a.get("source", "desktop"), a.get("destination", "documents"))
        elif intent == "copy_file":
            response = file_tools.copy_file(a.get("name") or "", a.get("source", "desktop"), a.get("destination", "documents"))
        elif intent == "rename_file":
            response = file_tools.rename_file(a.get("old_name") or "", a.get("new_name") or "", a.get("location", "desktop"))
        elif intent == "search_in_files":
            response = file_tools.search_in_files(a.get("keyword") or args or "", a.get("location", "desktop"))
        # ── Notes ────────────────────────────────────────────
        elif intent == "create_note":
            response = note_tools.create_note(a.get("content") or args or "")
        elif intent == "show_notes":
            response = note_tools.show_notes()
        elif intent == "delete_note":
            response = note_tools.delete_latest_note()

        # ── Volume ───────────────────────────────────────────
        elif intent == "volume_up":
            response = power_tools.volume_up()
        elif intent == "volume_down":
            response = power_tools.volume_down()
        elif intent == "volume_mute":
            response = power_tools.volume_mute()
        elif intent == "volume_unmute":
            response = power_tools.volume_unmute()
        elif intent == "get_volume":
            response = power_tools.get_volume()
        elif intent == "set_volume":
            response = power_tools.set_volume(int(args or 50))

        # ── Power ────────────────────────────────────────────
        elif intent == "lock_computer":
            response = power_tools.lock_computer()
        elif intent == "sleep_computer":
            response = power_tools.sleep_computer()
        elif intent == "shutdown_computer":
            response = power_tools.shutdown_computer()
        elif intent == "restart_computer":
            response = power_tools.restart_computer()
        elif intent == "cancel_shutdown":
            response = power_tools.cancel_shutdown()
        elif intent == "kill_process":
            response = power_tools.kill_process(a.get("name") or args or "")

        # ── Clipboard ────────────────────────────────────────
        elif intent == "read_clipboard":
            response = clipboard_tools.read_clipboard()
        elif intent == "summarize_clipboard":
            response = clipboard_tools.summarize_clipboard()
        elif intent == "fix_grammar":
            response = clipboard_tools.fix_grammar()
        elif intent == "translate_text":
            response = clipboard_tools.translate_text(a.get("language") or args or "English")

        # ── Information ──────────────────────────────────────
        elif intent == "get_weather":
            response = info_tools.get_weather(a.get("city") or args or "Lahore")
        elif intent == "get_wikipedia":
            response = info_tools.get_wikipedia(a.get("topic") or args or "")

        # ── Timer ────────────────────────────────────────────
        elif intent == "set_timer":
            duration_str = a.get("duration") or args or "1 minute"
            seconds = _parse_duration(duration_str)
            response = f"{TIMER_MARKER}{seconds}|Timer set for {duration_str}."

        # ── Controls ─────────────────────────────────────────
        elif intent == "stop_speaking":
            response = "__STOP_SPEAKING__"
        elif intent == "clear_chat":
            llm_brain.clear_history()
            response = "__CLEAR_CHAT__"

        else:
            return {"response": "I'm not sure how to do that yet.", "success": False}

        return {"response": response, "success": True}

    except Exception as e:
        return {"response": f"Something went wrong: {e}", "success": False}


def cancelled_response(state: NovaState) -> dict:
    return {"response": "Okay, cancelled.", "success": True}


def generate_response(state: NovaState) -> dict:
    return {"response": state["response"]}


def save_history(state: NovaState) -> dict:
    skip = ("__STOP_SPEAKING__", "__CLEAR_CHAT__")
    r = state["response"]
    if r not in skip and not r.startswith(CONFIRM_MARKER) and not r.startswith(TIMER_MARKER):
        db.save_history(state["raw_input"], r, state["success"])
    return {"success": state["success"]}


# ── Routing ───────────────────────────────────────────────────────────────────

def route_after_classify(state: NovaState) -> str:
    return "chat" if state["is_chat"] else "check_confirm"


def route_after_confirmation_check(state: NovaState) -> str:
    if not state["needs_confirm"]:
        return "execute"
    if state.get("confirmed") is True:
        return "execute"
    if state.get("confirmed") is False:
        return "cancelled"
    return "ask_confirmation"


# ── Graph assembly ────────────────────────────────────────────────────────────

def build_graph():
    g = StateGraph(NovaState)
    g.add_node("receive_input",      receive_input)
    g.add_node("classify_intent",    classify_intent)
    g.add_node("check_confirmation", check_confirmation)
    g.add_node("ask_confirmation",   ask_confirmation)
    g.add_node("execute_tool",       execute_tool)
    g.add_node("cancelled_response", cancelled_response)
    g.add_node("generate_response",  generate_response)
    g.add_node("save_history",       save_history)

    g.set_entry_point("receive_input")
    g.add_edge("receive_input", "classify_intent")

    g.add_conditional_edges("classify_intent", route_after_classify, {
        "chat":         "generate_response",
        "check_confirm": "check_confirmation",
    })
    g.add_conditional_edges("check_confirmation", route_after_confirmation_check, {
        "execute":          "execute_tool",
        "cancelled":        "cancelled_response",
        "ask_confirmation": "ask_confirmation",
    })

    for node in ("execute_tool", "cancelled_response", "ask_confirmation"):
        g.add_edge(node, "generate_response")
    g.add_edge("generate_response", "save_history")
    g.add_edge("save_history", END)

    return g.compile()


nova_graph = build_graph()


def run_command(raw_input, confirmed=None, intent=None, args=None, skip_classify=False):
    return nova_graph.invoke({
        "raw_input":    raw_input,
        "intent":       intent or "",
        "args":         args,
        "is_chat":      False,
        "needs_confirm": False,
        "confirmed":    confirmed,
        "skip_classify": skip_classify,
        "response":     "",
        "success":      False,
    })


def is_confirmation_request(response: str):
    if response.startswith(CONFIRM_MARKER):
        try:
            payload = json.loads(response[len(CONFIRM_MARKER):])
            return True, payload.get("intent"), payload.get("target", "this"), payload.get("args")
        except Exception:
            return True, None, "this item", None
    return False, None, None, None
