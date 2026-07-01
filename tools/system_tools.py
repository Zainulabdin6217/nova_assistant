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


def get_system_specs() -> str:
    """
    Returns complete hardware and OS specifications —
    CPU model, cores, speed, RAM size, GPU, disk, OS version etc.
    Works fully offline using platform, psutil, and wmi (Windows).
    """
    import platform, subprocess

    lines = []

    # ── Operating System ──────────────────────────────────────────────────
    try:
        uname = platform.uname()
        lines.append(f"OS: {uname.system} {uname.release} ({uname.version})")
        lines.append(f"Machine: {uname.machine}  |  Node: {uname.node}")
    except Exception:
        pass

    # ── CPU ───────────────────────────────────────────────────────────────
    try:
        cpu_name = platform.processor()
        if not cpu_name or cpu_name == "":
            # Try reading from Windows registry via wmic
            result = subprocess.run(
                ["wmic", "cpu", "get", "Name"],
                capture_output=True, text=True, timeout=5
            )
            lines_out = [l.strip() for l in result.stdout.splitlines() if l.strip() and l.strip() != "Name"]
            cpu_name = lines_out[0] if lines_out else "Unknown"

        lines.append(f"CPU: {cpu_name}")
        lines.append(f"Physical Cores: {psutil.cpu_count(logical=False)}  |  Logical Cores: {psutil.cpu_count(logical=True)}")

        freq = psutil.cpu_freq()
        if freq:
            lines.append(f"CPU Speed: {round(freq.current, 0)} MHz  (Max: {round(freq.max, 0)} MHz)")

        lines.append(f"CPU Usage right now: {psutil.cpu_percent(interval=0.3)}%")
    except Exception as e:
        lines.append(f"CPU info error: {e}")

    # ── RAM ───────────────────────────────────────────────────────────────
    try:
        mem = psutil.virtual_memory()
        total_gb  = round(mem.total  / (1024 ** 3), 1)
        used_gb   = round(mem.used   / (1024 ** 3), 1)
        avail_gb  = round(mem.available / (1024 ** 3), 1)
        lines.append(f"RAM Total: {total_gb} GB  |  Used: {used_gb} GB  |  Available: {avail_gb} GB  ({mem.percent}%)")
    except Exception:
        pass

    # ── RAM model / speed via wmic ────────────────────────────────────────
    try:
        result = subprocess.run(
            ["wmic", "memorychip", "get", "Capacity,Speed,Manufacturer,MemoryType,FormFactor"],
            capture_output=True, text=True, timeout=5
        )
        rows = [r.strip() for r in result.stdout.splitlines() if r.strip() and "Capacity" not in r]
        if rows:
            lines.append(f"RAM Details: {rows[0]}")
    except Exception:
        pass

    # ── GPU ───────────────────────────────────────────────────────────────
    try:
        result = subprocess.run(
            ["wmic", "path", "win32_VideoController", "get", "Name,AdapterRAM,DriverVersion"],
            capture_output=True, text=True, timeout=5
        )
        gpu_lines = [l.strip() for l in result.stdout.splitlines() if l.strip() and "Name" not in l]
        if gpu_lines:
            lines.append(f"GPU: {gpu_lines[0]}")
    except Exception:
        pass

    # ── Storage ───────────────────────────────────────────────────────────
    try:
        disk_parts = psutil.disk_partitions()
        for part in disk_parts:
            try:
                usage = psutil.disk_usage(part.mountpoint)
                total_gb = round(usage.total / (1024 ** 3), 1)
                free_gb  = round(usage.free  / (1024 ** 3), 1)
                lines.append(f"Disk {part.device}: {total_gb} GB total, {free_gb} GB free ({usage.percent}% used)")
            except Exception:
                continue
    except Exception:
        pass

    # ── Battery ───────────────────────────────────────────────────────────
    try:
        battery = psutil.sensors_battery()
        if battery:
            status = "Charging" if battery.power_plugged else "On battery"
            lines.append(f"Battery: {battery.percent}%  ({status})")
        else:
            lines.append("Battery: Desktop machine — no battery")
    except Exception:
        pass

    # ── Motherboard / System model ────────────────────────────────────────
    try:
        result = subprocess.run(
            ["wmic", "computersystem", "get", "Manufacturer,Model,TotalPhysicalMemory"],
            capture_output=True, text=True, timeout=5
        )
        sys_lines = [l.strip() for l in result.stdout.splitlines() if l.strip() and "Manufacturer" not in l]
        if sys_lines:
            lines.append(f"System Model: {sys_lines[0]}")
    except Exception:
        pass

    # ── BIOS / Motherboard ────────────────────────────────────────────────
    try:
        result = subprocess.run(
            ["wmic", "bios", "get", "Manufacturer,Name,Version"],
            capture_output=True, text=True, timeout=5
        )
        bios_lines = [l.strip() for l in result.stdout.splitlines() if l.strip() and "Manufacturer" not in l]
        if bios_lines:
            lines.append(f"BIOS: {bios_lines[0]}")
    except Exception:
        pass

    if not lines:
        return "Could not retrieve system specifications."

    return "System Specifications:\n" + "\n".join(f"• {line}" for line in lines)
