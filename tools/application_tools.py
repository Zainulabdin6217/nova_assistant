import subprocess


def open_notepad() -> str:
    subprocess.Popen(["notepad.exe"])
    return "Opening Notepad."


def open_calculator() -> str:
    subprocess.Popen(["calc.exe"])
    return "Opening Calculator."


def open_file_explorer() -> str:
    subprocess.Popen(["explorer.exe"])
    return "Opening File Explorer."
