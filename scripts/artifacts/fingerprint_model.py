"""Print a deterministic SHA-256 fingerprint for a local model artifact folder."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from model_server.services.artifacts import fingerprint_asdict, fingerprint_directory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "model_dir",
        type=Path,
        nargs="?",
        default=Path("artifacts/classifier/first-distilbert-freeze4/model"),
        help="Path to the saved Hugging Face model directory.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(json.dumps(fingerprint_asdict(fingerprint_directory(args.model_dir)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
