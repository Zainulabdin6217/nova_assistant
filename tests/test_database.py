import sys
from pathlib import Path
import tempfile
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.database import Database


def make_temp_db() -> Database:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return Database(db_path=path)


def test_add_and_get_note():
    db = make_temp_db()
    db.add_note("Presentation is on Monday")
    notes = db.get_notes()
    assert len(notes) == 1
    assert notes[0]["content"] == "Presentation is on Monday"


def test_delete_note():
    db = make_temp_db()
    note_id = db.add_note("Temporary note")
    deleted = db.delete_note(note_id)
    assert deleted is True
    assert len(db.get_notes()) == 0


def test_delete_nonexistent_note_returns_false():
    db = make_temp_db()
    deleted = db.delete_note(999)
    assert deleted is False


def test_notes_ordered_newest_first():
    db = make_temp_db()
    db.add_note("first")
    db.add_note("second")
    notes = db.get_notes()
    assert notes[0]["content"] == "second"
    assert notes[1]["content"] == "first"


def test_save_and_get_history():
    db = make_temp_db()
    db.save_history("open notepad", "Opening Notepad.", True)
    history = db.get_history()
    assert len(history) == 1
    assert history[0]["command"] == "open notepad"
    assert history[0]["success"] == 1


def test_history_failed_command():
    db = make_temp_db()
    db.save_history("delete file ghost.txt", "File not found.", False)
    history = db.get_history()
    assert history[0]["success"] == 0


def test_settings_get_default():
    db = make_temp_db()
    value = db.get_setting("voice_enabled", default="true")
    assert value == "true"


def test_settings_set_and_get():
    db = make_temp_db()
    db.set_setting("voice_enabled", "false")
    value = db.get_setting("voice_enabled")
    assert value == "false"


def test_get_latest_note_id():
    db = make_temp_db()
    db.add_note("old note")
    newest_id = db.add_note("new note")
    assert db.get_latest_note_id() == newest_id
