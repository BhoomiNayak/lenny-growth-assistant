import { useState, useEffect, useCallback } from 'react';
import { Menu, PanelRight, Sparkles, AlertTriangle, RefreshCw, X } from 'lucide-react';
import type { Session, Message, Artifact, ProviderConfig, StreamEvent } from './types';
import * as api from './api/client';
import { SessionSidebar } from './components/SessionSidebar';
import { MessageList } from './components/MessageList';
import { MessageInput } from './components/MessageInput';
import { ArtifactViewer } from './components/ArtifactViewer';
import { ModelToggle } from './components/ModelToggle';

function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSession, setActiveSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [activeArtifactId, setActiveArtifactId] = useState<string | null>(null);

  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [currentProvider, setCurrentProvider] = useState('ollama');
  const [currentModel, setCurrentModel] = useState('llama3.1:8b');

  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [lastFailedMessage, setLastFailedMessage] = useState<string | null>(null);

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [artifactOpen, setArtifactOpen] = useState(false);

  // ─── Initial load ────────────────────────────────────────────────────────
  useEffect(() => {
    loadSessions();
    loadConfig();
  }, []);

  const loadSessions = async () => {
    try {
      const res = await api.listSessions();
      setSessions(res.sessions);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const loadConfig = async () => {
    try {
      const cfg = await api.getModelConfig();
      setProviders(cfg.providers);
      setCurrentProvider(cfg.current_provider);
      setCurrentModel(cfg.current_model);
    } catch {
      // config load is non-critical
    }
  };

  const loadSessionData = useCallback(async (session: Session) => {
    try {
      const [msgRes, artRes] = await Promise.all([
        api.listMessages(session.id),
        api.listArtifacts(session.id),
      ]);
      setMessages(msgRes.messages);
      setArtifacts(artRes.artifacts);
      setCurrentProvider(session.model_provider);
      setCurrentModel(session.model_name);
      if (artRes.artifacts.length > 0) {
        setActiveArtifactId(artRes.artifacts[0].id);
      } else {
        setActiveArtifactId(null);
      }
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  // ─── Session handlers ────────────────────────────────────────────────────
  const handleNewSession = async () => {
    try {
      const session = await api.createSession();
      setSessions((prev) => [session, ...prev]);
      setActiveSession(session);
      setMessages([]);
      setArtifacts([]);
      setActiveArtifactId(null);
      setSidebarOpen(false);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const handleSelectSession = async (id: string) => {
    const session = sessions.find((s) => s.id === id);
    if (session) {
      setActiveSession(session);
      await loadSessionData(session);
      setSidebarOpen(false);
    }
  };

  const handleDeleteSession = async (id: string) => {
    try {
      await api.deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (activeSession?.id === id) {
        setActiveSession(null);
        setMessages([]);
        setArtifacts([]);
        setActiveArtifactId(null);
      }
    } catch (e) {
      setError((e as Error).message);
    }
  };

  // ─── Model switch ────────────────────────────────────────────────────────
  const handleSwitchModel = async (provider: string, model: string) => {
    setCurrentProvider(provider);
    setCurrentModel(model);
    if (activeSession) {
      try {
        const updated = await api.switchSessionModel(activeSession.id, provider, model);
        setActiveSession(updated);
      } catch (e) {
        setError((e as Error).message);
      }
    }
  };

  // ─── Message handler ─────────────────────────────────────────────────────
  const handleSend = async (content: string) => {
    setError(null);
    setLastFailedMessage(null);
    let session = activeSession;

    // Create session if none active
    if (!session) {
      try {
        session = await api.createSession();
        setSessions((prev) => [session!, ...prev]);
        setActiveSession(session);
      } catch (e) {
        setError((e as Error).message);
        setLastFailedMessage(content);
        return;
      }
    }

    // Optimistically add user message
    const userMsg: Message = {
      id: `temp-${Date.now()}`,
      session_id: session.id,
      role: 'user',
      content,
      sources: [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    setIsStreaming(true);
    setStreamingContent('');

    let accumulated = '';
    let sources: Message['sources'] = [];
    let streamError: string | null = null;

    try {
      await api.sendMessageStream(session.id, content, (event: StreamEvent) => {
        if (event.type === 'token' && event.content) {
          accumulated += event.content;
          setStreamingContent(accumulated);
        } else if (event.type === 'sources' && event.sources) {
          sources = event.sources;
        } else if (event.type === 'error') {
          streamError = event.message || 'An error occurred while generating the response.';
        }
      });

      if (streamError) {
        setError(streamError);
        setLastFailedMessage(content);
        return;
      }

      // Finalize assistant message
      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        session_id: session.id,
        role: 'assistant',
        content: accumulated,
        sources,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);

      // Refresh artifacts (in case one was generated) and session list
      const artRes = await api.listArtifacts(session.id);
      if (artRes.artifacts.length > artifacts.length) {
        setArtifacts(artRes.artifacts);
        setActiveArtifactId(artRes.artifacts[0].id);
        setArtifactOpen(true);
      }
      loadSessions();
    } catch (e) {
      setError((e as Error).message);
      setLastFailedMessage(content);
    } finally {
      setIsStreaming(false);
      setStreamingContent('');
    }
  };

  const handleRetry = () => {
    if (lastFailedMessage) {
      const msg = lastFailedMessage;
      setLastFailedMessage(null);
      setError(null);
      // Remove the optimistic user message that failed, then resend
      setMessages((prev) => prev.filter((m) => !m.id.startsWith('temp-')));
      handleSend(msg);
    }
  };

  // ─── Render ──────────────────────────────────────────────────────────────
  return (
    <div className="flex h-screen overflow-hidden bg-white">
      {/* Sidebar backdrop (mobile) */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/20 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <SessionSidebar
        sessions={sessions}
        activeSessionId={activeSession?.id ?? null}
        onNewSession={handleNewSession}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
        isOpen={sidebarOpen}
      />

      {/* Main chat area */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Header */}
        <header className="flex items-center justify-between border-b border-neutral-200 px-4 py-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              aria-label="Toggle sidebar"
              className="rounded-lg p-2 text-neutral-500 hover:bg-neutral-100 md:hidden"
            >
              <Menu size={20} />
            </button>
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-600 text-white">
                <Sparkles size={18} />
              </div>
              <h1 className="text-base font-semibold text-neutral-800">
                Lenny Growth Assistant
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <ModelToggle
              currentProvider={currentProvider}
              currentModel={currentModel}
              providers={providers}
              onSwitch={handleSwitchModel}
            />
            {artifacts.length > 0 && (
              <button
                onClick={() => setArtifactOpen(!artifactOpen)}
                aria-label="Toggle artifact panel"
                className="rounded-lg p-2 text-neutral-500 hover:bg-neutral-100"
              >
                <PanelRight size={20} />
              </button>
            )}
          </div>
        </header>

        {/* Error banner */}
        {error && (
          <div className="flex items-center gap-3 border-b border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800">
            <AlertTriangle size={16} className="shrink-0" />
            <span className="flex-1">{error}</span>
            {lastFailedMessage && (
              <button
                onClick={handleRetry}
                disabled={isStreaming}
                className="flex items-center gap-1 rounded-md bg-amber-600 px-2.5 py-1 text-xs font-medium text-white transition-colors hover:bg-amber-700 disabled:opacity-50"
              >
                <RefreshCw size={12} />
                Retry
              </button>
            )}
            <button
              onClick={() => {
                setError(null);
                setLastFailedMessage(null);
              }}
              className="rounded p-1 hover:bg-amber-100"
              aria-label="Dismiss error"
            >
              <X size={14} />
            </button>
          </div>
        )}

        {/* Messages or welcome */}
        {messages.length === 0 && !isStreaming ? (
          <WelcomeScreen onExampleClick={handleSend} />
        ) : (
          <MessageList
            messages={messages}
            isStreaming={isStreaming}
            streamingContent={streamingContent}
          />
        )}

        {/* Input */}
        <MessageInput onSend={handleSend} disabled={isStreaming} />
      </div>

      {/* Artifact viewer */}
      <ArtifactViewer
        artifacts={artifacts}
        activeArtifactId={activeArtifactId}
        onSelectArtifact={setActiveArtifactId}
        onClose={() => setArtifactOpen(false)}
        isOpen={artifactOpen}
      />
    </div>
  );
}

function WelcomeScreen({ onExampleClick }: { onExampleClick: (q: string) => void }) {
  const examples = [
    'How did Airbnb improve their activation rate?',
    'What growth strategies work for early-stage startups?',
    'Write a Ship 30 for 30 essay on user retention',
    'How do you build a high-performing growth team?',
  ];

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 text-center">
      <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary-600 text-white">
        <Sparkles size={32} />
      </div>
      <h2 className="mb-2 text-2xl font-semibold text-neutral-800">
        Ask me anything about product & growth
      </h2>
      <p className="mb-8 max-w-md text-neutral-500">
        I answer questions grounded in Lenny's Podcast transcripts, write Ship 30 for 30
        essays, and generate artifacts.
      </p>
      <div className="grid w-full max-w-2xl gap-3 sm:grid-cols-2">
        {examples.map((ex) => (
          <button
            key={ex}
            onClick={() => onExampleClick(ex)}
            className="rounded-xl border border-neutral-200 p-4 text-left text-sm text-neutral-700 transition-colors hover:border-primary-300 hover:bg-primary-50"
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}

export default App;
