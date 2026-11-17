import os
import re
import subprocess
import time
from pathlib import Path
from pypresence import Presence

CLIENT_ID = "1570543423558127818"
INTERVAL = 5

GAMES = {
    "mcpelauncher-client": {
        "name": "Minecraft Bedrock",
        "image": "minecraft",
        "state": "Playing Minecraft",
        "version_arg": "-dg",
    },
    "PPSSPPSDL": {
        "name": "PPSSPP",
        "image": "ppsspp",
        "state": "Playing PSP",
        "version_arg": None,
    },
}


def get_starttime(pid):
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
        fields = stat[stat.rfind(")") + 2:].split()
        return int(fields[19])
    except (OSError, ValueError, IndexError):
        return 0


def get_window_title(pid):
    """Find PPSSPP window title: serial-based ('ULES01523 : Name') or PPSSPP-branded."""
    try:
        env = dict(
            line.split(b"=", 1)
            for line in Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
            if b"=" in line
        )
        env = {os.fsdecode(k): os.fsdecode(v) for k, v in env.items()}
    except (OSError, ValueError):
        env = {}

    env.setdefault("DISPLAY", ":0")

    titles = []

    try:
        out = subprocess.run(
            ["wmctrl", "-l"], capture_output=True, text=True, timeout=5, env=env,
        )
        for line in out.stdout.splitlines():
            parts = line.split(None, 3)
            if len(parts) == 4:
                titles.append(parts[3])
    except (OSError, subprocess.TimeoutExpired):
        pass

    if not titles:
        try:
            out = subprocess.run(
                ["xdotool", "search", "--onlyvisible", ".", "getwindowname", "%@"],
                capture_output=True, text=True, timeout=5, env=env,
            )
            titles = [t for t in out.stdout.splitlines() if t.strip()]
        except (OSError, subprocess.TimeoutExpired):
            pass

    for t in titles:
        if re.match(r"^[A-Z]{4}\d{5}\s*:", t):
            return t
    for t in titles:
        if "ppsspp" in t.lower():
            return t

    return None


def clean_title(title):
    """Extract game name from PPSSPP window title."""
    m = re.match(r"^[A-Z]{4}\d{5}\s*:\s*(.+)$", title)   # "ULES01523 : Persona3 PORTABLE"
    if m:
        return m.group(1).strip()
    title = re.sub(r"^PPSSPP[^:]*:\s*", "", title)      # "PPSSPP 1.20.4: Name"
    title = re.sub(r"^PPSSPP\s*-?\s*", "", title)       # "PPSSPP - Name" / "PPSSPP Name"
    title = re.sub(r"\s*[-|]\s*PPSSPP.*$", "", title)   # "Name - PPSSPP ..."
    title = title.strip()
    # Reject titles that are just the version (no game loaded)
    if not title or re.fullmatch(r"v?[\d.]+\s*", title):
        return None
    return title


SHORT_NAMES = {
    "Persona3 PORTABLE": "Persona 3 Portable",
    "Shin Megami Tensei - Persona 3 Portable": "Persona 3 Portable",
    "Disney-Pixar Toy Story 3": "Toy Story 3",
    "LEGO Batman - The Videogame": "Batman",
    "LEGO Batman: The Videogame": "Batman",
    "LUMINES": "Lumines",
    "Lumines - Puzzle Fusion": "Lumines",
}

# Game serial (ULES01523 etc.) -> Discord asset key for large_image
ICONS = {
    "ULES01523": "persona3p",
    "ULUS10491": "halfminutehero",
    "ULES01384": "dantesinferno",
    "ULES01406": "toystory3",
    "UCES00012": "everybodysgolf",
    "ULES01586": "fifa14",
    "ULES00043": "lumines",
    "UCUS98662": "locoroco",
    "ULES01151": "batman",
    "ULUS10304": "crashtitans",
}

_REGION = re.compile(r"\s*\((?:USA|Europe|Japan|Asia|World|v[^)]*|En[^)]*)\)\s*$")


def shorten_name(name):
    for full, short in SHORT_NAMES.items():
        if name.startswith(full):
            return short
    while True:
        new = _REGION.sub("", name)
        if new == name:
            break
        name = new
    name = name.replace("™", "").replace("®", "").replace("©", "").strip()
    return name.strip()


def find_game():
    detected = []

    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue

        try:
            args = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
            args = [os.fsdecode(x) for x in args if x]

            if not args:
                continue

            executable = os.path.basename(args[0])

            if executable not in GAMES:
                continue

            config = GAMES[executable]
            version = None

            if config["version_arg"] in args:
                i = args.index(config["version_arg"])
                if i + 1 < len(args):
                    version = Path(args[i + 1]).name

            detected.append({
                "pid": int(pid),
                "config": config,
                "version": version,
                "started": get_starttime(pid),
            })

        except (OSError, ValueError):
            continue

    if not detected:
        return None

    return max(detected, key=lambda x: x["started"])


def main():
    rpc = None
    current_pid = None
    current_game = None
    current_details = None
    start_time = None
    last_title = None

    print("[INFO] Multi Emulator Discord RPC started", flush=True)

    while True:
        game = find_game()

        if game:
            pid = game["pid"]
            config = game["config"]
            details = config["name"]
            state = config["state"]
            image = config["image"]

            if config["version_arg"] is None:
                title = get_window_title(pid)
                if title and title != last_title:
                    last_title = title
                    print(f"[DEBUG] window title: {title!r}", flush=True)
                if title:
                    name = clean_title(title)
                    if name:
                        details = "PPSSPP"
                        state = f"Playing {shorten_name(name)}"
                        m = re.match(r"^([A-Z]{4}\d{5})", title)
                        if m:
                            image = ICONS.get(m.group(1), config["image"])

            if game["version"]:
                details += f" {game['version']}"

            try:
                if rpc is None:
                    rpc = Presence(CLIENT_ID)
                    rpc.connect()
                    print("[INFO] Discord connected")

                if pid != current_pid or details != current_details:
                    current_pid = pid
                    current_details = details
                    start_time = int(time.time())

                    print(f"[INFO] Detected {state}", flush=True)

                rpc.update(
                    details=details,
                    state=state,
                    start=start_time,
                    large_image=image,
                    large_text=details,
                )

            except Exception as e:
                print(f"[ERROR] {e}")

                try:
                    rpc.close()
                except Exception:
                    pass

                rpc = None

        else:
            if rpc:
                try:
                    rpc.clear()
                    rpc.close()
                except Exception:
                    pass
            rpc = None
            current_pid = None
            current_game = None
            start_time = None

        time.sleep(INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Stopped")

