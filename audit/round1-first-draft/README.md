# Round 1: audit of the first draft (2026-10-12)

Snapshot of `main.tex` as drafted, before any audit-driven revision, and the audit
records produced from it. The live records in `audit/` are updated as the text changes.

- 12 citing sentences, 19 cited references, 25 claim records (one sentence-source
  pair holds two claims)
- Verdicts: 15 SUPPORTED, 10 PARTIAL, 0 UNSUPPORTED, 0 CONTRADICTED
- Excerpt check: 25 MATCH, 0 NEAR, 0 MISSING
- Drift check: 0 STALE, 0 NOT AUDITED
- Process: four Claude (Opus 5.5) subagents, one per group of references, each given
  `audit/prompts/group-*.md`; 15:50-15:53 EDT wall clock; about 289k subagent tokens in total
  (57k-106k per group).
- Not yet human-checked.
