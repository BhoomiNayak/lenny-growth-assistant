import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Cpu, Cloud, Circle } from 'lucide-react';
import type { ProviderConfig } from '../types';

interface ModelToggleProps {
  currentProvider: string;
  currentModel: string;
  providers: ProviderConfig[];
  onSwitch: (provider: string, model: string) => void;
}

export function ModelToggle({
  currentProvider,
  currentModel,
  providers,
  onSwitch,
}: ModelToggleProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const isLocal = currentProvider === 'ollama';

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        aria-label="Switch model"
        aria-expanded={open}
        className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
          isLocal
            ? 'border-green-200 bg-green-50 text-green-700'
            : 'border-primary-200 bg-primary-50 text-primary-700'
        }`}
      >
        {isLocal ? <Cpu size={14} /> : <Cloud size={14} />}
        <span className="max-w-[160px] truncate">
          {currentProvider} — {currentModel}
        </span>
        <ChevronDown size={14} />
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-64 rounded-lg border border-neutral-200 bg-white p-2 shadow-lg">
          <p className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-neutral-400">
            Select Model
          </p>
          {providers.map((p) => {
            const isActive = p.provider === currentProvider;
            return (
              <button
                key={p.provider}
                onClick={() => {
                  if (p.available) {
                    onSwitch(p.provider, p.model);
                    setOpen(false);
                  }
                }}
                disabled={!p.available}
                className={`flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm transition-colors ${
                  isActive
                    ? 'bg-neutral-100'
                    : p.available
                      ? 'hover:bg-neutral-50'
                      : 'cursor-not-allowed opacity-50'
                }`}
              >
                {p.provider === 'ollama' ? (
                  <Cpu size={15} className="shrink-0 text-green-600" />
                ) : (
                  <Cloud size={15} className="shrink-0 text-primary-600" />
                )}
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-neutral-700">{p.provider}</p>
                  <p className="truncate text-xs text-neutral-400">
                    {p.available ? p.model : p.reason}
                  </p>
                </div>
                {isActive && <Circle size={8} className="shrink-0 fill-green-500 text-green-500" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
