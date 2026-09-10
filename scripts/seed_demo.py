#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialise the synthetic TrustSplit demo ledger.")
    parser.add_argument(
        "--database",
        type=Path,
        default=ROOT / "backend" / "trustsplit.db",
        help="SQLite database path (default: backend/trustsplit.db)",
    )
    args = parser.parse_args()
    config = Config(str(ROOT / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{args.database.resolve()}")
    command.upgrade(config, "head")
    print(f"Synthetic demo ledger ready: {args.database}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
