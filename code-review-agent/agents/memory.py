import os
import uuid
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

from clients.claude_client import ClaudeClient
from prompts.memory_prompt import build_memory_query_prompt, build_memory_storage_prompt

load_dotenv()


class MemoryAgent:
    """
    Manages the team's institutional knowledge using ChromaDB as a vector store.

    How RAG works here:
    1. STORE: When a reviewer approves feedback, we embed it and store it in ChromaDB
       with metadata (repo, date, type of issue).
    2. RETRIEVE: Before each review, we embed the incoming diff, query ChromaDB for
       similar past feedback, and inject those patterns into the review prompt.

    This is what makes the agent learn. After 10-20 reviews, it knows things like:
    - "This team always uses snake_case"
    - "They never use print() in production code"
    - "They require type hints on all public functions"
    Those patterns are retrieved automatically and applied to every future review.
    """

    def __init__(self):
        self.claude = ClaudeClient()
        db_path = os.environ.get("CHROMA_DB_PATH", "./chroma_db")

        # PersistentClient saves to disk so memory survives restarts
        self.chroma = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(anonymized_telemetry=False),
        )

        # A "collection" is like a table — one collection per use case
        self.collection = self.chroma.get_or_create_collection(
            name="code_review_memory",
            # cosine similarity works better than L2 for semantic text similarity
            metadata={"hnsw:space": "cosine"},
        )

    def retrieve_relevant_patterns(self, diff: str, n_results: int = 5) -> str:
        """
        Given a new diff, find the most relevant past feedback patterns.
        Returns a formatted string ready to inject into the review prompt.

        Steps:
        1. Ask Claude to summarize the diff into a semantic query
        2. Embed that query into a vector
        3. Query ChromaDB for the top-n most similar stored patterns
        4. Format them for prompt injection
        """
        if self.collection.count() == 0:
            return ""  # No memory yet — first few reviews run without it

        # Step 1: summarize diff into a clean semantic query
        query_summary = self.claude.review(build_memory_query_prompt(diff))

        # Step 2: embed the query
        query_embedding = self.claude.embed_text(query_summary)

        # Step 3: vector similarity search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        if not results["documents"][0]:
            return ""

        # Step 4: format for prompt injection
        patterns = []
        for doc, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # distance is cosine distance (0 = identical, 2 = opposite)
            # Only use patterns with reasonable similarity (distance < 0.8)
            if distance < 0.8:
                issue_type = meta.get("issue_type", "general")
                patterns.append(f"- [{issue_type}] {doc}")

        return "\n".join(patterns)

    def store_feedback(
        self,
        feedback: str,
        diff_snippet: str,
        repo_name: str,
        issue_type: str = "general",
    ) -> None:
        """
        Stores approved feedback as a generalizable pattern.
        Called after a human marks the feedback as useful (thumbs up in Streamlit).

        We don't store the raw feedback — we ask Claude to distill it into
        a reusable rule first, so retrieval stays clean and general.
        """
        # Distill raw feedback into a reusable pattern
        pattern = self.claude.review(
            build_memory_storage_prompt(feedback, diff_snippet)
        )

        # Embed the pattern
        embedding = self.claude.embed_text(pattern)

        # Store with metadata for filtering/debugging
        self.collection.add(
            ids=[str(uuid.uuid4())],
            embeddings=[embedding],
            documents=[pattern],
            metadatas=[
                {
                    "repo": repo_name,
                    "issue_type": issue_type,
                    "source_feedback": feedback[:500],  # truncated for storage
                }
            ],
        )
        print(f"[memory] Stored pattern: {pattern[:100]}...")

    def get_pattern_count(self) -> int:
        return self.collection.count()
