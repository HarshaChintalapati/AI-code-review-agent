def build_memory_storage_prompt(feedback: str, diff_snippet: str) -> str:
    """
    Used when storing new feedback into ChromaDB.
    We ask Claude to distill raw feedback into a reusable pattern — something
    that can be retrieved and applied to future, different diffs.
    """
    return f"""Given this code review feedback and the diff it applies to,
extract a generalizable coding pattern or standard that should apply to future reviews.

Keep it concise (1-2 sentences max). Focus on the rule, not the specific code instance.

Feedback: {feedback}

Diff snippet: {diff_snippet}

Respond with just the pattern, nothing else. Example format:
"Always validate user input before passing it to database queries to prevent SQL injection."
"""


def build_memory_query_prompt(diff: str) -> str:
    """
    Converts a raw diff into a semantic query for ChromaDB retrieval.
    We don't query with the raw diff (too noisy) — instead we extract
    the key concepts so the vector similarity search is more accurate.
    """
    return f"""Summarize the key programming concepts, patterns, and potential issues
in the following code diff in 2-3 sentences. This summary will be used to search
a database of past code review feedback.

Diff:
{diff[:2000]}

Respond with just the summary, no preamble.
"""


PROMPT_VERSION = "1.0.0"
