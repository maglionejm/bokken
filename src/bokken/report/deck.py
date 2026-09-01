"""PPTX renderer in the house workshop grammar.

Modeled on the Vatios Next-5 deliverable: kicker + statement title + footer
with page numbers, real tables (dark header, zebra rows, colored verdict
cells), chip rows for process, a HILL banner for the concept, and an
action-oriented close. Every figure comes from the Journal.
"""

from __future__ import annotations

import contextlib
import re
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

from bokken.report.context import ReportContext

INK = RGBColor(0x1F, 0x24, 0x30)
GRAY = RGBColor(0x6B, 0x72, 0x80)
ACCENT = RGBColor(0xC7, 0x3E, 0x3A)
ACCENT_DARK = RGBColor(0x8A, 0x2B, 0x28)
GREEN = RGBColor(0x2F, 0x6F, 0x4E)
AMBER = RGBColor(0xB3, 0x76, 0x2D)
PAPER = RGBColor(0xFA, 0xF7, 0xF2)
LIGHT = RGBColor(0xF1, 0xEC, 0xE2)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Helvetica Neue"

VERDICT_COLORS = {
    "supported": GREEN,
    "works": GREEN,
    "green": GREEN,
    "proceed": GREEN,
    "contradicted": ACCENT,
    "broken": ACCENT,
    "red": ACCENT,
    "kill": ACCENT,
    "untested": GRAY,
    "unclear": GRAY,
    "iterate": AMBER,
    "amber": AMBER,
}

PAGE_W, PAGE_H = Inches(13.333), Inches(7.5)
MARGIN = Inches(0.6)
BODY_W = Inches(12.13)
ROW_H = Inches(0.34)
BANNER_H = Inches(0.9)
CHIP_W = Inches(1.95)


class Deck:
    def __init__(self, ctx: ReportContext) -> None:
        self.ctx = ctx
        self.prs = Presentation()
        self.prs.slide_width = PAGE_W
        self.prs.slide_height = PAGE_H
        self.page = 0

    # ---- primitives (workshop grammar) -------------------------------------

    def slide(self):
        return self.prs.slides.add_slide(self.prs.slide_layouts[6])

    def text(self, s, x, y, w, h):
        frame = s.shapes.add_textbox(x, y, w, h).text_frame
        frame.word_wrap = True
        return frame

    def para(
        self,
        frame,
        text,
        *,
        size=10.5,
        bold=False,
        color=INK,
        before=2,
        first=False,
        align=PP_ALIGN.LEFT,
    ):
        p = frame.paragraphs[0] if first and not frame.paragraphs[0].runs else frame.add_paragraph()
        p.space_before = Pt(0 if first else before)
        p.alignment = align
        r = p.add_run()
        r.text = text
        r.font.name = FONT
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        return p

    def rect(self, s, x, y, w, h, fill):
        shape = s.shapes.add_shape(1, x, y, w, h)
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
        shape.line.fill.background()
        shape.shadow.inherit = False
        return shape

    def header(self, s, kicker: str, title: str):
        self.page += 1
        k = self.text(s, MARGIN, Inches(0.4), BODY_W, Inches(0.3))
        self.para(k, kicker.upper(), size=11, bold=True, color=ACCENT, first=True)
        t = self.text(s, MARGIN, Inches(0.72), BODY_W, Inches(0.7))
        self.para(t, title, size=25, bold=True, first=True)
        f = self.text(s, MARGIN, Inches(7.08), BODY_W, Inches(0.3))
        self.para(
            f,
            f"Bokken · session {self.ctx.model.name} — generated from the Journal, no manual "
            f"edits        {self.page:02d}",
            size=8,
            color=GRAY,
            first=True,
        )

    def block_title(self, frame, text, *, first=True):
        self.para(frame, text, size=12.5, bold=True, color=ACCENT_DARK, first=first)

    def bullets(self, frame, items, *, size=10, first=False):
        for i, item in enumerate(items):
            self.para(frame, f"•  {item}", size=size, first=first and i == 0)

    def table(
        self,
        s,
        x,
        y,
        w,
        rows_data,
        col_widths,
        *,
        header_size=10,
        body_size=9.5,
        row_h=ROW_H,
        cell_colors=None,
    ):
        """rows_data: first row = header; cell_colors: {(r, c): RGBColor} bolds too."""
        n_rows = len(rows_data)
        gt = s.shapes.add_table(n_rows, len(rows_data[0]), x, y, w, Emu(int(row_h) * n_rows)).table
        for ci, cw in enumerate(col_widths):
            gt.columns[ci].width = cw
        for ri, row in enumerate(rows_data):
            gt.rows[ri].height = row_h
            for ci, val in enumerate(row):
                cell = gt.cell(ri, ci)
                cell.margin_left, cell.margin_right = Inches(0.06), Inches(0.06)
                cell.margin_top = cell.margin_bottom = Inches(0.02)
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                cell.fill.solid()
                cell.fill.fore_color.rgb = INK if ri == 0 else (PAPER if ri % 2 else LIGHT)
                frame = cell.text_frame
                frame.word_wrap = True
                r = frame.paragraphs[0].add_run()
                r.text = str(val)
                r.font.name = FONT
                r.font.size = Pt(header_size if ri == 0 else body_size)
                r.font.bold = ri == 0
                r.font.color.rgb = WHITE if ri == 0 else INK
                if cell_colors and (ri, ci) in cell_colors:
                    r.font.color.rgb = cell_colors[(ri, ci)]
                    r.font.bold = True
        return gt

    def banner(self, s, y, text, *, fill=INK, size=11, h=BANNER_H):
        bar = self.rect(s, MARGIN, y, BODY_W, h, fill)
        frame = bar.text_frame
        frame.word_wrap = True
        frame.margin_left = frame.margin_right = Inches(0.18)
        r = frame.paragraphs[0].add_run()
        r.text = text
        r.font.name = FONT
        r.font.size = Pt(size)
        r.font.color.rgb = WHITE
        return bar

    def chip_row(self, s, y, items, *, width=CHIP_W):
        x = MARGIN
        for label, body in items:
            bar = self.rect(s, x, y, width, Inches(0.5), INK)
            frame = bar.text_frame
            p = frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            r = p.add_run()
            r.text = label
            r.font.name, r.font.size, r.font.bold, r.font.color.rgb = FONT, Pt(10.5), True, WHITE
            under = self.text(s, x, y + Inches(0.6), width, Inches(1.5))
            self.para(under, body, size=9, first=True)
            x += width + Inches(0.08)

    def _verdict_cells(self, rows, col):
        return {
            (ri, col): VERDICT_COLORS[str(row[col]).lower()]
            for ri, row in enumerate(rows)
            if ri > 0 and str(row[col]).lower() in VERDICT_COLORS
        }

    # ---- slides -------------------------------------------------------------

    def cover(self):
        m, c = self.ctx.model, self.ctx
        s = self.slide()
        self.rect(s, 0, 0, PAGE_W, PAGE_H, PAPER)
        self.rect(s, 0, Inches(6.9), PAGE_W, Inches(0.6), ACCENT)
        f = self.text(s, MARGIN, Inches(1.9), BODY_W, Inches(3.0))
        self.para(
            f, "BOKKEN · DESIGN THINKING RUN REPORT", size=16, bold=True, color=ACCENT, first=True
        )
        outcome = (m.recommendation.resolution if m.recommendation else m.stage).upper()
        headline = c.headline
        self.para(
            f,
            f"{outcome} — {headline}",
            size=30 if len(headline) < 90 else 24,
            bold=True,
            before=10,
        )
        counts = c.register_counts
        self.para(
            f,
            f"Session '{m.name}' · {len(m.evidence)} evidence items · {len(m.options)} options · "
            f"register {counts['supported']}/{counts['contradicted']}/{counts['untested']} "
            f"(supported/contradicted/untested) · ~${c.total_cost_usd:,.2f}",
            size=13,
            color=GRAY,
            before=12,
        )
        if m.dojo_banner:
            b = self.text(s, MARGIN, Inches(5.6), BODY_W, Inches(1.0))
            self.para(
                b,
                "SIMULATED RUN — autonomous run against a governed synthetic persona panel; all "
                "persona contributions are simulated and evidence-bounded. Flagged decisions "
                "require validation with real users.",
                size=10.5,
                bold=True,
                first=True,
            )

    def executive_summary(self):
        m, c = self.ctx.model, self.ctx
        s = self.slide()
        outcome = m.recommendation.resolution if m.recommendation else "in flight"
        self.header(
            s, "executive summary", f"The verdict is {outcome} — the whole story in one table"
        )
        rows = [["What", "Result", "So what"]]
        counts = c.register_counts
        if m.problem_statement:
            rows.append(
                [
                    "Problem chosen",
                    m.problem_statement.resolution[:120],
                    "selected on evidence + opportunity coverage",
                ]
            )
        if c.opportunities:
            rows.append(
                ["Top opportunity", c.opportunities[0][:120], "Ulwick score drives the focus"]
            )
        if m.concept:
            rows.append(
                ["Concept advanced", m.concept.resolution[:120], "won three firewalled lenses"]
            )
        if c.ui_feature_results:
            broken = sum(1 for r in c.ui_feature_results if r.get("verdict") == "broken")
            rows.append(
                [
                    "Product tested",
                    f"{len(c.ui_feature_results)} features exercised, {broken} broken",
                    "fix list in Next Actions",
                ]
            )
        rows.append(
            [
                "Register",
                f"{counts['supported']} supported · {counts['contradicted']} contradicted · "
                f"{counts['untested']} untested",
                f"verdict: {outcome}",
            ]
        )
        rows.append(
            [
                "Cost",
                f"${c.total_cost_usd:,.2f} · {sum(u.calls for u in c.usage)} model calls",
                "list-price estimate, fully journaled",
            ]
        )
        self.table(
            s,
            MARGIN,
            Inches(1.6),
            BODY_W,
            rows,
            [Inches(2.2), Inches(6.0), Inches(3.93)],
            row_h=Inches(0.62),
        )
        if m.recommendation and m.recommendation.requires_real_validation:
            self.banner(
                s,
                Inches(6.15),
                "Validation guardrail: synthetic personas scored these hypotheses; they do not "
                "validate them. Final judgment needs real users.",
                size=10,
                h=Inches(0.6),
            )

    def anatomy(self):
        m, c = self.ctx.model, self.ctx
        s = self.slide()
        self.header(s, "how this run worked", "Six stages, three panels, every actor journaled")
        stages = [
            ("EMPATHIZE", "interviews + UI tests + Ulwick outcome ranking"),
            ("DEFINE", "insights -> problem statement, losers preserved"),
            ("IDEATE", "quota divergence; 3 firewalled lenses converge"),
            ("PROTOTYPE", "web research; assumption register; artifacts"),
            ("TEST", "fresh panel scores register; verdict"),
            ("COMPLETE", "dossier + handoff + this report"),
        ]
        self.chip_row(s, Inches(1.55), stages)
        by_panel: dict[str, list] = {}
        for pc in m.personas:
            by_panel.setdefault(pc.panel_kind, []).append(pc)
        frame = self.text(s, MARGIN, Inches(3.6), Inches(7.4), Inches(3.2))
        self.block_title(frame, "The cast (synthetic, labeled)")
        for kind in ("interview", "ideation", "test"):
            cast = by_panel.get(kind, [])
            if cast:
                names = "; ".join(f"{pc.name} ({pc.role})" for pc in cast)
                self.para(frame, f"{kind}: {names}"[:230], size=8.5, before=4)
        right = self.text(s, Inches(8.2), Inches(3.6), Inches(4.5), Inches(3.2))
        self.block_title(right, "Models")
        self.bullets(
            right,
            [f"{u.model}: {u.calls} calls, ${u.cost_usd:,.2f}" for u in c.usage]
            + [f"loop-backs: {len(c.loopbacks)}"],
            size=9.5,
        )

    def ui_tests(self):
        c = self.ctx
        if not c.ui_feature_results:
            return
        s = self.slide()
        broken = sum(1 for r in c.ui_feature_results if r.get("verdict") == "broken")
        self.header(
            s,
            "observed · functional ui tests",
            f"{len(c.ui_feature_results)} features exercised in a real browser — {broken} broken",
        )
        rows = [["Feature", "Verdict", "Finding (observed)"]]
        for r in c.ui_feature_results[:8]:
            rows.append(
                [
                    r.get("feature", "")[:40],
                    r.get("verdict", "?"),
                    (r.get("finding") or f"{len(r.get('steps', []))} step(s), see report")[:110],
                ]
            )
        shot = None
        for r in c.ui_feature_results:
            if r.get("verdict") == "broken" and r.get("screenshot"):
                candidate = c.session_dir / "artifacts" / "ui" / r["screenshot"]
                if candidate.exists():
                    shot = candidate
                    break
        table_w = Inches(8.3) if shot else BODY_W
        self.table(
            s,
            MARGIN,
            Inches(1.6),
            table_w,
            rows,
            [Inches(2.3), Inches(1.0), table_w - Inches(3.3)],
            row_h=Inches(0.58),
            cell_colors=self._verdict_cells(rows, 1),
        )
        if shot:
            with contextlib.suppress(OSError):
                s.shapes.add_picture(str(shot), Inches(9.1), Inches(1.6), width=Inches(3.6))
                cap = self.text(s, Inches(9.1), Inches(4.35), Inches(3.6), Inches(0.4))
                self.para(
                    cap, "End state of a broken feature (observed)", size=8, color=GRAY, first=True
                )

    def opportunities(self):
        c = self.ctx
        if not c.opportunities:
            return
        s = self.slide()
        self.header(s, "empathize · output", "Where the underserved demand is (Ulwick-scored)")
        rows = [["#", "Outcome", "Opp", "Band"]]
        for i, statement in enumerate(c.opportunities[:8], 1):
            score = re.search(r"opportunity (\d+(?:\.\d+)?)", statement)
            tail = statement[statement.find("opportunity") :] if "opportunity" in statement else ""
            band = re.search(r"\(([^)]+)\)", tail)
            clean = re.sub(r"^O\d+: ", "", statement.split(" - opportunity")[0])
            rows.append(
                [
                    str(i),
                    clean[:105],
                    score.group(1) if score else "-",
                    (band.group(1) if band else "-")[:22],
                ]
            )
        colors = {}
        for ri, row in enumerate(rows):
            if ri > 0 and "underserved" in str(row[3]):
                colors[(ri, 3)] = ACCENT if "sever" in str(row[3]) else AMBER
        self.table(
            s,
            MARGIN,
            Inches(1.6),
            BODY_W,
            rows,
            [Inches(0.5), Inches(8.3), Inches(0.9), Inches(2.4)],
            row_h=Inches(0.55),
            cell_colors=colors,
        )
        note = self.text(s, MARGIN, Inches(6.35), BODY_W, Inches(0.6))
        self.para(
            note,
            "Opp = Importance + max(Importance - Satisfaction, 0), mean across personas; "
            ">=15 severely underserved, 12-15 underserved.",
            size=9,
            color=GRAY,
            first=True,
        )

    def concept(self):
        m, c = self.ctx.model, self.ctx
        if not m.concept:
            return
        s = self.slide()
        self.header(s, "the concept", "What advances, and why it won")
        hill = c.hill
        if hill.get("who") or hill.get("what"):
            hill_text = (
                f"HILL — WHO {hill.get('who', '?')[:80]} · WHAT {hill.get('what', '?')[:90]} · "
                f"WOW {hill.get('wow', '?')[:90]}"
            )
            self.banner(s, Inches(1.5), hill_text, size=10.5)
        else:
            self.banner(s, Inches(1.5), m.concept.resolution[:260], size=10.5)
        body_y = Inches(2.65)
        left = self.text(s, MARGIN, body_y, Inches(6.0), Inches(3.1))
        self.block_title(left, "Why it won (lens positions)")
        why = [v["position"][:150] for v in c.lens_votes if v.get("position")][:3]
        self.bullets(left, why or [m.concept.resolution[:200]], size=9.5)
        right = self.text(s, Inches(6.8), body_y, Inches(5.9), Inches(3.1))
        self.block_title(right, "Dissent on record")
        if c.dissent:
            self.bullets(
                right,
                [f"{d.get('actor', '')}: {d.get('reservation', '')[:150]}" for d in c.dissent[:3]],
                size=9.5,
            )
        else:
            self.para(right, "(none)", size=9.5)
        if hill.get("hypothesis"):
            self.banner(
                s,
                Inches(5.95),
                f"Hypothesis: {hill['hypothesis'][:230]}",
                fill=ACCENT_DARK,
                size=10,
                h=Inches(0.75),
            )

    def research(self):
        mr = self.ctx.market_research
        if not mr:
            return
        s = self.slide()
        self.header(
            s, "reported · concept research", "The market, on the record (every claim sourced)"
        )
        if mr.get("competitors"):
            rows = [["Competitor / prior art", "What it does", "Overlap with the concept"]]
            for comp in mr["competitors"][:5]:
                rows.append(
                    [
                        comp.get("name", "")[:34],
                        comp.get("what", "")[:60],
                        comp.get("overlap", "")[:52],
                    ]
                )
            self.table(
                s,
                MARGIN,
                Inches(1.55),
                BODY_W,
                rows,
                [Inches(3.0), Inches(5.0), Inches(4.13)],
                row_h=Inches(0.5),
            )
        frame = self.text(s, MARGIN, Inches(4.45), BODY_W, Inches(2.4))
        if mr.get("market_signals"):
            self.block_title(frame, "Market signals (sourced)")
            self.bullets(frame, [x.get("stat", "")[:170] for x in mr["market_signals"][:4]], size=9)
        if mr.get("differentiation_risks"):
            self.block_title(frame, "Differentiation risks", first=False)
            self.bullets(frame, [str(x)[:170] for x in mr["differentiation_risks"][:2]], size=9)

    def register(self):
        m, c = self.ctx.model, self.ctx
        if not m.assumptions:
            return
        s = self.slide()
        counts = c.register_counts
        self.header(
            s,
            "test · output",
            f"Register: {counts['supported']} supported · {counts['contradicted']} contradicted "
            f"· {counts['untested']} untested",
        )
        rows = [["Assumption", "Impact", "Verdict"]]
        ordered = sorted(m.assumptions.values(), key=lambda a: (a.score or "z") != "contradicted")
        for a in list(ordered)[:9]:
            rows.append([a.statement[:110], a.impact, a.score or "untested"])
        self.table(
            s,
            MARGIN,
            Inches(1.6),
            BODY_W,
            rows,
            [Inches(9.3), Inches(1.2), Inches(1.63)],
            row_h=Inches(0.52),
            cell_colors=self._verdict_cells(rows, 2),
        )

    def deliberation(self):
        c = self.ctx
        if not (c.lens_votes or c.skeptic_challenge):
            return
        s = self.slide()
        self.header(s, "how the agents argued", "Three lenses, one skeptic, dissent preserved")
        by_lens: dict[str, list[str]] = {}
        for vote in c.lens_votes:
            by_lens.setdefault(vote["lens"], []).append(vote["position"])
        left = self.text(s, MARGIN, Inches(1.55), Inches(6.4), Inches(5.1))
        for i, (lens, positions) in enumerate(list(by_lens.items())[:3]):
            self.block_title(left, f"{lens} ({len(positions)} votes)", first=i == 0)
            self.para(left, positions[0][:230], size=8.5)
        right = self.text(s, Inches(7.2), Inches(1.55), Inches(5.5), Inches(5.1))
        if c.skeptic_challenge:
            self.block_title(right, "The skeptic, verbatim")
            self.para(right, c.skeptic_challenge[:380], size=8.5)
        executed = [mv for mv in c.kata_moves if mv["executed"]]
        if executed:
            self.block_title(right, f"Kata interventions ({len(executed)})", first=False)
            self.bullets(right, [f"{mv['move']} ({mv['stage']})" for mv in executed[:5]], size=8.5)

    def next_actions(self):
        c = self.ctx
        if not c.next_actions:
            return
        s = self.slide()
        self.header(s, "action oriented", "What to do next, in order")
        rows = [["#", "Action"]]
        for i, action in enumerate(c.next_actions[:7], 1):
            rows.append([str(i), action[:165]])
        self.table(
            s, MARGIN, Inches(1.6), BODY_W, rows, [Inches(0.6), Inches(11.53)], row_h=Inches(0.68)
        )

    def appendix(self):
        c = self.ctx
        s = self.slide()
        self.header(s, "appendix", "Specifications handed off + the paper trail")
        frame = self.text(s, MARGIN, Inches(1.6), BODY_W, Inches(4.9))
        if c.spec_entries:
            for i, entry in enumerate(c.spec_entries):
                self.para(
                    frame,
                    f"{entry.capability} — {entry.sentence}"[:220],
                    size=10,
                    first=i == 0,
                    before=6,
                )
                self.para(frame, entry.path, size=8, color=GRAY)
        else:
            self.para(
                frame,
                f"No handoff package: {c.handoff_refusal or 'not generated yet'}.",
                size=10.5,
                first=True,
            )
        self.block_title(frame, "On file", first=False)
        records = [
            *c.dossier_paths,
            "journal.jsonl (hash-chained)",
            "artifacts/ (hashed, journaled)",
        ]
        self.bullets(frame, records, size=9.5)

    def render(self, out_path: Path) -> None:
        self.cover()
        self.executive_summary()
        self.anatomy()
        self.ui_tests()
        self.opportunities()
        self.concept()
        self.research()
        self.register()
        self.deliberation()
        self.next_actions()
        self.appendix()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        self.prs.save(str(out_path))


def render_deck(ctx: ReportContext, out_path: Path) -> None:
    Deck(ctx).render(out_path)
