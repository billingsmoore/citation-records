"""Build the European Science Editing submission (.docx) from ../main.tex.

main.tex stays the master: tools/bibaudit.py audits it.  This script writes a
pandoc-friendly copy (Figure 1 as an image, Table 1 as a plain tabular) and
converts it with Vancouver superscript citations (ese-vancouver.csl).

    python3 ese/build.py        # writes ese/submission.docx and ese/supplement/
"""
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

tex = (ROOT / "main.tex").read_text()
tex = re.sub(r"\\VerbatimInput\[[^\]]*\]\{[^}]*\}",
             r"\\includegraphics[width=\\linewidth]{fig1.png}", tex)
tex = tex.replace(r"\begin{tabularx}{\linewidth}{@{}lX@{}}", r"\begin{tabular}{ll}")
tex = tex.replace(r"\end{tabularx}", r"\end{tabular}")
# Bracketed placeholders survive into Word, so they cannot be missed.
tex = re.sub(r"\\TBD\{([^}]*)\}", r"[TBD: \1]", tex)
(HERE / "main-ese.tex").write_text(tex)

subprocess.run(
    ["pandoc", "main-ese.tex", "--from=latex", "--to=docx",
     "--citeproc", f"--bibliography={ROOT / 'references.bib'}",
     "--csl=ese-vancouver.csl", "--resource-path=.",
     "--metadata=link-citations:false", "-o", "submission.docx"],
    cwd=HERE, check=True)
print("wrote", HERE / "submission.docx")

# Supplementary material, regenerated so it cannot drift from the masters.
(HERE / "supplement").mkdir(exist_ok=True)
subprocess.run(["pandoc", str(ROOT / "audit" / "PROMPT.md"), "-o",
                str(HERE / "supplement" / "S1-audit-prompts.docx")], check=True)
(HERE / "supplement" / "S2-references.bib").write_text((ROOT / "references.bib").read_text())
print("wrote", HERE / "supplement")
