import subprocess


def _volume_interface():
    try:
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        iface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return iface.QueryInterface(IAudioEndpointVolume)
    except ImportError:
        raise RuntimeError("pycaw not installed. Run: pip install pycaw")

def get_volume() -> str:
    vol = _volume_interface()
    level = round(vol.GetMasterVolumeLevelScalar() * 100)
    muted = vol.GetMute()
    return f"Volume is at {level}%{' (muted)' if muted else ''}."

def volume_up() -> str:
    vol = _volume_interface()
    new = min(100, round(vol.GetMasterVolumeLevelScalar() * 100) + 10)
    vol.SetMasterVolumeLevelScalar(new / 100.0, None)
    return f"Volume increased to {new}%."

def volume_down() -> str:
    vol = _volume_interface()
    new = max(0, round(vol.GetMasterVolumeLevelScalar() * 100) - 10)
    vol.SetMasterVolumeLevelScalar(new / 100.0, None)
    return f"Volume decreased to {new}%."

def volume_mute() -> str:
    _volume_interface().SetMute(1, None)
    return "Volume muted."

def volume_unmute() -> str:
    _volume_interface().SetMute(0, None)
    return "Volume unmuted."

def set_volume(level: int) -> str:
    level = max(0, min(100, int(level)))
    _volume_interface().SetMasterVolumeLevelScalar(level / 100.0, None)
    return f"Volume set to {level}%."

def lock_computer() -> str:
    subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
    return "Computer locked."

def sleep_computer() -> str:
    subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState 0,1,0"])
    return "Putting the computer to sleep."

def shutdown_computer() -> str:
    subprocess.run(["shutdown", "/s", "/t", "15"], shell=True)
    return "Shutting down in 15 seconds. Say cancel shutdown to stop."

def restart_computer() -> str:
    subprocess.run(["shutdown", "/r", "/t", "15"], shell=True)
    return "Restarting in 15 seconds. Say cancel restart to stop."

def cancel_shutdown() -> str:
    subprocess.run(["shutdown", "/a"], shell=True)
    return "Shutdown or restart cancelled."

def kill_process(name: str) -> str:
    import psutil
    name_lower = name.lower().strip()
    if not name_lower.endswith(".exe"):
        name_lower += ".exe"
    killed = []
    for proc in psutil.process_iter(["name", "pid"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == name_lower:
                proc.kill()
                killed.append(str(proc.info["pid"]))
        except Exception:
            pass
    if killed:
        return f"Killed {name} (PID: {', '.join(killed)})."
    return f"No running process named '{name}' was found."
