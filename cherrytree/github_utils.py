import os
from github import Github
from github.Label import Label

REPO = 'apache/incubator-superset'


def get_github_instance():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise Exception("Env var 'GITHUB_TOKEN' is missing")
    return Github(token)


def get_repo():
    g = get_github_instance()
    return g.get_repo(REPO)


def get_issues_from_labels(labels, prs_only=False):
    repo = get_repo()
    label_objects = []
    for label in labels:
        label_objects.append(repo.get_label(label))
    issues = repo.get_issues(labels=label_objects, state='all')
    if prs_only:
        issues = [o for o in issues if o.pull_request]
    return issues


def get_prs_from_labels(labels):
    issues = get_issues_from_labels(labels, prs_only=True)
    prs = [o.as_pull_request() for o in issues]
    return prs


def get_commits(branch='master', since=None):
    repo = get_repo()
    branch_object = repo.get_branch(branch)
    sha = branch_object.commit.sha
    if since:
        commits = repo.get_commits(sha=sha, since=since)
    else:
        commits = repo.get_commits(sha=sha)
    return commits
