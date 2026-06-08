import hmac
import hashlib
import os

from flask import Flask, request, jsonify
from dotenv import load_dotenv

from clients.github_client import GitHubClient
from agents.orchestrator import Orchestrator

load_dotenv()

app = Flask(__name__)
github_client = GitHubClient()
orchestrator = Orchestrator()


def verify_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    GitHub signs every webhook payload with your GITHUB_WEBHOOK_SECRET using HMAC-SHA256.
    We re-sign the raw body locally and compare. If they match, the payload is genuine.
    compare_digest prevents timing attacks — it always takes the same time regardless
    of where the mismatch is, so attackers can't guess the secret character by character.
    """
    if not signature_header:
        return False
    secret = os.environ["GITHUB_WEBHOOK_SECRET"].encode()
    expected = "sha256=" + hmac.new(secret, payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


@app.route("/webhook", methods=["POST"])
def handle_webhook():
    # 1. Verify the payload is genuinely from GitHub
    if not verify_signature(request.data, request.headers.get("X-Hub-Signature-256")):
        return jsonify({"error": "Invalid signature"}), 403

    payload = request.json
    event = request.headers.get("X-GitHub-Event")

    # 2. Only act on new PRs or new commits pushed to an existing PR
    #    "opened"      = brand new PR
    #    "synchronize" = new commit pushed to an existing open PR
    if event == "pull_request" and payload["action"] in ["opened", "synchronize"]:
        pr_number = payload["number"]
        repo_name = payload["repository"]["full_name"]  # e.g. "myorg/myrepo"

        print(f"[webhook] PR #{pr_number} on {repo_name} — starting review")

        # Pull the diff and hand off to the Orchestrator
        diff = github_client.get_pr_diff(repo_name, pr_number)
        orchestrator.run(diff, repo_name, pr_number)

    return jsonify({"status": "ok"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    # For local dev: run with `python main.py`
    # Use ngrok to expose localhost to GitHub: `ngrok http 5000`
    # Then set your GitHub webhook URL to: https://<ngrok-id>.ngrok.io/webhook
    app.run(debug=True, port=5000)
