import os
import re
from collections import OrderedDict
from typing import Iterable, List, Optional, Reversible

from git import Commit
from github import Github
from github.Label import Label
from github.Issue import Issue
from github.GithubException import UnknownObjectException
from github.Repository import Repository

REPO = "apache/superset"
PR_REGEX = re.compile(r"(Merge pull request #(\d+) from|\(#(\d*)\)$)")


def get_github_instance() -> Github:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise Exception("Env var 'GITHUB_TOKEN' is missing")
    return Github(token)


def get_repo() -> Repository:
    g = get_github_instance()
    return g.get_repo(REPO)


def get_issues_from_labels(
        labels: Iterable[str],
        prs_only: bool = False
) -> Iterable[Issue]:
    repo = get_repo()
    label_objects: List[Label] = []
    for label in labels:
        print("---=-=-=-", label)
        try:
            label_objects.append(repo.get_label(label))
        except UnknownObjectException:
            # unknown label
            return []
    issues = repo.get_issues(labels=label_objects, state="all")
    if prs_only:
        issues = [o for o in issues if o.pull_request]
    return issues


def get_commits(branch="master", since=None):
    """Get commit objects from a branch, over a limited period"""
    repo = get_repo()
    branch_object = repo.get_branch(branch)
    sha = branch_object.commit.sha
    if since:
        commits = repo.get_commits(sha=sha, since=since)
    else:
        commits = repo.get_commits(sha=sha)
    return commits


def commit_pr_number(commit: Commit) -> Optional[int]:
    """Given a commit object, returns the PR number"""
    res = PR_REGEX.search(commit.summary)
    if res:
        groups = res.groups()
        return int(groups[1] or groups[2])
    return None


def get_commit_pr_map(commits: Reversible[Commit]):
    """Given a list of commits and prs, returns a map of pr_number to commit"""
    d = OrderedDict()
    for commit in reversed(commits):
        pr_number = commit_pr_number(commit)
        if pr_number:
            d[pr_number] = commit
    return d
