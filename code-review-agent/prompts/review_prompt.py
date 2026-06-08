def build_review_prompt(diff: str, pr_metadata: dict, memory_context: str = "") -> str:
    """
    Builds the full prompt sent to Claude for code review.

    Why a versioned function instead of a hardcoded string?
    Because prompts change constantly during development. When something breaks
    or quality drops, you need to know exactly what changed. Keeping prompts as
    versioned Python functions means you can diff them in git, roll back, and
    A/B test — the same way you'd treat any other code change.

    The memory_context parameter is what makes this agent learn over time.
    It injects past feedback patterns from the team's ChromaDB memory so Claude
    knows things like "this team uses snake_case" or "never use print() in prod".
    """

    memory_section = ""
    if memory_context:
        memory_section = f"""
## Team coding patterns (learned from past reviews)
The following patterns have been flagged or praised in this team's previous reviews.
Apply these as additional standards on top of general best practices:

{memory_context}

---
"""

    return f"""You are an expert code reviewer. Review the following Pull Request diff and provide
specific, actionable feedback. Focus on:

1. **Bugs and correctness** — logic errors, edge cases, off-by-ones
2. **Security** — SQL injection, hardcoded secrets, unvalidated input
3. **Code quality** — naming, readability, unnecessary complexity
4. **Error handling** — missing try/except, unhandled edge cases
5. **Performance** — obvious inefficiencies, N+1 queries, missing indexes
{memory_section}
## PR context
- Title: {pr_metadata.get('title', 'N/A')}
- Author: {pr_metadata.get('author', 'N/A')}
- Description: {pr_metadata.get('description', 'No description provided')}
- Files changed: {pr_metadata.get('changed_files', 'N/A')}
- Additions: {pr_metadata.get('additions', 0)} | Deletions: {pr_metadata.get('deletions', 0)}

## Diff
```diff
{diff}
```

## Response format
Return your review as a structured markdown comment suitable for posting directly to GitHub.
Use this format:

## 🤖 AI Code Review

### Summary
[2-3 sentence overall assessment]

### Issues found
For each issue:
**[filename]:[line range]** — [issue type: Bug / Security / Quality / Performance]
> [specific description and why it matters]
> **Suggestion:** [concrete fix]

### Looks good ✅
[things done well — keep this brief, 1-3 bullet points max]

---
*Powered by Claude + team memory ({memory_count} patterns loaded)*
"""


# Keep a version string so you can track which prompt version produced which review
PROMPT_VERSION = "1.0.0"
memory_count = 0  # Updated by the Memory agent before the prompt is built
