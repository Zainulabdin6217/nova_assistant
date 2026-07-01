"""
Adds or removes NOVA from the Windows startup registry
so it launches automatically when you log in.
"""
import sys
import winreg
from pathlib import Path

STARTUP_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME     = "NOVA_Assistant"


def _nova_command() -> str:
    python  = sys.executable          # full path to python.exe in .venv
    main_py = Path(__file__).parent.parent / "main.py"
    return f'"{python}" "{main_py}"'


def enable_startup() -> str:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0,
                             winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _nova_command())
        winreg.CloseKey(key)
        return "NOVA will now start automatically when you log in to Windows."
    except Exception as e:
        return f"Could not enable startup: {e}"


def disable_startup() -> str:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0,
                             winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        return "NOVA will no longer start automatically."
    except FileNotFoundError:
        return "NOVA was not in startup — nothing changed."
    except Exception as e:
        return f"Could not disable startup: {e}"


def is_startup_enabled() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0,
                             winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
