"""Agent routing tests — skill selection and topic extraction."""

import pytest

from app.agents.base import SkillRouter


class TestSkillRouter:
    """SkillRouter routes messages to the correct skill."""

    def setup_method(self):
        self.router = SkillRouter()

    # ─── RAG (default) ───────────────────────────────────────────────────────

    @pytest.mark.parametrize("message", [
        "How do I improve activation?",
        "What did Brian Chesky say about design?",
        "Tell me about product-market fit",
        "How does Notion approach growth?",
        "What are the best retention strategies?",
    ])
    def test_routes_questions_to_rag(self, message):
        assert self.router.route(message) == "rag"

    # ─── Ship 30 for 30 ──────────────────────────────────────────────────────

    @pytest.mark.parametrize("message", [
        "Write a Ship 30 for 30 essay on retention",
        "Write a ship30for30 essay about growth",
        "Turn this into an essay",
        "Write a blog post about activation",
        "Write an article on onboarding",
    ])
    def test_routes_to_ship30(self, message):
        assert self.router.route(message) == "ship30"

    # ─── Artifact ────────────────────────────────────────────────────────────

    @pytest.mark.parametrize("message", [
        "Create an HTML slide deck about onboarding",
        "Generate a markdown document summarizing our chat",
        "Make a presentation on growth",
        "Create a chart of the metrics",
        "Build a table comparing strategies",
    ])
    def test_routes_to_artifact(self, message):
        assert self.router.route(message) == "artifact"

    # ─── Artifact type detection ─────────────────────────────────────────────

    def test_detect_html_type(self):
        assert self.router.detect_artifact_type("create an HTML slide deck") == "html"
        assert self.router.detect_artifact_type("make a visual presentation") == "html"

    def test_detect_markdown_type_default(self):
        assert self.router.detect_artifact_type("create a document") == "markdown"

    # ─── Case insensitivity ──────────────────────────────────────────────────

    def test_routing_is_case_insensitive(self):
        assert self.router.route("WRITE AN ESSAY ON GROWTH") == "ship30"
        assert self.router.route("CREATE HTML") == "artifact"


class TestTopicExtraction:
    """AgentOrchestrator topic extraction for essays."""

    def test_extract_topic_strips_prefix(self):
        from app.agents.base import AgentOrchestrator

        # We only need the _extract_topic method, which doesn't touch the DB
        orchestrator = AgentOrchestrator.__new__(AgentOrchestrator)

        assert orchestrator._extract_topic(
            "Write an essay on user retention"
        ) == "user retention"
        assert orchestrator._extract_topic(
            "write a ship 30 for 30 essay on growth loops"
        ) == "growth loops"

    def test_extract_topic_no_prefix_returns_full(self):
        from app.agents.base import AgentOrchestrator

        orchestrator = AgentOrchestrator.__new__(AgentOrchestrator)
        assert orchestrator._extract_topic("growth strategies") == "growth strategies"
