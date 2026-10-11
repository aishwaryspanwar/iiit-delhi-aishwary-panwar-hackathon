from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"
STAMP = VENV / ".requirements.sha256"
FRONTEND = ROOT / "frontend"
DIST_INDEX = FRONTEND / "dist" / "index.html"
DIST_STAMP = FRONTEND / "dist" / ".source.sha256"
FRONTEND_INPUTS = ("src", "public", "index.html", "package.json", "package-lock.json", "vite.config.ts", "tsconfig.json")
STARTUP_SECONDS = 240
MIN_PYTHON = (3, 11)
PREFERRED_MINORS = (13, 12, 14, 11, 15)


def say(message: str) -> None:
    print(f"[run] {message}", flush=True)


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def inside_venv() -> bool:
    return Path(sys.prefix).resolve() == VENV.resolve()


def requirements_hash() -> str:
    return hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()


def ensure_requirements(python: Path) -> None:
    if STAMP.exists() and STAMP.read_text(encoding="utf-8").strip() == requirements_hash():
        return
    say("installing Python requirements (first run only)")
    subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", str(REQUIREMENTS)], check=True)
    STAMP.write_text(requirements_hash(), encoding="utf-8")


def interpreter_version(command: list[str]) -> tuple[int, int] | None:
    try:
        result = subprocess.run(
            [*command, "-c", "import sys; print(sys.version_info[0], sys.version_info[1])"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        major, minor = result.stdout.split()
        return int(major), int(minor)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def find_python() -> list[str] | None:
    if sys.version_info >= MIN_PYTHON:
        return [sys.executable]
    candidates = []
    for minor in PREFERRED_MINORS:
        if os.name == "nt":
            if shutil.which("py"):
                candidates.append(["py", f"-3.{minor}"])
        else:
            found = shutil.which(f"python3.{minor}")
            if found:
                candidates.append([found])
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found:
            candidates.append([found])
    for command in candidates:
        version = interpreter_version(command)
        if version is not None and version >= MIN_PYTHON:
            return command
    return None


def ensure_venv() -> Path:
    python = venv_python()
    if not python.exists():
        interpreter = find_python()
        if interpreter is None:
            sys.exit(
                f"[run] Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or later is required (this one is {sys.version.split()[0]}, and no newer one was found). "
                "Install it from https://www.python.org/downloads/ or create a conda environment with `conda create -n ripple python=3.13 -y`, "
                "activate it, and run this script again"
            )
        say(f"creating the virtual environment in .venv with {' '.join(interpreter)}")
        subprocess.run([*interpreter, "-m", "venv", str(VENV)], check=True)
    ensure_requirements(python)
    return python


def source_files(paths: list[Path]) -> list[Path]:
    files = []
    for path in paths:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(p for p in path.rglob("*") if p.is_file())
    return sorted(files)


def frontend_hash() -> str:
    digest = hashlib.sha256()
    for path in source_files([FRONTEND / name for name in FRONTEND_INPUTS]):
        digest.update(path.relative_to(FRONTEND).as_posix().encode("utf-8"))
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def frontend_stale() -> bool:
    if not DIST_INDEX.exists() or not DIST_STAMP.exists():
        return True
    return DIST_STAMP.read_text(encoding="utf-8").strip() != frontend_hash()


def ensure_frontend(force: bool) -> None:
    if not force and not frontend_stale():
        return
    npm = shutil.which("npm")
    if npm is None:
        if DIST_INDEX.exists():
            say("frontend sources changed but Node.js is not installed; serving the existing build")
            return
        sys.exit("[run] Node.js 20.19+ is required to build the frontend once: https://nodejs.org/")
    if not (FRONTEND / "node_modules").exists():
        say("installing frontend packages (first run only)")
        subprocess.run([npm, "ci", "--no-audit", "--no-fund"], cwd=FRONTEND, check=True)
    say("building the frontend")
    subprocess.run([npm, "run", "build"], cwd=FRONTEND, check=True)
    DIST_STAMP.write_text(frontend_hash() + "\n", encoding="utf-8")


def port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(1)
        return probe.connect_ex((host, port)) == 0


def wait_for_api(url: str, process: subprocess.Popen) -> bool:
    deadline = time.monotonic() + STARTUP_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=2) as response:
                if response.status == 200:
                    return True
        except OSError:
            time.sleep(1)
    return False


def stop(processes: list[subprocess.Popen]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def serve(args: argparse.Namespace) -> int:
    url = f"http://{args.host}:{args.port}"
    if port_in_use(args.host, args.port):
        say(f"port {args.port} is already in use; stop the other server or pass --port")
        return 1
    ensure_frontend(args.rebuild)
    python = sys.executable
    say("starting the API (loads the models and datasets, about a minute)")
    api = subprocess.Popen([python, "-m", "src.api", "--host", args.host, "--port", str(args.port)], cwd=ROOT)
    processes = [api]
    try:
        if not wait_for_api(url, api):
            say("the API did not start; see the messages above")
            stop(processes)
            return 1
        if not args.offline:
            say("starting the live GDELT poller: the first poll backfills 7 days of news, so Live appears in the header after a few minutes")
            processes.append(subprocess.Popen([python, "-m", "scripts.live_gdelt"], cwd=ROOT))
        say(f"ready: {url}   offline replays (W1, W3, N1) are available now{'' if args.offline else '; live data follows'}   (Ctrl+C to stop)")
        if not args.no_browser:
            webbrowser.open(url)
        while api.poll() is None:
            time.sleep(1)
        say("the API stopped")
        return api.returncode or 0
    except KeyboardInterrupt:
        say("stopping")
        return 0
    finally:
        stop(processes)


def main() -> int:
    parser = argparse.ArgumentParser(description="Set up and run Ripple: the API, the web app, the offline replays and the live GDELT feed.")
    parser.add_argument("--offline", action="store_true", help="replay the saved windows only; do not poll the live GDELT feed")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--rebuild", action="store_true", help="rebuild the frontend even if it looks current")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser tab")
    args = parser.parse_args()
    if not inside_venv():
        python = ensure_venv()
        try:
            return subprocess.call([str(python), str(ROOT / "run.py"), *sys.argv[1:]], cwd=ROOT)
        except KeyboardInterrupt:
            return 0
    ensure_requirements(Path(sys.executable))
    return serve(args)


if __name__ == "__main__":
    sys.exit(main())
