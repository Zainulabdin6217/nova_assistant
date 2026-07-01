"""
File tools — works on real Windows paths with OneDrive support.
"""
import os
import shutil
import subprocess
import requests
from pathlib import Path

HOME = Path.home()


def _get_real_path(folder_name: str) -> Path:
    """
    Use PowerShell to get the REAL Windows shell folder path.
    This correctly handles OneDrive-relocated Desktop/Documents/Downloads.
    Falls back to Path.home() / name if PowerShell fails.
    """
    # Map friendly names to Windows shell folder names
    shell_map = {
        "desktop":   "Desktop",
        "documents": "MyDocuments",
        "pictures":  "MyPictures",
        "videos":    "MyVideos",
        "music":     "MyMusic",
    }
    shell_name = shell_map.get(folder_name.lower())
    if shell_name:
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f'[Environment]::GetFolderPath("{shell_name}")'],
                capture_output=True, text=True, timeout=4,
            )
            path = Path(result.stdout.strip())
            if path.exists():
                return path
        except Exception:
            pass

    # Downloads has no shell folder constant — use USERPROFILE env var
    if folder_name.lower() == "downloads":
        try:
            up = os.environ.get("USERPROFILE", "")
            if up:
                p = Path(up) / "Downloads"
                if p.exists():
                    return p
        except Exception:
            pass

    # Final fallback
    return HOME / folder_name.capitalize()


# Build location map once at import time
LOCATIONS: dict[str, Path] = {
    "desktop":   _get_real_path("desktop"),
    "documents": _get_real_path("documents"),
    "downloads": _get_real_path("downloads"),
    "pictures":  _get_real_path("pictures"),
    "videos":    _get_real_path("videos"),
    "music":     _get_real_path("music"),
    "home":      HOME,
    "workspace": Path(__file__).parent.parent / "workspace",
}
LOCATIONS["workspace"].mkdir(exist_ok=True)


def safe_filename(name: str) -> str:
    bad = '<>:"/\\|?*'
    cleaned = "".join(c for c in name if c not in bad).strip()
    return cleaned or "untitled"


def _resolve(location: str) -> Path:
    loc = (location or "desktop").strip().lower()
    if loc in LOCATIONS:
        return LOCATIONS[loc]
    p = Path(location)
    if p.is_absolute():
        return p
    return LOCATIONS["desktop"]


def _add_ext(fname: str, ext: str = ".txt") -> str:
    return fname if "." in fname else fname + ext


def _open_file(path: Path):
    """Open file with default Windows application."""
    try:
        os.startfile(str(path))
    except Exception:
        try:
            subprocess.Popen(["explorer", str(path)])
        except Exception:
            pass


# ── AI content generation ─────────────────────────────────────────────────────

def _ai_write(prompt: str) -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return (
            f"[This file was created by NOVA]\n\n"
            f"Topic: {prompt}\n\n"
            f"(Add OPENAI_API_KEY to your .env file to enable AI-generated content)"
        )
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a skilled writer. Write exactly what the user requests — "
                            "essays, stories, letters, poems, assignments. "
                            "Be genuine, well-structured and complete. "
                            "Output the content only, no extra commentary."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.75,
                "max_tokens": 1200,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"AI writing error: {e}\n\nTopic: {prompt}"


def generate_and_write_file(filename: str, topic: str, location: str = "desktop") -> str:
    content  = _ai_write(topic)
    fname    = _add_ext(safe_filename(filename))
    base     = _resolve(location)
    base.mkdir(parents=True, exist_ok=True)
    path     = base / fname
    path.write_text(content, encoding="utf-8")
    _open_file(path)
    return f"'{fname}' created at {path} and opened for you."


# ── Core file operations ──────────────────────────────────────────────────────

def create_folder(name: str, location: str = "desktop") -> str:
    base = _resolve(location)
    path = base / safe_filename(name)
    path.mkdir(parents=True, exist_ok=True)
    # Open the parent folder so user can see it
    try:
        subprocess.Popen(["explorer", str(base)])
    except Exception:
        pass
    return f"Folder '{path.name}' created at {path}."


def create_text_file(name: str, location: str = "desktop", content: str = "") -> str:
    base  = _resolve(location)
    base.mkdir(parents=True, exist_ok=True)
    fname = _add_ext(safe_filename(name))
    path  = base / fname
    path.write_text(content, encoding="utf-8")
    _open_file(path)
    return f"File '{fname}' created at {path}."


def write_to_file(name: str, content: str, location: str = "desktop") -> str:
    base  = _resolve(location)
    base.mkdir(parents=True, exist_ok=True)
    fname = _add_ext(safe_filename(name))
    path  = base / fname
    path.write_text(content, encoding="utf-8")
    _open_file(path)
    return f"Written to '{fname}' at {path}."


def append_to_file(name: str, content: str, location: str = "desktop") -> str:
    base  = _resolve(location)
    fname = _add_ext(safe_filename(name))
    path  = base / fname
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n{content}")
    return f"Appended to '{fname}' at {path}."


def read_text_file(name: str, location: str = "desktop") -> str:
    fname = safe_filename(name)
    base  = _resolve(location)
    path  = base / fname
    if not path.exists():
        path = base / _add_ext(fname)
    if not path.exists():
        return f"'{name}' not found in {location} ({base})."
    text = path.read_text(encoding="utf-8", errors="ignore")
    return (f"Contents of {path.name}:\n{text}") if text else f"{path.name} is empty."


def list_files(location: str = "desktop") -> str:
    base = _resolve(location)
    try:
        items = sorted(base.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        if not items:
            return f"{location.title()} is empty. (Path: {base})"
        names = [f"[folder] {p.name}" if p.is_dir() else p.name for p in items[:30]]
        extra = f" (+{len(items)-30} more)" if len(items) > 30 else ""
        return f"{location.title()} ({base}):\n" + "\n".join(names) + extra
    except PermissionError:
        return f"No permission to list {location}."


def delete_file(name: str, location: str = "desktop") -> str:
    fname = safe_filename(name)
    base  = _resolve(location)
    path  = base / fname
    if not path.exists():
        path = base / _add_ext(fname)
    if not path.exists():
        return f"'{name}' not found in {location} ({base})."
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return f"'{path.name}' deleted from {location}."


def open_with_app(name: str, location: str = "desktop") -> str:
    fname = safe_filename(name)
    base  = _resolve(location)
    path  = base / fname
    if not path.exists():
        for ext in [".txt", ".pdf", ".docx", ".xlsx", ".jpg", ".png", ".mp4", ".mp3"]:
            if (base / (fname + ext)).exists():
                path = base / (fname + ext)
                break
    if not path.exists():
        return f"'{name}' not found in {location} ({base})."
    _open_file(path)
    return f"Opened '{path.name}'."


def open_folder(location: str = "desktop") -> str:
    path = _resolve(location)
    subprocess.Popen(["explorer", str(path)])
    return f"Opened {location} folder ({path}) in File Explorer."


def move_file(name: str, source: str = "desktop", destination: str = "documents") -> str:
    fname = safe_filename(name)
    src   = _resolve(source) / fname
    if not src.exists():
        src = _resolve(source) / _add_ext(fname)
    if not src.exists():
        return f"'{name}' not found in {source}."
    dst_dir = _resolve(destination)
    dst_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst_dir / src.name))
    return f"Moved '{src.name}' from {source} to {destination} ({dst_dir})."


def copy_file(name: str, source: str = "desktop", destination: str = "documents") -> str:
    fname = safe_filename(name)
    src   = _resolve(source) / fname
    if not src.exists():
        src = _resolve(source) / _add_ext(fname)
    if not src.exists():
        return f"'{name}' not found in {source}."
    dst_dir = _resolve(destination)
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    shutil.copytree(str(src), str(dst)) if src.is_dir() else shutil.copy2(str(src), str(dst))
    return f"Copied '{src.name}' to {destination} ({dst_dir})."


def rename_file(old_name: str, new_name: str, location: str = "desktop") -> str:
    base      = _resolve(location)
    old_fname = safe_filename(old_name)
    new_fname = safe_filename(new_name)
    old_path  = base / old_fname
    if not old_path.exists():
        old_path = base / _add_ext(old_fname)
    if not old_path.exists():
        return f"'{old_name}' not found in {location}."
    if "." not in new_fname:
        new_fname += old_path.suffix
    old_path.rename(base / new_fname)
    return f"Renamed to '{new_fname}' on {location}."


def search_in_files(keyword: str, location: str = "desktop") -> str:
    results = []
    try:
        for path in _resolve(location).rglob("*.txt"):
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                if keyword.lower() in content.lower():
                    lines = [str(i+1) for i, l in enumerate(content.splitlines()) if keyword.lower() in l.lower()]
                    results.append(f"{path.name} (lines {', '.join(lines)})")
            except Exception:
                continue
    except PermissionError:
        return f"No permission to search {location}."
    return f"Found '{keyword}' in: {', '.join(results)}." if results else f"'{keyword}' not found in {location}."
