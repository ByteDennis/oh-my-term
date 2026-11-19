"""Build the editable two-page requirements discussion deck.

Install the optional report dependency: python -m pip install python-pptx
All slide text and shapes remain editable. No production-readiness claims or
performance numbers are assumed. Bracketed fields are deliberate placeholders.
"""
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt

OUT = Path(__file__).parent
FONT = "Noto Sans CJK SC"
C = {"ink": "243149", "muted": "6A7890", "purple": "6554C0", "line": "E3E7EF",
     "light": "F7F8FC", "lavender": "F1EEFC", "white": "FFFFFF", "green": "40846E"}
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333333), Inches(7.5)
prs.core_properties.title = "元数据工作台 — 需求对齐与页面职责"
prs.core_properties.subject = "Design Proof of Concept · 需求讨论模板"
prs.core_properties.author = ""


def rect(slide, x, y, w, h, color="white", border=None, rounded=False):
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
                                Inches(x), Inches(y), Inches(w), Inches(h))
    box.fill.solid()
    box.fill.fore_color.rgb = RGBColor.from_string(C.get(color, color))
    if border:
        box.line.color.rgb = RGBColor.from_string(C.get(border, border))
        box.line.width = Pt(.8)
    else:
        box.line.fill.background()
    if rounded:
        box.adjustments[0] = .08
    return box


def text(slide, x, y, w, h, content, size=16, color="ink", bold=False, align=None):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = shape.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = 0
    frame.margin_top = frame.margin_bottom = 0
    frame.vertical_anchor = MSO_ANCHOR.TOP
    for i, line in enumerate(content.split("\n")):
        p = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        p.space_before = Pt(0)
        p.space_after = Pt(5)
        p.line_spacing = 1.18
        if align is not None:
            p.alignment = align
        run = p.add_run()
        run.text = line
        run.font.name = FONT
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = RGBColor.from_string(C.get(color, color))
        # Specify East Asian typeface so Chinese renders consistently on export.
        ea = OxmlElement("a:ea")
        ea.set("typeface", FONT)
        run._r.get_or_add_rPr().append(ea)
    return shape


def base(label):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = RGBColor.from_string(C["white"])
    rect(slide, .55, .37, .11, .17, "purple", rounded=True)
    text(slide, .77, .33, 7.5, .25, label, size=10, color="purple", bold=True)
    return slide


# Page 1: a requirements conversation, not a feature or technology presentation.
s = base("ATLAS  /  METADATA WORKSPACE  /  需求讨论稿")
text(s, .55, .83, 12.1, .58, "元数据工作台：先对齐需求，再验证设计", size=28, bold=True)
text(s, .55, 1.51, 12.0, .42, "一个入口，回答数据含义、来源、变更影响与责任归属", size=16, color="muted")

for x in (.55, 4.70, 8.85):
    rect(s, x, 2.18, 3.93, 2.95, "light", border="line", rounded=True)

text(s, .79, 2.42, 3.45, .32, "谁来用？", size=18, bold=True)
text(s, .79, 3.01, 3.45, .35, "业务用户  ·  只读查询", size=16, bold=True)
text(s, .79, 3.43, 3.40, .48, "查定义、追溯来源、评估影响", size=13.5, color="muted")
text(s, .79, 4.08, 3.45, .35, "管理员  ·  维护知识", size=16, bold=True)
text(s, .79, 4.50, 3.40, .45, "维护定义、关系、规则与归属", size=13.5, color="muted")

text(s, 4.94, 2.42, 3.45, .32, "需要回答什么？", size=18, bold=True)
for y, question, detail in [
    (3.00, "数据代表什么？", "业务定义 / 字段 / 转换口径"),
    (3.67, "数据从哪里来？", "表与字段的上下游关系"),
    (4.34, "改动影响谁？", "下游资产 / 业务团队 / 联系人"),
]:
    text(s, 4.94, y, 3.45, .30, question, size=15.5, bold=True)
    text(s, 4.94, y + .32, 3.45, .30, detail, size=12.5, color="muted")

text(s, 9.09, 2.42, 3.45, .32, "这次先做什么？", size=18, bold=True)
text(s, 9.09, 3.01, 3.45, .30, "当前 Design PoC", size=13.5, color="purple", bold=True)
text(s, 9.09, 3.41, 3.35, .72, "用样例数据验证\n信息组织与浏览、维护方式", size=15)
text(s, 9.09, 4.30, 3.45, .28, "后续阶段再接入", size=12.5, color="muted")
text(s, 9.09, 4.63, 3.45, .35, "真实数据库采集、定期质量检查", size=12.5, color="muted")

text(s, .55, 5.54, 12, .35, "本次希望对齐的需求", size=17, bold=True)
for x, question, placeholder in [
    (.55, "优先解决哪个业务场景？", "[优先业务场景]"),
    (4.70, "必须提供哪些信息？", "[必需信息 / 表或字段粒度]"),
    (8.85, "从哪里开始试点？", "[试点范围 / 业务负责人]"),
]:
    rect(s, x, 6.03, 3.93, .76, "lavender", rounded=True)
    text(s, x + .18, 6.15, 3.57, .26, question, size=13.5, color="purple", bold=True)
    text(s, x + .18, 6.49, 3.57, .22, placeholder, size=10.5, color="muted")
text(s, .55, 7.05, 9.7, .22, "汇报人：[姓名]    日期：[YYYY-MM-DD]    状态：需求与试点范围待确认", size=9.5, color="muted")
text(s, 11.48, 7.04, 1.3, .22, "主汇报页", size=9.5, color="muted", align=PP_ALIGN.RIGHT)
s.notes_slide.notes_text_frame.text = (
    "建议讲述约45秒。先说明目标：让业务用户在一个入口了解数据、追踪来源，并在变更前知道影响谁。"
    "本次讨论不展开技术栈与功能细节，也不宣称已有真实数据库接入或自动质量执行。"
    "希望确认三件事：优先业务场景、必需信息及粒度、试点范围与业务负责人。"
    "将方括号占位符替换为实际信息；如果暂未确认，保留为本次讨论的问题。"
)

# Page 2: compact page responsibilities; discussion prompts rather than a backlog.
s = base("ATLAS  /  METADATA WORKSPACE  /  附页")
text(s, .55, .83, 12.1, .58, "五个视图，各自回答一个问题", size=28, bold=True)
text(s, .55, 1.51, 12.0, .42, "同一工作台内切换；联系人与影响分析放在一起，Owner 保持低调可见", size=15, color="muted")

x0, y0, total = .55, 2.18, 12.23
columns = [2.12, 4.18, 5.93]
rect(s, x0, y0, total, .48, "lavender", rounded=False)
for x, w, label in [(x0, columns[0], "视图"), (x0 + columns[0], columns[1], "帮助用户回答"), (x0 + columns[0] + columns[1], columns[2], "展示的信息 / 交互（需求讨论项）")]:
    text(s, x + .16, y0 + .12, w - .32, .27, label, size=11.5, color="purple", bold=True)

rows = [
    ("Overview", "这张表是什么，谁负责？", "业务定义、业务域、简要 Owner 信息"),
    ("Attributes", "字段的业务含义和口径是什么？", "字段定义、类型、来源与转换逻辑"),
    ("Lineage", "数据从哪里来，流向哪里？", "表与字段的上游、下游关系"),
    ("Quality", "该检查什么，结果如何？", "规则定义、状态与记录；PoC 仅展示样例结果"),
    ("Impact", "变更影响谁，需要联系谁？", "受影响表 / 字段、业务团队与联系人；点击复制邮箱"),
]
for i, (view, question, detail) in enumerate(rows):
    y = y0 + .48 + i * .65
    rect(s, x0, y, total, .65, "light" if i % 2 == 0 else "white")
    rect(s, x0, y + .64, total, .008, "line")
    text(s, x0 + .16, y + .18, columns[0] - .32, .35, view, size=14, bold=True)
    text(s, x0 + columns[0] + .16, y + .19, columns[1] - .32, .35, question, size=13)
    text(s, x0 + columns[0] + columns[1] + .16, y + .19, columns[2] - .32, .38, detail, size=12.2, color="muted")

rect(s, .55, 6.29, 12.23, .55, "lavender", rounded=True)
text(s, .75, 6.44, 11.83, .25, "共用信息与权限：Owner 常驻概要区；联系人归入 Impact；业务用户只读，管理员维护。", size=12, color="purple")
text(s, .55, 7.05, 10.5, .22, "待确认：信息粒度、责任人定义、质量规则优先级，以及第一批试点范围。", size=9.5, color="muted")
text(s, 11.48, 7.04, 1.3, .22, "附页 · 视图职责", size=9.5, color="muted", align=PP_ALIGN.RIGHT)
s.notes_slide.notes_text_frame.text = (
    "只在老板追问页面范围时使用此附页。每个视图只讲它解决的业务问题，不逐项演示控件。"
    "People 不单设页面，联系信息并入 Impact；Owner 在概要区常驻，点击可查看联系方式，邮箱点击复制。"
    "Quality 当前只讨论规则定义与结果如何呈现，实际执行及定期调度属于未来阶段。"
    "这些是需求讨论项，不等同于已经获批的范围或已验证的业务成效。"
)

path = OUT / "requirements-alignment-template.pptx"
prs.save(path)
print(path)
