import { Code2, Download } from 'lucide-react';
import { importGithubRepo, ReviewFile } from '../api/client';

type Props = {
  repoUrl: string;
  branch: string;
  loading: boolean;
  onRepoUrlChange: (value: string) => void;
  onBranchChange: (value: string) => void;
  onLoadingChange: (value: boolean) => void;
  onFilesLoaded: (files: ReviewFile[]) => void;
  onError: (message: string) => void;
};

export function RepoImporter(props: Props) {
  async function handleImport() {
    if (!props.repoUrl.trim()) {
      props.onError('Paste a GitHub repository URL first.');
      return;
    }

    props.onLoadingChange(true);
    props.onError('');
    try {
      const result = await importGithubRepo(props.repoUrl, props.branch || 'main');
      props.onFilesLoaded(result.files);
    } catch (error) {
      props.onError(error instanceof Error ? error.message : 'Could not import repository.');
    } finally {
      props.onLoadingChange(false);
    }
  }

  return (
    <section className="card">
      <div className="section-title">
        <Code2 size={20} />
        <div>
          <h2>Import GitHub repo</h2>
          <p>Pull public source files and review them file-by-file.</p>
        </div>
      </div>
      <div className="repo-row">
        <input
          value={props.repoUrl}
          onChange={(e) => props.onRepoUrlChange(e.target.value)}
          placeholder="https://github.com/owner/repo"
        />
        <input
          className="branch-input"
          value={props.branch}
          onChange={(e) => props.onBranchChange(e.target.value)}
          placeholder="main"
        />
        <button onClick={handleImport} disabled={props.loading}>
          <Download size={16} />
          {props.loading ? 'Importing...' : 'Import'}
        </button>
      </div>
    </section>
  );
}
