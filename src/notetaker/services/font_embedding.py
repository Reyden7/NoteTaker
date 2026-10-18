"""Embed the unmodified OFL TTF files in Word documents, without a system install."""
from importlib.resources import files


def embed_docx_fonts(document):
    from docx.opc.part import Part
    from docx.opc.packuri import PackURI
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docx.oxml import OxmlElement, parse_xml
    from docx.oxml.ns import qn
    table = document.part.part_related_by(RT.FONT_TABLE)
    root = parse_xml(table.blob)
    font = OxmlElement("w:font")
    font.set(qn("w:name"), "Noto Sans")
    for style, filename in (("Regular", "NotoSans-Regular.ttf"), ("Bold", "NotoSans-Bold.ttf")):
        data = files("notetaker").joinpath("assets/fonts", filename).read_bytes()
        part = Part(PackURI("/word/fonts/" + filename), "application/x-font-ttf", data, document.part.package)
        relationship = table.relate_to(part, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/font")
        embedded = OxmlElement("w:embed" + style)
        embedded.set(qn("r:id"), relationship)
        # Word documents support plain TrueType parts with the all-zero key.
        # MS-OI29500, Part 1 section 15.2.13 (Font Part).
        embedded.set(qn("w:fontKey"), "{00000000-0000-0000-0000-000000000000}")
        font.append(embedded)
    root.append(font)
    from lxml import etree
    table._blob = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    setting = OxmlElement("w:embedTrueTypeFonts")
    document.settings.element.append(setting)
