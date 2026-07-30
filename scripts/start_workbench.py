"""One-command launcher for CateMate Workbench (FastAPI + Express + Vite).

Usage:
    python scripts/start_workbench.py          # Start all three services
    python scripts/start_workbench.py --api     # FastAPI only
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKBENCH_DIR = PROJECT_ROOT / "CateMate-Workbench"
API_DIR = PROJECT_ROOT / "api"

PYTHON = sys.executable
DEFAULT_FASTAPI_PORT = 8100
FALLBACK_FASTAPI_PORT = 8101
EXPRESS_PORT = 3001
VITE_PORT = 5173


def _port_is_free(port: int, host: str = "127.0.0.1") -> bool:
    """Return True if we can bind the port (likely free for local listen)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def _resolve_fastapi_port() -> int:
    """Prefer 8100; if occupied (including Windows ghost LISTEN), fall back to 8101."""
    if _port_is_free(DEFAULT_FASTAPI_PORT):
        return DEFAULT_FASTAPI_PORT
    if _port_is_free(FALLBACK_FASTAPI_PORT):
        print(
            f"[CateMate] Port {DEFAULT_FASTAPI_PORT} is busy; "
            f"using FastAPI on {FALLBACK_FASTAPI_PORT} instead."
        )
        return FALLBACK_FASTAPI_PORT
    raise RuntimeError(
        f"Neither FastAPI port {DEFAULT_FASTAPI_PORT} nor {FALLBACK_FASTAPI_PORT} is available."
    )


def _pnpm_cmd() -> list[str]:
    """Return a cross-platform command prefix to invoke pnpm."""
    if sys.platform == "win32":
        # .cmd shims cannot be launched via CreateProcess without cmd.exe.
        if shutil.which("corepack") or shutil.which("corepack.cmd"):
            return ["cmd", "/c", "corepack", "pnpm"]
        pnpm = shutil.which("pnpm.cmd") or shutil.which("pnpm")
        if pnpm:
            return ["cmd", "/c", pnpm]
        raise RuntimeError("Neither corepack nor pnpm found on PATH.")
    if shutil.which("pnpm"):
        return ["pnpm"]
    if shutil.which("corepack"):
        return ["corepack", "pnpm"]
    raise RuntimeError("Neither pnpm nor corepack found on PATH.")


def start_fastapi(port: int):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    return subprocess.Popen(
        [
            PYTHON,
            "-m",
            "uvicorn",
            "catemate_api:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(port),
            "--reload",
        ],
        cwd=str(API_DIR),
        env=env,
    )


def start_express(fastapi_port: int):
    env = os.environ.copy()
    env["NODE_ENV"] = "development"
    env["PORT"] = str(EXPRESS_PORT)
    env["PYTHON_API_URL"] = f"http://127.0.0.1:{fastapi_port}"
    return subprocess.Popen(
        [*_pnpm_cmd(), "run", "dev"],
        cwd=str(WORKBENCH_DIR / "artifacts" / "api-server"),
        env=env,
    )


def start_vite():
    env = os.environ.copy()
    env["NODE_ENV"] = "development"
    env["PORT"] = str(VITE_PORT)
    env["BASE_PATH"] = "/"
    return subprocess.Popen(
        [*_pnpm_cmd(), "run", "dev"],
        cwd=str(WORKBENCH_DIR / "artifacts" / "catemate"),
        env=env,
    )


def main():
    parser = argparse.ArgumentParser(description="Start CateMate Workbench")
    parser.add_argument("--api", action="store_true", help="Start FastAPI only")
    args = parser.parse_args()

    fastapi_port = _resolve_fastapi_port()
    processes: list[subprocess.Popen] = []

    def cleanup(signum=None, frame=None):
        for p in processes:
            try:
                p.terminate()
            except Exception:
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, cleanup)

    print(f"[CateMate] Starting FastAPI bridge on port {fastapi_port}...")
    processes.append(start_fastapi(fastapi_port))

    if not args.api:
        time.sleep(2)
        print(f"[CateMate] Starting Express proxy on port {EXPRESS_PORT}...")
        print(f"[CateMate] PYTHON_API_URL=http://127.0.0.1:{fastapi_port}")
        processes.append(start_express(fastapi_port))
        time.sleep(1)
        print(f"[CateMate] Starting Vite dev server on port {VITE_PORT}...")
        processes.append(start_vite())
        print(f"\n[CateMate] Workbench ready:")
        print(f"  Frontend:   http://localhost:{VITE_PORT}")
        print(f"  Express:    http://localhost:{EXPRESS_PORT}/api")
        print(f"  FastAPI:    http://localhost:{fastapi_port}/docs")
    else:
        print(f"\n[CateMate] FastAPI only:")
        print(f"  API:        http://localhost:{fastapi_port}/api")
        print(f"  Swagger UI: http://localhost:{fastapi_port}/docs")

    print("\nPress Ctrl+C to stop all services.\n")

    try:
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
