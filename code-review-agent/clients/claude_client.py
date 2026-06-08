import os
import anthropic
from dotenv import load_dotenv

load_dotenv()


class ClaudeClient:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        # Sonnet gives the best balance of quality and speed for code review
        self.model = "claude-sonnet-4-20250514"

    def review(self, prompt: str) -> str:
        """
        Sends a prompt to Claude and returns the text response.
        Temperature is intentionally low (0.1) — we want consistent, deterministic
        feedback, not creative variation. Code review should be reproducible.
        """
        message = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    def embed_text(self, text: str) -> list[float]:
        """
        Generates a vector embedding for a piece of text.
        Used by the Memory agent to store and retrieve feedback from ChromaDB.
        We use sentence-transformers locally (free, no API cost) rather than
        calling a paid embeddings API — fine for this use case.
        """
        from sentence_transformers import SentenceTransformer

        # Loaded lazily so the model only downloads when first needed
        if not hasattr(self, "_embed_model"):
            self._embed_model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._embed_model.encode(text).tolist()
