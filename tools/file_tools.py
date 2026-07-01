import shutil
from pathlib import Path

# Trusted locations the user can reference by name
WORKSPACE_DIR = Path(__file__).parent.parent / "workspace"
WORKSPACE_DIR.mkdir(exist_ok=True)

LOCATIONS: dict[str, Path] = {
    "workspace":  WORKSPACE_DIR,
    "desktop":    Path.home() / "Desktop",
    "downloads":  Path.home() / "Downloads",
    "documents":  Path.home() / "Documents",
}


def safe_filename(name: str) -> str:
    bad = '<>:"/\\|?*'
    cleaned = "".join(c for c in name if c not in bad).strip()
    return cleaned or "untitled"


def _resolve(location: str) -> Path:
    return LOCATIONS.get(location.lower().strip(), WORKSPACE_DIR)


# ── Basic file ops ──────────────────────────────────────────────────────────

def create_folder(name: str) -> str:
    path = WORKSPACE_DIR / safe_filename(name)
    path.mkdir(exist_ok=True)
    return f"Folder '{path.name}' created in workspace."


def create_text_file(name: str, content: str = "") -> str:
    fname = safe_filename(name)
    if not fname.endswith(".txt"):
        fname += ".txt"
    path = WORKSPACE_DIR / fname
    path.write_text(content, encoding="utf-8")
    return f"File '{fname}' created."


def write_to_file(name: str, content: str) -> str:
    fname = safe_filename(name)
    if not fname.endswith(".txt"):
        fname += ".txt"
    path = WORKSPACE_DIR / fname
    path.write_text(content, encoding="utf-8")
    return f"Written to '{fname}'."


def append_to_file(name: str, content: str) -> str:
    fname = safe_filename(name)
    if not fname.endswith(".txt"):
        fname += ".txt"
    path = WORKSPACE_DIR / fname
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n{content}")
    return f"Appended text to '{fname}'."


def read_text_file(name: str, location: str = "workspace") -> str:
    fname = safe_filename(name)
    if not fname.endswith(".txt"):
        fname += ".txt"
    base = _resolve(location)
    path = base / fname
    if not path.exists():
        return f"File '{fname}' was not found in {location}."
    content = path.read_text(encoding="utf-8")
    return f"Contents of {fname}:\n{content}" if content else f"{fname} is empty."


def list_files(location: str = "workspace") -> str:
    base = _resolve(location)
    try:
        items = list(base.iterdir())
        if not items:
            return f"The {location} folder is empty."
        return location.title() + " contains: " + ", ".join(i.name for i in items)
    except PermissionError:
        return f"No permission to list {location}."


def delete_file(name: str, location: str = "workspace") -> str:
    fname = safe_filename(name)
    base  = _resolve(location)
    path  = base / fname
    if not path.exists():
        path = base / (fname + ".txt")
    if not path.exists():
        return f"'{name}' was not found in {location}."
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return f"'{path.name}' deleted from {location}."


# ── Advanced file ops ───────────────────────────────────────────────────────

def move_file(name: str, source: str = "workspace", destination: str = "workspace") -> str:
    fname    = safe_filename(name)
    src_base = _resolve(source)
    dst_base = _resolve(destination)

    src_path = src_base / fname
    if not src_path.exists():
        src_path = src_base / (fname + ".txt")
    if not src_path.exists():
        return f"'{name}' was not found in {source}."

    dst_path = dst_base / src_path.name
    shutil.move(str(src_path), str(dst_path))
    return f"Moved '{src_path.name}' from {source} to {destination}."


def copy_file(name: str, source: str = "workspace", destination: str = "workspace") -> str:
    fname    = safe_filename(name)
    src_base = _resolve(source)
    dst_base = _resolve(destination)

    src_path = src_base / fname
    if not src_path.exists():
        src_path = src_base / (fname + ".txt")
    if not src_path.exists():
        return f"'{name}' was not found in {source}."

    dst_path = dst_base / src_path.name
    if src_path.is_dir():
        shutil.copytree(str(src_path), str(dst_path))
    else:
        shutil.copy2(str(src_path), str(dst_path))
    return f"Copied '{src_path.name}' to {destination}."


def rename_file(old_name: str, new_name: str) -> str:
    old_fname = safe_filename(old_name)
    new_fname = safe_filename(new_name)

    old_path = WORKSPACE_DIR / old_fname
    if not old_path.exists():
        old_path = WORKSPACE_DIR / (old_fname + ".txt")
    if not old_path.exists():
        return f"'{old_name}' was not found in workspace."

    # Keep extension if new name has none and old name has one
    if "." not in new_fname and "." in old_path.name:
        new_fname += old_path.suffix

    new_path = WORKSPACE_DIR / new_fname
    old_path.rename(new_path)
    return f"Renamed '{old_path.name}' to '{new_path.name}'."


def search_in_files(keyword: str) -> str:
    results = []
    for path in WORKSPACE_DIR.rglob("*.txt"):
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            if keyword.lower() in content.lower():
                lines = [
                    str(i + 1)
                    for i, line in enumerate(content.splitlines())
                    if keyword.lower() in line.lower()
                ]
                results.append(f"{path.name} (lines {', '.join(lines)})")
        except Exception:
            continue
    if not results:
        return f"'{keyword}' was not found in any workspace files."
    return f"Found '{keyword}' in: {', '.join(results)}."
