#!/usr/bin/env python3
"""Run the OpenMontage single-entry plan through offline technical QA."""

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
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--pipeline", default="cinematic")
    parser.add_argument("--brief-json", required=True, type=Path)
    parser.add_argument("--project-root", type=Path, default=Path("projects"))
    parser.add_argument("--style", dest="primary_style")
    parser.add_argument("--runtime", action="append", dest="runtimes", default=["ffmpeg"])
    parser.add_argument("--provider", action="append", dest="providers", default=[])
    args = parser.parse_args(argv)
    brief = json.loads(args.brief_json.read_text(encoding="utf-8"))
    from lib.single_entry_run import run_single_entry_offline

    result = run_single_entry_offline(
        project_id=args.project_id,
        title=args.title,
        pipeline=args.pipeline,
        brief=brief,
        project_root=args.project_root,
        available_runtimes=args.runtimes,
        available_providers=args.providers,
        primary_style=args.primary_style,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
