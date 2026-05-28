from __future__ import annotations

import re
from typing import Iterable
from .schemas import ReviewComment, ReviewFile, Severity


def detect_language(path: str, provided: str | None = None) -> str:
    if provided:
        return provided.lower()
    suffix = path.split(".")[-1].lower() if "." in path else ""
    return {
        "py": "python",
        "js": "javascript",
        "jsx": "javascript",
        "ts": "typescript",
        "tsx": "typescript",
        "java": "java",
        "go": "go",
        "rs": "rust",
        "css": "css",
        "html": "html",
    }.get(suffix, "text")


def _comment(file_path: str, line: int, severity: Severity, category: str, message: str,
             suggestion: str | None = None, patch: str | None = None) -> ReviewComment:
    return ReviewComment(
        file_path=file_path,
        line=line,
        severity=severity,
        category=category,
        message=message,
        suggestion=suggestion,
        patch=patch,
        source="rule",
    )


def run_rule_review(files: Iterable[ReviewFile]) -> list[ReviewComment]:
    comments: list[ReviewComment] = []
    for file in files:
        language = detect_language(file.path, file.language)
        lines = file.content.splitlines()
        comments.extend(_generic_rules(file.path, lines))
        if language in {"javascript", "typescript"}:
            comments.extend(_js_ts_rules(file.path, lines))
        if language == "python":
            comments.extend(_python_rules(file.path, lines))
    return comments


def _generic_rules(path: str, lines: list[str]) -> list[ReviewComment]:
    out: list[ReviewComment] = []
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if len(line) > 120:
            out.append(_comment(
                path, idx, Severity.low, "readability",
                "This line is longer than 120 characters, which can hurt readability.",
                "Split the statement into smaller expressions or extract a named variable."
            ))
        if "TODO" in line or "FIXME" in line:
            out.append(_comment(
                path, idx, Severity.info, "maintainability",
                "Unresolved TODO/FIXME found.",
                "Convert this into a tracked issue or complete it before production use."
            ))
        if re.search(r"console\.log\(|print\(", line):
            out.append(_comment(
                path, idx, Severity.low, "maintainability",
                "Debug output appears in the code.",
                "Use a structured logger or remove debug prints before shipping."
            ))
        if re.search(r"api[_-]?key|secret|password|token", line, re.I) and "process.env" not in line and "import.meta.env" not in line:
            out.append(_comment(
                path, idx, Severity.high, "configuration",
                "Possible hardcoded secret or credential-like value.",
                "Move secrets into environment variables or a secret manager."
            ))
    return out


def _js_ts_rules(path: str, lines: list[str]) -> list[ReviewComment]:
    out: list[ReviewComment] = []
    for idx, line in enumerate(lines, start=1):
        if re.search(r"\bvar\s+", line):
            out.append(_comment(
                path, idx, Severity.medium, "modernization",
                "Avoid `var`; it is function-scoped and can create subtle bugs.",
                "Use `const` by default and `let` only when reassignment is needed.",
                patch=line.replace("var ", "const ")
            ))
        if "any" in line and (": any" in line or "as any" in line):
            out.append(_comment(
                path, idx, Severity.medium, "type-safety",
                "`any` weakens TypeScript's safety benefits.",
                "Create a specific interface/type or use `unknown` with narrowing."
            ))
        if re.search(r"useEffect\([^,]+\)$", line.strip()):
            out.append(_comment(
                path, idx, Severity.medium, "react",
                "React useEffect appears to be missing a dependency array.",
                "Add a dependency array or explain why this effect should run after every render."
            ))
        if re.search(r"fetch\(.+\)", line) and "try" not in "\n".join(lines[max(0, idx-4):idx+3]):
            out.append(_comment(
                path, idx, Severity.medium, "reliability",
                "Network request may not have nearby error handling.",
                "Wrap fetch calls in try/catch and surface friendly error states in the UI."
            ))
    return out


def _python_rules(path: str, lines: list[str]) -> list[ReviewComment]:
    out: list[ReviewComment] = []
    for idx, line in enumerate(lines, start=1):
        if re.search(r"except\s*:\s*$", line):
            out.append(_comment(
                path, idx, Severity.high, "reliability",
                "Bare except catches everything, including KeyboardInterrupt/SystemExit.",
                "Catch a specific exception type and log the failure context."
            ))
        if re.search(r"\beval\(|\bexec\(", line):
            out.append(_comment(
                path, idx, Severity.high, "safety",
                "Dynamic execution is risky and hard to reason about.",
                "Replace eval/exec with explicit parsing or a safe mapping of allowed operations."
            ))
        if re.search(r"def\s+\w+\(.*\):", line) and "->" not in line:
            out.append(_comment(
                path, idx, Severity.info, "maintainability",
                "Function is missing a return type annotation.",
                "Add a return type to improve readability and editor support."
            ))
    return out
