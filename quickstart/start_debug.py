import argparse
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / ".run_logs"


def http_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 500
    except Exception:
        return False


def port_listening(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def start_process(name: str, args: list[str], stdout_name: str, stderr_name: str) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    stdout = open(LOG_DIR / stdout_name, "ab", buffering=0)
    stderr = open(LOG_DIR / stderr_name, "ab", buffering=0)
    process = subprocess.Popen(
        [sys.executable, *args],
        cwd=PROJECT_ROOT,
        stdout=stdout,
        stderr=stderr,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    print(f"{name} started. PID={process.pid}")


def wait_http(name: str, url: str, timeout_seconds: int) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if http_ok(url):
            print(f"{name} is ready: {url}")
            return True
        time.sleep(1)
    print(f"{name} did not respond within {timeout_seconds} seconds: {url}")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Start HuhuSleep API and Streamlit debug UI.")
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--streamlit-port", type=int, default=8501)
    args = parser.parse_args()

    api_url = f"http://127.0.0.1:{args.api_port}"
    frontend_url = f"http://127.0.0.1:{args.streamlit_port}"

    print(f"Project: {PROJECT_ROOT}")

    if http_ok(f"{api_url}/docs"):
        print(f"API is already ready: {api_url}")
    elif port_listening(args.api_port):
        print(f"Port {args.api_port} is already in use. API may be running at {api_url}")
    else:
        start_process(
            "API",
            ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(args.api_port)],
            "api.out.log",
            "api.err.log",
        )

    if http_ok(frontend_url):
        print(f"Streamlit is already ready: {frontend_url}")
    elif port_listening(args.streamlit_port):
        print(f"Port {args.streamlit_port} is already in use. Streamlit may be running at {frontend_url}")
    else:
        start_process(
            "Streamlit",
            [
                "-m",
                "streamlit",
                "run",
                "streamlit_app.py",
                "--server.address",
                "127.0.0.1",
                "--server.port",
                str(args.streamlit_port),
                "--server.headless",
                "true",
            ],
            "streamlit.out.log",
            "streamlit.err.log",
        )

    api_ready = wait_http("API", f"{api_url}/docs", 45)
    frontend_ready = wait_http("Streamlit", frontend_url, 60)

    if frontend_ready:
        webbrowser.open(frontend_url)
    elif api_ready:
        webbrowser.open(f"{api_url}/docs")

    print()
    print(f"Frontend: {frontend_url}")
    print(f"Swagger:  {api_url}/docs")
    print(f"Logs:     {LOG_DIR}")
    return 0 if frontend_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())

