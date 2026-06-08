"""
Tests for the MemoryAgent.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestMemoryAgent:

    @patch("agents.memory.chromadb.PersistentClient")
    @patch("agents.memory.ClaudeClient")
    def test_returns_empty_string_when_no_memory(self, mock_claude_cls, mock_chroma_cls):
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_chroma = MagicMock()
        mock_chroma.get_or_create_collection.return_value = mock_collection
        mock_chroma_cls.return_value = mock_chroma

        from agents.memory import MemoryAgent
        agent = MemoryAgent()

        result = agent.retrieve_relevant_patterns("some diff")
        assert result == ""

    @patch("agents.memory.chromadb.PersistentClient")
    @patch("agents.memory.ClaudeClient")
    def test_store_feedback_calls_embed_and_add(self, mock_claude_cls, mock_chroma_cls):
        mock_claude = MagicMock()
        mock_claude.review.return_value = "Always validate user input."
        mock_claude.embed_text.return_value = [0.1, 0.2, 0.3]
        mock_claude_cls.return_value = mock_claude

        mock_collection = MagicMock()
        mock_chroma = MagicMock()
        mock_chroma.get_or_create_collection.return_value = mock_collection
        mock_chroma_cls.return_value = mock_chroma

        from agents.memory import MemoryAgent
        agent = MemoryAgent()
        agent.store_feedback("Never use print()", "diff snippet", "myorg/repo", "quality")

        mock_claude.embed_text.assert_called_once()
        mock_collection.add.assert_called_once()
