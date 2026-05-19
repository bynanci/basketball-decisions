# Drill Template Standard (S7)

This standard defines the human-authored drill catalog structure used by deterministic recommendations, practice plans, and coach reports.

## Required identity/stability

- `drill_id` is stable and must not be regenerated.
- `title`, `situation`, and `description` are required.
- Catalog entries are authored and reviewed by humans; no LLM generation is used.

## Practical coaching fields

Each drill should include practical operational text:

- `purpose`: what decision or behavior the drill trains.
- `court_area`: where the drill primarily operates.
- `constraints`: rules that force the target read.
- `scoring`: simple success accounting for reps.
- `common_mistakes`: frequent failure patterns to watch.
- `progression`: ways to increase complexity.
- `regression`: ways to simplify without changing intent.

## Safety/product constraints

- Do not add medical or injury advice.
- Do not claim real-world identity inference from aliases.
- Keep recommendation logic deterministic and compatibility-safe.

## UI/display guidance

`/drills` should present practical fields on recommendation cards and catalog cards when present. Practice plans and reports should preserve these fields for coach-facing exports.
