import { useEffect, useState } from 'react';
import { BarChart3, Code2, History, Info, Loader2, LogOut, Sparkles, UserRound, Wand2, X } from 'lucide-react';
import { CodeInput } from './components/CodeInput';
import { RepoImporter } from './components/RepoImporter';
import { ReviewResults } from './components/ReviewResults';
import {
  DashboardResponse,
  ReviewHistoryItem,
  explainCodebase,
  getDashboard,
  getHistory,
  getReview,
  login,
  register,
  reviewCode,
  ReviewFile,
  ReviewResponse,
  setAuthToken
} from './api/client';
import './styles/app.css';

const starterFiles: ReviewFile[] = [
  {
    path: 'src/calculateTotal.ts',
    language: 'typescript',
    content: `type Item = any;\n\nexport function calculateTotal(items: Item[]) {\n  var total = 0;\n  items.forEach(item => {\n    total += item.price\n  })\n  console.log('total', total);\n  return total;\n}`
  }
];

function App() {
  const [files, setFiles] = useState<ReviewFile[]>(starterFiles);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [useAi, setUseAi] = useState(false);
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<ReviewResponse | undefined>();
  const [email, setEmail] = useState(localStorage.getItem('code_review_email') ?? '');
  const [password, setPassword] = useState('');
  const [signedInEmail, setSignedInEmail] = useState(localStorage.getItem('code_review_email') ?? '');
  const [history, setHistory] = useState<ReviewHistoryItem[]>([]);
  const [dashboard, setDashboard] = useState<DashboardResponse | undefined>();
  const [showTutorial, setShowTutorial] = useState(() => localStorage.getItem('code_review_tutorial_seen') !== 'true');

  async function refreshWorkspace() {
    if (!signedInEmail) {
      setHistory([]);
      setDashboard(undefined);
      return;
    }
    try {
      const [historyRes, dashboardRes] = await Promise.all([getHistory(), getDashboard()]);
      setHistory(historyRes);
      setDashboard(dashboardRes);
    } catch {
      // Keep the app usable even when the local API is being restarted.
    }
  }

  useEffect(() => { void refreshWorkspace(); }, [signedInEmail]);

  function dismissTutorial() {
    localStorage.setItem('code_review_tutorial_seen', 'true');
    setShowTutorial(false);
  }

  async function runReview() {
    setError('');
    setLoading(true);
    try {
      const response = await reviewCode(files, useAi, { repoUrl, branch, title: repoUrl || files[0]?.path });
      setResult(response);
      await refreshWorkspace();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Review failed.');
    } finally {
      setLoading(false);
    }
  }

  async function runExplain() {
    setError('');
    setLoading(true);
    try {
      const response = await explainCodebase(files);
      setResult({
        summary: `Explained ${files.length} file(s).`,
        comments: [],
        unit_test_suggestions: [],
        explanation: response.explanation
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Explanation failed.');
    } finally {
      setLoading(false);
    }
  }

  async function handleAuth(mode: 'login' | 'register') {
    setError('');
    try {
      const res = mode === 'login' ? await login(email, password) : await register(email, password);
      localStorage.setItem('code_review_email', res.email);
      setSignedInEmail(res.email);
      setPassword('');
      await refreshWorkspace();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed.');
    }
  }

  async function loadHistoryItem(id: number) {
    setError('');
    try {
      setResult(await getReview(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load saved review.');
    }
  }

  function logout() {
    setAuthToken('');
    localStorage.removeItem('code_review_email');
    setSignedInEmail('');
    void refreshWorkspace();
  }

  return (
    <main className="app-shell">
      {showTutorial && (
        <div className="tutorial-backdrop" role="dialog" aria-modal="true" aria-label="AI Code Review Assistant tutorial">
          <section className="tutorial-card">
            <button className="tutorial-close" onClick={dismissTutorial} aria-label="Close tutorial"><X size={18} /></button>
            <div className="hero-badge"><Sparkles size={16} /> Quick tour</div>
            <h2>Welcome to AI Code Review Assistant</h2>
            <p>This tool helps you paste code or import a public GitHub repo, then generates review findings with severity labels, suggested fixes, inline comments, and a downloadable report.</p>
            <div className="tutorial-steps">
              <div><strong>1. Try as guest</strong><span>Run rule-based reviews without creating an account.</span></div>
              <div><strong>2. Sign in to save work</strong><span>Login/register only matters for saved history, dashboard metrics, and future project tracking.</span></div>
              <div><strong>3. AI review is optional</strong><span>AI can improve findings, but it may use OpenRouter credits. Keep it off unless you are intentionally demoing AI.</span></div>
            </div>
            <button onClick={dismissTutorial}>Start reviewing</button>
          </section>
        </div>
      )}

      <header className="hero">
        <div className="hero-badge"><Sparkles size={16} /> Portfolio-grade developer tool</div>
        <h1><Code2 size={36} /> AI Code Review Assistant</h1>
        <p>
          Paste code or import a GitHub repository to get rule-based findings, AI review comments,
          severity labels, GitHub-style inline comments, reports, and review history.
        </p>
      </header>

      <section className="card workspace-grid">
        <div>
          <div className="mini-title"><UserRound size={16} /> User authentication</div>
          {signedInEmail ? (
            <div className="auth-row"><span>Signed in as <strong>{signedInEmail}</strong></span><button className="ghost" onClick={logout}><LogOut size={16} /> Logout</button></div>
          ) : (
            <div className="auth-grid">
              <input placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} />
              <input placeholder="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
              <button className="secondary" onClick={() => handleAuth('login')}>Login</button>
              <button className="ghost" onClick={() => handleAuth('register')}>Register</button>
            </div>
          )}
        </div>
        <div>
          <div className="mini-title"><BarChart3 size={16} /> Project dashboard</div>
          {signedInEmail ? (
            <div className="stat-grid">
              <div><strong>{dashboard?.total_reviews ?? 0}</strong><span>reviews</span></div>
              <div><strong>{dashboard?.total_comments ?? 0}</strong><span>comments</span></div>
              <div><strong>{dashboard?.high_count ?? 0}</strong><span>high</span></div>
              <div><strong>{dashboard?.medium_count ?? 0}</strong><span>medium</span></div>
            </div>
          ) : (
            <p className="muted-copy auth-note">Sign in to unlock saved dashboard metrics. Guest reviews still work.</p>
          )}
        </div>
        <div>
          <div className="mini-title"><History size={16} /> Saved review history</div>
          <div className="history-list">
            {signedInEmail ? (
              <>
                {history.slice(0, 4).map((item) => (
                  <button className="history-item" key={item.id} onClick={() => loadHistoryItem(item.id)}>
                    #{item.id} {item.title.slice(0, 32)} · {item.comment_count} findings
                  </button>
                ))}
                {!history.length && <p className="muted-copy">Run a review while signed in to save it here.</p>}
              </>
            ) : (
              <p className="muted-copy auth-note">History is private. Sign in before running a review to save it.</p>
            )}
          </div>
        </div>
      </section>

      <RepoImporter
        repoUrl={repoUrl}
        branch={branch}
        loading={importing}
        onRepoUrlChange={setRepoUrl}
        onBranchChange={setBranch}
        onLoadingChange={setImporting}
        onFilesLoaded={(loadedFiles) => {
          setFiles(loadedFiles.length ? loadedFiles : files);
          setSelectedIndex(0);
          setResult(undefined);
        }}
        onError={setError}
      />

      {error && <div className="error-box">{error}</div>}

      <div className="toolbar card">
        <div className="ai-control">
          <label className="toggle">
            <input type="checkbox" checked={useAi} onChange={(e) => setUseAi(e.target.checked)} />
            <span>Optional AI review</span>
          </label>
          <p><Info size={14} /> AI review may use OpenRouter credits. Keep this off for free local testing and turn it on only for intentional demos.</p>
        </div>
        <div className="action-row">
          <button className="secondary" onClick={runExplain} disabled={loading || importing}>
            <Wand2 size={16} /> Explain codebase
          </button>
          <button onClick={runReview} disabled={loading || importing}>
            {loading ? <Loader2 className="spin" size={16} /> : <Sparkles size={16} />}
            {loading ? 'Reviewing...' : 'Run review'}
          </button>
        </div>
      </div>

      <div className="main-grid">
        <CodeInput
          files={files}
          selectedIndex={selectedIndex}
          onFilesChange={setFiles}
          onSelectedIndexChange={setSelectedIndex}
        />
        <ReviewResults result={result} files={files} repoUrl={repoUrl} />
      </div>
    </main>
  );
}

export default App;
