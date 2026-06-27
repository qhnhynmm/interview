from app.agents.base import AgentBase
from app.agents.planning.prompts import ANALYST_SYSTEM
from app.config import get_settings
from app.schemas.internal.planning import AnalystGrounding
from app.skills.jd_analysis import analyze_jd


class PlanningAnalyst(AgentBase):
    name = "planning_analyst"

    async def analyze(
        self,
        *,
        jd_text: str,
        cv_text: str,
        position: str,
        seniority: str | None,
        language: str,
        candidate_name: str,
    ) -> AnalystGrounding:
        settings = get_settings()
        baseline = analyze_jd(
            jd_text=jd_text,
            cv_text=cv_text,
            position=position,
            seniority=seniority,
            language=language,
            candidate_name=candidate_name,
        )

        user_prompt = (
            f"Position: {position}\nSeniority: {seniority or 'n/a'}\nLanguage: {language}\n"
            f"Candidate: {candidate_name or 'n/a'}\n\nJD:\n{jd_text[:4000]}\n\nCV:\n{cv_text[:4000]}"
        )
        llm_data = await self._maybe_llm_json(
            span="planning.analyst",
            model=settings.planning_analyst_effective_model,
            system=ANALYST_SYSTEM,
            user=user_prompt,
            temperature=settings.planning_temperature,
            max_tokens=settings.planning_analyst_max_tokens,
            timeout=settings.planning_request_timeout,
        )
        if not llm_data:
            return baseline

        merged = baseline.model_dump()
        for key in ("jd_keywords", "cv_skills", "summary"):
            if llm_data.get(key):
                merged[key] = llm_data[key]
        if llm_data.get("skill_evidence"):
            merged["skill_evidence"] = llm_data["skill_evidence"]
        return AnalystGrounding.model_validate(merged)