#!/usr/bin/env python3
"""Create an offline OpenMontage single-entry project plan.

This command only discovers styles, locks a creative treatment, and writes
canonical project artifacts. It does not call any external provider.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--pipeline", default="cinematic")
    parser.add_argument("--brief-json", required=True, type=Path)
    parser.add_argument("--project-root", type=Path, default=Path("projects"))
    parser.add_argument("--style", dest="primary_style")
    parser.add_argument("--runtime", action="append", dest="runtimes", default=["ffmpeg"])
    parser.add_argument("--provider", action="append", dest="providers", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        brief = json.loads(args.brief_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"无法读取 brief JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(brief, dict):
        print("brief JSON 必须是对象", file=sys.stderr)
        return 2

    # Imports happen after argument parsing so --help remains usable in a
    # minimal environment and the command follows the repository's package
    # layout when executed from OpenMontage/.
    from lib.single_entry import create_single_entry_plan

    result = create_single_entry_plan(
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
