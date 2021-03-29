from collections import OrderedDict

import click
import git
from cherrytree import github_utils as g
from dateutil import parser

SHORT_SHA_LEN = 12


class GitBranch:
    """Represents a git branch, fetches commits since branch-off point"""

    def __init__(self, branch, base_commit):
        self.branch = branch
        self.base_commit = base_commit
        self.fetch_commits()

    def fetch_commits(self):
        since = parser.parse(self.base_commit.last_modified)
        click.secho(
            f"Fetching all commits in {self.branch} " + f"since {since}",
            fg="cyan",
        )
        commits = OrderedDict()
        for commit in g.get_commits(self.branch, since=since):
            commits[commit.commit.sha] = commit
        click.secho(f"{len(commits)} commits found in {self.branch}", fg="cyan")
        self.commits = commits


class CherryTreeBranch:
    """Represents a release branch"""

    def __init__(self, branch, base_ref=None, search_branches=None, labels=None):
        self.search_branches = search_branches or ["master"]

        self.branch = branch

        github_repo = g.get_repo()
        self.github_repo = github_repo
        self.git_repo = git.repo.Repo()

        self.base_ref = base_ref or self.get_base()
        click.secho(f"Base ref is {self.base_ref}", fg="cyan")

        """
        click.secho(f"Fetching tags", fg="cyan")
        self.tags_map = {t.commit.sha: t.name for t in github_repo.get_tags()}
        click.secho(f"{len(self.tags_map)} tags retrieved", fg="cyan")
        """

        labels = labels or [f"v{branch}"]
        prs = []
        for label in labels:
            click.secho(f'Fetching & listing PRs for label "{label}"', fg="cyan")
            prs += g.get_issues_from_labels([label], prs_only=True)
            click.secho(f"{len(prs)} PRs found", fg="cyan")

        self.branches = {}
        commits = OrderedDict()
        for branch in self.search_branches:
            for commit in self.git_repo.iter_commits(branch):
                commits[commit.hexsha] = commit

        click.secho(f"Matching PRs to commits", fg="cyan")
        pr_number_commit_map = g.get_commit_pr_map(commits.values(), prs)
        self.missing_pull_requests = []
        for pr in prs:
            commit = pr_number_commit_map.get(pr.number)
            self.echo_match(commit, pr)

        click.secho(f"Listing ordered commits", fg="cyan")
        pr_map = {pr.number: pr for pr in prs}
        self.cherries = []
        for pr_number, commit in pr_number_commit_map.items():
            pr = pr_map.get(pr_number)
            if pr:
                self.cherries.append(self.cherry(pr, commit))

    def get_base(self):
        base_commits = self.git_repo.merge_base("master", self.branch)
        if len(base_commits) < 1:
            raise Exception("No common ancestor found!")
        elif len(base_commits) > 1:
            raise Exception("Multiple common ancestors found!?")
        return base_commits[0].hexsha

    def echo_match(self, commit, pr):
        if commit:
            str_commit = commit.hexsha[:SHORT_SHA_LEN]
        else:
            str_commit = " " * SHORT_SHA_LEN
        pr_info = f"#{pr.number} | {pr.state} | {str_commit} | {pr.title}"
        if commit:
            color = "green"
            icon = "✅"
        else:
            color = "red"
            icon = "❌"
            self.missing_pull_requests.append(pr)
        click.secho(f"{icon}: {pr_info}", fg=color)

    def cherry(self, pr, commit):
        return {
            "SHA": commit.hexsha[:SHORT_SHA_LEN],
            "pr_number": pr.number,
            "pr_title": pr.title,
            "fixed_sha": None,
        }

    def data(self):
        d = {
            "branch": self.branch,
            "base_ref": self.base_ref,
            "cherries": self.cherries,
        }
        if self.missing_pull_requests:
            d["missing_pull_requests"] = [
                {
                    "pr_number": pr.number,
                    "pr_title": pr.title,
                }
                for pr in self.missing_pull_requests
            ]
        return d
