# Design Studio v1 Runbook

## Scope

Design Studio v1 supports product design exploration inside the existing Council conversation flow:

- create web, iOS, or mixed Design Studio sessions
- attach relevant source artifacts
- generate candidate directions
- compare and rank variants
- approve one direction for refinement
- export an implementation-oriented `DESIGN.md` handoff

## Observability

Backend streaming runs persist `design_studio_observability` metadata on Design Studio assistant turns. Use it before reading raw model output.

Key fields:

- `design_target`: normalized target (`web_app`, `ios_app`, or `mixed`)
- `studio_goal`: normalized workflow goal
- `approved_direction_id`: approved direction when one exists
- `candidate_count`: number of viable Stage 1 directions
- `comparison_status`: `pending` or `complete`
- `ranked_direction_count`: number of ranked variants from Stage 2
- `selected_direction_id`: current winning direction
- `handoff_status`: `pending` or `ready`
- `partial_failure_count`: Stage 1 model failures kept in the turn
- `degraded_model_selection`: whether attached artifacts forced a degraded model-selection path
- `requested_model_count`, `effective_model_count`, `responded_model_count`
- `timing`: stage and total durations

Streaming logs also emit `[design-studio]` lines for Stage 1, Stage 2, and Stage 3 with candidate counts, comparison status, handoff status, partial failures, degraded selection, selected direction, and duration.

## Triage

Blank or empty workspace:

- Check `candidate_count`.
- If it is `0`, inspect `partial_failure_count` and `stage1_errors`.
- If model selection was degraded, inspect `degraded_model_selection` and `model_selection.warnings`.

Comparison missing:

- Check `comparison_status`.
- `pending` with multiple candidates means Stage 2 did not complete or was skipped.
- Check `ranked_direction_count` before reading the Stage 2 raw ranking text.

Handoff missing:

- Check `handoff_status`.
- `pending` means Stage 3 did not produce a parseable final handoff yet.
- Confirm the session reached a handoff/refinement goal and that the chairman response used the expected section headings.

Approval/refinement issues:

- Check `approved_direction_id` in both `session_config` and `design_studio_observability`.
- The approve endpoint only accepts known candidate IDs when candidate metadata exists.

## Guardrails

- Design Studio metadata is only attached to `design_studio` sessions.
- Visual critique surfaces are enabled for Design Studio only when configured goals and artifact findings justify them.
- `DESIGN.md` export is only available through the authenticated conversation export endpoint and rejects non-Design Studio sessions.
- If an approved direction differs from an older synthesis winner, the handoff export uses the approved candidate summary instead of stale winner sections.

## Non-Goals

- v1 does not auto-generate production UI code from a handoff.
- v1 does not guarantee every selected model is vision-capable; degraded model selection is explicit metadata.
- v1 does not persist separate normalized Design Studio tables.
- v1 does not replace full design QA; browser and human review remain required before shipping generated handoffs.
