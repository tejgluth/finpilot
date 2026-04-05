from __future__ import annotations

from backend.config import settings


def main() -> None:
    try:
        print(settings.audit_log_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print("")


if __name__ == "__main__":
    main()
