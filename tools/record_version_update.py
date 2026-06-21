from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from latka_jazn.memory.version_update_recorder import VersionUpdateRecorder


def parse_list(raw: str) -> list[str]:
    if not raw:
        return []
    return [x.strip() for x in raw.split(";") if x.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Dopisz aktualizację wersji do dziennika Łatki i warstw pamięci.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--version", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--modules", default="")
    parser.add_argument("--experience", required=True)
    parser.add_argument("--memories", default="")
    parser.add_argument("--emotions", default="")
    parser.add_argument("--truth-boundary", required=True)
    parser.add_argument("--tests", default="")
    args = parser.parse_args()

    rec = VersionUpdateRecorder(root=Path(args.root))
    try:
        result = rec.record_version_update(
            version=args.version,
            title=args.title,
            summary=args.summary,
            modules=parse_list(args.modules),
            experience=args.experience,
            memories_to_preserve=parse_list(args.memories),
            emotions=parse_list(args.emotions),
            truth_boundary=args.truth_boundary,
            tests=parse_list(args.tests),
            source="tools/record_version_update.py",
        )
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    finally:
        rec.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
