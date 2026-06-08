from clients.github_client import GitHubClient
from agents.reviewer import ReviewerAgent


class Orchestrator:
    """
    The traffic controller. Coordinates the full pipeline:
    1. Pull PR metadata from GitHub
    2. Hand diff + metadata to the Reviewer agent
    3. Post the result back to GitHub
    4. Store results for the Streamlit UI

    It doesn't do any analysis itself — it delegates.
    Why? Separation of concerns. If you want to swap Claude for GPT-4,
    you change ReviewerAgent. If you want to swap GitHub for GitLab,
    you change GitHubClient. The Orchestrator never needs to change.

    This also makes each component independently testable.
    """

    def __init__(self):
        self.github = GitHubClient()
        self.reviewer = ReviewerAgent()
        # In-memory store for the Streamlit UI to read
        # In production you'd use a database (SQLite/Postgres)
        self.review_history: list[dict] = []

    def run(self, diff: str, repo_name: str, pr_number: int) -> dict:
        """
        Full pipeline. Returns the review result dict.
        """
        print(f"[orchestrator] Starting review for PR #{pr_number} on {repo_name}")

        # Step 1: Get PR metadata for richer context in the prompt
        try:
            pr_metadata = self.github.get_pr_metadata(repo_name, pr_number)
        except Exception as e:
            print(f"[orchestrator] Warning: couldn't fetch PR metadata: {e}")
            pr_metadata = {"title": f"PR #{pr_number}", "author": "unknown",
                           "description": "", "changed_files": 0,
                           "additions": 0, "deletions": 0, "head_sha": ""}

        # Step 2: Run the review
        try:
            result = self.reviewer.review(diff, pr_metadata)
        except Exception as e:
            # Don't block the developer — post a fallback comment
            print(f"[orchestrator] Review failed: {e}")
            self.github.post_review_comment(
                repo_name, pr_number,
                "⚠️ AI review encountered an error and could not complete. "
                "Please review manually."
            )
            return {"error": str(e)}

        # Step 3: Post the review to GitHub
        self.github.post_review_comment(repo_name, pr_number, result["comment"])
        print(f"[orchestrator] Review posted to PR #{pr_number}")

        # Step 4: Store for Streamlit UI and potential feedback loop
        review_record = {
            "pr_number": pr_number,
            "repo_name": repo_name,
            "pr_title": pr_metadata.get("title", ""),
            "author": pr_metadata.get("author", ""),
            "comment": result["comment"],
            "memory_patterns_used": result["memory_patterns_used"],
            "total_patterns_in_memory": result["total_patterns_in_memory"],
            "raw_diff": diff,
            "memory_context": result["memory_context"],
            "feedback_given": None,  # Set by Streamlit when user thumbs up/down
        }
        self.review_history.append(review_record)

        return review_record
