from app.agents.assignment.domain.directive import ResolvedTrack
from app.schemas.assignment import (
    Assignment,
    AssignmentType,
    CodingChallenge,
    CodingMode,
    CognitiveTest,
    MCQQuestion,
    TestCase,
)
from app.schemas.plan import AssignmentDirective, ProblemBankEntry
from app.skills.interview_planning.scripts.planning_tools import search_problem_bank


def _bank_test_cases(entry: ProblemBankEntry) -> list[TestCase]:
    return [
        TestCase(
            label=str(tc.get("label", f"case{i}")),
            inputs=list(tc.get("inputs", [])),
            expected=tc["expected"],
        )
        for i, tc in enumerate(entry.test_cases)
    ]


def build_dsa_assignment(
    *,
    entry: ProblemBankEntry,
    directive: AssignmentDirective,
    summary: str | None = None,
) -> Assignment:
    return Assignment(
        type=AssignmentType.coding,
        summary=summary or f"DSA screening — {entry.title}, AI assistant disabled.",
        coding=CodingChallenge(
            mode=CodingMode.dsa,
            title=entry.title,
            difficulty=entry.difficulty,
            statement=entry.statement,
            function_name=entry.function_name,
            starter_code=entry.starter_code,
            starter_files={},
            test_cases=_bank_test_cases(entry),
            ai_assistant_enabled=False,
            allowed_resources=["Python standard library"],
        ),
        cognitive=None,
        source="assignment-agent",
    )


def build_project_assignment(
    *,
    title: str,
    directive: AssignmentDirective,
    position: str,
    summary: str,
) -> Assignment:
    app_js = (
        "import { useState } from 'react';\n"
        "import './styles.css';\n\n"
        "export default function App() {\n"
        "  const [messages, setMessages] = useState([]);\n"
        "  const [input, setInput] = useState('');\n\n"
        "  const send = () => {\n"
        "    if (!input.trim()) return;\n"
        "    setMessages((prev) => [...prev, { role: 'user', text: input.trim() }]);\n"
        "    setInput('');\n"
        "  };\n\n"
        "  return (\n"
        "    <div className=\"app\">\n"
        "      <h1 className=\"title\">" + title + "</h1>\n"
        "      <div className=\"chat\">\n"
        "        {messages.map((m, i) => (\n"
        "          <div key={i} className=\"msg\">{m.text}</div>\n"
        "        ))}\n"
        "      </div>\n"
        "      <div className=\"composer\">\n"
        "        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder=\"Type...\" />\n"
        "        <button onClick={send}>Send</button>\n"
        "      </div>\n"
        "    </div>\n"
        "  );\n"
        "}\n"
    )
    styles = (
        ".app { font-family: system-ui; padding: 1rem; max-width: 640px; margin: 0 auto; }\n"
        ".title { font-size: 1.25rem; font-weight: 600; margin-bottom: 0.75rem; }\n"
        ".chat { min-height: 200px; border: 1px solid #ddd; border-radius: 8px; padding: 0.75rem; }\n"
        ".msg { padding: 0.35rem 0; }\n"
        ".composer { display: flex; gap: 0.5rem; margin-top: 0.75rem; }\n"
        "input { flex: 1; padding: 0.5rem; }\n"
        "button { padding: 0.5rem 1rem; }\n"
    )
    statement = (
        f"## {title}\n"
        f"**Role context**: Mini frontend task for {position}.\n"
        "### What to build\n"
        "Build a simple chat-style UI that appends user messages to a scrollable panel.\n"
        "### Acceptance criteria\n"
        "- [ ] Typing and clicking Send adds a message bubble\n"
        "- [ ] Empty input does not add messages\n"
        "- [ ] Layout remains readable on a narrow viewport\n"
        "### Notes\n"
        "- You are encouraged to use the AI assistant.\n"
    )
    return Assignment(
        type=AssignmentType.coding,
        summary=summary,
        coding=CodingChallenge(
            mode=CodingMode.project,
            title=title,
            difficulty=directive.difficulty,
            statement=statement,
            function_name="App",
            starter_code=app_js,
            starter_files={"App.js": app_js, "styles.css": styles},
            test_cases=[
                TestCase(label="Messages render", inputs=[], expected="User messages appear in the chat panel."),
                TestCase(label="Empty guard", inputs=[], expected="Blank input does not create a message."),
                TestCase(label="Responsive layout", inputs=[], expected="UI stays usable on narrow screens."),
            ],
            ai_assistant_enabled=True,
            allowed_resources=["React (built-in)", "Tailwind CDN classes", "AI assistant"],
        ),
        cognitive=None,
        source="assignment-agent+fallback",
    )


def build_cognitive_assignment(*, position: str, topic: str | None = None) -> Assignment:
    role = position or "General"
    subject = topic or f"{role} judgement & reasoning"
    templates = [
        ("A campaign CTR dropped 20% week-over-week. What is the BEST first step?", ["Pause all ads", "Check tracking/data pipeline", "Double the budget", "Change brand logo"], "B"),
        ("A stakeholder demands a feature that conflicts with compliance. You should:", ["Ship quietly", "Escalate with documented risk", "Ignore compliance", "Quit immediately"], "B"),
        ("Two priorities are due today with one owner. Best approach?", ["Multitask both halfway", "Rank by impact and sequence", "Ask candidate to choose randomly", "Delay both"], "B"),
        ("A metric improved but revenue fell. Likely explanation?", ["Metric is a vanity proxy", "Revenue always follows", "Sample size too large", "Calendar effect only"], "A"),
        ("Customer complaint volume rose 15% after a UI change. Next step?", ["Revert without analysis", "Segment complaints and correlate with UI paths", "Disable support", "Increase prices"], "B"),
        ("You have 3 hours before a demo and a broken build. You:", ["Rewrite architecture", "Identify minimal fix path and communicate risk", "Cancel demo silently", "Blame another team"], "B"),
        ("A/B test shows +2% lift, p=0.21. Decision?", ["Ship winner immediately", "Treat as inconclusive; extend test or revisit hypothesis", "Fire analyst", "Change significance after the fact"], "B"),
        ("Budget cut 30%. Best portfolio response?", ["Cut everything evenly", "Prioritize by ROI and strategic bets", "Stop measurement", "Hire more contractors"], "B"),
        ("New hire underperforms at 60 days. First action?", ["Terminate", "Clarify expectations with specific examples and support plan", "Ignore", "Public criticism"], "B"),
        ("Data shows funnel drop at step 3. You:", ["Optimize step 1 only", "Investigate step 3 friction with qualitative + quantitative signals", "Remove step 3", "Buy more traffic"], "B"),
    ]
    questions = [
        MCQQuestion(
            prompt=p,
            options=opts,
            answer=ans,
            explanation="Measures structured reasoning under role constraints.",
        )
        for p, opts, ans in templates
    ]
    return Assignment(
        type=AssignmentType.cognitive,
        summary=f"10-question aptitude test calibrated for {role}.",
        coding=None,
        cognitive=CognitiveTest(topic=subject, questions=questions),
        source="assignment-agent+fallback",
    )


def build_fallback_assignment(
    *,
    directive: AssignmentDirective,
    resolved: ResolvedTrack,
    position: str,
    assignment_brief: str,
) -> Assignment:
    if directive.type == "cognitive":
        return build_cognitive_assignment(position=position)

    if directive.mode == "dsa":
        entry = search_problem_bank(resolved.domain, resolved.level)  # type: ignore[arg-type]
        if entry is None:
            raise ValueError("No problem bank entry for DSA fallback")
        return build_dsa_assignment(entry=entry, directive=directive)

    title = "Streaming Chat UI"
    if "frontend" in (position or "").lower():
        title = "Component State Panel"
    return build_project_assignment(
        title=title,
        directive=directive,
        position=position or "Engineer",
        summary=f"Project sandbox for {position} — probes practical UI implementation with AI assist enabled.",
    )