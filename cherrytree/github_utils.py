import os
import re
from collections import OrderedDict
from typing import List, Optional, Reversible, Sequence

import delegator
from git import Commit
from github import Github
from github.Label import Label
from github.Issue import Issue
from github.GithubException import UnknownObjectException
from github.Repository import Repository

from cherrytree.classes import CherryTreeExecutionException

# PRs are either of form "Merge pull request #nnn from..." or "...(#nnn)"
PR_REGEX = re.compile(r"(^Merge pull request #(\d+) from|\(#(\d+)\)$)")


def get_github_instance() -> Github:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise Exception("Env var 'GITHUB_TOKEN' is missing")
    return Github(token)


def get_repo(repo: str) -> Repository:
    g = get_github_instance()
    return g.get_repo(repo)


def get_issues_from_labels(repo: str, label: str, prs_only: bool = False) -> List[Issue]:
    label_objects: List[Label] = []
    gh_repo = get_repo(repo)
    try:
        label_objects.append(gh_repo.get_label(label))
    except UnknownObjectException:
        # unknown label
        return []
    issues = gh_repo.get_issues(labels=label_objects, state="all")
    if prs_only:
        return [o for o in issues if o.pull_request]
    return [o for o in issues]


def get_commits(repo: str, branch: str, since=None):
    """Get commit objects from a branch, over a limited period"""
    gh_repo = get_repo(repo)
    branch_object = gh_repo.get_branch(branch)
    sha = branch_object.commit.sha
    if since:
        commits = gh_repo.get_commits(sha=sha, since=since)
    else:
        commits = gh_repo.get_commits(sha=sha)
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


def truncate_str(value: str, width: int = 90) -> str:
    cont_str = "..."
    trunc_value = value[: width - len(cont_str)].strip()
    if len(trunc_value) < len(value.strip()):
        trunc_value = f"{trunc_value}{cont_str}"
    return f"{trunc_value:<{width}}"


def git_get_current_head() -> str:
    output = os_system("git status | head -1")
    match = re.match("(?:HEAD detached at|On branch) (.*)", output)
    if not match:
        return ""
    return match.group(1)


def os_system(cmd, raise_on_error=True) -> str:
    p = delegator.run(cmd)
    if raise_on_error and p.return_code != 0:
        raise CherryTreeExecutionException(p.err)
    return p.out


def check_if_branch_exists(branch: str) -> bool:
    current_head = git_get_current_head()
    try:
        os_system(f"git checkout {branch}")
    except CherryTreeExecutionException:
        return False
    os_system(f"git checkout {current_head}")
    return True


def deduplicate_prs(prs: List[Issue]) -> List[Issue]:
    pr_set = set()
    ret: List[Issue] = []
    for pr in prs:
        if pr.number not in pr_set:
            ret.append(pr)
            pr_set.add(pr.number)
    return ret
