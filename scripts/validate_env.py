from __future__ import annotations

from backend.config import settings


def main() -> None:
    print("FinPilot environment summary")
    print(f"AI provider: {settings.ai_provider}")
    print(f"Alpaca mode: {settings.alpaca_mode}")
    print(f"Available data sources: {', '.join(settings.available_data_sources())}")
    print(f"Database: {settings.db_path}")


if __name__ == "__main__":
    main()
