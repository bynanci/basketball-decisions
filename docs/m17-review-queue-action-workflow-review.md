# M17 Review Queue Action Workflow Review

Date: 2026-05-11

## Pass/fail checklist

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Review actions are explicit and never automatic. | Pass | Queue generation only rebuilds candidates and preserves existing item state; action side effects only run through `POST /api/review-queue/{item_id}/actions`. |
| 2 | Raw tracking artifacts are not mutated. | Pass | Recognition scoring reads `tracking.json`, while false-positive resolution writes `tracking_review_patch.json`; tests verify `tracking.json` remains unchanged. |
| 3 | `MARK_TRACK_FALSE_POSITIVE` updates review patch only. | Pass | The handler appends excluded track/detection IDs to `TrackReviewPatch` and writes only `tracking_review_patch.json`. |
| 4 | `ASSIGN_TRACK_TO_PLAYER_ALIAS` rejects duplicate track ownership. | Pass | Alias assignment detects overlaps against other player keys and returns `PLAYER_ALIAS_TRACK_OVERLAP` with HTTP 409. |
| 5 | UNKNOWN attribution is never converted to fake identity. | Pass | UNKNOWN acceptance records a log warning only; alias assignment requires an explicit reviewer-provided `player_key` and track IDs. |
| 6 | Rule draft approval/rejection uses existing governance rules. | Pass | Review actions delegate to `approve_decision_rule_draft` and `reject_decision_rule_draft`. |
| 7 | Prompt label issues and teaching cases are persisted. | Pass | Prompt issues append to `prompt_review_notes.json`; teaching cases append to `teaching_cases.json`. |
| 8 | Every action writes `review_action_log.json`. | Pass | Allowed actions log `APPLIED`; disallowed or handler-failed actions log `FAILED`; the action log is queryable. |
| 9 | Queue item status updates correctly. | Pass | Applied actions set `RESOLVED`, dismissals set `DISMISSED`, and manual queue item updates can reopen or close items. |
| 10 | Frontend shows allowed actions per item type. | Pass | The API returns `allowed_actions`, and the Review Queue page renders the select options from `item.allowed_actions`. |
| 11 | README documents the workflow. | Pass | README describes explicit actions, local review artifacts, immutable raw tracking, alias overlap rejection, governance reuse, and UNKNOWN handling. |
| 12 | Tests pass. | Pass | Backend and frontend test suites passed locally after installing backend requirements. |

## Bugs found

No blocking workflow bugs were found in the M17 Review Queue Action Workflow implementation during this review. The items below remain tracked as risks rather than M17 pass/fail blockers because the current local workflow is single-user/file-backed and the tested review actions behave correctly.

## Remaining risks

- Action logging is file-based JSON append/write, so simultaneous reviewers could race without a file lock or transactional store.
- Failed-action logs capture the failed status and request payload, but they do not persist the exception code/message in structured fields; debugging still depends on the API error response.
- `PUT /api/review-queue/{item_id}` can change queue status without writing an action log because it is a status endpoint rather than an action endpoint; this is acceptable for current behavior but may be surprising for audit users who expect every queue state transition to appear in `review_action_log.json`.
- Alias assignment validates duplicate ownership inside `player_aliases.json`, but it does not verify that provided track IDs exist in the raw tracking artifact before saving the alias.

## Suggested next milestone

M18 should harden review auditability and concurrency: add structured error details to failed action logs, file-lock or transactional persistence for queue/action writes, optional status-change audit events for manual reopen/close operations, and alias assignment validation against available project tracks.
