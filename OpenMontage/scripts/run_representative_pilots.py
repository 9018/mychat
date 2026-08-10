#!/usr/bin/env python3
"""Run the seven-family offline pilot matrix and write playable previews."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", type=Path, default=ROOT / "tests/eval/golden_scenarios")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/representative-pilots")
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Optional Backlot projects root; materializes each pilot as pilot-<scenario>",
    )
    args = parser.parse_args(argv)
    from lib.representative_pilots import materialize_pilot_projects, run_pilot_matrix

    result = run_pilot_matrix(args.scenarios, args.output_dir)
    if args.project_root:
        result["materialized_projects"] = materialize_pilot_projects(args.output_dir, args.project_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
