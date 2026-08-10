# Vox Collage Scene Director

Transform the approved script and narration/visual contract into schema-valid `scene_plan`. Every scene declares a time range, shot description, asset source, target aspect ratio, motion intent and `title_policy`, and binds one or more `claim_ids`. Set `must_show`, `fact_layer_policy` and `semantic_risk` for factual scenes; exact claims must use deterministic overlays, diagrams, source media or verified actions. Add `text_in_image`, `safe_zones` and `title_max_width_ratio` whenever text is involved. Run `validate_reference_aspect` before approving image-to-video references.

One beat may contain one or two shots, but each motion-required beat must request a real video asset. Export to `beats.json` only after the canonical scene plan is approved.
