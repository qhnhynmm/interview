from app.schemas.plan import GroundingFacts


def _competency_lines(facts: GroundingFacts) -> list[str]:
    return [f"- **{c.name}** — {c.weight}%" for c in facts.competencies]


def fallback_interview_brief(facts: GroundingFacts, cv_markdown: str) -> str:
    evidence = facts.skills_evidence[:2]
    ev_text = "; ".join(f"{e.name}: \"{e.evidence[:80]}\"" for e in evidence) or "limited CV evidence"
    gaps = ", ".join(facts.skill_gaps[:3]) or "none flagged"
    comps = "\n".join(_competency_lines(facts))

    first_project = ""
    for line in cv_markdown.splitlines():
        if len(line.strip()) > 20 and any(k in line.lower() for k in ("built", "led", "developed", "designed")):
            first_project = line.strip()[:120]
            break

    warm_up = (
        f"Walk me through {first_project} — what was your ownership and the hardest trade-off?"
        if first_project
        else f"Pick your strongest {facts.domain} project and explain your personal contribution end-to-end."
    )

    flow_lines = []
    for comp in facts.competencies[:4]:
        gap_hint = facts.skill_gaps[0] if facts.skill_gaps else facts.required_skills[0] if facts.required_skills else comp.name
        flow_lines.append(
            f"- **[{comp.name}]** MAIN: How did you apply {gap_hint} in production? "
            "Probe: metrics, failure modes, what you would redo."
        )

    return f"""**Snapshot** — {facts.position} candidate at **{facts.seniority_level}** level ({facts.domain}). \
Evidence: {ev_text}. Gaps to probe: {gaps}.

**## Competencies (weighted)**
{comps}

**## Interview flow**
- Warm-up (spoken): {warm_up}
{chr(10).join(flow_lines)}"""


def fallback_evaluation_brief(facts: GroundingFacts) -> str:
    comps = "\n".join(_competency_lines(facts))
    blocks = []
    for comp in facts.competencies:
        blocks.append(
            f"### {comp.name} ({comp.weight}%)\n"
            f"- **5/STRONG**: Names concrete project, quantifies impact, explains trade-offs.\n"
            f"- **1-2/WEAK**: Vague ownership, cannot explain decisions, contradicts CV."
        )

    gate = facts.skill_gaps[0] if facts.skill_gaps else facts.competencies[0].name
    return f"""**## Competencies & weights**
{comps}

{chr(10).join(blocks)}

**## Recommendation guide**
- **HIRE** (≥4.0 weighted): Strong on ≥2 top-weight competencies with evidence.
- **LEAN-HIRE** (3.2–3.9): Solid but gaps in {gate}; verify with references.
- **NO-HIRE** (<3.2): Multiple competencies ≤2 or integrity red flags.
- **HARD GATE**: {gate} — score ≤2 → cap recommendation at LEAN-HIRE.

**## Red flags**
- Claims skill in CV but cannot describe real usage ({', '.join(facts.skill_gaps[:2]) or 'n/a'}).
- Vague team pronouns ("we") without clarifying personal ownership."""


def fallback_assignment_brief(facts: GroundingFacts) -> str:
    directive = facts.assignment
    gaps = ", ".join(facts.skill_gaps[:3]) or "core stack depth"
    ref = facts.suggested_problem.title if facts.suggested_problem else "N/A"
    body = (
        f"Context: {facts.domain} {facts.seniority_level} — probe **{gaps}** under time pressure. "
        f"Expect a {directive.difficulty} task shaped like **{ref}** (difficulty reference only). "
        f"A strong solution shows clear structure, edge-case handling, and verbalized trade-offs. "
        f"For project mode, include realistic file layout and incremental validation."
    )
    header = (
        f"ASSIGNMENT DIRECTIVE → type: {directive.type} · mode: {directive.mode} · "
        f"ai_assistant: {'enabled' if directive.ai_assistant else 'disabled'} · "
        f"difficulty: {directive.difficulty}\n\n"
    )
    return header + body


def prepend_assignment_directive(brief: str, facts: GroundingFacts) -> str:
    directive = facts.assignment
    header = (
        f"ASSIGNMENT DIRECTIVE → type: {directive.type} · mode: {directive.mode} · "
        f"ai_assistant: {'enabled' if directive.ai_assistant else 'disabled'} · "
        f"difficulty: {directive.difficulty}\n\n"
    )
    if brief.strip().startswith("ASSIGNMENT DIRECTIVE"):
        return brief
    return header + brief.strip()