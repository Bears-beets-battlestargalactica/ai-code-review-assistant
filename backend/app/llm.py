from __future__ import annotations

import json
from typing import Iterable
import httpx
from .config import settings
from .schemas import ReviewComment, ReviewFile, Severity
from .rules import detect_language


def _trim(content: str) -> str:
    return content[: settings.max_file_chars]


def _files_prompt(files: Iterable[ReviewFile]) -> str:
    blocks = []
    for file in files:
        lang = detect_language(file.path, file.language)
        blocks.append(f"FILE: {file.path}\nLANGUAGE: {lang}\n```{lang}\n{_trim(file.content)}\n```")
    return "\n\n".join(blocks)


async def ai_review(files: list[ReviewFile], include_tests: bool = True) -> tuple[list[ReviewComment], list[str], str | None]:
    if not settings.openrouter_api_key:
        return [], [], None

    system = """
You are a senior software engineer performing a practical code review.
Return strict JSON only. No markdown.
Schema:
{
  "comments": [
    {
      "file_path": "string",
      "line": number,
      "severity": "info|low|medium|high",
      "category": "readability|bug|performance|maintainability|testing|architecture|type-safety|reliability",
      "message": "specific issue",
      "suggestion": "specific improvement",
      "patch": "optional small replacement snippet"
    }
  ],
  "unit_test_suggestions": ["specific tests to add"],
  "explanation": "brief explanation of the codebase"
}
Focus on real bugs, maintainability, performance, readability, and tests. Avoid vague comments.
"""
    user = f"Review these files. Include unit test suggestions: {include_tests}.\n\n{_files_prompt(files)}"

    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": settings.app_name,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return [], [], "AI response could not be parsed as JSON. Rule-based review still completed."

    comments: list[ReviewComment] = []
    for raw in parsed.get("comments", []):
        try:
            comments.append(ReviewComment(
                file_path=raw.get("file_path", files[0].path if files else "unknown"),
                line=max(1, int(raw.get("line", 1))),
                severity=Severity(raw.get("severity", "medium")),
                category=raw.get("category", "maintainability"),
                message=raw.get("message", "AI review comment"),
                suggestion=raw.get("suggestion"),
                patch=raw.get("patch"),
                source="ai",
            ))
        except Exception:
            continue

    return comments, parsed.get("unit_test_suggestions", []), parsed.get("explanation")


async def explain_codebase(files: list[ReviewFile]) -> str:
    if not settings.openrouter_api_key:
        names = ", ".join(file.path for file in files[:8])
        return f"AI explanation is disabled because OPENROUTER_API_KEY is not set. Imported files include: {names}."

    system = "You are a senior engineer explaining a codebase to a new teammate. Be concise, specific, and useful."
    user = f"Explain the architecture, main responsibilities, data flow, and likely entry points of this codebase.\n\n{_files_prompt(files)}"
    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": settings.app_name,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
