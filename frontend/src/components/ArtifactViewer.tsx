import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { X, Copy, Download, Check, FileText, Code } from 'lucide-react';
import type { Artifact } from '../types';

interface ArtifactViewerProps {
  artifacts: Artifact[];
  activeArtifactId: string | null;
  onSelectArtifact: (id: string) => void;
  onClose: () => void;
  isOpen: boolean;
}

export function ArtifactViewer({
  artifacts,
  activeArtifactId,
  onSelectArtifact,
  onClose,
  isOpen,
}: ArtifactViewerProps) {
  const [copied, setCopied] = useState(false);

  const active = artifacts.find((a) => a.id === activeArtifactId) || artifacts[0] || null;

  const handleCopy = async () => {
    if (active) {
      await navigator.clipboard.writeText(active.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownload = () => {
    if (!active) return;
    const ext = active.type === 'html' ? 'html' : 'md';
    const blob = new Blob([active.content], {
      type: active.type === 'html' ? 'text/html' : 'text/markdown',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${active.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!isOpen) return null;

  return (
    <aside
      aria-label="Artifact viewer"
      className="fixed inset-y-0 right-0 z-40 flex w-full flex-col border-l border-neutral-200 bg-white md:static md:z-0 md:w-[420px]"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-neutral-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-neutral-700">Artifacts</h2>
        <button
          onClick={onClose}
          aria-label="Close artifact viewer"
          className="rounded p-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600"
        >
          <X size={18} />
        </button>
      </div>

      {artifacts.length === 0 ? (
        <div className="flex flex-1 items-center justify-center p-8 text-center">
          <p className="text-sm text-neutral-400">
            No artifacts yet. Ask the assistant to create an essay, document, or HTML.
          </p>
        </div>
      ) : (
        <>
          {/* Artifact tabs */}
          {artifacts.length > 1 && (
            <div className="flex gap-1 overflow-x-auto border-b border-neutral-200 px-2 py-2">
              {artifacts.map((art) => (
                <button
                  key={art.id}
                  onClick={() => onSelectArtifact(art.id)}
                  className={`flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs transition-colors ${
                    art.id === active?.id
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-neutral-500 hover:bg-neutral-100'
                  }`}
                >
                  {art.type === 'html' ? <Code size={13} /> : <FileText size={13} />}
                  <span className="max-w-[120px] truncate">{art.title}</span>
                </button>
              ))}
            </div>
          )}

          {/* Toolbar */}
          {active && (
            <div className="flex items-center justify-between border-b border-neutral-200 px-4 py-2">
              <span className="flex items-center gap-1.5 text-xs font-medium text-neutral-500">
                {active.type === 'html' ? <Code size={13} /> : <FileText size={13} />}
                {active.type.toUpperCase()}
                {active.sanitized && (
                  <span className="rounded bg-green-50 px-1.5 py-0.5 text-[10px] text-green-700">
                    sanitized
                  </span>
                )}
              </span>
              <div className="flex gap-1">
                <button
                  onClick={handleCopy}
                  aria-label="Copy artifact"
                  className="flex items-center gap-1 rounded p-1.5 text-xs text-neutral-500 hover:bg-neutral-100"
                >
                  {copied ? <Check size={14} className="text-green-600" /> : <Copy size={14} />}
                </button>
                <button
                  onClick={handleDownload}
                  aria-label="Download artifact"
                  className="flex items-center gap-1 rounded p-1.5 text-xs text-neutral-500 hover:bg-neutral-100"
                >
                  <Download size={14} />
                </button>
              </div>
            </div>
          )}

          {/* Content */}
          <div className="flex-1 overflow-y-auto">
            {active && active.type === 'html' ? (
              <iframe
                srcDoc={active.content}
                sandbox=""
                title="Artifact Preview"
                className="h-full w-full border-0"
              />
            ) : active ? (
              <div className="prose prose-sm max-w-none p-6">
                <ReactMarkdown>{active.content}</ReactMarkdown>
              </div>
            ) : null}
          </div>
        </>
      )}
    </aside>
  );
}
