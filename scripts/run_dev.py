from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from backend.config import settings


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    return subprocess.call([
        sys.executable,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(settings.backend_port),
        "--reload",
        "--reload-dir",
        str(repo_root / "backend"),
    ])


if __name__ == "__main__":
    raise SystemExit(main())
