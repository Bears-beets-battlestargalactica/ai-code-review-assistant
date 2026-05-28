export type Severity = 'info' | 'low' | 'medium' | 'high';

export type ReviewFile = {
  path: string;
  language?: string;
  content: string;
};

export type ReviewComment = {
  file_path: string;
  line: number;
  severity: Severity;
  category: string;
  message: string;
  suggestion?: string;
  patch?: string;
  source: 'rule' | 'ai' | 'ruff' | 'eslint';
};

export type ReviewResponse = {
  id?: number;
  summary: string;
  comments: ReviewComment[];
  unit_test_suggestions: string[];
  explanation?: string;
  lint_output?: string[];
};

export type AuthResponse = { token: string; email: string };

export type ReviewHistoryItem = {
  id: number;
  title: string;
  repo_url?: string;
  branch?: string;
  summary: string;
  created_at: string;
  comment_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  info_count: number;
};

export type DashboardResponse = {
  total_reviews: number;
  total_comments: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  info_count: number;
  recent_reviews: ReviewHistoryItem[];
};

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';
let authToken = localStorage.getItem('code_review_token') ?? '';

export function setAuthToken(token: string) {
  authToken = token;
  if (token) localStorage.setItem('code_review_token', token);
  else localStorage.removeItem('code_review_token');
}

function authHeaders() {
  return authToken ? { Authorization: `Bearer ${authToken}` } : {}; 
}

async function request<T>(path: string, body?: unknown, method = 'POST'): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', ...authHeaders() } as HeadersInit,
    body: body === undefined ? undefined : JSON.stringify(body)
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail ?? 'Request failed');
  }
  return res.json();
}

export async function register(email: string, password: string): Promise<AuthResponse> {
  const res = await request<AuthResponse>('/api/auth/register', { email, password });
  setAuthToken(res.token);
  return res;
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const res = await request<AuthResponse>('/api/auth/login', { email, password });
  setAuthToken(res.token);
  return res;
}

export async function reviewCode(files: ReviewFile[], useAi: boolean, meta?: { repoUrl?: string; branch?: string; title?: string }): Promise<ReviewResponse> {
  return request<ReviewResponse>('/api/review', {
    files,
    use_ai: useAi,
    include_tests: true,
    repo_url: meta?.repoUrl,
    branch: meta?.branch,
    title: meta?.title
  });
}

export async function importGithubRepo(repoUrl: string, branch: string, maxFiles = 15): Promise<{ repo: string; branch: string; files: ReviewFile[] }> {
  return request('/api/import/github', {
    repo_url: repoUrl,
    branch,
    max_files: maxFiles
  });
}

export async function explainCodebase(files: ReviewFile[]): Promise<{ explanation: string }> {
  return request<{ explanation: string }>('/api/explain', {
    files,
    use_ai: true
  });
}

export async function getHistory(): Promise<ReviewHistoryItem[]> {
  return request<ReviewHistoryItem[]>('/api/history', undefined, 'GET');
}

export async function getDashboard(): Promise<DashboardResponse> {
  return request<DashboardResponse>('/api/dashboard', undefined, 'GET');
}

export async function getReview(id: number): Promise<ReviewResponse> {
  return request<ReviewResponse>(`/api/history/${id}`, undefined, 'GET');
}

export async function getMarkdownReport(review: ReviewResponse): Promise<{ markdown: string }> {
  return request<{ markdown: string }>('/api/report/markdown', review);
}

export async function generatePrComment(review: ReviewResponse, repoUrl?: string, prNumber?: number, mode: 'draft' | 'post' = 'draft'): Promise<{ body: string; posted: boolean; url?: string }> {
  return request('/api/pr/comment', { review, repo_url: repoUrl, pr_number: prNumber, mode });
}
