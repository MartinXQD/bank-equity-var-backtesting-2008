"""Render the GitHub Markdown report as a letter-size PDF."""
from html import escape
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString
from markdown import markdown
from matplotlib import get_data_path
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

HERE = Path(__file__).resolve().parent
FONT_DIR = Path(get_data_path()) / "fonts" / "ttf"
for face, suffix in [("DejaVu", ""), ("DejaVu-Bold", "-Bold"), ("DejaVu-Italic", "-Oblique"),
                     ("DejaVu-BoldItalic", "-BoldOblique")]:
    pdfmetrics.registerFont(TTFont(face, str(FONT_DIR / f"DejaVuSans{suffix}.ttf")))
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold",
                              italic="DejaVu-Italic", boldItalic="DejaVu-BoldItalic")

NAVY = colors.HexColor("#122c42")
BLUE = colors.HexColor("#146797")
MUTED = colors.HexColor("#475569")
RULE = colors.HexColor("#d9e2eb")
CONTENT_WIDTH = 504

body = ParagraphStyle("Body", fontName="DejaVu", fontSize=9.6, leading=14.3,
                      textColor=NAVY, spaceAfter=8)
title = ParagraphStyle("Title", parent=body, fontName="DejaVu-Bold",
                       fontSize=24, leading=28, spaceAfter=15, keepWithNext=True)
heading = ParagraphStyle("Heading", parent=body, fontName="DejaVu-Bold", fontSize=15,
                         leading=19, spaceBefore=7, spaceAfter=8, keepWithNext=True)
subheading = ParagraphStyle("Subheading", parent=body, fontName="DejaVu-Bold", fontSize=10,
                            leading=14, spaceBefore=6, spaceAfter=5, keepWithNext=True)
caption = ParagraphStyle("Caption", parent=body, fontSize=8.2, leading=11.5, textColor=MUTED)
cell = ParagraphStyle("Cell", parent=body, fontSize=8, leading=11, spaceAfter=0)
right_cell = ParagraphStyle("RightCell", parent=cell, alignment=TA_RIGHT)
header_cell = ParagraphStyle("HeaderCell", parent=cell, fontName="DejaVu-Bold",
                             textColor=colors.white)
right_header = ParagraphStyle("RightHeader", parent=header_cell, alignment=TA_RIGHT)
bullet = ParagraphStyle("Bullet", parent=body, leftIndent=12, bulletIndent=1, spaceAfter=4)


def inline(node):
    if isinstance(node, NavigableString):
        return escape(str(node))
    content = "".join(inline(child) for child in node.children)
    if node.name == "a":
        return f'<link href="{escape(node["href"], quote=True)}" color="#146797">{content}</link>'
    if node.name == "strong":
        return f"<b>{content}</b>"
    if node.name == "em":
        return f"<i>{content}</i>"
    if node.name == "br":
        return "<br/>"
    return content


def report_table(node):
    rows = []
    for index, row in enumerate(node.find_all("tr")):
        cells = []
        for tag in row.find_all(["th", "td"]):
            numeric = "right" in tag.get("style", "")
            cell_style = (right_header if numeric else header_cell) if index == 0 else (
                right_cell if numeric else cell
            )
            cells.append(Paragraph(inline(tag), cell_style))
        rows.append(cells)
    fractions = {
        2: [0.56, 0.44],
        3: [0.42, 0.29, 0.29],
        4: [0.37, 0.21, 0.21, 0.21],
        5: [0.27, 0.20, 0.18, 0.18, 0.17],
        6: [0.22, 0.30, 0.16, 0.10, 0.11, 0.11],
        7: [0.25, 0.15, 0.12, 0.12, 0.12, 0.12, 0.12],
        8: [0.13, 0.13, 0.14, 0.12, 0.12, 0.12, 0.12, 0.12],
    }
    table = Table(rows, colWidths=[CONTENT_WIDTH * part for part in fractions[len(rows[0])]],
                  hAlign="LEFT", repeatRows=1)
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#edf3f7")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, RULE),
    ]))
    return table


def page_elements(source):
    html = BeautifulSoup(markdown(source, extensions=["tables"]), "html.parser")
    elements = []
    for node in html.find_all(recursive=False):
        if node.name in {"h1", "h2", "h3"}:
            elements.append(Paragraph(inline(node), {"h1": title, "h2": heading, "h3": subheading}[node.name]))
        elif node.name == "table":
            elements.extend([report_table(node), Spacer(1, 9)])
        elif node.name == "ul":
            elements.extend(Paragraph(inline(li), bullet, bulletText="•") for li in node.find_all("li"))
        elif node.name == "p" and node.find("img"):
            path = HERE / node.img["src"]
            with PILImage.open(path) as image:
                width, height = image.size
            image_width = 474 if path.name == "var_backtest.png" else CONTENT_WIDTH
            elements.append(Image(str(path), width=image_width, height=image_width * height / width))
            elements.append(Spacer(1, 4))
        elif node.name == "p":
            elements.append(Paragraph(inline(node), caption if node.get_text().startswith("Figure ") else body))
    return elements


def page_frame(canvas, document):
    width, height = letter
    canvas.setStrokeColor(RULE)
    canvas.line(54, height - 42, width - 54, height - 42)
    canvas.line(54, 43, width - 54, 43)
    canvas.setFont("DejaVu-Bold", 8)
    canvas.setFillColor(BLUE)
    canvas.drawString(54, height - 33, "MARKET RISK RESEARCH")
    canvas.setFont("DejaVu", 8)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(width - 54, height - 33, "Qidian (Martin) Xing")
    canvas.drawString(54, 29, "Bank Equity Under Stress")
    canvas.drawRightString(width - 54, 29, str(document.page))


def main():
    source = (HERE / "research_report.md").read_text(encoding="utf-8")
    story = []
    for page in source.split("<!-- pagebreak -->"):
        if story:
            story.append(PageBreak())
        story.extend(page_elements(page))
    document = SimpleDocTemplate(
        str(HERE / "research_report.pdf"), pagesize=letter,
        leftMargin=48, rightMargin=48, topMargin=54, bottomMargin=52,
        title="Bank Equity Under Stress — Backtesting Portfolio VaR in 2008",
        author="Qidian (Martin) Xing",
    )
    document.build(story, onFirstPage=page_frame, onLaterPages=page_frame)


if __name__ == "__main__":
    main()
