from database.database import db


def create_note(content: str) -> str:
    if not content.strip():
        return "Note content cannot be empty."
    db.add_note(content.strip())
    return "Note saved."


def show_notes() -> str:
    notes = db.get_notes()
    if not notes:
        return "You have no notes yet."

    lines = [f"{i + 1}. {n['content']}" for i, n in enumerate(notes)]
    return "Your notes: " + " | ".join(lines)


def delete_latest_note() -> str:
    note_id = db.get_latest_note_id()
    if note_id is None:
        return "There are no notes to delete."
    db.delete_note(note_id)
    return "Note deleted."


def delete_note_by_id(note_id: int) -> str:
    deleted = db.delete_note(note_id)
    return "Note deleted." if deleted else f"Note #{note_id} was not found."
