# Rounds 6-7: audit of the finished draft (2026-10-13)

Snapshot of `main.tex` after the final revision, and the audit records for it.

- Round 6: the revision left 11 sentence-source pairs (10 references) STALE / NOT AUDITED.
  Three Claude (Opus 5.5) subagents, prompt version 2 (`audit/prompts/round6-group-*.md`);
  about 109k subagent tokens in total. 10 SUPPORTED, 1 PARTIAL (zhang2026verifiable: the
  sentence attributed the whole shortfall to "unsupported additions"; the source says it
  is largely due to partial support, mostly unsupported addition).
- Round 7: the Zhang sentence was revised per the note and re-audited by one subagent
  (`audit/prompts/round7.md`); about 32k subagent tokens. SUPPORTED.
- Final state: 24 citing sentence-source records over 20 references; 24 SUPPORTED.
- Excerpt check: 24 MATCH, 0 NEAR, 0 MISSING. Drift check: 0 STALE, 0 NOT AUDITED.
- The 11 records written in rounds 6-7 have not been human-checked. Superseded by round 8.
