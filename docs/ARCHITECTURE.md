# Architecture

```text
React/Vite frontend
  ├── GitHub import UI
  ├── code editor
  ├── inline review display
  ├── auth/history/dashboard panels
  └── report + PR comment actions

FastAPI backend
  ├── auth endpoints
  ├── GitHub repo importer
  ├── rule-based review engine
  ├── Ruff + JS/TS lint integration
  ├── OpenRouter LLM review
  ├── SQLite review history
  ├── report generator
  └── optional GitHub PR comment posting
```

## Review pipeline

```text
Files → rules → lint integrations → optional AI review → merged comments → saved review → UI/report/PR comment
```

## Authentication

The MVP uses local email/password registration and bearer tokens stored in SQLite. This keeps the project simple for portfolio/demo use. A production version should use OAuth or a managed auth provider.

## GitHub PR comment generation

The app can generate a PR-style Markdown summary for copy/paste. If `GITHUB_TOKEN` is configured and a PR number is supplied through the API, the backend can post the comment to the PR conversation using GitHub's issue comments endpoint.
