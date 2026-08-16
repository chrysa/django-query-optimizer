# Known issues (append-only)

## 2026-08-14 — N+1 and duplicate detectors double-flag the same query

Exact-duplicate SQL (same string ≥2×) is flagged by BOTH `_detect_duplicate_queries`
(exact `q.sql`) and `NplusOneDetector` (normalised SQL + same file/line). Result:
two recommendations for one root cause, and a doubled score penalty.
Fix direction: dedupe by (file, line, normalised sql) before scoring, or make the
two detectors mutually exclusive.

## 2026-08-14 — Health score not normalised to workload

`QueryScorer` subtracts a flat penalty per issue with no reference to total query
count. A 2-query request and a 200-query request with the same issue score identically.
Consider a ratio/normalised component.

## 2026-08-14 — Per-query stack extraction cost unbenchmarked

`QueryCollector._capture` calls `traceback.extract_stack()` on every query and stores
the full stack as strings. No benchmark proves the middleware path stays cheap.
Tracked by ADR-0001 kill-test (gate open).
