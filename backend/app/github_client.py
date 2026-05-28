from __future__ import annotations

import base64
import re
from urllib.parse import urlparse
import httpx
from .config import settings
from .schemas import ReviewFile
from .rules import detect_language

ALLOWED_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".css", ".html"}
IGNORE_PARTS = {"node_modules", "dist", "build", ".git", "venv", ".next", "coverage", "target"}


def parse_github_url(repo_url: str) -> tuple[str, str]:
    parsed = urlparse(repo_url)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if parsed.netloc not in {"github.com", "www.github.com"} or len(parts) < 2:
        raise ValueError("Please provide a valid GitHub repository URL, e.g. https://github.com/owner/repo")
    return parts[0], parts[1].replace(".git", "")


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


def _is_allowed(path: str) -> bool:
    if any(part in IGNORE_PARTS for part in path.split("/")):
        return False
    return any(path.endswith(ext) for ext in ALLOWED_EXTENSIONS)


async def import_repo_files(repo_url: str, branch: str = "main", max_files: int = 20) -> tuple[str, list[ReviewFile]]:
    owner, repo = parse_github_url(repo_url)
    api = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    async with httpx.AsyncClient(timeout=30) as client:
        tree_response = await client.get(api, headers=_headers())
        if tree_response.status_code == 404 and branch == "main":
            api = f"https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1"
            tree_response = await client.get(api, headers=_headers())
            branch = "master"
        tree_response.raise_for_status()
        tree = tree_response.json().get("tree", [])

        candidates = [item for item in tree if item.get("type") == "blob" and _is_allowed(item.get("path", ""))]
        candidates = sorted(candidates, key=lambda x: ("test" in x.get("path", "").lower(), len(x.get("path", ""))))[:max_files]

        files: list[ReviewFile] = []
        for item in candidates:
            url = item.get("url")
            if not url:
                continue
            blob = await client.get(url, headers=_headers())
            if blob.status_code >= 400:
                continue
            data = blob.json()
            if data.get("encoding") != "base64":
                continue
            try:
                content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
            except Exception:
                continue
            if len(content.strip()) == 0:
                continue
            files.append(ReviewFile(path=item["path"], language=detect_language(item["path"]), content=content))

    return f"{owner}/{repo}", files
