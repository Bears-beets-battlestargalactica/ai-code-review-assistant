# Deployment Guide

## Frontend on Vercel

1. Push the repo to GitHub.
2. Import the `frontend` folder as a Vercel project.
3. Set `VITE_API_BASE` to your deployed backend URL, for example `https://your-api.onrender.com`.
4. Deploy.

## Backend on Render

1. Create a new Render Web Service from the GitHub repo.
2. Set the root directory to `backend`.
3. Build command:

```bash
pip install -r requirements.txt
```

4. Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

5. Add environment variables:

```env
OPENROUTER_API_KEY=your_key
OPENROUTER_MODEL=openai/gpt-4o-mini
GITHUB_TOKEN=optional_for_posting_pr_comments
CORS_ORIGINS=https://your-frontend.vercel.app,http://localhost:5173
```

## Optional GitHub PR comment posting

To post comments to a real PR, create a GitHub fine-grained token with repo issue/comment permissions and set:

```env
GITHUB_TOKEN=github_pat_your_token
```

The app can always generate a PR-style Markdown comment without a token. Posting requires the token.
