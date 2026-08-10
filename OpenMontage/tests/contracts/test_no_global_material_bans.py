from __future__ import annotations

from pathlib import Path
import re


PRODUCTION_ROOTS = ("lib", "styles", "pipeline_defs", "skills", "schemas")
FORBIDDEN_GLOBAL_RULES = (
    re.compile(r"(?:cinematic|电影).{0,80}(?:cannot|must\s+not|禁止|不得).{0,80}(?:collage|拼贴)", re.I | re.S),
    re.compile(r"(?:documentary|纪录片).{0,80}(?:never|must\s+not|禁止|不得).{0,80}(?:ai|generated|生成|重建)", re.I | re.S),
)


def test_material_choices_are_style_and_provenance_scoped():
    violations: list[str] = []
    root = Path(__file__).parents[2]
    for relative_root in PRODUCTION_ROOTS:
        for path in (root / relative_root).rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".yaml", ".yml", ".json", ".md"}:
                continue
            text = path.read_text(encoding="utf-8")
            if any(pattern.search(text) for pattern in FORBIDDEN_GLOBAL_RULES):
                violations.append(str(path.relative_to(root)))
    assert not violations, f"global cinematic/documentary material bans found: {violations}"
