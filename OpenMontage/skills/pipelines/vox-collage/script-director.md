# Vox Collage Script Director

Write narration in short timed beats. Each section needs a stable `section_id`, start/end timing, narration text, visual intent and title text separated from text that belongs inside the image. For every factual, time, location, quantity or warning statement, also create a claim in `narration_visual_contract.json` with `must_show`, precision, deterministic representation mode and required visual tokens. The claim's target interval must match the narration section; do not leave factual content only in an unbound paragraph. Use `tts_selector` only after the voice decision is approved. Avoid asking image models to render the final title when `title_policy` is `overlay`.

Stop for human approval when the script and beat rhythm are complete.
