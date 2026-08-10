# Vox Collage Compose Director

Before rendering, create the title static-frame preview and obtain the visual check required by the project. Route only through the `render_runtime` recorded in the approved decision (`remotion`, `hyperframes`, or explicit `ffmpeg`). HyperFrames must be considered and its availability constraint surfaced; never silently replace the approved runtime. Use FFmpeg stream copy whenever all clip stream signatures match; otherwise record the reason for re-encoding. Write `render_report` with output path, ffprobe fields, segment policy, codec, duration and warnings, then perform the reviewer pass.

Motion-required output must remain motion-led. Do not silently substitute an animatic.
