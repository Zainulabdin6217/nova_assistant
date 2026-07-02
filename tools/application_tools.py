import subprocess
import time
import keyboard
def open_notepad() -> str:
    subprocess.Popen(["notepad.exe"])
    return "Opening Notepad."


def open_calculator() -> str:
    subprocess.Popen(["calc.exe"])
    return "Opening Calculator."


def open_file_explorer() -> str:
    subprocess.Popen(["explorer.exe"])
    return "Opening File Explorer."


def open_application(app_name: str, text_to_type: str = None) -> str:
    try:
        # Open start menu
        keyboard.send("win")
        time.sleep(0.5)
        # Search for app
        keyboard.write(app_name)
        time.sleep(1.0)
        keyboard.send("enter")
        
        if text_to_type:
            # Wait for app to open before typing
            time.sleep(4.0)
            keyboard.write(text_to_type, delay=0.01)
            return f"Opening {app_name} and typing text."
        
        return f"Opening {app_name}."
    except Exception as e:
        return f"Failed to open {app_name}: {e}"


def type_text(text: str) -> str:
    try:
        time.sleep(1.0) # wait a bit before typing just in case window needs to focus
        keyboard.write(text, delay=0.01)
        return "Typed the requested text."
    except Exception as e:
        return f"Failed to type text: {e}"
