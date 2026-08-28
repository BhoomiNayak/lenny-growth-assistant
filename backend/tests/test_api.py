"""API endpoint tests — sessions, messages, health, config."""

import pytest
from httpx import AsyncClient


class TestHealth:
    """Health and readiness endpoints."""

    async def test_health_returns_ok(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data

    async def test_readiness_returns_dependencies(self, client: AsyncClient):
        resp = await client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ready", "degraded")
        assert "database" in data["dependencies"]
        assert "ollama" in data["dependencies"]
        assert "anthropic" in data["dependencies"]


class TestSessions:
    """Session CRUD endpoints."""

    async def test_create_session_default_title(self, client: AsyncClient):
        resp = await client.post("/api/v1/sessions", json={})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "New Chat"
        assert data["model_provider"] == "ollama"
        assert "id" in data

    async def test_create_session_custom_title(self, client: AsyncClient):
        resp = await client.post("/api/v1/sessions", json={"title": "My Chat"})
        assert resp.status_code == 201
        assert resp.json()["title"] == "My Chat"

    async def test_list_sessions_empty(self, client: AsyncClient):
        resp = await client.get("/api/v1/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["sessions"] == []

    async def test_list_sessions_returns_created(self, client: AsyncClient):
        await client.post("/api/v1/sessions", json={"title": "Chat 1"})
        await client.post("/api/v1/sessions", json={"title": "Chat 2"})
        resp = await client.get("/api/v1/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    async def test_get_session_by_id(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/sessions", json={"title": "Fetch Me"})
        session_id = create_resp.json()["id"]
        resp = await client.get(f"/api/v1/sessions/{session_id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Fetch Me"

    async def test_get_session_not_found(self, client: AsyncClient):
        resp = await client.get("/api/v1/sessions/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "SESSION_NOT_FOUND"

    async def test_patch_session_title(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/sessions", json={})
        session_id = create_resp.json()["id"]
        resp = await client.patch(
            f"/api/v1/sessions/{session_id}",
            json={"title": "Updated Title"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"

    async def test_delete_session(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/sessions", json={})
        session_id = create_resp.json()["id"]
        del_resp = await client.delete(f"/api/v1/sessions/{session_id}")
        assert del_resp.status_code == 204
        # Confirm it's gone
        get_resp = await client.get(f"/api/v1/sessions/{session_id}")
        assert get_resp.status_code == 404

    async def test_delete_session_not_found(self, client: AsyncClient):
        resp = await client.delete("/api/v1/sessions/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


class TestMessages:
    """Message endpoint tests (sync mode only — streaming tested via manual plan)."""

    async def test_list_messages_empty(self, client: AsyncClient):
        sess = await client.post("/api/v1/sessions", json={})
        session_id = sess.json()["id"]
        resp = await client.get(f"/api/v1/sessions/{session_id}/messages")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["messages"] == []

    async def test_list_messages_session_not_found(self, client: AsyncClient):
        resp = await client.get("/api/v1/sessions/00000000-0000-0000-0000-000000000000/messages")
        assert resp.status_code == 404

    async def test_send_message_validation_empty_content(self, client: AsyncClient):
        sess = await client.post("/api/v1/sessions", json={})
        session_id = sess.json()["id"]
        resp = await client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"content": "", "stream": False},
        )
        assert resp.status_code == 422  # Pydantic validation


class TestConfig:
    """Model configuration endpoint."""

    async def test_get_models(self, client: AsyncClient):
        resp = await client.get("/api/v1/config/models")
        assert resp.status_code == 200
        data = resp.json()
        assert "current_provider" in data
        assert "current_model" in data
        assert "providers" in data
        assert len(data["providers"]) == 3  # ollama, anthropic, openai
