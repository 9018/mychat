# Style package authoring

OpenMontage style packages are versioned contracts, not prompt snippets. A
package must explain what it looks like, when it is appropriate, how it moves,
what sources it accepts, and how it is verified.

## Required profile fields

Each package lives under `styles/packages/<style-id>/profile.yaml` and must
declare:

- `id`, `version`, `family`, `maturity`;
- `runtimes`, `renderers`, `providers`;
- `asset_strategies`, including whether assets are generated, user-provided,
  procedural, recorded, or mixed;
- `composition_modes`, `title_policy`, `sample_gate`;
- prompt/director documentation and anti-patterns.

The registry validates these fields and snapshots the exact package into the
project before generation. Updating a package version never silently changes
an existing project.

## Adding a new style

1. Add the profile and its director/prompt documentation.
2. Add a compatibility test for every intended pipeline, aspect ratio, asset
   strategy and runtime.
3. Add at least two unique hero candidates when the package is used in `hero`
   mode; the bakeoff must record seed/prompt and preview hashes.
4. Add a representative pilot scenario and a family-specific QA rubric.
5. Run the capability matrix and all style-director contract tests.

No style is globally banned because it is cinematic, documentary, collage or
AI-assisted. The package and project treatment must instead make provenance,
adaptation, labeling and approval explicit.
