# AI Code Review Agent

An autonomous code review agent that learns your team's coding standards over time.

Built with Claude (Anthropic), ChromaDB, PyGithub, and Streamlit.

## What it does

- Triggers automatically on every new Pull Request via GitHub webhooks
- Reviews the diff using Claude with team-specific context injected from memory
- Posts a structured review comment directly to the PR
- Learns from feedback, approved reviews get stored as reusable patterns in ChromaDB
- Gets smarter the more your team uses it

## Architecture

```
GitHub PR → Webhook → Orchestrator → Reviewer Agent → Claude API
                                  ↕
                            Memory Agent ↔ ChromaDB
                                  ↓
                          Streamlit Dashboard
```

## Setup

### 1. Clone and install

```bash
git clone https://github.com/yourusername/code-review-agent
cd code-review-agent
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in GITHUB_TOKEN, GITHUB_WEBHOOK_SECRET, ANTHROPIC_API_KEY
```

### 3. Run locally

```bash
# Terminal 1: start the webhook server
python main.py

# Terminal 2: expose to GitHub via ngrok
ngrok http 5000

# Terminal 3: start the Streamlit dashboard
streamlit run ui/app.py
```

### 4. Configure GitHub webhook

1. Go to your repo → Settings → Webhooks → Add webhook
2. Payload URL: `https://<your-ngrok-id>.ngrok.io/webhook`
3. Content type: `application/json`
4. Secret: the value of `GITHUB_WEBHOOK_SECRET` from your `.env`
5. Events: select "Pull requests"

## Running tests

```bash
pytest tests/
```

## Project structure

```
code-review-agent/
├── main.py                  # Flask webhook receiver
├── agents/
│   ├── orchestrator.py      # Pipeline coordinator
│   ├── reviewer.py          # Code analysis agent
│   └── memory.py            # ChromaDB RAG memory agent
├── clients/
│   ├── github_client.py     # GitHub API wrapper
│   └── claude_client.py     # Anthropic SDK wrapper
├── prompts/
│   ├── review_prompt.py     # Versioned review prompt template
│   └── memory_prompt.py     # Memory storage/retrieval prompts
├── ui/
│   └── app.py               # Streamlit dashboard + feedback loop
└── tests/
    ├── test_reviewer.py
    └── test_memory.py
```

## Key design decisions

**Why three agents?** Separation of concerns. Swap Claude for another model without touching GitHub code. Swap GitHub for GitLab without touching the review logic.

**Why versioned prompts?** LLM apps break when prompts change. Keeping prompts as versioned Python files means you can diff, roll back, and A/B test them like any other code.

**Why ChromaDB?** Runs locally with zero infra for prototyping. The MemoryAgent interface is stable — swapping to Pinecone or Weaviate in production requires changing one file.

**Why low temperature (0.1)?** Code review should be deterministic and consistent, not creative.
