"""Deterministic PDF + markdown from ScoreCard — fpdf2 + embedded chart PNGs."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from fpdf import FPDF
from PIL import Image

from app.skills.inspector_report.scripts import charts
from app.skills.inspector_report.scripts.labels import labels, recommendation_label

if TYPE_CHECKING:
    from app.schemas.inspector.scorecard import IntegritySummary, ScoreCard


def _font_path(filename: str) -> str | None:
    roots = [
        Path(__file__).resolve().parents[4] / "infra" / "fonts",
    ]
    try:
        import matplotlib

        roots.append(Path(matplotlib.get_data_path()) / "fonts" / "ttf")
    except Exception:
        pass
    for root in roots:
        candidate = root / filename
        if candidate.exists():
            return str(candidate)
    return None


def _ascii_safe(text: str) -> str:
    return (
        text.replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )


def _embed_png(pdf: FPDF, png: bytes, w: float = 180) -> None:
    img = Image.open(io.BytesIO(png))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    pdf.image(buf, w=w)
    pdf.set_x(pdf.l_margin)
    pdf.ln(2)


def build_markdown(
    scorecard: "ScoreCard",
    integrity: "IntegritySummary",
    language: str,
) -> str:
    L = labels(language)
    lines = [
        f"# {L['report_title']}",
        "",
        f"**{L['candidate']}:** {scorecard.candidate_name}",
        f"**{L['position']}:** {scorecard.position}",
        f"**{L['overall_score']}:** {scorecard.overall_score:.1f}/5",
        f"**{L['integrity']}:** {L.get('risk_' + integrity.risk, integrity.risk)}",
        "",
        f"## {recommendation_label(scorecard.recommendation.value, language)}",
        "",
        scorecard.headline,
        "",
        f"### {L['executive_summary']}",
        scorecard.summary,
        "",
        f"### {L['competencies']}",
    ]
    for c in scorecard.competencies:
        lines.append(f"- **{c.name}** ({c.score:.1f}/5, w={c.weight:.0%}): {c.rationale}")
    if scorecard.strengths:
        lines.extend(["", f"### {L['strengths']}"] + [f"- {s}" for s in scorecard.strengths])
    if scorecard.concerns:
        lines.extend(["", f"### {L['concerns']}"] + [f"- {c}" for c in scorecard.concerns])
    lines.extend(["", f"### {L['integrity_section']}", integrity.note])
    if scorecard.next_steps:
        lines.extend(["", f"### {L['next_steps']}", scorecard.next_steps])
    return "\n".join(lines)


def build_pdf(
    scorecard: "ScoreCard",
    integrity: "IntegritySummary",
    language: str,
) -> bytes:
    L = labels(language)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()

    regular = _font_path("DejaVuSans.ttf")
    bold = _font_path("DejaVuSans-Bold.ttf")
    if regular:
        pdf.add_font("DejaVu", "", regular)
        if bold:
            pdf.add_font("DejaVu", "B", bold)
        pdf.set_font("DejaVu", size=10)
        font_family = "DejaVu"
    else:
        pdf.set_font("Helvetica", size=10)
        font_family = "Helvetica"

    def _heading(text: str, size: int = 14) -> None:
        style = "B" if font_family == "DejaVu" and bold else "B"
        pdf.set_font(font_family, style=style, size=size)
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(font_family, style="", size=10)

    _heading(L["report_title"], 16)

    def _line(text: str, h: float = 6) -> None:
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, h, _ascii_safe(text), new_x="LMARGIN", new_y="NEXT")

    def _para(text: str, h: float = 5) -> None:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, h, _ascii_safe(text))

    _line(f"{L['candidate']}: {scorecard.candidate_name}")
    _line(f"{L['position']}: {scorecard.position}")
    _line(f"{L['date']}: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
    pdf.ln(4)

    rec = recommendation_label(scorecard.recommendation.value, language)
    pdf.set_fill_color(16, 185, 129)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, f"  {rec}  ", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    track_lbl = L["track_tech"] if scorecard.track == "tech" else L["track_nontech"]
    risk_lbl = L.get(f"risk_{integrity.risk}", integrity.risk)
    pdf.cell(
        0, 6,
        f"{L['overall_score']}: {scorecard.overall_score:.1f}/5  |  {L['track']}: {track_lbl}  |  {L['integrity']}: {risk_lbl}",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(2)

    gauge = charts.overall_gauge(
        scorecard.overall_score,
        scorecard.recommendation.value,
        title=L["overall_score"],
        caption=L["gauge_caption"],
    )
    _embed_png(pdf, gauge, w=120)

    _heading(L["executive_summary"])
    if scorecard.headline:
        _para(scorecard.headline)
        pdf.ln(2)
    _para(scorecard.summary or "-")
    pdf.ln(4)

    radar = charts.competency_radar(
        scorecard.competencies,
        title=L["competencies"],
        caption=L["radar_caption"],
    )
    _embed_png(pdf, radar, w=140)
    bar = charts.score_breakdown_barh(
        scorecard.competencies,
        title=L["competency_detail"],
        caption=L["bar_caption"],
    )
    _embed_png(pdf, bar, w=140)

    if scorecard.track == "tech" and scorecard.coding_eval:
        ce = scorecard.coding_eval
        _heading(L["coding_assessment"])
        dim_png = charts.coding_dimensions(ce, title=L["coding_assessment"], caption=L["coding_caption"])
        _embed_png(pdf, dim_png, w=140)
        if ce.tests_total:
            donut = charts.test_pass_donut(
                ce.tests_passed or 0,
                ce.tests_total,
                title=L["tests_passed"],
                caption=L["donut_caption"],
            )
            _embed_png(pdf, donut, w=100)
        if ce.notes:
            _para(ce.notes)
        pdf.ln(4)

    _heading(L["strengths"])
    _para("\n".join(f"- {s}" for s in scorecard.strengths) or "-")
    pdf.ln(2)
    _heading(L["concerns"])
    _para("\n".join(f"- {c}" for c in scorecard.concerns) or "-")
    pdf.ln(2)

    _heading(L["competency_detail"])
    pdf.set_font(font_family, size=8)
    for c in scorecard.competencies:
        _para(f"{c.name} | {c.score:.1f}/5 | {c.weight:.0%}", h=4)
        if c.rationale:
            _para(c.rationale[:240], h=4)
        pdf.ln(1)
    pdf.set_font(font_family, size=10)
    pdf.ln(2)

    _heading(L["integrity_section"])
    _para(integrity.note)
    if integrity.counts_by_kind:
        kinds = ", ".join(f"{k}: {v}" for k, v in integrity.counts_by_kind.items())
        _para(kinds)

    if scorecard.next_steps:
        pdf.ln(2)
        _heading(L["next_steps"])
        _para(scorecard.next_steps)

    out = pdf.output()
    if isinstance(out, bytes):
        return out
    if isinstance(out, bytearray):
        return bytes(out)
    return str(out).encode("latin-1")