# External Review Round 1 — LLM Synthesis Prototype

## Purpose

This prototype supports **draft-only** LLM-assisted synthesis of External Review Round 1 feedback. It clusters structured reviewer feedback into themes and draft issue proposals to reduce manual triage overhead.

## Governance Rules (Hard Constraints)

1. **LLM may summarize and cluster reviewer feedback** into draft themes and issue proposals.
2. **LLM must not invent reviewer quotes**. Every quote in synthesis output must be directly source-preserved from submitted reviewer entries.
3. **LLM must not change quantitative ratings**. Original numeric ratings are preserved in source entries and reflected unchanged in synthesis artifacts.
4. **LLM must not hide negative feedback**. Negative input is retained and surfaced in draft themes/issues.
5. **LLM must not make release decisions automatically**.
6. **Human reviewer approval is required** before any ER3 findings are finalized.

## API Endpoints

- `POST /api/reviews/external-review/synthesize`
  - Accepts structured reviewer feedback entries.
  - Uses the `mock` provider by default.
  - Returns deterministic draft themes and issue proposals.
  - Saves synthesis artifact to:
    - `backend/app/data/reviews/external_review_synthesis/{synthesis_id}.json`

- `GET /api/reviews/external-review/synthesis/{synthesis_id}`
  - Fetches a previously saved synthesis artifact.

## Provider Behavior

- `mock` provider is enabled by default for deterministic prototype behavior.
- External provider usage is unsupported unless explicitly configured.
- Requests using unsupported providers return a clear API error.

## Data Model Overview

- `ReviewerFeedbackEntry`
- `LLMReviewSynthesisRequest`
- `LLMReviewTheme`
- `LLMReviewIssueProposal`
- `LLMReviewSynthesisResponse`

## Human-in-the-loop Requirement

This flow does **not** replace ER3 review. Output is a draft artifact for human review and approval, and no release decision is automated.
