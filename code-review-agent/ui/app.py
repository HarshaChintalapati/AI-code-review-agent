"""
Streamlit dashboard — run with: streamlit run ui/app.py

Shows:
- All reviews the agent has posted
- Which memory patterns were used for each review
- Thumbs up/down feedback loop that stores approved feedback back into ChromaDB
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from dotenv import load_dotenv
from agents.memory import MemoryAgent

load_dotenv()

st.set_page_config(
    page_title="Code Review Agent",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 AI Code Review Agent")
st.caption("Powered by Claude + team memory")

# ── Sidebar: memory stats ──────────────────────────────────────────────────
memory = MemoryAgent()

with st.sidebar:
    st.header("Team memory")
    pattern_count = memory.get_pattern_count()
    st.metric("Patterns learned", pattern_count)

    if pattern_count == 0:
        st.info(
            "No patterns yet. After a few reviews, approve useful feedback "
            "with 👍 and the agent will learn your team's standards."
        )
    else:
        st.success(f"The agent has learned {pattern_count} patterns from your team.")

    st.divider()
    st.caption("Each 👍 on a review stores that pattern in ChromaDB. "
               "The more you use it, the smarter it gets.")

# ── Main: review history ───────────────────────────────────────────────────
st.header("Recent reviews")

# In a real deployment, review_history would come from a database.
# For demo/local use, we show a manual review input form.
if "reviews" not in st.session_state:
    st.session_state.reviews = []

# ── Manual review trigger (for demo without live GitHub webhooks) ──────────
with st.expander("➕ Manually trigger a review (demo mode)", expanded=len(st.session_state.reviews) == 0):
    st.caption(
        "In production, reviews are triggered automatically by GitHub webhooks. "
        "Use this form to test the agent locally without setting up ngrok."
    )
    demo_repo = st.text_input("Repo name", value="myorg/myrepo")
    demo_pr = st.number_input("PR number", value=1, min_value=1)
    demo_diff = st.text_area(
        "Paste a diff here",
        height=200,
        placeholder="### auth/login.py (modified)\n@@ -12,7 +12,10 @@\n-    result = db.query(f\"SELECT * FROM users WHERE name={username}\")\n+    result = db.query(\"SELECT * FROM users WHERE name=?\", (username,))",
    )

    if st.button("Run review", type="primary"):
        if demo_diff.strip():
            with st.spinner("Reviewing..."):
                from agents.orchestrator import Orchestrator
                orch = Orchestrator()
                result = orch.run(
                    diff=demo_diff,
                    repo_name=demo_repo,
                    pr_number=int(demo_pr),
                )
                if "error" not in result:
                    st.session_state.reviews.insert(0, result)
                    st.success("Review complete!")
                else:
                    st.error(f"Error: {result['error']}")
        else:
            st.warning("Paste a diff first.")

# ── Display reviews ────────────────────────────────────────────────────────
if not st.session_state.reviews:
    st.info("No reviews yet. Trigger one above or open a PR on a connected repo.")
else:
    for i, review in enumerate(st.session_state.reviews):
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.subheader(f"PR #{review['pr_number']} — {review.get('pr_title', '')}")
                st.caption(f"Repo: {review['repo_name']} · Author: {review.get('author', 'unknown')}")
            with col2:
                st.metric("Memory patterns used", review.get("memory_patterns_used", 0))
            with col3:
                st.metric("Total in memory", review.get("total_patterns_in_memory", 0))

            # The review comment
            st.markdown(review["comment"])

            # Memory context used (collapsible)
            if review.get("memory_context"):
                with st.expander("🧠 Memory patterns injected into this review"):
                    st.code(review["memory_context"])

            # Feedback buttons — this is the feedback loop
            st.write("**Was this review helpful?**")
            col_up, col_down, col_spacer = st.columns([1, 1, 6])

            with col_up:
                if st.button("👍 Yes", key=f"up_{i}"):
                    # Store the approved feedback as a reusable pattern
                    memory.store_feedback(
                        feedback=review["comment"],
                        diff_snippet=review["raw_diff"][:1000],
                        repo_name=review["repo_name"],
                        issue_type="approved_review",
                    )
                    st.session_state.reviews[i]["feedback_given"] = "positive"
                    st.success("Stored! The agent will apply this pattern to future reviews.")
                    st.rerun()

            with col_down:
                if st.button("👎 No", key=f"down_{i}"):
                    # Negative feedback is discarded — we don't want to
                    # poison the memory with bad patterns
                    st.session_state.reviews[i]["feedback_given"] = "negative"
                    st.info("Noted. This feedback won't be stored.")
                    st.rerun()

            if review.get("feedback_given") == "positive":
                st.success("✅ Feedback stored in team memory")
            elif review.get("feedback_given") == "negative":
                st.warning("❌ Feedback discarded")

            st.divider()
