from __future__ import annotations
from .schemas import ReviewResponse, ReviewComment


def build_markdown_report(review: ReviewResponse) -> str:
    lines = ["# AI Code Review Report", "", f"**Summary:** {review.summary}", ""]
    if review.explanation:
        lines += ["## Codebase explanation", "", review.explanation, ""]
    lines += ["## Findings", ""]
    if not review.comments:
        lines.append("No findings generated.")
    for c in review.comments:
        lines += [
            f"### {c.file_path}:{c.line}",
            f"**Severity:** {c.severity}  ",
            f"**Category:** {c.category}  ",
            f"**Source:** {c.source}",
            "",
            c.message,
            "",
        ]
        if c.suggestion:
            lines += [f"**Suggestion:** {c.suggestion}", ""]
        if c.patch:
            lines += ["**Suggested patch:**", "", "```diff", c.patch, "```", ""]
    if review.unit_test_suggestions:
        lines += ["## Unit test suggestions", ""]
        lines += [f"- {item}" for item in review.unit_test_suggestions]
    return "\n".join(lines)


def build_pr_comment(review: ReviewResponse) -> str:
    lines = [
        "## AI Code Review Assistant",
        "",
        review.summary,
        "",
        "### Review comments",
        "",
    ]
    for c in review.comments:
        lines += [
            f"#### `{c.file_path}:{c.line}` — **{c.severity.upper()}** / {c.category} / {c.source}",
            c.message,
        ]
        if c.suggestion:
            lines.append(f"**Suggestion:** {c.suggestion}")
        if c.patch:
            lines += ["", "```diff", c.patch, "```"]
        lines.append("")
    if review.unit_test_suggestions:
        lines += ["### Suggested tests", ""]
        lines += [f"- {t}" for t in review.unit_test_suggestions]
    return "\n".join(lines)
