"""Execute candidate Python code against assignment test cases."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def _extract_function_name(coding: dict[str, Any]) -> str:
    explicit = str(coding.get("function_name") or "").strip()
    if explicit:
        return explicit
    starter = str(coding.get("starter_code") or "")
    match = re.search(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", starter)
    return match.group(1) if match else "solution"


def _build_runner_script(*, code: str, function_name: str, test_cases: list[dict]) -> str:
    payload = json.dumps(test_cases, ensure_ascii=False)
    return f"""import json
import traceback

USER_CODE = {json.dumps(code)}

namespace = {{}}
try:
    exec(USER_CODE, namespace)
except Exception as exc:
    print(json.dumps({{"error": str(exc), "traceback": traceback.format_exc()}}))
    raise SystemExit(1)

fn = namespace.get({json.dumps(function_name)})
if fn is None or not callable(fn):
    print(json.dumps({{"error": "function {function_name} not found"}}))
    raise SystemExit(1)

tests = json.loads({json.dumps(payload)})
results = []
passed = 0
for tc in tests:
    label = tc.get("label") or "test"
    inputs = tc.get("inputs") or []
    expected = tc.get("expected")
    try:
        if isinstance(inputs, list):
            got = fn(*inputs)
        else:
            got = fn(inputs)
        ok = got == expected
        if ok:
            passed += 1
        results.append({{
            "label": label,
            "passed": ok,
            "expected": repr(expected),
            "got": repr(got),
        }})
    except Exception as exc:
        results.append({{
            "label": label,
            "passed": False,
            "expected": repr(expected),
            "got": str(exc),
        }})

print(json.dumps({{"results": results, "passed": passed, "total": len(tests)}}))
"""


def run_python_tests(
    *,
    code: str,
    coding: dict[str, Any],
    timeout_sec: float = 8.0,
) -> dict[str, Any]:
    test_cases = coding.get("test_cases") or []
    if not test_cases:
        return {
            "stdout": "",
            "stderr": "No test cases configured for this assignment.",
            "exit_code": 1,
            "timed_out": False,
            "test_results": [],
            "tests_passed": 0,
            "tests_total": 0,
        }

    function_name = _extract_function_name(coding)
    script = _build_runner_script(code=code, function_name=function_name, test_cases=test_cases)

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "run_tests.py"
        path.write_text(script, encoding="utf-8")
        try:
            proc = subprocess.run(
                ["python3", str(path)],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Execution timed out after {timeout_sec:.0f}s",
                "exit_code": 124,
                "timed_out": True,
                "test_results": [],
                "tests_passed": 0,
                "tests_total": len(test_cases),
            }

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    if proc.returncode != 0:
        err_line = stdout.strip() or stderr.strip() or "Execution failed"
        return {
            "stdout": stdout,
            "stderr": err_line,
            "exit_code": proc.returncode,
            "timed_out": False,
            "test_results": [],
            "tests_passed": 0,
            "tests_total": len(test_cases),
        }

    try:
        last_line = stdout.strip().splitlines()[-1]
        parsed = json.loads(last_line)
    except (json.JSONDecodeError, IndexError):
        return {
            "stdout": stdout,
            "stderr": stderr or "Could not parse test output",
            "exit_code": 1,
            "timed_out": False,
            "test_results": [],
            "tests_passed": 0,
            "tests_total": len(test_cases),
        }

    results = parsed.get("results") or []
    passed = int(parsed.get("passed") or 0)
    total = int(parsed.get("total") or len(test_cases))
    return {
        "stdout": "All tests completed.\n" if passed == total else "Tests ran with failures.\n",
        "stderr": stderr,
        "exit_code": 0 if passed == total else 1,
        "timed_out": False,
        "test_results": results,
        "tests_passed": passed,
        "tests_total": total,
    }