#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.ledger.repository import ExposureRepository  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialise the synthetic TrustSplit demo ledger.")
    parser.add_argument(
        "--database",
        type=Path,
        default=ROOT / "backend" / "trustsplit.db",
        help="SQLite database path (default: backend/trustsplit.db)",
    )
    args = parser.parse_args()
    repository = ExposureRepository(f"sqlite:///{args.database.resolve()}")
    repository.initialize()
    print(f"Synthetic demo ledger ready: {args.database}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
