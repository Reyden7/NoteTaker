"""Phase 0 local exporters: human-reviewed draft only, never official approval."""
import os
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape
from notetaker.domain.minutes import require_review

DISCLAIMER = "BROUILLON NON OFFICIEL - contrôle humain requis avant utilisation"

def export_draft(content, review, destination: Path, *, session_id: str, municipality: str, session_date: str):
    require_review(content, review)
    suffix = destination.suffix.lower()
    if suffix not in {".docx", ".pdf"}:
        raise ValueError("UNSUPPORTED_EXPORT_FORMAT")
    # This proof deliberately refuses votes until the complete structured renderer exists.
    if any(p["vote_id"] is not None for p in content["points"]):
        raise ValueError("STRUCTURED_VOTE_RENDERING_NOT_IMPLEMENTED")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=destination.parent, suffix=suffix)
    os.close(fd)
    temporary = Path(name)
    metadata = f"{municipality} | {session_date} | Séance {session_id}"
    try:
        if suffix == ".docx":
            _docx(content, metadata, temporary)
        else:
            _pdf(content, metadata, temporary)
        with temporary.open("r+b") as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination

def _docx(content, metadata, path):
    from docx import Document
    from docx.shared import Cm, Pt, RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    doc = Document()
    # python-docx's bundled template contains theme-colored paragraph borders.
    for border in list(doc.styles.element.iter(qn("w:pBdr"))):
        border.getparent().remove(border)
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin = section.bottom_margin = Cm(2)
    section.left_margin = section.right_margin = Cm(2.2)
    for name in ["Normal", "Title", "Heading 1", "Heading 2"]:
        style = doc.styles[name]
        style.font.name = "Arial"
        style.font.color.rgb = RGBColor(0, 0, 0)
    doc.styles["Normal"].font.size = Pt(11)
    section.header.paragraphs[0].text = metadata
    doc.add_paragraph("Projet de procès verbal", "Title")
    doc.add_paragraph(DISCLAIMER)
    for p in content["points"]:
        doc.add_heading(p["title"], 1)
        doc.add_paragraph(p["summary"])
        doc.add_paragraph("Sources : " + ", ".join(p["sources"]))
        if p["vote_id"] is None:
            doc.add_paragraph("Résultat du vote : à compléter")
    if content["to_verify"]:
        doc.add_heading("Éléments à vérifier", 1)
        for item in content["to_verify"]:
            doc.add_paragraph(item)
    footer = section.footer.paragraphs[0]
    footer.add_run("Page ")
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    footer._p.append(field)
    doc.save(path)

def _pdf(content, metadata, path):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.textColor = colors.black
    flow = [Paragraph("Projet de procès verbal", styles["Title"]),
            Paragraph(escape(DISCLAIMER), styles["Normal"]), Spacer(1, 16)]
    for p in content["points"]:
        flow += [Paragraph(escape(p["title"]), styles["Heading1"]),
                 Paragraph(escape(p["summary"]).replace("\n", "<br/>"), styles["BodyText"]),
                 Paragraph("Sources : " + escape(", ".join(p["sources"])), styles["BodyText"])]
        if p["vote_id"] is None:
            flow.append(Paragraph("Résultat du vote : à compléter", styles["BodyText"]))
    if content["to_verify"]:
        flow.append(Paragraph("Éléments à vérifier", styles["Heading1"]))
        flow += [Paragraph(escape(item), styles["BodyText"]) for item in content["to_verify"]]
    def page(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        canvas.drawString(48, A4[1] - 35, metadata)
        canvas.drawRightString(A4[0] - 48, 30, f"Page {doc.page}")
        canvas.restoreState()
    SimpleDocTemplate(str(path), pagesize=A4, rightMargin=48, leftMargin=48,
                      topMargin=60, bottomMargin=50).build(flow, onFirstPage=page, onLaterPages=page)
