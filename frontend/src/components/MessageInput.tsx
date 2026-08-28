import { useState, useRef, useEffect, type KeyboardEvent } from 'react';
import { Send } from 'lucide-react';

interface MessageInputProps {
  onSend: (content: string) => void;
  disabled: boolean;
  placeholder?: string;
}

export function MessageInput({ onSend, disabled, placeholder }: MessageInputProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
    }
  }, [value]);

  const handleSend = () => {
    const trimmed = value.trim();
    if (trimmed && !disabled) {
      onSend(trimmed);
      setValue('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Cmd/Ctrl + Enter to send
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-neutral-200 bg-white p-4">
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <div className="flex-1 rounded-2xl border border-neutral-300 bg-white transition-colors focus-within:border-primary-500 focus-within:ring-2 focus-within:ring-primary-100">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={placeholder || 'Ask anything about product & growth...'}
            rows={1}
            aria-label="Message input"
            className="max-h-40 w-full resize-none rounded-2xl bg-transparent px-4 py-3 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none disabled:opacity-50"
          />
        </div>
        <button
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          aria-label="Send message"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary-600 text-white transition-colors hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Send size={18} />
        </button>
      </div>
      <p className="mx-auto mt-2 max-w-3xl text-center text-xs text-neutral-400">
        Press <kbd className="rounded bg-neutral-100 px-1">Cmd/Ctrl + Enter</kbd> to send
      </p>
    </div>
  );
}
