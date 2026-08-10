# Vox Collage Asset Director

Run preflight and select concrete tools through selectors or an explicitly approved provider. First generate one keyframe and one short motion sample. Inspect them at the target aspect ratio before batch generation. Use `mimo_tts` for approved narration and save every output under `projects/<id>/assets/`.

For asynchronous video, persist `request_id`, provider, model and status in checkpoint partial progress after each shot. A failed shot may retry within the approved limit; never resubmit a completed request ID. All assets must pass image decoding or ffprobe before the asset gate.
