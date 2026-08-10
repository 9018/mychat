import subprocess

from tools.video.video_compose import VideoCompose


def test_short_external_audio_does_not_truncate_video(tmp_path):
    video = tmp_path / "video.mp4"
    audio = tmp_path / "audio.wav"
    output = tmp_path / "out.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=320x568:r=30",
        "-t", "3", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video),
    ], check=True, capture_output=True)
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000",
        "-t", "0.5", str(audio),
    ], check=True, capture_output=True)
    result = VideoCompose().execute({
        "operation": "compose",
        "edit_decisions": {"cuts": [{"source": str(video), "in_seconds": 0, "out_seconds": 3}]},
        "audio_path": str(audio), "output_path": str(output),
    })
    assert result.success
    probe = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(output)
    ], text=True)
    assert abs(float(probe.strip()) - 3.0) < 0.2
