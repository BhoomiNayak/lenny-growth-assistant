import { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Bot, User } from 'lucide-react';
import type { Message } from '../types';
import { SourceCitation } from './SourceCitation';

interface MessageListProps {
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
}

export function MessageList({ messages, isStreaming, streamingContent }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  return (
    <main
      aria-label="Chat messages"
      role="log"
      aria-live="polite"
      className="flex-1 space-y-6 overflow-y-auto px-4 py-6 md:px-8"
    >
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}

      {/* Streaming message */}
      {isStreaming && (
        <div className="flex gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-100 text-primary-600">
            <Bot size={18} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="prose prose-sm max-w-none rounded-2xl rounded-tl-sm bg-neutral-50 px-4 py-3 text-neutral-800">
              {streamingContent ? (
                <ReactMarkdown>{streamingContent}</ReactMarkdown>
              ) : (
                <TypingIndicator />
              )}
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </main>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end gap-3">
        <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-primary-600 px-4 py-3 text-white">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-600 text-white">
          <User size={18} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-100 text-primary-600">
        <Bot size={18} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="prose prose-sm max-w-none rounded-2xl rounded-tl-sm bg-neutral-50 px-4 py-3 text-neutral-800">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>
        <SourceCitation sources={message.sources} />
        {message.latency_ms != null && (
          <p className="mt-1 text-xs text-neutral-400">
            {(message.latency_ms / 1000).toFixed(1)}s
            {message.token_count ? ` · ${message.token_count} tokens` : ''}
          </p>
        )}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 py-1" aria-label="Assistant is typing">
      <span className="h-2 w-2 animate-bounce rounded-full bg-neutral-400 [animation-delay:-0.3s]" />
      <span className="h-2 w-2 animate-bounce rounded-full bg-neutral-400 [animation-delay:-0.15s]" />
      <span className="h-2 w-2 animate-bounce rounded-full bg-neutral-400" />
    </div>
  );
}
