import { FileCode2, Plus, Trash2 } from 'lucide-react';
import { ReviewFile } from '../api/client';

type Props = {
  files: ReviewFile[];
  selectedIndex: number;
  onFilesChange: (files: ReviewFile[]) => void;
  onSelectedIndexChange: (index: number) => void;
};

const starterCode = `function calculateTotal(items) {\n  var total = 0;\n  items.forEach(item => {\n    total += item.price\n  })\n  console.log(total);\n  return total;\n}`;

export function CodeInput({ files, selectedIndex, onFilesChange, onSelectedIndexChange }: Props) {
  const selected = files[selectedIndex] ?? files[0];

  function updateSelected(patch: Partial<ReviewFile>) {
    onFilesChange(files.map((file, index) => index === selectedIndex ? { ...file, ...patch } : file));
  }

  function addFile() {
    const next = [...files, { path: `src/example-${files.length + 1}.ts`, language: 'typescript', content: starterCode }];
    onFilesChange(next);
    onSelectedIndexChange(next.length - 1);
  }

  function removeFile(index: number) {
    if (files.length === 1) return;
    const next = files.filter((_, i) => i !== index);
    onFilesChange(next);
    onSelectedIndexChange(Math.max(0, Math.min(selectedIndex, next.length - 1)));
  }

  return (
    <section className="card editor-card">
      <div className="section-title between">
        <div className="section-title compact">
          <FileCode2 size={20} />
          <div>
            <h2>Files</h2>
            <p>Paste code directly or import a repo above.</p>
          </div>
        </div>
        <button className="ghost" onClick={addFile}><Plus size={16} /> Add file</button>
      </div>

      <div className="file-tabs">
        {files.map((file, index) => (
          <button
            key={`${file.path}-${index}`}
            className={index === selectedIndex ? 'file-tab active' : 'file-tab'}
            onClick={() => onSelectedIndexChange(index)}
          >
            {file.path}
            {files.length > 1 && (
              <span onClick={(event) => { event.stopPropagation(); removeFile(index); }}>
                <Trash2 size={12} />
              </span>
            )}
          </button>
        ))}
      </div>

      {selected && (
        <>
          <div className="field-grid">
            <input value={selected.path} onChange={(e) => updateSelected({ path: e.target.value })} />
            <input value={selected.language ?? ''} onChange={(e) => updateSelected({ language: e.target.value })} placeholder="typescript" />
          </div>
          <textarea
            className="code-area"
            value={selected.content}
            onChange={(e) => updateSelected({ content: e.target.value })}
            spellCheck={false}
          />
        </>
      )}
    </section>
  );
}
