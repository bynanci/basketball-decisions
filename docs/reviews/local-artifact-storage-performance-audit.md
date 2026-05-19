# S11 Review: Local Artifact Storage / Performance Audit

## Scope and constraints

This audit reviews the current local JSON/JSONL persistence approach for Court IQ artifacts, focusing on storage growth, read/write patterns, and operational safety as artifact counts increase.

- **In scope:** documentation and review of current behavior + low-risk recommendations.
- **Out of scope:** migrating to a database, rewriting the persistence layer, or adding background jobs.

## Risk priority legend

- **P0 (HIGH):** Data loss/corruption or severe operational correctness risk likely under normal multi-user/multi-request usage.
- **P1 (MEDIUM):** Meaningful scalability/performance risk or operational fragility that can block workflows as data grows.
- **P2 (LOW):** Hygiene, maintainability, or optimization opportunities with lower immediate impact.

---

## 1) Artifact count and directory structure

**Current behavior**
- Artifacts are spread across project-scoped paths (`backend/data/projects/<project_id>`) and global app-data paths (`backend/app/data/**`) for datasets, drills, reports, workflows, review queue, and practice artifacts. 
- The artifact map enumerates per-project and global artifacts by scanning directories and known file paths. 

**Risk level:** **MEDIUM (P1)**

**Observed issue**
- Hybrid storage roots (`backend/data` + `backend/app/data`) increase operational complexity and make backup/restore/versioning boundaries less obvious.
- Artifact discovery is partly convention-based and partly hard-coded, which can drift as new artifact classes are added.

**Recommended fix**
- Add a single source-of-truth artifact inventory doc/table (artifact key → owner service → path pattern → retention policy).
- Add lightweight path constants docs/comments for every new artifact-producing service.
- Add a periodic manual checklist for “new artifact type” PRs (must update inventory + artifact map coverage).

**Suggested milestone**
- **S11/S12 (docs + guardrails only).**

---

## 2) Large JSON file risks

**Current behavior**
- Multiple services use `path.read_text()` + `json.loads(...)` to load full JSON payloads into memory.
- Some index files and summaries are fully rewritten on update (`index.json`, workflow index, report index, etc.).

**Risk level:** **MEDIUM (P1)**

**Observed issue**
- Full-file read/write patterns are acceptable for MVP sizes, but latency and memory usage can degrade as indexes and summary files grow.
- Full rewrite without temp-file swap can increase partial-write exposure on interruption.

**Recommended fix**
- Introduce size guidance in docs (soft caps) for key files (e.g., index files, summary aggregates).
- Add `TODO` notes in core services to migrate high-growth artifacts to append-partitioning or chunked snapshots before DB migration.
- Add low-risk atomic write helper (`write temp file -> fsync -> rename`) and adopt incrementally for critical indexes.

**Suggested milestone**
- **S12 for atomic write helper**, **S13+ for broader adoption**.

---

## 3) JSONL append safety

**Current behavior**
- JSONL readers parse line-by-line from whole-text reads and skip malformed lines with warnings.
- At least one key JSONL writer rewrites the full file deterministically (`write_practice_feedback_signals`) instead of append-only.

**Risk level:** **HIGH (P0)**

**Observed issue**
- “Append-like” datasets are not consistently append-atomic; rewrite patterns can lose writes under concurrent requests.
- There is no explicit locking or compare-and-swap protocol around JSONL writes.

**Recommended fix**
- Document per-artifact write mode (`append`, `rewrite`, `rebuild`) and ownership (single writer vs multi-writer).
- For true event logs, use append-only + fsync boundaries; for rebuilt artifacts, mark them explicitly as derived caches.
- Add a narrow file-lock utility for high-risk JSONL writers to prevent interleaving/truncation races.

**Suggested milestone**
- **S12 (locking + write-mode documentation)**.

---

## 4) Repeated file reads in Development Dashboard

**Current behavior**
- Dashboard aggregation reads many artifacts on each request (player value summaries/trends, plans, executions, review queue, model registry, reports, rules, dataset manifests, feedback JSONL, and artifact map).
- File reads are repeated even when artifacts are unchanged.

**Risk level:** **MEDIUM (P1)**

**Observed issue**
- N-way synchronous file reads can stack latency as artifact volume and concurrency grow.
- Duplicate reads across dashboard + artifact map increase I/O.

**Recommended fix**
- Add a short-lived in-process cache (e.g., 1–5s TTL keyed by file path + mtime) for read-heavy endpoints.
- Add cheap timing instrumentation in the dashboard service to surface slow artifact reads.
- De-duplicate overlapping reads where artifact map already computes nearby status metadata.

**Suggested milestone**
- **S12 (micro-cache + timings).**

---

## 5) Repeated file reads in Artifact Map

**Current behavior**
- Artifact map scans project directories and many file mtimes/payload timestamps every build.
- Workflow staleness checks also iterate across broad input path sets.

**Risk level:** **MEDIUM (P1)**

**Observed issue**
- Map generation cost grows with project count and workflow count.
- Repeated `_updated_at(...)` calls over the same paths can duplicate filesystem work.

**Recommended fix**
- Introduce request-local memoization for `_read_json`, `_updated_at`, and `_file_mtime` inside artifact map build.
- Add optional map depth/detail modes (summary-only vs full artifacts) for high-level dashboard views.
- Add simple size guardrails in docs (“if project count > N, prefer summary endpoint first”).

**Suggested milestone**
- **S12 (memoization, summary mode).**

---

## 6) Race condition risk

**Current behavior**
- Core writers update files with direct `write_text(...)`; several flows do read-modify-write on indexes.
- No explicit inter-process locks, transaction boundaries, or CAS tokens.

**Risk level:** **HIGH (P0)**

**Observed issue**
- Concurrent mutations can cause lost updates in index JSON files and derived JSONL artifacts.
- Multi-request overlap may persist stale index contents after near-simultaneous saves.

**Recommended fix**
- Add a tiny storage safety layer: atomic write helper + advisory file lock helper for critical mutation paths.
- Apply first to highest-write artifacts (`practice_executions/index.json`, `workflows/index.json`, review queue action logs where applicable).
- Add explicit comments where writes are intentionally last-write-wins.

**Suggested milestone**
- **S12 (critical paths), S13 (broader rollout).**

---

## 7) Deletion safety

**Current behavior**
- Sample-data deletion attempts to remove only sample-owned artifacts and checks marker content before unlink.
- Non-sample artifacts at sample paths are protected from deletion.

**Risk level:** **LOW (P2)**

**Observed issue**
- Safety is strong for marker-aware files, but deletion remains path-driven and can silently skip mixed-content files.
- No dry-run endpoint/log summary for operators to preview exactly what will be deleted.

**Recommended fix**
- Add docs for deletion semantics (sample-only, marker requirements, skipped-file behavior).
- Add optional dry-run mode (docs/API contract first) for future low-risk implementation.

**Suggested milestone**
- **S13 (docs now, dry-run later).**

---

## 8) Sample data cleanup safety

**Current behavior**
- Seeder blocks overwrite when sample project id/path is occupied by non-sample content.
- Cleanup checks sample markers before deleting non-project artifacts.

**Risk level:** **LOW (P2)**

**Observed issue**
- Marker detection relies on content heuristics; malformed JSON or partial files can produce conservative skips that leave residue.

**Recommended fix**
- Document expected cleanup residue scenarios and safe manual cleanup steps.
- Add explicit operator output listing deleted vs skipped artifacts (if not already exposed in API response).

**Suggested milestone**
- **S12/S13 (docs + response clarity).**

---

## 9) Backup/export strategy

**Current behavior**
- No unified documented backup/export playbook for both project-scoped and app-scoped artifact roots.

**Risk level:** **MEDIUM (P1)**

**Observed issue**
- Operators may back up only one root and miss dependent artifacts.
- No standard restore verification checklist increases recovery risk.

**Recommended fix**
- Publish a backup runbook with:
  - required roots,
  - recommended snapshot cadence,
  - restore verification steps (project load, dashboard load, artifact map sanity).
- Include a minimal “cold copy” strategy and a warning about copying during active writes.

**Suggested milestone**
- **S11 (documentation).**

---

## 10) Future database migration trigger points

**Current behavior**
- JSON/JSONL remains the MVP persistence approach without formal thresholds to trigger migration.

**Risk level:** **MEDIUM (P1)**

**Observed issue**
- Without predefined triggers, migration may start too late (after user-facing latency and correctness issues appear).

**Recommended fix**
- Define explicit trigger thresholds (example policy):
  - P95 dashboard API latency exceeds target for 2+ consecutive weeks,
  - artifact map generation exceeds target on representative datasets,
  - recurring lost-update incidents from concurrent writes,
  - operator burden from backup/restore exceeds agreed SLA.
- Keep migration planning docs separate from implementation until trigger is met.

**Suggested milestone**
- **S11 (define triggers), S14+ (re-evaluate).**

---

## Consolidated priority list

### P0 (act first)
1. Race condition risk across JSON read-modify-write and JSONL rewrites.
2. JSONL write-mode inconsistency for event-like artifacts.

### P1 (next)
1. Repeated file reads in Development Dashboard.
2. Repeated/memoizable reads in Artifact Map.
3. Large JSON/index growth and non-atomic rewrite patterns.
4. Missing unified backup/export runbook.
5. Missing objective DB migration trigger thresholds.

### P2 (hygiene)
1. Deletion semantics documentation and optional dry-run behavior.
2. Sample cleanup residue/operator visibility improvements.

## Low-risk implementation notes (non-migration)

- Add inline `TODO(storage-s11)` comments in high-risk writer paths for lock/atomic-write rollout.
- Add `docs/` runbook for backup/restore and artifact inventory.
- Keep all changes docs-first; do not migrate persistence in this milestone.
