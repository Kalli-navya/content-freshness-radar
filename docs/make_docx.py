#!/usr/bin/env python3
"""Generate the shareable Word doc (Content_Freshness_Radar.docx) for the
hackathon organizing team. Run: python3 docs/make_docx.py"""

import os
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "dashboard.png")
OUT = os.path.join(HERE, "Content_Freshness_Radar.docx")

WIKI_BLUE = RGBColor(0x33, 0x66, 0xCC)
INK = RGBColor(0x20, 0x21, 0x22)
SUBTLE = RGBColor(0x54, 0x59, 0x5D)

doc = Document()

# Base font
style = doc.styles["Normal"]
style.font.name = "Calibri"
style.font.size = Pt(11)
style.font.color.rgb = INK


def heading(text, size, color=INK, space_before=14, space_after=6, bold=True):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    r = p.add_run(text)
    r.bold = bold
    r.font.size = Pt(size)
    r.font.color.rgb = color
    return p


def body(text, italic=False, color=INK, size=11, space_after=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    r = p.add_run(text)
    r.italic = italic
    r.font.size = Pt(size)
    r.font.color.rgb = color
    return p


def bullet(text, bold_prefix=None):
    p = doc.add_paragraph(style="List Bullet")
    if bold_prefix:
        r = p.add_run(bold_prefix)
        r.bold = True
        p.add_run(text)
    else:
        p.add_run(text)
    return p


# ---- Title block ----
heading("Content Freshness Radar", 26, WIKI_BLUE, space_before=0, space_after=2)
body("Making Wikipedia's obsolescence visible — and easy to fix.",
     italic=True, color=SUBTLE, size=12, space_after=2)
body("Hackathon submission overview", color=SUBTLE, size=10, space_after=10)

# ---- Challenge ----
heading("The challenge", 15, WIKI_BLUE)
body("Identify and flag outdated articles, obsolete illustrations and "
     "screenshots, and outdated graphics — to encourage the community to "
     "update them. An article may be factually accurate when written but become "
     "misleading over time: a statistic from 2012, an org chart of a "
     "restructured institution, or a political map from before an election. "
     "This obsolescence is usually invisible to readers, and those who notice a "
     "problem rarely have an easy way to act.")

# ---- Solution ----
heading("Our solution", 15, WIKI_BLUE)
body("Content Freshness Radar scans a topic area of a wiki and produces a "
     "color-coded, prioritized worklist of content that is genuinely out of "
     "date, with a one-click path to fix each item. It is built to look and "
     "feel native to the wiki, using the Wikimedia Codex design system.")

# ---- Screenshot ----
if os.path.exists(IMG):
    doc.add_picture(IMG, width=Inches(6.3))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap = body("The dashboard: freshness bands, priority ranking, and an "
               "\u201cUpdate\u201d button on every row.", italic=True,
               color=SUBTLE, size=9, space_after=10)
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER

# ---- Mapping table ----
heading("How it addresses the challenge (all five example projects)", 15, WIKI_BLUE)
rows = [
    ("Challenge example", "How we do it"),
    ("Color-code by how long since last update",
     "GREEN / YELLOW / ORANGE / RED bands from the last substantive edit"),
    ("Flag articles not updated in a long time",
     "Priority ranking = staleness \u00d7 pageviews \u00d7 topic volatility"),
    ("Identify outdated screenshots",
     "Images scored by last re-upload date + screenshot/graphic classification"),
    ("Identify outdated data in charts",
     "Detects {{As of|YYYY}} dated statements and surfaces the year (e.g. \u201cdata as of 2012\u201d)"),
    ("Encourage improvement of outdated content",
     "Every row has an \u201cUpdate\u201d button deep-linking to the editor; stale pages get a suggested {{Update}} template"),
]
table = doc.add_table(rows=0, cols=2)
table.style = "Light Grid Accent 1"
for i, (a, b) in enumerate(rows):
    cells = table.add_row().cells
    cells[0].text = a
    cells[1].text = b
    if i == 0:
        for c in cells:
            for para in c.paragraphs:
                for run in para.runs:
                    run.bold = True
body("", space_after=4)

# ---- Precision ----
heading("What makes it accurate (not just noisy)", 15, WIKI_BLUE)
body("The hard part of this challenge is precision — flagging stable content "
     "(a maths proof, a historical battle) erodes community trust. Two design "
     "choices keep the signal clean:")
bullet("A page's freshness clock is only reset by a real content edit. Minor "
       "edits, bot edits, reverts, and cosmetic tweaks are filtered out, so a "
       "page that only receives automated touches still surfaces as outdated.",
       bold_prefix="\u201cSubstantive edit\u201d detection. ")
bullet("Content that decays fast (elections, economies, demographics, software) "
       "and pages carrying {{As of}} dated statements or maintenance tags are "
       "boosted; stable topics are not. The dashboard shows why each page was "
       "flagged.", bold_prefix="Volatility weighting. ")

# ---- How it works ----
heading("How it works", 15, WIKI_BLUE)
bullet("Live MediaWiki Action API + Pageviews API for revisions, pageviews, "
       "categories, and images.", bold_prefix="Data: ")
bullet("Python, standard library only — no dependencies to install.",
       bold_prefix="Backend: ")
bullet("Vue 3 + Wikimedia Codex, loaded via an ES-module import map — no build "
       "step and no npm required.", bold_prefix="Frontend: ")
bullet("The same logic maps to the Wikimedia replica databases / dumps for "
       "whole-wiki analysis (grounded in the real MediaWiki 1.45 schema).",
       bold_prefix="Scale path: ")

# ---- Results ----
heading("Live results", 15, WIKI_BLUE)
body("Run on real English Wikipedia categories, the tool immediately surfaces "
     "genuine problems — for example Pacific Island Countries Trade Agreement, "
     "last substantively edited in 2013 (flagged RED), and Economy of India, "
     "still carrying a statistic marked \u201cas of 2012.\u201d")

# ---- Try it ----
heading("Try it in two commands", 15, WIKI_BLUE)
for line in [
    "python3 run_pipeline.py --category \"Economy of Asia\" --recursive --limit 30 --images",
    "cd webapp && python3 -m http.server 8777   # open http://localhost:8777",
]:
    p = doc.add_paragraph()
    r = p.add_run(line)
    r.font.name = "Consolas"
    r.font.size = Pt(9.5)
body("Point it at any category on any MediaWiki wiki with --wiki and --category.",
     color=SUBTLE, size=10)

# ---- Roadmap ----
heading("Status & roadmap", 15, WIKI_BLUE)
bullet("freshness bands, substantive-edit filtering, volatility weighting, "
       "pageview priority, recursive category scanning, image/screenshot "
       "scoring, {{As of}} dated-data detection, and the Codex dashboard.",
       bold_prefix="Working today: ")
bullet("parse chart/table data years from wikitext, a browser-extension overlay "
       "that color-codes pages live, and replica-DB/dump ingestion for full-wiki "
       "coverage.", bold_prefix="Next: ")

doc.save(OUT)
print("Wrote", OUT)
