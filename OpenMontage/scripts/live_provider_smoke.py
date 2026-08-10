"""Opt-in live smoke checks for the unified OpenMontage gateway providers."""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from lib.workspace_config import load_workspace_config
from tools.graphics.self_hosted_gateway_image import SelfHostedGatewayImage
from tools.video.self_hosted_gateway_video import SelfHostedGatewayVideo
from tools.audio.mimo_tts import MiMoTTS


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", default="A paper collage bird flying over a city")
    parser.add_argument("--image", help="optional local reference image")
    parser.add_argument("--output-dir", default="live-smoke-output")
    parser.add_argument("--confirm-live", action="store_true", help="explicitly authorize real API calls")
    parser.add_argument("--skip-tts", action="store_true")
    args = parser.parse_args()
    if not args.confirm_live:
        raise SystemExit("refusing live calls without --confirm-live")
    cfg = load_workspace_config(Path(__file__).resolve().parents[1])
    if not cfg.gateway_key or not cfg.gateway_base:
        raise SystemExit("gateway key/base missing; refusing live smoke")
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    image = SelfHostedGatewayImage().execute({"prompt": args.prompt, "output_path": str(out / "image.png")})
    if not image.success:
        print(json.dumps({"image": image.error}, ensure_ascii=False))
        return 1
    video_inputs = {"prompt": args.prompt, "duration": 4, "output_path": str(out / "video.mp4"), "timeout_seconds": 900}
    if args.image:
        video_inputs["image_path"] = args.image
    video = SelfHostedGatewayVideo().execute(video_inputs)
    tts = None
    if not args.skip_tts:
        tts = MiMoTTS().execute({"text": "这是 OpenMontage 的四秒闭环冒烟测试。", "output_path": str(out / "tts.mp3")})
    print(json.dumps({"image": image.data, "video": video.data, "video_error": video.error, "tts": tts.data if tts else None, "tts_error": tts.error if tts else None}, ensure_ascii=False, indent=2))
    return 0 if video.success and (tts is None or tts.success) else 1


if __name__ == "__main__":
    raise SystemExit(main())
