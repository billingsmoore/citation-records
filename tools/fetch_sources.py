"""Download the cited sources listed in sources/SOURCES.md into sources/.

The sources are not redistributed with this repository; this fetches each from the
URL it was retrieved from on 2026-10-12.  Best effort only: a URL can move, a site
can block scripted downloads, and a web page can change after retrieval, in which
case `bibaudit.py excerpts` may report NEAR or MISSING for an excerpt that matched
the copy actually audited.  The arXiv and PMC links are versioned and should
reproduce the audited text exactly.  For anything that fails, retrieve the source
by hand and save it under the file name given in SOURCES.md.

    python3 tools/fetch_sources.py [--root .] [--force]
"""
import argparse
import re
import sys
import urllib.request
from pathlib import Path

READER = "https://r.jina.ai/"

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--root", type=Path, default=Path("."))
ap.add_argument("--force", action="store_true", help="download even if the file exists")
args = ap.parse_args()

sources = args.root / "sources"
failed = []
for row in (sources / "SOURCES.md").read_text().splitlines():
    cells = [c.strip() for c in row.strip("|").split("|")]
    if len(cells) != 5 or not cells[2].startswith("http"):
        continue
    key, _, url_cell, _, file_cell = cells
    url = re.match(r"\S+", url_cell).group(0)
    if READER in url_cell:  # the row says the text came through the reader proxy
        url = READER + url
    dest = sources / file_cell.split()[0]
    if dest.exists() and not args.force:
        print(f"have     {dest.name}")
        continue
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (citation-records fetch_sources.py)"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            dest.write_bytes(resp.read())
        print(f"fetched  {dest.name}")
    except Exception as e:  # report and carry on with the rest
        failed.append(key)
        print(f"FAILED   {dest.name}: {e}  ({url})")

if failed:
    print(f"\n{len(failed)} failed: {', '.join(failed)}. Retrieve these by hand (see SOURCES.md).")
sys.exit(1 if failed else 0)
