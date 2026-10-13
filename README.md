# Claim-level citation records

Materials for *Claim-Level Citation Records Submitted with the Bibliography: A Proposal and
Worked Example* (Jacob Moore, Lawrence Technological University).

The article proposes that authors submit, with the bibliography, a record for each citing
sentence: the claim, a verbatim supporting excerpt from the source, its location and a
verdict. Every reference in the article was audited this way, and this repository holds
everything needed to rerun the checks.

## Contents

| Path | What it is |
|---|---|
| `main.tex` | The manuscript (master copy) |
| `references.bib` | The bibliography, with a generated audit block above each entry |
| `tools/bibaudit.py` | The audit tool (`tools/crosscheck.py`: the cross-source control) |
| `audit/<bibkey>.json` | Current audit records, one per reference |
| `audit/PROMPT.md` | The audit prompt (Supplementary material S1) |
| `audit/prompts/` | The prompt actually given to each auditing agent, per round |
| `audit/round*/` | Snapshots of the manuscript and records after selected rounds |
| `audit/human-check/` | The author's judgements of the records: `labels.json` (blind, 26 records; see the case study) and `labels-round9.json` (the 11 records written afterwards) |
| `audit/removed/` | Records for a reference cut during revision |
| `sources/SOURCES.md` | Each cited source, with its version and retrieval date |
| `ese/`, `arxiv/` | Builds of the journal submission files and the arXiv source package |

The cited sources themselves are not redistributed (see below for running the checks
that need them).

## Running the checks

Requires Python 3.9+ and `pdftotext` (poppler-utils); no Python packages beyond the standard library.

```sh
python3 tools/bibaudit.py check      # every citing sentence has a record, and every record a sentence
python3 tools/bibaudit.py excerpts   # every excerpt occurs in its source (needs sources/)
python3 tools/bibaudit.py annotate   # regenerate the audit blocks in references.bib
python3 tools/bibaudit.py extract    # rebuild the JSON records from references.bib (see below)
python3 tools/crosscheck.py          # control: each excerpt against every other source (needs sources/)
```

`check` and `annotate` need only the repository. `excerpts` and `crosscheck.py` need the
sources: download each from the URL in `sources/SOURCES.md` and save it as
`sources/<file>` under the file name given there. Sources not present are reported as
`NO SOURCE` (or skipped by `crosscheck.py`), so the checks can be run on any subset.

A reader holding only `main.tex` and `references.bib` can rebuild the records from the
comment blocks and check them without this repository's `audit/` directory:

```sh
mkdir records
python3 tools/bibaudit.py --audit records extract
python3 tools/bibaudit.py --audit records check
python3 tools/bibaudit.py excerpts --from-bib
```

`extract` writes into `audit/` unless `--audit` is given, so use a separate directory to
avoid overwriting the committed records. `python3 tools/bibaudit.py --help` describes each
command and the record format.

## License

`tools/*.py`, `ese/build.py` and `arxiv/build.py` are under the MIT License. Everything else (the
manuscript, prompts, audit records and other text) is under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Excerpts quoted from cited
sources in the audit records remain the work of their authors and are reproduced as
quotations. See `LICENSE`.
