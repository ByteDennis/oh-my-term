"""Editable English management report: site structure, business use, progress."""
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.xmlchemy import OxmlElement
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

OUT = Path(__file__).parent
FONT = "Arial"
C = {"ink": "243149", "muted": "69788F", "purple": "6554C0", "line": "DFE5EF",
     "light": "F7F8FC", "lavender": "F2EFFB", "white": "FFFFFF", "green": "347C65",
     "blue": "3C74A1", "amber": "9D7528"}
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333333), Inches(7.5)
prs.core_properties.title = "Datasaurus | Data catalog"
prs.core_properties.subject = "Site structure, business use, and weekly progress"
prs.core_properties.author = ""


def rect(slide, x, y, w, h, fill="white", border=None, rounded=False):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
                                  Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor.from_string(C.get(fill, fill))
    if border:
        shape.line.color.rgb = RGBColor.from_string(C.get(border, border))
        shape.line.width = Pt(.8)
    else:
        shape.line.fill.background()
    if rounded:
        shape.adjustments[0] = .07
    shape._element.spPr.append(OxmlElement("a:effectLst"))
    return shape


def text(slide, x, y, w, h, content, size=16, color="ink", bold=False, align=None):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = shape.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.margin_top = frame.margin_bottom = frame.margin_left = frame.margin_right = 0
    frame.vertical_anchor = MSO_ANCHOR.TOP
    for i, line in enumerate(content.split("\n")):
        p = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        p.space_before = Pt(0)
        p.space_after = Pt(3)
        p.line_spacing = 1.13
        if align is not None:
            p.alignment = align
        run = p.add_run()
        run.text = line
        run.font.name = FONT
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = RGBColor.from_string(C.get(color, color))
    return shape


def arrow(slide, x1, y1, x2, y2, color):
    connector = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    connector.line.color.rgb = RGBColor.from_string(C[color])
    connector.line.width = Pt(1.2)
    end = OxmlElement("a:tailEnd")
    end.set("type", "triangle")
    end.set("w", "sm")
    end.set("len", "sm")
    connector._element.spPr.find(qn("a:ln")).append(end)


def base(title, subtitle):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = RGBColor.from_string(C["white"])
    text(slide, .55, .34, 11, .2, "DATASAURUS", size=10, color="purple", bold=True)
    text(slide, .55, .82, 12.2, .55, title, size=30, bold=True)
    text(slide, .55, 1.43, 12.2, .35, subtitle, size=16, color="muted")
    rect(slide, .55, 6.93, 12.23, .008, "line")
    text(slide, .55, 7.10, 9.5, .20, "[Team / owner]  |  Week of [date]", size=10, color="muted")
    return slide


s = base("Data catalog", "Site structure and business use")
text(s, .55, 1.92, 7.6, .28, "Site structure", size=13, bold=True)
text(s, 8.85, 1.92, 3.93, .28, "Business impact", size=13, bold=True)

# A browser outline: navigation and page responsibilities remain editable.
rect(s, .55, 2.32, 7.6, 4.28, "white", "line", rounded=True)
rect(s, .56, 2.33, 7.58, .40, "lavender")
text(s, .75, 2.43, 5.0, .20, "Datasaurus", size=11, color="purple", bold=True)
rect(s, .56, 2.74, 1.52, 3.84, "light")
text(s, .74, 2.96, 1.15, .24, "Catalog", size=12, bold=True)
rect(s, .73, 3.34, 1.17, .33, "white", "line", rounded=True)
text(s, .83, 3.43, .97, .18, "Search tables", size=9.5, color="muted")
for i, label in enumerate(["Orders", "Customers", "Revenue"]):
    if i == 0:
        rect(s, .73, 3.93 + i * .45, 1.17, .32, "lavender", rounded=True)
    text(s, .83, 4.02 + i * .45, .97, .20, label, size=10.5, color="purple" if i == 0 else "muted", bold=i == 0)
text(s, 2.31, 2.95, 5.5, .25, "Selected table", size=14, bold=True)
text(s, 2.31, 3.30, 5.5, .20, "Owner and business definition", size=10.5, color="muted")

rows = [
    ("Overview", "Table purpose and ownership", "green", 2.99),
    ("Attributes", "Field definitions and calculations", "green", 2.99),
    ("Lineage", "Upstream and downstream dependencies", "blue", 4.45),
    ("Quality", "Checks, exceptions and run history", "amber", 5.91),
    ("Impact", "Affected teams and points of contact", "amber", 5.91),
]
for i, (label, detail, color, target_y) in enumerate(rows):
    y = 3.75 + i * .46
    rect(s, 2.30, y, 5.57, .36, "white", "line", rounded=True)
    text(s, 2.43, y + .095, 1.18, .20, label, size=10.8, color="purple", bold=True)
    text(s, 3.65, y + .095, 4.02, .20, detail, size=10.8, color="muted")
    arrow(s, 7.92, y + .18, 8.77, target_y, color)
text(s, 2.31, 6.31, 2.5, .18, "Create time", size=9.5, color="muted")
text(s, 5.45, 6.31, 2.4, .18, "Update time", size=9.5, color="muted", align=PP_ALIGN.RIGHT)

cards = [
    (2.32, "Revenue", "Which definition should sales\nand finance use?", "Support consistent growth and pricing decisions.", "green"),
    (3.78, "Cost", "Can teams trace and reuse information\nwith less manual work?", "Reduce duplicate analysis and investigation.", "blue"),
    (5.24, "Risk", "Who is affected by a change\nor a failed quality check?", "Identify reporting exposure before release.", "amber"),
]
for y, label, question, benefit, color in cards:
    rect(s, 8.85, y, 3.93, 1.30, "white", "line", rounded=True)
    rect(s, 8.85, y + .12, .045, 1.06, color)
    text(s, 9.05, y + .16, 3.50, .25, label, size=16, color=color, bold=True)
    text(s, 9.05, y + .49, 3.50, .48, question, size=13)
    text(s, 9.05, y + 1.04, 3.50, .20, benefit, size=10.5, color="muted")

s.notes_slide.notes_text_frame.text = (
    "The left side is the site outline, not a screenshot of a live company dataset. "
    "Overview covers table purpose and ownership; Attributes covers field definitions and calculation logic. "
    "Lineage shows dependencies; Quality shows recorded rule results; Impact combines affected assets, teams and contacts. "
    "Revenue: shared sales and finance definitions can support consistent pricing, customer and growth analysis. "
    "Cost: reuse and traceability can reduce duplicate analysis and manual investigation. "
    "Risk: change impact and quality exceptions help identify reporting exposure and missed dependencies. "
    "These are business uses to validate. No revenue uplift, cost saving or incident reduction has been measured. "
    "The clickable site currently uses demonstration records. The real Databricks connection and daily ingestion are not implemented. "
    "Owner details are kept in the shared summary area. Contacts are included in Impact, and an email address copies when clicked."
)

s = base("Progress and next steps", "Current delivery, next week’s work and business impact")
x, y, w = .55, 2.14, 12.23
widths = [1.65, 3.75, 3.62, 3.21]
headings = ["Workstream", "Completed", "Next week", "Business impact"]
rect(s, x, y, w, .48, "lavender")
offset = x
for width, label in zip(widths, headings):
    text(s, offset + .15, y + .14, width - .30, .24, label, size=12.5, color="purple", bold=True)
    offset += width

progress = [
    ("Catalog &\nownership", "Five linked views; owner details,\ncopy-email links and admin editing.",
     "Review definitions and ownership\nfor one sales or revenue dataset.",
     "Revenue / cost\nShared definitions; less\nduplicate analysis."),
    ("Lineage &\nchange", "Table and field lineage; impact\nby attribute, team and contact.",
     "Validate one source-to-report path\nwith the team that owns it.",
     "Cost / risk\nFaster investigation; clearer\nchange dependencies."),
    ("Quality\nreporting", "Compact DQX result view; filters,\nrun history and metric mapping.",
     "Confirm UC tables and access;\ntest one read-only results pull.",
     "Cost / risk\nDaily exception visibility;\nless manual monitoring."),
]
for i, values in enumerate(progress):
    row_y = y + .48 + i * 1.12
    rect(s, x, row_y, w, 1.12, "light" if i % 2 == 0 else "white")
    rect(s, x, row_y + 1.11, w, .008, "line")
    offset = x
    for j, (width, value) in enumerate(zip(widths, values)):
        text(s, offset + .15, row_y + .22, width - .30, .83, value,
             size=13 if j == 0 else 12.4, bold=j == 0, color="ink" if j < 3 else "muted")
        offset += width

rect(s, .55, 6.26, 12.23, .43, "lavender", rounded=True)
text(s, .75, 6.39, 11.83, .22, "Next milestone: one verified daily results feed from Unity Catalog.", size=13, color="purple", bold=True)
s.notes_slide.notes_text_frame.text = (
    "Completed means implemented and checked locally: catalog browsing, ownership, role-based edits, "
    "table/attribute lineage, impact contacts, and the DQX-style reporting view. "
    "The DQX adapter has unit coverage for overlapping error/warning populations, empty or skipped checks, "
    "historical execution identity and exact rule-version matching. No company Databricks connection was tested. "
    "Next week is a proposed work sequence, not an already scheduled background job: choose one business dataset, "
    "review its definitions and owners, validate a dependency path, then confirm the DQX version, source tables "
    "and SQL warehouse access before one read-only ingestion test. If access is unavailable, finish the source "
    "mapping and access handoff rather than reporting integration as complete. "
    "Business impact is the value to measure after a pilot; no financial outcome is claimed. "
    "Useful baselines are time to find a definition, time to assess a field change, manual quality-review effort "
    "and time from a quality exception to the responsible team. "
    "Keep this slide separate from the structure page for weekly updates; the former page-by-page appendix "
    "has been absorbed into the first slide. Replace the team and reporting-week placeholders before presenting."
)

output = OUT / "datasaurus-report.pptx"
prs.save(output)
print(output)
