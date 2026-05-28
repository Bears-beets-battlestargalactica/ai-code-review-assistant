import { Bot, CheckCircle2, Clipboard, Download, FlaskConical, GitPullRequest, MessageSquare, Sparkles } from 'lucide-react';
import { generatePrComment, getMarkdownReport, ReviewFile, ReviewResponse, Severity } from '../api/client';

const severityRank: Record<Severity, number> = { high: 1, medium: 2, low: 3, info: 4 };

type Props = {
  result?: ReviewResponse;
  files: ReviewFile[];
  repoUrl?: string;
};

function lineWindow(totalLines: number, targetLine: number, radius = 2) {
  const start = Math.max(1, targetLine - radius);
  const end = Math.min(totalLines, targetLine + radius);
  return { start, end };
}

function buildInlineMarkdown(result: ReviewResponse): string {
  if (!result.comments.length) {
    return 'No review comments generated.';
  }

  return result.comments
    .map((comment) => {
      const suggestion = comment.suggestion ? `\nSuggestion: ${comment.suggestion}` : '';
      const patch = comment.patch ? `\n\nSuggested patch:\n\`\`\`diff\n${comment.patch}\n\`\`\`` : '';
      return `### ${comment.file_path}:${comment.line}\n**${comment.severity.toUpperCase()} · ${comment.category} · ${comment.source}**\n\n${comment.message}${suggestion}${patch}`;
    })
    .join('\n\n---\n\n');
}

function downloadText(filename: string, text: string) {
  const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function PatchDiff({ patch }: { patch: string }) {
  const lines = patch.split('\n');
  return (
    <pre className="patch-diff">
      {lines.map((line, index) => {
        const klass = line.startsWith('+') ? 'added' : line.startsWith('-') ? 'removed' : 'context';
        return <div className={klass} key={index}>{line || ' '}</div>;
      })}
    </pre>
  );
}

export function ReviewResults({ result, files, repoUrl }: Props) {
  if (!result) {
    return (
      <section className="card empty-state">
        <Bot size={32} />
        <h2>Review results will appear here</h2>
        <p>Run a review to get rule-based findings, lint results, AI comments, suggested patches, and tests.</p>
      </section>
    );
  }

  const currentResult = result;
  const comments = [...currentResult.comments].sort((a, b) => severityRank[a.severity] - severityRank[b.severity]);
  const commentedFiles = files
    .map((file) => ({ file, comments: comments.filter((comment) => comment.file_path === file.path) }))
    .filter((entry) => entry.comments.length > 0);

  async function copyInlineComments() {
    await navigator.clipboard.writeText(buildInlineMarkdown(currentResult));
  }

  async function downloadReport() {
    const report = await getMarkdownReport(currentResult);
    downloadText(`code-review-report-${currentResult.id ?? 'latest'}.md`, report.markdown);
  }

  async function copyPrDraft() {
    const pr = await generatePrComment(currentResult, repoUrl, undefined, 'draft');
    await navigator.clipboard.writeText(pr.body);
    alert('GitHub PR-style comment copied to clipboard.');
  }

  return (
    <section className="card results-card">
      <div className="section-title between">
        <div className="section-title compact">
          <CheckCircle2 size={20} />
          <div>
            <h2>Review Summary</h2>
            <p>{currentResult.summary}</p>
            {!currentResult.id && <p className="guest-save-note">Guest review: this result was not saved. Sign in before running a review to keep history.</p>}
          </div>
        </div>
        {currentResult.comments.length > 0 && (
          <div className="action-row">
            <button className="ghost" onClick={copyInlineComments} type="button"><Clipboard size={16} /> Copy comments</button>
            <button className="ghost" onClick={copyPrDraft} type="button"><GitPullRequest size={16} /> Copy PR comment</button>
            <button className="ghost" onClick={downloadReport} type="button"><Download size={16} /> Download report</button>
          </div>
        )}
      </div>

      {currentResult.explanation && (
        <div className="explanation-box">
          <div className="mini-title"><Sparkles size={16} /> Codebase explanation</div>
          <p>{currentResult.explanation}</p>
        </div>
      )}

      {currentResult.lint_output && currentResult.lint_output.length > 0 && (
        <div className="lint-box">
          <div className="mini-title">ESLint/Ruff integration</div>
          {currentResult.lint_output.map((line, index) => <p key={index}>{line}</p>)}
        </div>
      )}

      {commentedFiles.length > 0 && (
        <div className="inline-review-box">
          <div className="mini-title"><MessageSquare size={16} /> GitHub-style inline comments</div>
          <p className="muted-copy">Comments are shown directly under the nearby source line, similar to a pull request review.</p>

          {commentedFiles.map(({ file, comments: fileComments }) => {
            const lines = file.content.split('\n');
            const sortedFileComments = [...fileComments].sort((a, b) => a.line - b.line);

            return (
              <div className="inline-file" key={file.path}>
                <div className="inline-file-head">{file.path}</div>
                {sortedFileComments.map((comment, index) => {
                  const { start, end } = lineWindow(lines.length, comment.line);
                  const snippet = lines.slice(start - 1, end);

                  return (
                    <div className="inline-thread" key={`${file.path}-${comment.line}-${index}`}>
                      <div className="code-snippet">
                        {snippet.map((line, lineIndex) => {
                          const lineNumber = start + lineIndex;
                          const isTarget = lineNumber === comment.line;
                          return (
                            <div className={`code-line ${isTarget ? 'target' : ''}`} key={lineNumber}>
                              <span className="line-number">{lineNumber}</span>
                              <code>{line || ' '}</code>
                            </div>
                          );
                        })}
                      </div>
                      <div className={`inline-comment ${comment.severity}`}>
                        <div className="comment-head">
                          <span className={`badge ${comment.severity}`}>{comment.severity}</span>
                          <span className="badge muted">{comment.category}</span>
                          <span className="badge source">{comment.source}</span>
                        </div>
                        <strong>{comment.file_path}:{comment.line}</strong>
                        <p>{comment.message}</p>
                        {comment.suggestion && <p className="suggestion"><strong>Suggestion:</strong> {comment.suggestion}</p>}
                        {comment.patch && <PatchDiff patch={comment.patch} />}
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      )}

      {currentResult.unit_test_suggestions.length > 0 && (
        <div className="tests-box">
          <div className="mini-title"><FlaskConical size={16} /> Unit test suggestions</div>
          <ul>
            {currentResult.unit_test_suggestions.map((test, index) => <li key={index}>{test}</li>)}
          </ul>
        </div>
      )}
    </section>
  );
}
