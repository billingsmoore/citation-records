"""Control for the excerpt check: score every excerpt against every *other* source.

An excerpt should reach NEAR or MATCH only against its own source.  This prints
the highest 4-gram coverage of any excerpt in a source other than its own.

    python3 tools/crosscheck.py [--root .] [--top 5]
"""
import argparse
import json
from pathlib import Path

from bibaudit import NEAR, excerpt_status, grams, normalize, source_text, words

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--root", type=Path, default=Path("."))
ap.add_argument("--top", type=int, default=5)
args = ap.parse_args()

records = [json.loads(p.read_text()) for p in sorted((args.root / "audit").glob("*.json"))]
texts, missing = {}, []
for r in records:
    path = args.root / r["source"]
    if not path.exists():
        missing.append(r["source"])
        continue
    t = words(normalize(source_text(path)))
    texts[r["bibkey"]] = (t, set(grams(t)))
if missing:
    print(f"{len(missing)} of {len(records)} sources missing (see sources/SOURCES.md); "
          "checking against the rest")
if len(texts) < 2:
    raise SystemExit("need at least two sources under sources/ to cross-check")

scores = []
for r in records:
    for c in r["claims"]:
        for key, (t, tg) in texts.items():
            if key != r["bibkey"]:
                status, cover = excerpt_status(c["excerpt"], t, tg)
                scores.append((1.0 if status == "MATCH" else cover, r["bibkey"], key))
scores.sort(reverse=True)
print(f"{len(scores)} excerpt-source pairs; NEAR threshold {NEAR:.0%}")
for cover, own, other in scores[:args.top]:
    print(f"{cover:6.1%}  excerpt for {own} in {other}")
