// ─── Session ──────────────────────────────────────────────────────────────────

export interface Session {
  id: string;
  title: string;
  model_provider: string;
  model_name: string;
  created_at: string;
  updated_at: string;
}

export interface SessionListResponse {
  sessions: Session[];
  total: number;
}

// ─── Message ──────────────────────────────────────────────────────────────────

export interface SourceCitation {
  episode_id: string;
  guest: string;
  episode_title: string;
  youtube_url?: string | null;
  publish_date?: string | null;
  excerpt: string;
}

export interface Message {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources: SourceCitation[];
  latency_ms?: number | null;
  token_count?: number | null;
  created_at: string;
}

export interface MessageListResponse {
  messages: Message[];
  total: number;
}

// ─── Artifact ─────────────────────────────────────────────────────────────────

export interface Artifact {
  id: string;
  session_id: string;
  type: 'markdown' | 'html';
  title: string;
  content: string;
  sanitized: boolean;
  created_at: string;
}

export interface ArtifactListResponse {
  artifacts: Artifact[];
}

// ─── Config ───────────────────────────────────────────────────────────────────

export interface ProviderConfig {
  provider: string;
  model: string;
  available: boolean;
  reason?: string | null;
}

export interface ModelConfigResponse {
  current_provider: string;
  current_model: string;
  providers: ProviderConfig[];
}

// ─── Streaming Events ─────────────────────────────────────────────────────────

export type StreamEventType = 'start' | 'token' | 'sources' | 'done' | 'artifact' | 'error';

export interface StreamEvent {
  type: StreamEventType;
  content?: string;
  message_id?: string;
  sources?: SourceCitation[];
  artifact_id?: string;
  title?: string;
  latency_ms?: number;
  token_count?: number;
  code?: string;
  message?: string;
}

// ─── Error ────────────────────────────────────────────────────────────────────

export interface ApiError {
  error: {
    code: string;
    message: string;
    retryable: boolean;
  };
}
