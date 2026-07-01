import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.command_parser import parse_command, needs_confirmation


def test_open_notepad():
    result = parse_command("open notepad")
    assert result["intent"] == "open_notepad"


def test_open_calculator():
    result = parse_command("open calculator")
    assert result["intent"] == "open_calculator"


def test_search_google_extracts_query():
    result = parse_command("search google for python tutorials")
    assert result["intent"] == "search_google"
    assert result["args"] == "python tutorials"


def test_search_youtube_extracts_query():
    result = parse_command("search youtube for langgraph tutorials")
    assert result["intent"] == "search_youtube"
    assert result["args"] == "langgraph tutorials"


def test_create_note_extracts_content():
    result = parse_command("create note saying presentation is on Monday")
    assert result["intent"] == "create_note"
    assert result["args"] == "presentation is on monday"


def test_create_folder_extracts_name():
    result = parse_command("create folder HCI Project")
    assert result["intent"] == "create_folder"
    assert result["args"] == "hci project"


def test_show_cpu_usage():
    result = parse_command("show cpu usage")
    assert result["intent"] == "show_cpu"


def test_show_ram_usage():
    result = parse_command("show ram usage")
    assert result["intent"] == "show_ram"


def test_unknown_command():
    result = parse_command("do a backflip please")
    assert result["intent"] == "unknown"


def test_delete_file_needs_confirmation():
    result = parse_command("delete file test.txt")
    assert result["intent"] == "delete_file"
    assert needs_confirmation(result["intent"]) is True


def test_open_notepad_does_not_need_confirmation():
    result = parse_command("open notepad")
    assert needs_confirmation(result["intent"]) is False


def test_case_insensitive():
    result = parse_command("OPEN NOTEPAD")
    assert result["intent"] == "open_notepad"


def test_trailing_punctuation_ignored():
    result = parse_command("what time is it?")
    assert result["intent"] == "show_time"
