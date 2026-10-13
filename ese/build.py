"""Build the European Science Editing submission from ../main.tex.

main.tex stays the master: tools/bibaudit.py audits it.  This script writes a
pandoc-friendly copy (Figure 1 as an image, Table 1 as a plain tabular) and
converts it with Vancouver superscript citations (ese-vancouver.csl).

ESE requirements this build meets (https://ese.arphahub.com/about):
- review version as .docx and .pdf, figures embedded at low resolution
  (REVIEW_DPI); 12-point type, page numbers, bold level-1 headings
- tables and figures at the end of the manuscript, each on a separate page
- figures also uploaded separately at high resolution: figures/ holds each as
  .tif at UPLOAD_DPI (600 dpi, at least 12 cm wide)

    python3 ese/build.py        # writes ese/submission.{docx,pdf}, ese/figures/
                                # and ese/supplement/
"""
import re
import subprocess
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REVIEW_DPI = 150
UPLOAD_DPI = 600

PAGE_BREAK_LUA = r"""
-- Runs before citeproc: the reference list goes before the first \newpage,
-- ahead of the tables and figures; \newpage becomes a Word page break.
local function place_refs(doc)
  for i, el in ipairs(doc.blocks) do
    if el.t == "RawBlock" and el.text:match("^\\newpage") then
      doc.blocks:insert(i, pandoc.Div({}, {id = "refs"}))
      doc.blocks:insert(i, pandoc.Header(1, "References", {class = "unnumbered"}))
      break
    end
  end
  return doc
end

local function page_break(el)
  if el.text:match("^\\newpage") and FORMAT == "docx" then
    return pandoc.RawBlock("openxml", '<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
  end
end

return {{Pandoc = place_refs}, {RawBlock = page_break}}
"""

FOOTER_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    '<w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
    '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
    '<w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
    '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>1</w:t></w:r>'
    '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>')


def heading_rpr(size: int, italic: bool) -> str:
    return ('<w:rPr><w:b/><w:bCs/>' + ('<w:i/><w:iCs/>' if italic else '') +
            f'<w:color w:val="000000"/><w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr>')


def reference_docx(path: Path) -> None:
    """Pandoc's default reference.docx, restyled: 12-point type throughout, bold
    black level-1 headings, bold italic level-2 headings, page numbers."""
    default = subprocess.run(["pandoc", "--print-default-data-file", "reference.docx"],
                             check=True, capture_output=True).stdout
    src = path.with_suffix(".default.docx")
    src.write_bytes(default)
    restyle = {"Heading1": heading_rpr(28, False), "Heading2": heading_rpr(24, True),
               "Abstract": '<w:rPr><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>'}
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/styles.xml":
                s = data.decode()
                for sid, rpr in restyle.items():
                    s = re.sub(rf'(<w:style [^>]*w:styleId="{sid}".*?)<w:rPr>.*?</w:rPr>',
                               lambda m: m.group(1) + rpr, s, count=1, flags=re.S)
                data = s.encode()
            elif item.filename == "word/document.xml":
                data = data.decode().replace(
                    "<w:sectPr>", '<w:sectPr><w:footerReference w:type="default" r:id="rIdFtr1"/>'
                ).encode()
            elif item.filename == "word/_rels/document.xml.rels":
                data = data.decode().replace("</Relationships>",
                    '<Relationship Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                    'relationships/footer" Id="rIdFtr1" Target="footer1.xml"/></Relationships>'
                ).encode()
            elif item.filename == "[Content_Types].xml":
                data = data.decode().replace("</Types>",
                    '<Override PartName="/word/footer1.xml" ContentType="application/'
                    'vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>'
                ).encode()
            zout.writestr(item, data)
        zout.writestr("word/footer1.xml", FOOTER_XML)
    src.unlink()


subprocess.run(["pdftoppm", "-png", "-singlefile", "-r", str(REVIEW_DPI),
                "fig1.pdf", "fig1-review"], cwd=HERE, check=True)

tex = (ROOT / "main.tex").read_text()
tex = re.sub(r"\\VerbatimInput\[[^\]]*\]\{[^}]*\}",
             r"\\includegraphics[width=\\linewidth]{fig1-review.png}", tex)
tex = tex.replace(r"\begin{tabularx}{\linewidth}{@{}lX@{}}", r"\begin{tabular}{ll}")
tex = tex.replace(r"\end{tabularx}", r"\end{tabular}")
# Bracketed placeholders survive into Word, so they cannot be missed.
tex = re.sub(r"\\TBD\{([^}]*)\}", r"[TBD: \1]", tex)
# Number tables and figures by hand: pandoc's Word output drops \ref and leaves
# captions unnumbered.  The PDF gets the same text with LaTeX's labels off.
for env, name in (("table", "Table"), ("figure", "Figure")):
    for n, m in enumerate(re.finditer(rf"\\begin\{{{env}\}}.*?\\end\{{{env}\}}", tex, re.S), 1):
        label = re.search(r"\\label\{([^}]*)\}", m.group(0)).group(1)
        tex = tex.replace(rf"\ref{{{label}}}", str(n))
        tex = tex.replace(m.group(0), m.group(0).replace(r"\caption{", rf"\caption{{{name} {n}. ", 1))
# Tables, then figures, go after the references, one per page.
floats = [m.group(0) for env in ("table", "figure")
          for m in re.finditer(rf"\\begin\{{{env}\}}.*?\\end\{{{env}\}}\n", tex, re.S)]
for f in floats:
    tex = tex.replace(f, "")
# With raw_tex on, a \centering inside a float would be read as a second subfigure.
floats = [f.replace("\\centering\n", "") for f in floats]
tex = tex.replace(r"\end{document}",
                  "".join("\\newpage\n\n" + f + "\n" for f in floats)
                  + r"\end{document}")
(HERE / "main-ese.tex").write_text(tex)
(HERE / "pagebreak.lua").write_text(PAGE_BREAK_LUA)
reference_docx(HERE / "reference.docx")

common = ["pandoc", "main-ese.tex", "--from=latex+raw_tex", "--lua-filter=pagebreak.lua",
          "--citeproc", f"--bibliography={ROOT / 'references.bib'}",
          "--csl=ese-vancouver.csl", "--resource-path=.", "--metadata=link-citations:false"]
subprocess.run(common + ["--reference-doc=reference.docx", "-o", "submission.docx"],
               cwd=HERE, check=True)
(HERE / "nolabels.tex").write_text("\\usepackage{caption}\\captionsetup{labelformat=empty}\n")
subprocess.run(common + ["--pdf-engine=pdflatex", "-H", "nolabels.tex", "-V", "geometry:margin=1in",
                         "-V", "fontsize=12pt", "-o", "submission.pdf"],
               cwd=HERE, check=True, capture_output=True)
print("wrote", HERE / "submission.docx", "and", HERE / "submission.pdf")

(HERE / "figures").mkdir(exist_ok=True)
subprocess.run(["pdftoppm", "-tiff", "-tiffcompression", "lzw", "-singlefile",
                "-r", str(UPLOAD_DPI), "fig1.pdf", "figures/Figure1"], cwd=HERE, check=True)
print("wrote", HERE / "figures")

# Supplementary material, regenerated so it cannot drift from the masters.
(HERE / "supplement").mkdir(exist_ok=True)
subprocess.run(["pandoc", str(ROOT / "audit" / "PROMPT.md"), "-o",
                str(HERE / "supplement" / "S1-audit-prompts.docx")], check=True)
(HERE / "supplement" / "S2-references.bib").write_text((ROOT / "references.bib").read_text())
print("wrote", HERE / "supplement")
