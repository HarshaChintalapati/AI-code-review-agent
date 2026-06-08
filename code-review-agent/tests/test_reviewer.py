"""
Tests for the ReviewerAgent.
Run with: pytest tests/
"""

import pytest
from unittest.mock import MagicMock, patch


class TestReviewerAgent:
    """
    We mock ClaudeClient and MemoryAgent so tests don't hit real APIs.
    This makes tests fast, free, and deterministic.
    """

    @patch("agents.reviewer.MemoryAgent")
    @patch("agents.reviewer.ClaudeClient")
    def test_review_returns_expected_keys(self, mock_claude_cls, mock_memory_cls):
        mock_claude = MagicMock()
        mock_claude.review.return_value = "## 🤖 AI Code Review\n\nLooks good!"
        mock_claude_cls.return_value = mock_claude

        mock_memory = MagicMock()
        mock_memory.retrieve_relevant_patterns.return_value = ""
        mock_memory.get_pattern_count.return_value = 0
        mock_memory_cls.return_value = mock_memory

        from agents.reviewer import ReviewerAgent
        reviewer = ReviewerAgent()

        diff = "### main.py (modified)\n@@ -1,3 +1,4 @@\n+print('hello')"
        metadata = {"title": "Test PR", "author": "dev", "description": "",
                    "changed_files": 1, "additions": 1, "deletions": 0}

        result = reviewer.review(diff, metadata)

        assert "comment" in result
        assert "memory_patterns_used" in result
        assert "total_patterns_in_memory" in result
        assert "raw_diff" in result
        assert result["comment"] == "## 🤖 AI Code Review\n\nLooks good!"

    @patch("agents.reviewer.MemoryAgent")
    @patch("agents.reviewer.ClaudeClient")
    def test_memory_patterns_injected_when_available(self, mock_claude_cls, mock_memory_cls):
        mock_claude = MagicMock()
        mock_claude.review.return_value = "Review with memory"
        mock_claude_cls.return_value = mock_claude

        mock_memory = MagicMock()
        mock_memory.retrieve_relevant_patterns.return_value = (
            "- [quality] Always use snake_case\n- [security] Never use print() in prod"
        )
        mock_memory.get_pattern_count.return_value = 10
        mock_memory_cls.return_value = mock_memory

        from agents.reviewer import ReviewerAgent
        reviewer = ReviewerAgent()

        result = reviewer.review("some diff", {"title": "PR", "author": "dev",
                                               "description": "", "changed_files": 1,
                                               "additions": 1, "deletions": 0})

        # Verify memory patterns were retrieved
        mock_memory.retrieve_relevant_patterns.assert_called_once()
        assert result["total_patterns_in_memory"] == 10
