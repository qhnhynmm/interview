"""Deterministic chart generation from ScoreCard numbers — no LLM."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

if TYPE_CHECKING:
    from app.schemas.inspector.scorecard import CodingEval, CompetencyScore

EMERALD = "#10b981"
EMERALD_DARK = "#047857"
SLATE = "#0f172a"
MUTED = "#64748b"


def _score_color(score: float) -> str:
    if score >= 4.0:
        return EMERALD
    if score >= 3.0:
        return "#14b8a6"
    if score >= 2.0:
        return "#f59e0b"
    return "#ef4444"


def _fig_to_png(fig: plt.Figure, dpi: int = 120) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def overall_gauge(score: float, recommendation: str, *, title: str, caption: str) -> bytes:
    fig, ax = plt.subplots(figsize=(5, 3), subplot_kw={"projection": "polar"})
    theta = np.linspace(np.pi, 0, 100)
    ax.plot(theta, [1] * 100, color="#e2e8f0", linewidth=14, solid_capstyle="round")
    fill = max(0.0, min(score / 5.0, 1.0))
    t_fill = np.linspace(np.pi, np.pi * (1 - fill), max(2, int(100 * fill)))
    ax.plot(t_fill, [1] * len(t_fill), color=_score_color(score), linewidth=14, solid_capstyle="round")
    ax.set_ylim(0, 1.2)
    ax.axis("off")
    ax.text(
        0.5, 0.55, f"{score:.1f}/5",
        transform=ax.transAxes, ha="center", va="center",
        fontsize=22, fontweight="bold", color=SLATE,
    )
    ax.text(
        0.5, 0.35, recommendation.replace("_", " ").upper(),
        transform=ax.transAxes, ha="center", va="center",
        fontsize=9, color=EMERALD_DARK,
    )
    fig.suptitle(title, fontsize=11, fontweight="bold", color=SLATE, y=0.98)
    fig.text(0.5, 0.02, caption, ha="center", fontsize=8, color=MUTED)
    return _fig_to_png(fig)


def competency_radar(competencies: list["CompetencyScore"], *, title: str, caption: str) -> bytes:
    names = [c.name[:18] for c in competencies]
    scores = [c.score for c in competencies]
    if not names:
        names, scores = ["N/A"], [0.0]
    angles = np.linspace(0, 2 * np.pi, len(names), endpoint=False).tolist()
    scores_loop = scores + scores[:1]
    angles_loop = angles + angles[:1]

    fig, ax = plt.subplots(figsize=(5, 4), subplot_kw={"projection": "polar"})
    ax.plot(angles_loop, scores_loop, color=EMERALD, linewidth=2)
    ax.fill(angles_loop, scores_loop, color=EMERALD, alpha=0.2)
    ax.set_xticks(angles)
    ax.set_xticklabels(names, fontsize=8)
    ax.set_ylim(0, 5)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.grid(color="#cbd5e1", alpha=0.6)
    fig.suptitle(title, fontsize=11, fontweight="bold", color=SLATE)
    fig.text(0.5, 0.02, caption, ha="center", fontsize=8, color=MUTED)
    return _fig_to_png(fig)


def score_breakdown_barh(competencies: list["CompetencyScore"], *, title: str, caption: str) -> bytes:
    names = [c.name[:22] for c in competencies]
    scores = [c.score for c in competencies]
    if not names:
        names, scores = ["N/A"], [0.0]
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    names = [names[i] for i in order]
    scores = [scores[i] for i in order]
    colors = [_score_color(s) for s in scores]

    fig, ax = plt.subplots(figsize=(5, max(2.5, len(names) * 0.45)))
    ax.barh(names, scores, color=colors, height=0.6)
    ax.set_xlim(0, 5)
    ax.set_xlabel("Score (0–5)", fontsize=8, color=MUTED)
    ax.tick_params(labelsize=8)
    for spine in ax.spines.values():
        spine.set_color("#e2e8f0")
    fig.suptitle(title, fontsize=11, fontweight="bold", color=SLATE)
    fig.text(0.5, 0.01, caption, ha="center", fontsize=8, color=MUTED)
    return _fig_to_png(fig)


def coding_dimensions(coding_eval: "CodingEval", *, title: str, caption: str) -> bytes:
    dims = ["correctness", "code_quality", "problem_solving", "communication"]
    labels = ["Correctness", "Quality", "Problem solving", "Communication"]
    scores = [getattr(coding_eval, d) for d in dims]
    colors = [_score_color(s) for s in scores]

    fig, ax = plt.subplots(figsize=(5, 3))
    ax.bar(labels, scores, color=colors, width=0.55)
    ax.set_ylim(0, 5)
    ax.set_ylabel("Score", fontsize=8, color=MUTED)
    ax.tick_params(axis="x", labelsize=7, rotation=15)
    fig.suptitle(title, fontsize=11, fontweight="bold", color=SLATE)
    fig.text(0.5, 0.02, caption, ha="center", fontsize=8, color=MUTED)
    return _fig_to_png(fig)


def test_pass_donut(passed: int, total: int, *, title: str, caption: str) -> bytes:
    if total <= 0:
        passed, total = 0, 1
    pct = passed / total
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.pie(
        [passed, max(0, total - passed)],
        colors=[EMERALD, "#e2e8f0"],
        startangle=90,
        wedgeprops={"width": 0.45, "edgecolor": "white"},
    )
    ax.text(0, 0, f"{int(pct * 100)}%", ha="center", va="center", fontsize=18, fontweight="bold", color=SLATE)
    ax.text(0, -0.15, f"{passed}/{total}", ha="center", va="center", fontsize=9, color=MUTED)
    fig.suptitle(title, fontsize=11, fontweight="bold", color=SLATE)
    fig.text(0.5, 0.02, caption, ha="center", fontsize=8, color=MUTED)
    return _fig_to_png(fig)