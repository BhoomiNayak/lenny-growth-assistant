import { Plus, MessageSquare, Trash2 } from 'lucide-react';
import type { Session } from '../types';

interface SessionSidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  onNewSession: () => void;
  onSelectSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  isOpen: boolean;
}

export function SessionSidebar({
  sessions,
  activeSessionId,
  onNewSession,
  onSelectSession,
  onDeleteSession,
  isOpen,
}: SessionSidebarProps) {
  return (
    <nav
      aria-label="Chat sessions"
      className={`${
        isOpen ? 'translate-x-0' : '-translate-x-full'
      } fixed md:static z-30 flex h-full w-72 flex-col border-r border-neutral-200 bg-white transition-transform md:translate-x-0`}
    >
      {/* Header */}
      <div className="p-4">
        <button
          onClick={onNewSession}
          aria-label="Start new chat"
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        >
          <Plus size={18} />
          New Chat
        </button>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto px-2 pb-4">
        {sessions.length === 0 ? (
          <p className="px-3 py-4 text-sm text-neutral-400">No chats yet</p>
        ) : (
          <ul role="list" className="space-y-1">
            {sessions.map((session) => (
              <li key={session.id}>
                <div
                  className={`group flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                    session.id === activeSessionId
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-neutral-700 hover:bg-neutral-100'
                  }`}
                >
                  <button
                    onClick={() => onSelectSession(session.id)}
                    aria-current={session.id === activeSessionId ? 'page' : undefined}
                    className="flex flex-1 items-center gap-2 truncate text-left focus:outline-none"
                  >
                    <MessageSquare size={16} className="shrink-0" />
                    <span className="truncate">{session.title}</span>
                  </button>
                  <button
                    onClick={() => {
                      if (confirm('Delete this chat?')) onDeleteSession(session.id);
                    }}
                    aria-label={`Delete ${session.title}`}
                    className="shrink-0 rounded p-1 text-neutral-400 opacity-0 transition-opacity hover:bg-neutral-200 hover:text-red-600 focus:opacity-100 group-hover:opacity-100"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-neutral-200 p-4">
        <p className="text-xs text-neutral-400">
          Lenny Growth Assistant
        </p>
      </div>
    </nav>
  );
}
