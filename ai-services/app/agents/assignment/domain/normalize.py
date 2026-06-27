"""Post-process LLM assignment output — fix common PROJECT omissions, honor directive."""

import logging
import re

from app.schemas.assignment import Assignment, CodingChallenge, CodingMode, TestCase
from app.schemas.plan import AssignmentDirective

logger = logging.getLogger(__name__)

_STYLES_IMPORT_RE = re.compile(r"""import\s+['"]\./styles\.css['"]\s*;?""")
_DEFAULT_STYLES_CSS = (
    "/* Starter styles — extend as needed */\n"
    "body { margin: 0; font-family: system-ui, sans-serif; }\n"
    ".app { padding: 1rem; max-width: 720px; margin: 0 auto; }\n"
)

_DEFAULT_PROJECT_TESTS = [
    TestCase(label="Core behavior", inputs=[], expected="Primary user interaction works as described."),
    TestCase(label="Empty guard", inputs=[], expected="Invalid or empty input is handled safely."),
]


def _ensure_styles_import(app_js: str) -> str:
    if _STYLES_IMPORT_RE.search(app_js):
        return app_js
    lines = app_js.splitlines()
    last_import = -1
    for i, line in enumerate(lines):
        if line.strip().startswith("import "):
            last_import = i
    insert = "import './styles.css';"
    if last_import >= 0:
        lines.insert(last_import + 1, insert)
    else:
        lines.insert(0, insert)
    return "\n".join(lines)


def normalize_project_coding(coding: CodingChallenge) -> CodingChallenge:
    """Ensure Sandpack-ready starter_files; sync starter_code from App.js."""
    files = dict(coding.starter_files)
    app_js = files.get("App.js") or coding.starter_code or ""
    app_js = _ensure_styles_import(app_js)
    files["App.js"] = app_js
    if "styles.css" not in files or not files["styles.css"].strip():
        files["styles.css"] = _DEFAULT_STYLES_CSS

    test_cases = list(coding.test_cases)
    if len(test_cases) < 2:
        existing = {tc.label for tc in test_cases}
        for default in _DEFAULT_PROJECT_TESTS:
            if default.label not in existing:
                test_cases.append(default)
            if len(test_cases) >= 2:
                break

    return coding.model_copy(
        update={
            "starter_files": files,
            "starter_code": app_js,
            "test_cases": test_cases[:4],
        }
    )


def normalize_assignment(assignment: Assignment, directive: AssignmentDirective) -> Assignment:
    """Apply directive overrides and structural fixes before validation."""
    fixes: list[str] = []

    if directive.type == "coding" and assignment.coding:
        coding = assignment.coding
        updates: dict = {}
        if coding.mode.value != directive.mode:
            updates["mode"] = CodingMode(directive.mode)
            fixes.append(f"mode→{directive.mode}")
        if coding.ai_assistant_enabled != directive.ai_assistant:
            updates["ai_assistant_enabled"] = directive.ai_assistant
            fixes.append(f"ai_assistant→{directive.ai_assistant}")
        if coding.difficulty != directive.difficulty:
            updates["difficulty"] = directive.difficulty
        if updates:
            coding = coding.model_copy(update=updates)

        if directive.mode == "project":
            before = coding.starter_files.get("App.js", coding.starter_code)
            coding = normalize_project_coding(coding)
            after = coding.starter_files.get("App.js", "")
            if _STYLES_IMPORT_RE.search(after) and not _STYLES_IMPORT_RE.search(before):
                fixes.append("injected styles.css import")
            if "styles.css" not in (assignment.coding.starter_files or {}):
                fixes.append("added styles.css")
        elif directive.mode == "dsa":
            coding = coding.model_copy(update={"starter_files": {}})

        if fixes:
            logger.info("assignment normalized: %s", ", ".join(fixes))
        return assignment.model_copy(update={"coding": coding})

    return assignment