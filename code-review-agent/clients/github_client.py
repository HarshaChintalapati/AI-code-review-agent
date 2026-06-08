import os
from github import Github
from dotenv import load_dotenv

load_dotenv()


class GitHubClient:
    def __init__(self):
        # PAT authenticates all API calls — read diffs, post comments
        self.gh = Github(os.environ["GITHUB_TOKEN"])

    def get_pr_diff(self, repo_name: str, pr_number: int) -> str:
        """
        Returns a unified diff string of all changed files in the PR.
        Format per file:
            ### path/to/file.py (modified)
            @@ -12,7 +12,10 @@
             context line
            -removed line
            +added line

        Lines starting with '-' were removed, '+' were added.
        Binary files (images, compiled artifacts) have no patch — we skip them.
        """
        repo = self.gh.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        files = pr.get_files()

        diff_parts = []
        for f in files:
            if f.patch:  # binary files return None for patch
                diff_parts.append(f"### {f.filename} ({f.status})\n{f.patch}")

        return "\n\n".join(diff_parts)

    def post_review_comment(self, repo_name: str, pr_number: int, body: str) -> None:
        """Posts a comment to the PR's main comment thread."""
        repo = self.gh.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        pr.create_issue_comment(body)

    def post_inline_comment(
        self,
        repo_name: str,
        pr_number: int,
        body: str,
        commit_sha: str,
        path: str,
        line: int,
    ) -> None:
        """
        Posts a review comment on a specific line of a specific file.
        Requires the commit SHA, file path, and line number from the diff.
        """
        repo = self.gh.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        commit = repo.get_commit(commit_sha)
        pr.create_review_comment(body=body, commit=commit, path=path, line=line)

    def get_pr_metadata(self, repo_name: str, pr_number: int) -> dict:
        """Returns basic PR info useful for context in the review prompt."""
        repo = self.gh.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        return {
            "title": pr.title,
            "description": pr.body or "",
            "author": pr.user.login,
            "base_branch": pr.base.ref,
            "head_branch": pr.head.ref,
            "changed_files": pr.changed_files,
            "additions": pr.additions,
            "deletions": pr.deletions,
            "head_sha": pr.head.sha,
        }
