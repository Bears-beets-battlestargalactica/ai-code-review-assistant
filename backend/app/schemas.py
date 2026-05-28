from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class Severity(str, Enum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"


class ReviewFile(BaseModel):
    path: str = Field(..., examples=["src/App.tsx"])
    language: Optional[str] = Field(None, examples=["typescript"])
    content: str


class ReviewRequest(BaseModel):
    files: List[ReviewFile]
    use_ai: bool = True
    include_tests: bool = True
    repo_url: Optional[str] = None
    branch: Optional[str] = None
    title: Optional[str] = None


class ReviewComment(BaseModel):
    file_path: str
    line: int
    severity: Severity
    category: str
    message: str
    suggestion: Optional[str] = None
    patch: Optional[str] = None
    source: str = "rule"


class ReviewResponse(BaseModel):
    id: Optional[int] = None
    summary: str
    comments: List[ReviewComment]
    unit_test_suggestions: List[str] = []
    explanation: Optional[str] = None
    lint_output: List[str] = []


class RepoImportRequest(BaseModel):
    repo_url: str = Field(..., examples=["https://github.com/vercel/next.js"])
    branch: str = "main"
    max_files: int = 20


class RepoImportResponse(BaseModel):
    repo: str
    branch: str
    files: List[ReviewFile]


class ExplainRequest(BaseModel):
    files: List[ReviewFile]
    use_ai: bool = True


class AuthRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    email: str


class ReviewHistoryItem(BaseModel):
    id: int
    title: str
    repo_url: Optional[str] = None
    branch: Optional[str] = None
    summary: str
    created_at: str
    comment_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int


class DashboardResponse(BaseModel):
    total_reviews: int
    total_comments: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    recent_reviews: List[ReviewHistoryItem]


class PrCommentRequest(BaseModel):
    review: ReviewResponse
    repo_url: Optional[str] = None
    pr_number: Optional[int] = None
    mode: str = "draft"


class PrCommentResponse(BaseModel):
    body: str
    posted: bool = False
    url: Optional[str] = None
