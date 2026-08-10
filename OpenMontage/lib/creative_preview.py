"""Deterministic, provenance-labeled creative pilot previews.

These previews can use either local procedural backgrounds or a real generated
image supplied by a provider. They are not a replacement for a final provider
render, but they exercise the creative contract: a style-specific visual
language, title hierarchy, motion beats, audio bed, and explicit source
labeling.
"""

from __future__ import annotations

import json
import glob
import os
import subprocess
from pathlib import Path
from typing import Any


_FONT_CANDIDATES = [
    os.environ.get("OPENMONTAGE_CJK_FONT", ""),
    *glob.glob("/data/a9017/cache-rollback-*/camoufox/browsers/official/*/fonts/linux/NotoSansSC-Regular.otf"),
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
]
FONT = next((candidate for candidate in _FONT_CANDIDATES if candidate and Path(candidate).is_file()), _FONT_CANDIDATES[-1])


STYLE_TOKENS: dict[str, dict[str, str]] = {
    "vox-newsprint-editorial": {
        "background": "efe8d8", "ink": "171a1f", "accent": "c83d3d", "support": "2d5f8d",
        "language": "newsprint halftone, headline cut-ins, archive-caption pairing",
    },
    "vox-paper-collage": {
        "background": "d8c4a7", "ink": "241f1a", "accent": "d64b35", "support": "365f57",
        "language": "paper grain, layered cutouts, tactile wipes",
    },
    "clean-professional": {
        "background": "0d1725", "ink": "f4f7fb", "accent": "4ed2d0", "support": "5888ff",
        "language": "restrained grid, chart-led reveals, measured easing",
    },
    "minimalist-diagram": {
        "background": "f7f9fc", "ink": "182437", "accent": "2563eb", "support": "8bb8ff",
        "language": "diagram-first composition, whitespace, single accent",
    },
    "anime-ghibli": {
        "background": "b9d8c6", "ink": "18332c", "accent": "f28d68", "support": "f6d78b",
        "language": "breathing holds, soft illustrated shapes, character beat timing",
    },
    "premium-minimalist": {
        "background": "10131b", "ink": "f7f1e6", "accent": "c7a66a", "support": "66758c",
        "language": "luxury negative space, tonal drift, restrained gold linework",
    },
}


def _escape_text(value: str) -> str:
    # drawtext uses ':' and '\\' as separators.  Keep copy simple and avoid
    # shell interpolation because the command is passed as argv.
    return value.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _drawtext(text: str, *, x: str, y: str, fontsize: int, color: str, border: int = 0) -> str:
    fields = [
        f"fontfile={FONT}",
        f"text='{_escape_text(text)}'",
        f"x={x}", f"y={y}", f"fontsize={fontsize}",
        f"fontcolor=0x{color}", "line_spacing=8",
    ]
    if border:
        fields.extend([f"borderw={border}", "bordercolor=0x000000@0.45"])
    return "drawtext=" + ":".join(fields)


def _box(x: str, y: str, w: str, h: str, color: str, opacity: str = "1") -> str:
    # drawbox exposes the input dimensions as iw/ih (w/h are the box's own
    # dimensions), so normalize the compact layout expressions here.
    expr = lambda value: value.replace("w", "iw").replace("h", "ih")
    return f"drawbox=x={expr(x)}:y={expr(y)}:w={expr(w)}:h={expr(h)}:color=0x{color}@{opacity}:t=fill"


def _style_filter(
    style_id: str,
    family: str,
    width: int,
    height: int,
    title: str,
    subtitle: str,
    *,
    image_backed: bool = False,
) -> tuple[str, str]:
    token = STYLE_TOKENS.get(style_id, STYLE_TOKENS["clean-professional"])
    bg, ink, accent, support = token["background"], token["ink"], token["accent"], token["support"]
    # Keep long CJK titles inside the 9:16 safe area.  Earlier pilots used a
    # width//9 size and clipped the final characters on vertical output.
    title_size = max(34, min(78, width // 13))
    small_size = max(18, min(32, width // 26))
    title_color = ink
    filters: list[str] = []

    if style_id in {"vox-newsprint-editorial", "vox-paper-collage"}:
        filters.extend([
            _box("w*0.06+sin(t*0.8)*18", "h*0.10", "w*0.88", "h*0.02", ink, "0.9"),
            _box("w*0.07+sin(t*0.45)*35", "h*0.25", "w*0.42", "h*0.44", support, "0.92"),
            _box("w*0.51+cos(t*0.55)*28", "h*0.31", "w*0.38", "h*0.22", accent, "0.94"),
            _box("w*0.56+sin(t*0.38)*22", "h*0.55", "w*0.29", "h*0.12", ink, "0.94"),
            "noise=alls=7:allf=t+u",
            _box("w*0.06", "h*0.70", "w*0.88", "h*0.20", bg, "0.86"),
            _drawtext(title, x="w*0.09", y="h*0.74", fontsize=title_size, color=title_color, border=2),
            _drawtext(subtitle, x="w*0.09", y="h*0.87", fontsize=small_size, color=ink),
        ])
    elif style_id in {"clean-professional", "premium-minimalist"}:
        filters.extend([
            _box("0", "0", "w", "h*0.012", accent, "0.95"),
            _box("w*0.08", "h*0.21+sin(t*0.4)*12", "w*0.84", "h*0.01", support, "0.85"),
            _box("w*0.10", "h*0.42", "w*0.10", "h*0.24+sin(t*0.5)*h*0.04", accent, "0.85"),
            _box("w*0.24", "h*0.50", "w*0.10", "h*0.16+sin(t*0.5+1)*h*0.06", support, "0.85"),
            _box("w*0.38", "h*0.35", "w*0.10", "h*0.31+sin(t*0.5+2)*h*0.05", accent, "0.85"),
            _box("w*0.52", "h*0.28", "w*0.10", "h*0.38+sin(t*0.5+3)*h*0.04", support, "0.85"),
            _drawtext(title, x="w*0.10", y="h*0.70", fontsize=title_size, color=ink),
            _drawtext(subtitle, x="w*0.10", y="h*0.84", fontsize=small_size, color=ink),
        ])
    elif style_id == "minimalist-diagram":
        filters.extend([
            _box("w*0.12", "h*0.20", "w*0.76", "h*0.008", support, "0.9"),
            _box("w*0.22+sin(t*0.6)*20", "h*0.37", "w*0.12", "w*0.12", accent, "0.95"),
            _box("w*0.66+cos(t*0.6)*20", "h*0.52", "w*0.12", "w*0.12", support, "0.95"),
            _box("w*0.34", "h*0.48", "w*0.32", "h*0.008", ink, "0.8"),
            _drawtext("01  WEATHER SYSTEM", x="w*0.12", y="h*0.12", fontsize=small_size, color=ink),
            _drawtext(title, x="w*0.12", y="h*0.72", fontsize=title_size, color=ink),
            _drawtext(subtitle, x="w*0.12", y="h*0.86", fontsize=small_size, color=ink),
        ])
    elif style_id == "anime-ghibli":
        filters.extend([
            _box("w*0.12+sin(t*0.35)*30", "h*0.18+cos(t*0.4)*14", "w*0.24", "w*0.24", support, "0.9"),
            _box("w*0.60+cos(t*0.3)*24", "h*0.28+sin(t*0.45)*16", "w*0.18", "w*0.18", accent, "0.85"),
            _box("w*0.08", "h*0.61", "w*0.84", "h*0.018", ink, "0.55"),
            _drawtext("A WEATHER STORY", x="w*0.11", y="h*0.12", fontsize=small_size, color=ink),
            _drawtext(title, x="w*0.11", y="h*0.70", fontsize=title_size, color=title_color, border=2),
            _drawtext(subtitle, x="w*0.11", y="h*0.85", fontsize=small_size, color=ink),
        ])
    else:
        filters.extend([
            _box("0", "0", "w", "h", bg, "1"),
            _drawtext(title, x="w*0.10", y="h*0.70", fontsize=title_size, color=ink),
            _drawtext(subtitle, x="w*0.10", y="h*0.84", fontsize=small_size, color=ink),
        ])

    marker = (
        "ILLUSTRATIVE RECONSTRUCTION · NOT ARCHIVAL FOOTAGE"
        if family == "documentary-archive"
        else ("GENERATED IMAGE PILOT · NOT FINAL DELIVERY" if image_backed else "PROCEDURAL CREATIVE PILOT · NOT FINAL DELIVERY")
    )
    filters.append(_drawtext(marker, x="w*0.07", y="h*0.95", fontsize=max(14, small_size // 2), color=ink))
    return ",".join([f"format=yuv420p", *filters]), token["language"]


def render_creative_preview(
    scenario: dict[str, Any],
    output_path: str | Path,
    *,
    duration_seconds: float | None = None,
) -> dict[str, Any]:
    """Render a local creative sample and return its provenance manifest."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    delivery = scenario["delivery"]
    if duration_seconds is not None:
        # Short previews are useful for human comparison.  The representative
        # pilot validator still enforces its separate 10–15 second gate.
        duration = max(0.5, float(duration_seconds))
    else:
        duration = min(max(float(delivery.get("duration_seconds", 10.2)), 10.2), 15.0)
    title = scenario.get("sample_title") or "第13号台风 白海豚"
    subtitle = scenario.get("sample_subtitle") or "8月10日风雨增强 · 8月12日全省降温"
    filter_graph, motion_language = _style_filter(
        scenario["primary_style"], scenario.get("style_family", ""),
        int(delivery["width"]), int(delivery["height"]), title, subtitle,
        image_backed=bool(scenario.get("image_path")),
    )
    image_path = scenario.get("image_path")
    if image_path:
        video_input = ["-framerate", str(delivery["fps"]), "-loop", "1", "-i", str(image_path)]
        fit_filter = (
            f"scale={int(delivery['width'])}:{int(delivery['height'])}:force_original_aspect_ratio=increase,"
            f"crop={int(delivery['width'])}:{int(delivery['height'])}"
        )
        filter_graph = f"{fit_filter},{filter_graph}"
    else:
        video_input = [
            "-f", "lavfi", "-i",
            f"color=c=0x{STYLE_TOKENS.get(scenario['primary_style'], STYLE_TOKENS['clean-professional'])['background']}:s={delivery['width']}x{delivery['height']}:r={delivery['fps']}",
        ]
    cmd = [
        "ffmpeg", "-y", *video_input,
        "-f", "lavfi", "-i", f"sine=frequency=220:sample_rate=48000:duration={duration}",
        "-t", str(duration), "-vf", filter_graph,
        "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest", str(output),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    family = scenario.get("style_family", "")
    provenance = {
        "version": "1.0",
        "sample_kind": "creative_dynamic_local",
        "style_id": scenario["primary_style"],
        "style_package_version": scenario.get("style_package_version"),
        "style_language": motion_language,
        "title_policy": "overlay",
        "asset_sources": ([
            {
                "id": "background",
                "kind": "generated",
                "source": scenario.get("image_provider", "image_api"),
                "model": scenario.get("image_model"),
                "path": str(image_path),
                "prompt": scenario.get("image_prompt"),
            }
        ] if image_path else [{"id": "background", "kind": "procedural", "source": "ffmpeg:color"}]) + [
            {"id": "graphic_layers", "kind": "procedural", "source": "ffmpeg:drawbox"},
            {"id": "audio_bed", "kind": "procedural", "source": "ffmpeg:sine"},
        ],
        "documentary_label": "illustrative_reconstruction" if family == "documentary-archive" else None,
        "final_delivery": False,
        "review_required": True,
    }
    manifest_path = output.with_suffix(".provenance.json")
    manifest_path.write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"path": str(output), "provenance_path": str(manifest_path), "provenance": provenance}
