r"""Build the arXiv source package from ../main.tex.

arXiv compiles the TeX itself but does not run BibTeX, so the package carries a
freshly generated main.bbl.  arXiv's file scan does not see \VerbatimInput and
marks figures/ as unused, so Figure 1's text is inlined as a Verbatim block and
the package is just main.tex and main.bbl.  The bibliography's audit comment
blocks are not needed to compile and stay in the repository.  The package is
test-compiled in a clean directory before it is written.

    python3 arxiv/build.py      # writes arxiv/arxiv-source.tar.gz and arxiv/main.pdf
"""
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FILES = ["main.tex", "main.bbl"]


def latex(cwd: Path, bibtex: bool) -> None:
    run = lambda *cmd: subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)
    run("pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex")
    if bibtex:
        run("bibtex", "main")
    run("pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex")
    run("pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex")


with tempfile.TemporaryDirectory() as build, tempfile.TemporaryDirectory() as clean:
    build, clean = Path(build), Path(clean)
    tex = (ROOT / "main.tex").read_text()
    tex = re.sub(r"\\VerbatimInput(\[[^\]]*\])\{([^}]*)\}",
                 lambda m: "\\begin{Verbatim}" + m.group(1) + "\n"
                 + (ROOT / m.group(2)).read_text().rstrip("\n") + "\n\\end{Verbatim}", tex)
    assert "VerbatimInput" not in tex
    (build / "main.tex").write_text(tex)
    shutil.copy(ROOT / "references.bib", build / "references.bib")
    latex(build, bibtex=True)

    for f in FILES:
        (clean / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(build / f, clean / f)
    latex(clean, bibtex=False)
    log = (clean / "main.log").read_text(errors="replace")
    for bad in ("Citation", "Reference"):
        assert f"LaTeX Warning: {bad}" not in log, f"undefined {bad.lower()} in clean build"

    with tarfile.open(HERE / "arxiv-source.tar.gz", "w:gz") as tar:
        for f in FILES:
            tar.add(clean / f, arcname=f)
    shutil.copy(clean / "main.pdf", HERE / "main.pdf")
print("wrote", HERE / "arxiv-source.tar.gz", "and", HERE / "main.pdf")
