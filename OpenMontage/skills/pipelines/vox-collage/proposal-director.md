# Vox Collage Proposal Director

Produce `proposal_packet` and append `decision_log` entries for provider/model, render runtime, composition mode, voice, music and title policy. Present the costed style sample and 3–5 second motion sample before batch generation. When Remotion and HyperFrames are both available, present both; when HyperFrames is unavailable, record it as unavailable and explain the FFmpeg/Remotion path.

The proposal must specify aspect ratio, duration, `motion_required`, output path, title policy and whether music is absent, supplied or generated. Stop for human approval.
# Runtime selection is a conversation decision, not a default.

Present both composition runtimes before approval: `render_runtime=remotion`
for image/title/motion composition, or `render_runtime=hyperframes` when its
runtime is available and appropriate. If HyperFrames is unavailable, surface
that constraint explicitly and record a `render_runtime_selection` decision;
never silently switch after approval. FFmpeg is an explicit third option for
pure video cuts only.
