import type {
  Session,
  SessionListResponse,
  MessageListResponse,
  Message,
  Artifact,
  ArtifactListResponse,
  ModelConfigResponse,
  StreamEvent,
} from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

// ─── Helpers ──────────────────────────────────────────────────────────────────

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: res.statusText } }));
    throw new Error(err.error?.message || `API error: ${res.status}`);
  }
  return res.json();
}

// ─── Sessions ─────────────────────────────────────────────────────────────────

export async function createSession(title?: string): Promise<Session> {
  return request<Session>('/api/v1/sessions', {
    method: 'POST',
    body: JSON.stringify(title ? { title } : {}),
  });
}

export async function listSessions(): Promise<SessionListResponse> {
  return request<SessionListResponse>('/api/v1/sessions?limit=50');
}

export async function deleteSession(id: string): Promise<void> {
  await fetch(`${API_URL}/api/v1/sessions/${id}`, { method: 'DELETE' });
}

// ─── Messages ─────────────────────────────────────────────────────────────────

export async function listMessages(sessionId: string): Promise<MessageListResponse> {
  return request<MessageListResponse>(`/api/v1/sessions/${sessionId}/messages?limit=100`);
}

export async function sendMessage(sessionId: string, content: string): Promise<Message> {
  return request<Message>(`/api/v1/sessions/${sessionId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ content, stream: false }),
  });
}

export async function sendMessageStream(
  sessionId: string,
  content: string,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, stream: true }),
    signal,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: res.statusText } }));
    throw new Error(err.error?.message || `API error: ${res.status}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event: StreamEvent = JSON.parse(line.slice(6));
          onEvent(event);
        } catch {
          // skip malformed events
        }
      }
    }
  }
}

// ─── Artifacts ────────────────────────────────────────────────────────────────

export async function listArtifacts(sessionId: string): Promise<ArtifactListResponse> {
  return request<ArtifactListResponse>(`/api/v1/sessions/${sessionId}/artifacts`);
}

export async function getArtifact(artifactId: string): Promise<Artifact> {
  return request<Artifact>(`/api/v1/artifacts/${artifactId}`);
}

export async function generateArtifact(
  sessionId: string,
  type: 'markdown' | 'html',
  prompt: string,
): Promise<Artifact> {
  return request<Artifact>(`/api/v1/sessions/${sessionId}/artifacts`, {
    method: 'POST',
    body: JSON.stringify({ type, prompt }),
  });
}

// ─── Config ───────────────────────────────────────────────────────────────────

export async function getModelConfig(): Promise<ModelConfigResponse> {
  return request<ModelConfigResponse>('/api/v1/config/models');
}

export async function switchSessionModel(
  sessionId: string,
  provider: string,
  model: string,
): Promise<Session> {
  return request<Session>(`/api/v1/sessions/${sessionId}/model`, {
    method: 'PUT',
    body: JSON.stringify({ provider, model }),
  });
}

// ─── Health ───────────────────────────────────────────────────────────────────

export async function healthCheck(): Promise<{ status: string; version: string }> {
  return request<{ status: string; version: string }>('/health');
}
