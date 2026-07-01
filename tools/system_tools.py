import psutil
from PIL import ImageGrab
from datetime import datetime
from pathlib import Path

SCREENSHOTS_DIR = Path(__file__).parent.parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def get_cpu_usage() -> str:
    percent = psutil.cpu_percent(interval=0.5)
    return f"CPU usage is {percent} percent."


def get_ram_usage() -> str:
    mem = psutil.virtual_memory()
    return f"RAM usage is {mem.percent} percent. {round(mem.used / (1024**3), 1)} GB used of {round(mem.total / (1024**3), 1)} GB."


def get_battery() -> str:
    battery = psutil.sensors_battery()
    if battery is None:
        return "No battery detected — this looks like a desktop machine."
    plugged = "and charging" if battery.power_plugged else "and not charging"
    return f"Battery is at {battery.percent} percent {plugged}."


def get_time() -> str:
    now = datetime.now()
    return f"It is currently {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d')}."


def take_screenshot() -> str:
    filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = SCREENSHOTS_DIR / filename
    img = ImageGrab.grab()
    img.save(str(filepath))
    return f"Screenshot saved as {filename}."


def get_stats_snapshot() -> dict:
    """Used by the side panel for live stats — no speech response needed."""
    mem = psutil.virtual_memory()
    battery = psutil.sensors_battery()
    return {
        "cpu": psutil.cpu_percent(interval=None),
        "ram": mem.percent,
        "battery": battery.percent if battery else None,
        "time": datetime.now().strftime("%I:%M %p"),
    }
