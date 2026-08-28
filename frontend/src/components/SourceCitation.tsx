import { useState } from 'react';
import { ExternalLink, Quote } from 'lucide-react';
import type { SourceCitation as Source } from '../types';

interface SourceCitationProps {
  sources: Source[];
}

export function SourceCitation({ sources }: SourceCitationProps) {
  const [expanded, setExpanded] = useState<number | null>(null);
  const [showAll, setShowAll] = useState(false);

  if (!sources || sources.length === 0) return null;

  const visible = showAll ? sources : sources.slice(0, 3);
  const hidden = sources.length - 3;

  return (
    <div className="mt-3 space-y-2" aria-label="Sources">
      <div className="flex flex-wrap gap-2">
        {visible.map((source, i) => (
          <button
            key={`${source.episode_id}-${i}`}
            onClick={() => setExpanded(expanded === i ? null : i)}
            aria-label={`Source: ${source.guest}, ${source.episode_title}`}
            className="inline-flex items-center gap-1.5 rounded-full border border-neutral-200 bg-neutral-50 px-3 py-1 text-xs text-neutral-600 transition-colors hover:bg-neutral-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <Quote size={11} />
            <span className="max-w-[200px] truncate font-medium">{source.guest}</span>
          </button>
        ))}
        {!showAll && hidden > 0 && (
          <button
            onClick={() => setShowAll(true)}
            className="rounded-full border border-neutral-200 px-3 py-1 text-xs text-neutral-500 hover:bg-neutral-100"
          >
            +{hidden} more
          </button>
        )}
      </div>

      {expanded !== null && visible[expanded] && (
        <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-3 text-xs">
          <p className="mb-1 font-semibold text-neutral-700">
            {visible[expanded].episode_title}
          </p>
          <p className="mb-2 italic text-neutral-500">"{visible[expanded].excerpt}"</p>
          {visible[expanded].youtube_url && (
            <a
              href={visible[expanded].youtube_url!}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-primary-600 hover:underline"
            >
              <ExternalLink size={11} />
              Watch on YouTube
            </a>
          )}
        </div>
      )}
    </div>
  );
}
