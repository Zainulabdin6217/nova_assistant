import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.file_tools import safe_filename, create_text_file, read_text_file, delete_file, WORKSPACE_DIR
from tools.system_tools import get_time


def test_safe_filename_strips_bad_chars():
    result = safe_filename('te<st>:fi"le?.txt')
    assert "<" not in result
    assert ">" not in result
    assert ":" not in result
    assert '"' not in result
    assert "?" not in result


def test_safe_filename_empty_falls_back():
    result = safe_filename("???")
    assert result == "untitled"


def test_create_and_read_text_file():
    create_text_file("pytest_temp_file", "hello world")
    result = read_text_file("pytest_temp_file")
    assert "hello world" in result
    # cleanup
    delete_file("pytest_temp_file")


def test_read_nonexistent_file():
    result = read_text_file("this_file_does_not_exist_12345")
    assert "not found" in result.lower()


def test_delete_file_returns_message():
    create_text_file("pytest_delete_me", "temp content")
    result = delete_file("pytest_delete_me")
    assert "deleted" in result.lower()


def test_delete_nonexistent_file():
    result = delete_file("totally_fake_file_xyz")
    assert "not found" in result.lower()


def test_get_time_returns_string():
    result = get_time()
    assert isinstance(result, str)
    assert "currently" in result.lower()


def test_workspace_dir_exists():
    assert WORKSPACE_DIR.exists()
