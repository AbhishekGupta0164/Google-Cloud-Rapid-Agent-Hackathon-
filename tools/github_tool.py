"""
DevSentinel — GitHub ADK FunctionTools
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Wraps PyGitHub operations as Google ADK FunctionTools so they can be
called by any agent in the pipeline via tool_use.

HOW ADK FunctionTool WORKS:
  - Wrap any Python function with FunctionTool(fn)
  - ADK automatically generates the JSON schema from the docstring + type hints
  - The agent (e.g. ActionAgent) calls it like: github_tools.post_github_comment(...)
  - ADK handles parameter validation and error wrapping

TOOLS PROVIDED:
  1. post_github_comment    — Posts risk brief to a PR
  2. create_pull_request    — Opens a fix PR (migration script)
  3. get_pr_files           — Fetches diff for a PR
  4. get_pr_details         — Full PR metadata
  5. add_pr_label           — Tags PR with risk label
  6. request_pr_review      — Assigns senior reviewer for CRITICAL PRs
"""

import os
from typing import Optional

from github import Github, GithubException
from google.adk.tools import FunctionTool

# ── Singleton GitHub client ───────────────────────────────────────
_gh: Optional[Github] = None


def _get_gh() -> Github:
    """Lazy-init the GitHub client."""
    global _gh
    if _gh is None:
        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            raise ValueError("GITHUB_TOKEN environment variable is not set.")
        _gh = Github(token)
    return _gh


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TOOL FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def post_github_comment(repo: str, pr_number: int, comment: str) -> dict:
    """
    Post a Markdown comment to a GitHub pull request.

    Args:
        repo:       Full repository name, e.g. "myorg/myrepo"
        pr_number:  Pull request number, e.g. 142
        comment:    Markdown text of the comment to post

    Returns:
        dict with comment_id and html_url of the posted comment,
        or an error dict if posting fails.

    Example:
        post_github_comment("myorg/myrepo", 142, "## 🔴 DevSentinel Risk Alert...")
        → {"comment_id": 1234567, "url": "https://github.com/myorg/myrepo/pull/142#issuecomment-1234567"}
    """
    try:
        repo_obj = _get_gh().get_repo(repo)
        pr = repo_obj.get_pull(pr_number)
        comment_obj = pr.create_issue_comment(comment)
        return {
            "success": True,
            "comment_id": comment_obj.id,
            "url": comment_obj.html_url
        }
    except GithubException as e:
        return {"success": False, "error": str(e), "status": e.status}
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_pull_request(
    repo: str,
    title: str,
    body: str,
    head: str,
    base: str = "main"
) -> dict:
    """
    Create a new pull request in a GitHub repository.

    Args:
        repo:   Full repository name, e.g. "myorg/myrepo"
        title:  PR title, e.g. "fix: Add compound index for orders.customerId"
        body:   PR description in Markdown (include migration steps)
        head:   Source branch name, e.g. "fix/add-payment-index"
        base:   Target branch name, defaults to "main"

    Returns:
        dict with pr_number and html_url of the created PR,
        or an error dict if creation fails.

    Example:
        create_pull_request("myorg/myrepo",
            "fix: Add index for payment_status query",
            "Adds compound index as recommended by DevSentinel\\n\\n```js\\n"
            "db.orders.createIndex({customerId:1, status:1})\\n```",
            "fix/add-order-index")
        → {"pr_number": 143, "url": "https://github.com/myorg/myrepo/pull/143"}
    """
    try:
        repo_obj = _get_gh().get_repo(repo)
        pr = repo_obj.create_pull(
            title=title,
            body=body,
            head=head,
            base=base
        )
        return {
            "success": True,
            "pr_number": pr.number,
            "url": pr.html_url
        }
    except GithubException as e:
        return {"success": False, "error": str(e), "status": e.status}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_pr_files(repo: str, pr_number: int) -> dict:
    """
    Get the list of files changed in a pull request, including diffs.

    Args:
        repo:       Full repository name, e.g. "myorg/myrepo"
        pr_number:  Pull request number

    Returns:
        dict with a "files" list, each entry containing:
          filename, status, additions, deletions, patch (first 500 chars)

    Example:
        get_pr_files("myorg/myrepo", 142)
        → {"files": [{"filename": "services/orders.js", "status": "modified",
                       "additions": 12, "deletions": 8, "patch": "..."}]}
    """
    try:
        repo_obj = _get_gh().get_repo(repo)
        pr = repo_obj.get_pull(pr_number)
        files = [
            {
                "filename": f.filename,
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
                "patch": (f.patch or "")[:500]
            }
            for f in pr.get_files()
        ]
        return {"success": True, "files": files, "total_files": len(files)}
    except GithubException as e:
        return {"success": False, "error": str(e), "files": []}
    except Exception as e:
        return {"success": False, "error": str(e), "files": []}


def get_pr_details(repo: str, pr_number: int) -> dict:
    """
    Get full metadata for a pull request.

    Args:
        repo:       Full repository name, e.g. "myorg/myrepo"
        pr_number:  Pull request number

    Returns:
        dict with PR title, body, author, branch, state, labels, and URLs.
    """
    try:
        repo_obj = _get_gh().get_repo(repo)
        pr = repo_obj.get_pull(pr_number)
        return {
            "success": True,
            "number": pr.number,
            "title": pr.title,
            "body": (pr.body or "")[:1000],
            "state": pr.state,
            "author": pr.user.login,
            "head_branch": pr.head.ref,
            "base_branch": pr.base.ref,
            "head_sha": pr.head.sha,
            "html_url": pr.html_url,
            "labels": [l.name for l in pr.labels],
            "created_at": pr.created_at.isoformat() if pr.created_at else None,
            "mergeable": pr.mergeable,
        }
    except GithubException as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def add_pr_label(repo: str, pr_number: int, label: str) -> dict:
    """
    Add a label to a pull request (creates the label if it doesn't exist).

    Args:
        repo:       Full repository name, e.g. "myorg/myrepo"
        pr_number:  Pull request number
        label:      Label name, e.g. "🔴 CRITICAL", "devsentiinel-reviewed"

    Returns:
        dict with success status and current labels on the PR.
    """
    try:
        repo_obj = _get_gh().get_repo(repo)

        # Ensure label exists in repo
        try:
            repo_obj.get_label(label)
        except GithubException:
            color_map = {
                "CRITICAL": "ff4757",
                "HIGH": "ffa502",
                "LOW": "2ed573",
                "devsentiinel": "00d9ff",
            }
            color = next((v for k, v in color_map.items() if k.lower() in label.lower()), "7c3aed")
            repo_obj.create_label(name=label, color=color)

        pr = repo_obj.get_pull(pr_number)
        pr.add_to_labels(label)
        current_labels = [l.name for l in pr.labels]
        return {"success": True, "label_added": label, "all_labels": current_labels}
    except GithubException as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def request_pr_review(repo: str, pr_number: int, reviewer: str) -> dict:
    """
    Request a review from a specific GitHub user on a pull request.
    Used for CRITICAL risk PRs to ensure senior engineer sign-off.

    Args:
        repo:       Full repository name, e.g. "myorg/myrepo"
        pr_number:  Pull request number
        reviewer:   GitHub username of the reviewer, e.g. "senior-engineer"

    Returns:
        dict with success status and reviewer info.
    """
    try:
        repo_obj = _get_gh().get_repo(repo)
        pr = repo_obj.get_pull(pr_number)
        pr.create_review_request(reviewers=[reviewer])
        return {
            "success": True,
            "reviewer_requested": reviewer,
            "pr_number": pr_number
        }
    except GithubException as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REGISTER AS ADK FunctionTools
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
github_tools = [
    FunctionTool(post_github_comment),
    FunctionTool(create_pull_request),
    FunctionTool(get_pr_files),
    FunctionTool(get_pr_details),
    FunctionTool(add_pr_label),
    FunctionTool(request_pr_review),
]

# Individual exports for direct import
__all__ = [
    "github_tools",
    "post_github_comment",
    "create_pull_request",
    "get_pr_files",
    "get_pr_details",
    "add_pr_label",
    "request_pr_review",
]
