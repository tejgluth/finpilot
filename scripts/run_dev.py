from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from backend.config import settings


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    repo_root_str = str(repo_root)
    env["PYTHONPATH"] = (
        repo_root_str if not existing_pythonpath else f"{repo_root_str}{os.pathsep}{existing_pythonpath}"
    )
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--app-dir",
            repo_root_str,
            "--host",
            "0.0.0.0",
            "--port",
            str(settings.backend_port),
            "--reload",
            "--reload-dir",
            str(repo_root / "backend"),
        ],
        cwd=repo_root,
        env=env,
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
