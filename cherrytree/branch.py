from collections import OrderedDict

import click
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
            f"Fetching all commits in {self.branch} "
            f"since {since}",
            fg="bright_cyan",
        )
        commits = OrderedDict()
        for commit in g.get_commits(self.branch, since=since):
            commits[commit.commit.sha] = commit
        click.secho(f"{len(commits)} commits found in {self.branch}", fg="cyan")
        self.commits = commits


class CherryTreeBranch:
    """Represents a release branch"""
    def __init__(self, branch, base_ref, search_branches=None):
        self.search_branches = search_branches or ['master']

        self.branch = branch
        self.base_ref = base_ref

        repo = g.get_repo()
        click.secho(f'Fetching base commit info for {base_ref}', fg="bright_cyan")
        self.base_commit = repo.get_commit(base_ref)
        since = parser.parse(self.base_commit.last_modified)
        short_sha = self.base_commit.commit.sha[:SHORT_SHA_LEN]
        click.secho(f'Base SHA {short_sha} last_modified {since}', fg="cyan")

        click.secho(f"Fetching tags", fg="bright_cyan")
        self.tags_map = {t.commit.sha: t.name for t in repo.get_tags()}
        click.secho(f"{len(self.tags_map)} tags retrieved", fg="cyan")

        label = f"v{branch}"
        click.secho(f'Fetching & listing PRs for label "{label}"', fg="bright_cyan")
        prs = g.get_issues_from_labels([label], prs_only=True)
        click.secho(f"{len(prs)} PRs found", fg="cyan")

        self.branches = {}
        commits = OrderedDict()
        for branch in self.search_branches:
            self.branches[branch] = GitBranch(branch, self.base_commit)
            commits.update(self.branches[branch].commits)

        click.secho(f"Matching PRs to commits", fg="bright_cyan")
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

    def echo_match(self, commit, pr):
        if commit:
            str_commit = commit.commit.sha[:SHORT_SHA_LEN]
        else:
            str_commit = ' ' * SHORT_SHA_LEN
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
            "SHA": commit.commit.sha[:SHORT_SHA_LEN],
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
