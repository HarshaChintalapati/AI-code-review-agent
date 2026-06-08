from clients.claude_client import ClaudeClient
from prompts.review_prompt import build_review_prompt
from agents.memory import MemoryAgent


class ReviewerAgent:
    """
    Does the actual code analysis. Takes a diff + PR metadata,
    retrieves relevant memory patterns, builds the prompt, calls Claude,
    returns structured feedback.

    Single responsibility: produce a review comment string.
    It doesn't know about GitHub, ChromaDB internals, or Streamlit —
    those are the Orchestrator's concern.
    """

    def __init__(self):
        self.claude = ClaudeClient()
        self.memory = MemoryAgent()

    def review(self, diff: str, pr_metadata: dict) -> dict:
        """
        Returns a dict with:
          - comment: the full review string to post to GitHub
          - memory_patterns_used: how many patterns were injected (for UI display)
          - raw_diff: passed through for potential storage later
        """
        # 1. Retrieve relevant patterns from team memory
        memory_context = self.memory.retrieve_relevant_patterns(diff)
        pattern_count = self.memory.get_pattern_count()

        # 2. Build the prompt with memory context injected
        prompt = build_review_prompt(
            diff=diff,
            pr_metadata=pr_metadata,
            memory_context=memory_context,
        )

        # 3. Call Claude
        review_comment = self.claude.review(prompt)

        return {
            "comment": review_comment,
            "memory_patterns_used": len(memory_context.splitlines()) if memory_context else 0,
            "total_patterns_in_memory": pattern_count,
            "raw_diff": diff,
            "memory_context": memory_context,
        }
