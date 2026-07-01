import requests
import psutil
import socket


def get_weather(city: str = "Lahore") -> str:
    try:
        url = f"https://wttr.in/{city.replace(' ', '+')}?format=j1"
        data = requests.get(url, timeout=6).json()
        cur = data["current_condition"][0]
        return (
            f"Weather in {city}: {cur['temp_C']}°C, feels like {cur['FeelsLikeC']}°C. "
            f"{cur['weatherDesc'][0]['value']}. Humidity {cur['humidity']}%, "
            f"wind {cur['windspeedKmph']} km/h."
        )
    except Exception:
        return f"Could not get weather for '{city}'. Check your internet connection."


def get_weather_snapshot(city: str = "Lahore") -> dict | None:
    try:
        url = f"https://wttr.in/{city.replace(' ', '+')}?format=j1"
        data = requests.get(url, timeout=5).json()
        cur = data["current_condition"][0]
        return {
            "city":     city,
            "temp":     cur["temp_C"],
            "feels":    cur["FeelsLikeC"],
            "desc":     cur["weatherDesc"][0]["value"],
            "humidity": cur["humidity"],
        }
    except Exception:
        return None


def get_wikipedia(topic: str) -> str:
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic.replace(' ', '_')}"
        data = requests.get(url, timeout=6).json()
        extract = data.get("extract", "")
        if not extract:
            return f"No Wikipedia article found for '{topic}'."
        # return first 3 sentences
        sentences = extract.split(". ")
        return ". ".join(sentences[:3]) + ("." if len(sentences) > 3 else "")
    except Exception:
        return f"Could not fetch Wikipedia info for '{topic}'."


def get_network_info() -> str:
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        net_io = psutil.net_io_counters()
        sent_mb = round(net_io.bytes_sent / 1024 ** 2, 1)
        recv_mb = round(net_io.bytes_recv / 1024 ** 2, 1)
        return (
            f"Hostname: {hostname}. Local IP: {local_ip}. "
            f"Data sent: {sent_mb} MB, received: {recv_mb} MB this session."
        )
    except Exception as e:
        return f"Could not retrieve network info: {e}"


def get_disk_usage() -> str:
    lines = []
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            lines.append(
                f"{part.device}: {round(usage.free / 1024**3, 1)} GB free "
                f"of {round(usage.total / 1024**3, 1)} GB ({usage.percent}% used)"
            )
        except PermissionError:
            continue
    return ("Disk usage — " + " | ".join(lines)) if lines else "No disk info available."
