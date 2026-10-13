"""Embed a claim-level citation audit in a BibTeX file, and check it.

The audit is one JSON record per bibkey (audit/<bibkey>.json):

    {"bibkey": "...", "source": "sources/<file>.pdf", "source_version": "...",
     "audited": "YYYY-MM-DD",
     "claims": [{"file": "main.tex", "line": 12, "sentence": "<verbatim>",
                 "claim": "<what the sentence attributes to the source>",
                 "verdict": "SUPPORTED|PARTIAL|UNSUPPORTED|CONTRADICTED",
                 "excerpt": "<verbatim from the source>", "location": "<page/section>",
                 "note": "<optional>"}]}

Commands:

  annotate  Write a comment block above each .bib entry: the source, then every
            sentence in the manuscript that cites the entry, with its verdict,
            claim, excerpt and note.  Blocks are regenerated on every run, so
            edit the JSON, not the .bib.
  check     Drift check, writes nothing.  Every citing sentence in the .tex must
            have a record (else NOT AUDITED) and every record must still match a
            sentence in the .tex (else STALE).  Exits 1 if either remains.
  excerpts  Check that every excerpt occurs in the text of its source (pdftotext
            for PDFs, tags stripped for HTML), compared as word sequences after
            normalizing Unicode and hyphenation.  MATCH = found verbatim; NEAR =
            at least NEAR of its word 4-grams found (usually a table, formula,
            page break or small caps in the extracted text; worth a look);
            MISSING = below that.  Exits 1 if any excerpt is MISSING.
  extract   Rebuild the JSON records from the comment blocks, so that an editor
            holding only the manuscript, the .bib and their own copies of the
            sources can run `check` and `excerpts --from-bib`.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import textwrap
import unicodedata
from pathlib import Path

BEGIN = "% >>> citation-audit"
END = "% <<< citation-audit"
CITE = re.compile(r"\\(?:no)?cite[tp]?\*?(?:\[[^\]]*\])*\{([^}]+)\}")
ENTRY = re.compile(r"^@(\w+)\{([^,\s]+),", re.M)
WIDTH = 100
# Share of an excerpt's word 4-grams that must occur in the source for NEAR.
# Excerpts checked against unrelated sources stay far below it.
NEAR = 0.4
LABELS = {"Paper:  ": "sentence", "Claim:  ": "claim", "Source: ": "excerpt", "Note:   ": "note"}


# --- manuscript -----------------------------------------------------------

def citing_sites(tex_files: list[Path], root: Path) -> dict[str, list[tuple[str, int, str]]]:
    """bibkey -> [(file, line, sentence)] for every \\cite in the manuscript.

    Assumes one paragraph per source line (the sentence split is per line)."""
    sites: dict[str, list[tuple[str, int, str]]] = {}
    for f in tex_files:
        rel = str(f.relative_to(root))
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if line.lstrip().startswith("%"):
                continue
            for sent in re.split(r"(?<=[.!?])\s+(?=[A-Z\\])", line):
                for m in CITE.finditer(sent):
                    for key in (k.strip() for k in m.group(1).split(",")):
                        site = (rel, n, sent.strip())
                        if site not in sites.setdefault(key, []):
                            sites[key].append(site)
    return sites


# --- annotate / check -----------------------------------------------------

def wrap(label: str, text: str) -> list[str]:
    # '@' outside an entry starts a new entry in BibTeX, so it cannot appear.
    text = " ".join(text.replace("@", "(at)").split())
    return textwrap.wrap(text, WIDTH, initial_indent=f"%   {label}",
                         subsequent_indent="%   " + " " * len(label),
                         break_long_words=False, break_on_hyphens=False) or [f"%   {label}"]


def block(key: str, record: dict | None, sites: list[tuple[str, int, str]]) -> tuple[list[str], int]:
    """Comment lines for one entry, and the number of STALE / NOT AUDITED items."""
    out = [f"{BEGIN} {key}"]
    problems = 0
    if record is None and not sites:
        out.append("% Not cited in the manuscript.")
        return out + [END], 0
    if record is not None:
        version = f" ({record['source_version']})" if record.get("source_version") else ""
        src = f"{record.get('source') or record.get('source_pdf') or 'none'}{version}"
        out += textwrap.wrap(f"% Source: {src} -- audited {record.get('audited', '?')}", WIDTH,
                             subsequent_indent="%         ", break_long_words=False, break_on_hyphens=False)
    claims = record["claims"] if record else []
    current = {(f, s): n for f, n, s in sites}
    recorded = {(c["file"], c["sentence"]) for c in claims}
    for i, c in enumerate(claims, 1):
        line = current.get((c["file"], c["sentence"]))
        if line is None:
            problems += 1
            where = f"{c['file']}:{c['line']} STALE (sentence no longer in manuscript)"
        else:
            where = f"{c['file']}:{line}"
        out.append(f"% [{i}] {where} -- {c['verdict']}")
        out += wrap("Paper:  ", c["sentence"])
        out += wrap("Claim:  ", c["claim"])
        if c.get("excerpt"):
            loc = f"({c['location']}) " if c.get("location") else ""
            out += wrap("Source: ", f"{loc}\"{c['excerpt']}\"")
        if c.get("note"):
            out += wrap("Note:   ", c["note"])
    for f, n, s in sites:
        if (f, s) not in recorded:
            problems += 1
            out.append(f"% [-] {f}:{n} -- NOT AUDITED")
            out += wrap("Paper:  ", s)
    return out + [END], problems


def strip_blocks(bib: str) -> str:
    return re.sub(rf"^{re.escape(BEGIN)}.*?^{re.escape(END)}\n", "", bib, flags=re.M | re.S)


def annotate(args, write: bool) -> int:
    records = {p.stem: json.loads(p.read_text()) for p in sorted(args.audit.glob("*.json"))}
    sites = citing_sites(args.tex, args.root)
    bib = strip_blocks(args.bib.read_text())
    keys = [m.group(2) for m in ENTRY.finditer(bib)]

    total, report = 0, []

    def insert(m: re.Match) -> str:
        nonlocal total
        lines, problems = block(m.group(2), records.get(m.group(2)), sites.get(m.group(2), []))
        if problems:
            report.append(f"{m.group(2)}: {problems} STALE / NOT AUDITED")
        total += problems
        return "\n".join(lines) + "\n" + m.group(0)

    new = ENTRY.sub(insert, bib)
    for key in sorted(set(sites) - set(keys)):
        report.append(f"{key}: cited but not in {args.bib.name}")
        total += 1
    for key in sorted(set(records) - set(keys)):
        report.append(f"{key}: audit record but no .bib entry")

    if report:
        print("\n".join(report), file=sys.stderr)
    n_claims = sum(len(s) for k, s in sites.items() if k in keys)
    if not write:
        print(f"{len(keys)} entries, {n_claims} citing sentences; {total} STALE / NOT AUDITED")
        return 1 if total else 0
    args.bib.write_text(new)
    print(f"annotated {len(keys)} entries, {n_claims} citing sentences; {total} STALE / NOT AUDITED")
    return 0


# --- extract (records from the .bib alone) ----------------------------------

def extract(bib_text: str) -> dict[str, dict]:
    """Rebuild audit records from the comment blocks, for a reader with only the .bib."""
    records = {}
    for m in re.finditer(rf"^{re.escape(BEGIN)} (\S+)\n(.*?)^{re.escape(END)}", bib_text, re.M | re.S):
        key, body = m.group(1), m.group(2)
        rec: dict = {"bibkey": key, "claims": []}
        cur, field = None, None
        body = re.sub(r"\n%         (?=\S)", " ", body)  # rejoin a wrapped Source header
        for line in body.splitlines():
            if h := re.match(r"% Source: (.*?)(?: \((.*)\))? -- audited (\S+)$", line):
                rec.update(source=h.group(1), source_version=h.group(2), audited=h.group(3))
            elif h := re.match(r"% \[(\d+|-)\] (\S+?):(\d+)(?: STALE.*?)? -- (.+)$", line):
                cur = {"file": h.group(2), "line": int(h.group(3)), "verdict": h.group(4)}
                rec["claims"].append(cur)
            elif cur is not None and (h := re.match(r"%   (Paper:  |Claim:  |Source: |Note:   )(.*)$", line)):
                field = LABELS[h.group(1)]
                cur[field] = h.group(2)
            elif cur is not None and field and line.startswith("%   "):
                cur[field] += " " + line[4:].strip()
        for c in rec["claims"]:
            if "excerpt" in c and (h := re.match(r'(?:\((.*?)\) )?"(.*)"$', c["excerpt"])):
                c["location"], c["excerpt"] = h.group(1), h.group(2)
        if rec["claims"]:
            records[key] = rec
    return records


# --- excerpts ---------------------------------------------------------------

def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.translate(str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
                                   "\u2013": "-", "\u2014": "-", "\u2212": "-", "\u00ad": ""}))
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)      # hyphenation at line ends
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def source_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return subprocess.run(["pdftotext", str(path), "-"],
                              capture_output=True, text=True, check=True).stdout
    raw = path.read_text(errors="replace")
    raw = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", raw)
    return html.unescape(re.sub(r"<[^>]+>", " ", raw))


def grams(s: str, n: int = 4) -> list[tuple[str, ...]]:
    w = re.findall(r"\w+", s)
    return [tuple(w[i:i + n]) for i in range(max(len(w) - n + 1, 1))] if w else []


def words(s: str) -> str:
    """The word sequence of s, space-delimited at both ends, punctuation dropped."""
    return " " + " ".join(re.findall(r"\w+", s)) + " "


def excerpt_status(excerpt: str, text: str, text_grams: set) -> tuple[str, float]:
    # Compared as word sequences, so spacing around punctuation in the extracted
    # text does not matter.  An ellipsis marks an elision; each part must occur.
    parts = [normalize(p) for p in re.split(r"\s*(?:\.\.\.|\u2026|\[\.\.\.\])\s*", excerpt)]
    parts = [p for p in parts if re.search(r"\w", p)]
    if all(words(p) in text for p in parts):
        return "MATCH", 1.0
    g = [x for p in parts for x in grams(p)]
    cover = sum(x in text_grams for x in g) / len(g) if g else 0.0
    return ("NEAR" if cover >= NEAR else "MISSING"), cover


def excerpts(args) -> int:
    records = ({p.stem: json.loads(p.read_text()) for p in sorted(args.audit.glob("*.json"))}
               if not args.from_bib else extract(args.bib.read_text()))
    counts = {"MATCH": 0, "NEAR": 0, "MISSING": 0, "NO SOURCE": 0}
    for key, rec in records.items():
        src = rec.get("source") or rec.get("source_pdf")
        path = (args.sources_root / src) if src else None
        claims = [c for c in rec["claims"] if c.get("excerpt")]
        if not claims:
            continue
        if path is None or not path.exists():
            counts["NO SOURCE"] += len(claims)
            print(f"NO SOURCE  {key}: {src}")
            continue
        text = words(normalize(source_text(path)))
        tg = set(grams(text))
        for c in claims:
            status, cover = excerpt_status(c["excerpt"], text, tg)
            counts[status] += 1
            if status != "MATCH" or args.verbose:
                print(f"{status:<9}  {key} [{c['file']}:{c['line']}] {cover:.0%} of 4-grams: "
                      f"\"{c['excerpt'][:90]}{'...' if len(c['excerpt']) > 90 else ''}\"")
    print(", ".join(f"{k} {v}" for k, v in counts.items()))
    return 1 if counts["MISSING"] else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("command", choices=["annotate", "check", "excerpts", "extract"])
    ap.add_argument("--root", type=Path, default=Path("."), help="manuscript directory (default .)")
    ap.add_argument("--bib", type=Path, help="default <root>/references.bib")
    ap.add_argument("--audit", type=Path, help="JSON records, default <root>/audit")
    ap.add_argument("--sources-root", type=Path, help="base for record 'source' paths, default <root>")
    ap.add_argument("--from-bib", action="store_true", help="excerpts: read records from the .bib comments")
    ap.add_argument("-v", "--verbose", action="store_true", help="excerpts: list MATCHes too")
    ap.add_argument("tex", nargs="*", type=Path, help="default <root>/main.tex and <root>/sections/**/*.tex")
    args = ap.parse_args()
    args.root = args.root.resolve()
    args.bib = args.bib or args.root / "references.bib"
    args.audit = args.audit or args.root / "audit"
    args.sources_root = args.sources_root or args.root
    args.tex = [t.resolve() for t in args.tex] or sorted(
        p for p in [args.root / "main.tex", *args.root.glob("sections/**/*.tex")] if p.exists())

    if args.command == "extract":
        for key, rec in extract(args.bib.read_text()).items():
            (args.audit / f"{key}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
        return 0
    if args.command == "excerpts":
        return excerpts(args)
    return annotate(args, write=args.command == "annotate")


if __name__ == "__main__":
    sys.exit(main())
