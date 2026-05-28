from __future__ import annotations
import subprocess
import tempfile
from pathlib import Path
from .schemas import ReviewFile, ReviewComment, Severity

PY_EXTS = {'.py'}
JS_EXTS = {'.js', '.jsx', '.ts', '.tsx'}


def run_lint_integrations(files: list[ReviewFile]) -> tuple[list[ReviewComment], list[str]]:
    comments: list[ReviewComment] = []
    output: list[str] = []
    output.append("Lint integrations: Ruff enabled for Python files; ESLint-compatible JS/TS heuristics enabled for frontend files.")
    comments.extend(run_ruff(files, output))
    comments.extend(run_eslint_heuristics(files))
    return comments, output


def run_ruff(files: list[ReviewFile], output: list[str]) -> list[ReviewComment]:
    comments: list[ReviewComment] = []
    py_files = [f for f in files if Path(f.path).suffix in PY_EXTS]
    if not py_files:
        return comments
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for f in py_files:
            target = root / f.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f.content, encoding='utf-8')
        try:
            proc = subprocess.run(
                ['ruff', 'check', str(root), '--output-format', 'concise'],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if proc.stdout.strip():
                output.append(proc.stdout.strip())
            for raw in proc.stdout.splitlines()[:20]:
                # concise roughly: path:line:col: CODE message
                parts = raw.split(':', 3)
                if len(parts) >= 4:
                    rel = str(Path(parts[0]).relative_to(root)) if str(parts[0]).startswith(str(root)) else parts[0]
                    line = int(parts[1]) if parts[1].isdigit() else 1
                    message = parts[3].strip()
                    comments.append(ReviewComment(file_path=rel, line=line, severity=Severity.low, category='ruff', message=message, suggestion='Run `ruff check --fix` where safe.', source='ruff'))
        except Exception as exc:
            output.append(f"Ruff did not run: {exc}")
    return comments


def run_eslint_heuristics(files: list[ReviewFile]) -> list[ReviewComment]:
    comments: list[ReviewComment] = []
    for f in files:
        if Path(f.path).suffix not in JS_EXTS:
            continue
        for index, line in enumerate(f.content.splitlines(), start=1):
            stripped = line.strip()
            if '==' in stripped and '===' not in stripped and '!=' not in stripped:
                comments.append(ReviewComment(file_path=f.path, line=index, severity=Severity.medium, category='eslint', message='Prefer strict equality in JavaScript/TypeScript.', suggestion='Use `===` or `!==` instead of loose equality.', patch=stripped.replace('==', '==='), source='eslint'))
            if stripped.startswith('debugger'):
                comments.append(ReviewComment(file_path=f.path, line=index, severity=Severity.high, category='eslint', message='Debugger statement should not be committed.', suggestion='Remove the debugger statement before shipping.', source='eslint'))
    return comments
