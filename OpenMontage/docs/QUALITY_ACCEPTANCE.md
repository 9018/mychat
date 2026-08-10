# Quality acceptance

Acceptance is evidence-backed and occurs at four levels.

## 1. Contract acceptance

- the locked `creative_treatment.json` has a stable hash;
- `scene_plan.json` carries that hash;
- `motion_plan.json` carries the same hash and resolves every asset source,
  movement, transition, title policy and safe zone;
- assets, edit and compose checkpoints reject missing or mismatched treatment
  bindings.

## 2. Technical acceptance

The render must be playable, have the promised dimensions/fps, contain the
expected audio policy, and have no missing media. Offline representative pilots
produce short local creative previews for all seven supported production
families, plus review frames and a provenance manifest. They prove the
style/motion/title contract can be opened and inspected but do not replace
human creative review or provider-backed final delivery.

## 3. Creative acceptance

`lib.family_qa.build_qa_report` evaluates the primary family plus declared
supporting families. A missing preview/evidence file is `blocked`; a low rubric
score is `fail`; only real evidence with all checks above threshold can pass.
Production callers must enable score provenance: every rubric score must point
to an evidence file that is present in the report. Local pilot samples are
explicitly marked `creative_status: awaiting_human_review` and cannot satisfy
the final approval gate by themselves.
This is why a cinematic collage can pass when both rubrics are satisfied, and a
documentary reconstruction can pass only when context, facts and labeling are
shown.

## 4. Approval and provenance

Hero bakeoffs require multiple unique candidates and a recorded approval with
preview SHA-256. Any generated, reconstructed or user-supplied source remains
labeled in the artifact chain. Runtime/provider fallbacks require explicit
re-resolution and re-approval; there is no silent fallback.

## Local verification

The pilot matrix can also be materialized into Backlot projects so reviewers
can inspect the same preview, frames, provenance and pending gate in the UI:

```bash
python scripts/run_representative_pilots.py \
  --output-dir /data/a9017/ai-v2/creative-pilot-20260810 \
  --project-root /path/to/OpenMontage/projects
```

```bash
pytest -q tests/contracts/test_capability_matrix.py \
  tests/contracts/test_all_pipeline_style_director.py \
  tests/lib/test_creative_treatment.py \
  tests/lib/test_motion_plan.py \
  tests/lib/test_runtime_resolver.py \
  tests/lib/test_style_bakeoff.py \
  tests/qa/test_family_qa.py \
  tests/integration/test_representative_pilots.py \
  tests/integration/test_single_entry_plan.py
```

The full repository suite also includes optional Playwright and provider
adapters. Their environment failures must be reported separately from the
core OpenMontage contract result.
