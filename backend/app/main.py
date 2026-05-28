from __future__ import annotations

import re
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx

from .config import settings
from .schemas import (
    AuthRequest,
    AuthResponse,
    DashboardResponse,
    ExplainRequest,
    PrCommentRequest,
    PrCommentResponse,
    RepoImportRequest,
    RepoImportResponse,
    ReviewHistoryItem,
    ReviewRequest,
    ReviewResponse,
)
from .rules import run_rule_review
from .linting import run_lint_integrations
from .llm import ai_review, explain_codebase
from .github_client import import_repo_files
from .reporting import build_markdown_report, build_pr_comment
from .storage import authenticate, create_user, get_review, get_user_by_token, init_db, list_reviews, save_review

app = FastAPI(title=settings.app_name, version="0.2.0")

origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


def current_user(authorization: str | None) -> dict | None:
    return get_user_by_token(authorization)


def count_by_severity(comments) -> tuple[int, int, int, int]:
    high_count = sum(1 for c in comments if c.severity == "high")
    medium_count = sum(1 for c in comments if c.severity == "medium")
    low_count = sum(1 for c in comments if c.severity == "low")
    info_count = sum(1 for c in comments if c.severity == "info")
    return high_count, medium_count, low_count, info_count


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/register", response_model=AuthResponse)
def register(payload: AuthRequest) -> AuthResponse:
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    try:
        user = create_user(payload.email, payload.password)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="That email is already registered.") from exc
    return AuthResponse(token=user["token"], email=user["email"])


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: AuthRequest) -> AuthResponse:
    user = authenticate(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return AuthResponse(token=user["token"], email=user["email"])


@app.get("/api/me")
def me(authorization: str | None = Header(default=None)) -> dict[str, str]:
    user = current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in.")
    return {"email": user["email"]}


@app.post("/api/review", response_model=ReviewResponse)
async def review_code(payload: ReviewRequest, authorization: str | None = Header(default=None)) -> ReviewResponse:
    if not payload.files:
        raise HTTPException(status_code=400, detail="At least one file is required.")

    rule_comments = run_rule_review(payload.files)
    lint_comments, lint_output = run_lint_integrations(payload.files)
    ai_comments = []
    unit_tests: list[str] = []
    explanation = None

    if payload.use_ai:
        try:
            ai_comments, unit_tests, explanation = await ai_review(payload.files, payload.include_tests)
        except Exception as exc:
            explanation = f"AI review failed: {exc}. Rule-based and lint review completed."

    comments = sorted(rule_comments + lint_comments + ai_comments, key=lambda c: (c.file_path, c.line, c.severity.value))
    high_count, medium_count, low_count, info_count = count_by_severity(comments)
    summary = (
        f"Reviewed {len(payload.files)} file(s). Found {len(comments)} comments: "
        f"{high_count} high, {medium_count} medium, {low_count} low, {info_count} info."
    )
    if not settings.openrouter_api_key and payload.use_ai:
        summary += " AI review was skipped because OPENROUTER_API_KEY is not configured."

    response = ReviewResponse(summary=summary, comments=comments, unit_test_suggestions=unit_tests, explanation=explanation, lint_output=lint_output)

    user = current_user(authorization)
    if user:
        title = payload.title or payload.repo_url or (payload.files[0].path if payload.files else "Manual review")
        review_id = save_review(user["id"], title, payload.repo_url, payload.branch, response)
        response.id = review_id
    return response


@app.post("/api/import/github", response_model=RepoImportResponse)
async def import_github_repo(payload: RepoImportRequest) -> RepoImportResponse:
    try:
        repo, files = await import_repo_files(payload.repo_url, payload.branch, payload.max_files)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not import GitHub repository: {exc}") from exc

    return RepoImportResponse(repo=repo, branch=payload.branch, files=files)


@app.post("/api/explain")
async def explain(payload: ExplainRequest) -> dict[str, str]:
    if not payload.files:
        raise HTTPException(status_code=400, detail="At least one file is required.")
    try:
        return {"explanation": await explain_codebase(payload.files)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not explain codebase: {exc}") from exc


@app.get("/api/history", response_model=list[ReviewHistoryItem])
def history(authorization: str | None = Header(default=None)) -> list[ReviewHistoryItem]:
    user = current_user(authorization)
    if not user:
        return []
    return list_reviews(user["id"])


@app.get("/api/history/{review_id}", response_model=ReviewResponse)
def history_detail(review_id: int, authorization: str | None = Header(default=None)) -> ReviewResponse:
    user = current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in to view saved reviews.")
    review = get_review(review_id, user["id"])
    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")
    return review


@app.get("/api/dashboard", response_model=DashboardResponse)
def dashboard(authorization: str | None = Header(default=None)) -> DashboardResponse:
    user = current_user(authorization)
    if not user:
        return DashboardResponse(total_reviews=0, total_comments=0, high_count=0, medium_count=0, low_count=0, info_count=0, recent_reviews=[])
    items = list_reviews(user["id"])
    return DashboardResponse(
        total_reviews=len(items),
        total_comments=sum(i.comment_count for i in items),
        high_count=sum(i.high_count for i in items),
        medium_count=sum(i.medium_count for i in items),
        low_count=sum(i.low_count for i in items),
        info_count=sum(i.info_count for i in items),
        recent_reviews=items[:5],
    )


@app.post("/api/report/markdown")
def report_markdown(payload: ReviewResponse) -> dict[str, str]:
    return {"markdown": build_markdown_report(payload)}


@app.post("/api/pr/comment", response_model=PrCommentResponse)
async def pr_comment(payload: PrCommentRequest) -> PrCommentResponse:
    body = build_pr_comment(payload.review)
    if payload.mode != "post":
        return PrCommentResponse(body=body, posted=False)
    if not payload.repo_url or not payload.pr_number:
        raise HTTPException(status_code=400, detail="repo_url and pr_number are required to post to GitHub.")
    if not settings.github_token:
        raise HTTPException(status_code=400, detail="GITHUB_TOKEN is required to post PR comments.")

    match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)", payload.repo_url)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid GitHub repo URL.")
    owner = match.group("owner")
    repo = match.group("repo")
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{payload.pr_number}/comments"
    async with httpx.AsyncClient(timeout=20) as client:
        res = await client.post(
            url,
            headers={"Authorization": f"Bearer {settings.github_token}", "Accept": "application/vnd.github+json"},
            json={"body": body},
        )
    if res.status_code >= 300:
        raise HTTPException(status_code=502, detail=f"GitHub comment failed: {res.text}")
    data = res.json()
    return PrCommentResponse(body=body, posted=True, url=data.get("html_url"))
