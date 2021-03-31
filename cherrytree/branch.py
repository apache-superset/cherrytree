from collections import OrderedDict
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

import click
from git import Commit
from git.repo import Repo
from cherrytree import github_utils as g
from github.Issue import Issue

from cherrytree.github_utils import commit_pr_number, tbl_cell

SHORT_SHA_LEN = 12


@dataclass
class Cherry:
    commit: Optional[Commit]
    pr: Issue
    is_applied: bool


@dataclass
class Summary:
    pr_number: str
    color: str
    opened_by: str
    merged_by: str
    icon: str
    state: str
    sha: str
    title: str


class CherryTreeBranch:
    """Represents a release branch"""

    branch: str
    base_ref: str
    search_branches: Sequence[str]
    labels: Sequence[str]
    branch_commits: Dict[str, Dict[int, Commit]]
    missing_pull_requests: List[Issue]

    def __init__(
        self,
        branch: str,
        base_ref: Optional[str] = None,
        search_branches: Optional[Sequence[str]] = None,
        labels: Optional[Sequence[str]] = None,
    ):
        self.missing_pull_requests = []
        self.search_branches = search_branches or ["master", branch]
        self.branch = branch

        github_repo = g.get_repo()
        self.github_repo = github_repo
        self.git_repo = Repo()

        self.base_ref = base_ref or self.get_base()
        click.secho(f"Base ref is {self.base_ref}", fg="cyan")

        """
        click.secho(f"Fetching tags", fg="cyan")
        self.tags_map = {t.commit.sha: t.name for t in github_repo.get_tags()}
        click.secho(f"{len(self.tags_map)} tags retrieved", fg="cyan")
        """

        labels = labels or [f"v{branch}"]
        prs: List[Issue] = []
        for label in labels:
            click.secho(f'Fetching & listing PRs for label "{label}"', fg="cyan")
            prs += g.get_issues_from_labels([label], prs_only=True)
        now = datetime.now()
        prs.sort(
            key=lambda x: x.closed_at if x.closed_at is not None else now, reverse=True
        )
        click.secho(f"{len(prs)} PRs found", fg="cyan")

        self.branches = {}
        self.branch_commits = {}
        skipped_commits = 0
        for branch in self.search_branches:
            commits = OrderedDict()
            self.branch_commits[branch] = commits
            for commit in self.git_repo.iter_commits(branch):
                pr_number = commit_pr_number(commit)
                if pr_number is None:
                    skipped_commits += 1
                else:
                    commits[pr_number] = commit
        if skipped_commits:
            click.secho(
                f"{skipped_commits} commits skipped due to missing PRs", fg="yellow"
            )

        click.secho(f"Matching PRs to commits", fg="cyan")
        master_commits = self.branch_commits["master"]
        branch_commits = self.branch_commits[branch]
        pr_number_commit_map = g.get_commit_pr_map(master_commits.values())

        click.secho(f"Listing ordered commits", fg="cyan")
        self.cherries = []
        for pr in prs:
            master_commit = master_commits.get(pr.number)
            applied_commit = branch_commits.get(pr.number)
            cherry = Cherry(
                commit=master_commit,
                pr=pr,
                is_applied=True if applied_commit is not None else False,
            )
            self.cherries.append(cherry)

        self.echo_cherries()

    def get_base(self) -> str:
        base_commits = self.git_repo.merge_base("master", self.branch)
        if len(base_commits) < 1:
            raise Exception("No common ancestor found!")
        elif len(base_commits) > 1:
            raise Exception("Multiple common ancestors found!?")
        return base_commits[0].hexsha

    def echo_cherries(self) -> None:
        summaries: List[Summary] = []
        for cherry in self.cherries:
            commit = cherry.commit
            pr = cherry.pr
            opened_by, merged_by = pr.user, pr.closed_by
            if commit:
                str_commit = commit.hexsha[:SHORT_SHA_LEN]
            else:
                str_commit = " " * SHORT_SHA_LEN
            if cherry.is_applied:
                color = "blue"
                icon = "☑️"
                state = "applied"
            elif cherry.commit:
                color = "green"
                icon = "✅"
                state = pr.state
            else:
                color = "red"
                icon = "❌"
                state = pr.state
            summaries.append(
                Summary(
                    pr_number=f"#{pr.number}",
                    color=color,
                    opened_by=opened_by.login if opened_by else "",
                    merged_by=merged_by.login if merged_by else "",
                    icon=icon,
                    state=state,
                    sha=str_commit,
                    title=pr.title,
                )
            )
        (
            pr_width,
            opened_by_width,
            merged_by_width,
            state_width,
            sha_width,
            title_width,
        ) = (
            len("number"),
            len("opened by"),
            len("merged by"),
            len("state"),
            len("sha"),
            len("title"),
        )
        for summary in summaries:
            pr_width = max(pr_width, len(summary.pr_number))
            opened_by_width = max(opened_by_width, len(summary.opened_by))
            merged_by_width = max(merged_by_width, len(summary.merged_by))
            # unicode icon widths are misrepresented by len()
            icon_width = 2
            state_width = max(state_width, len(summary.state))
            sha_width = max(sha_width, len(summary.sha))
            title_width = max(title_width, len(summary.title))

        click.secho(
            f"🔘 | "
            f"{tbl_cell('number', pr_width)} | "
            f"{tbl_cell('opened by', opened_by_width)} | "
            f"{tbl_cell('merged_by', merged_by_width)} | "
            f"{tbl_cell('state', state_width)} | "
            f"{tbl_cell('sha', sha_width)} | "
            f"{tbl_cell('title', title_width)}"
        )
        for summary in summaries:
            pr_info = (
                f"{summary.icon} | "
                f"{tbl_cell(summary.pr_number, pr_width)} | "
                f"{tbl_cell(summary.opened_by, opened_by_width)} | "
                f"{tbl_cell(summary.merged_by, merged_by_width)} | "
                f"{tbl_cell(summary.state, state_width)} | "
                f"{tbl_cell(summary.sha, sha_width)} | "
                f"{tbl_cell(summary.title, title_width)}"
            )
            click.secho(f"{pr_info}", fg=summary.color)

    def data(self):
        commits = [cherry for cherry in self.cherries if cherry.commit is not None]
        missing_prs = [cherry for cherry in self.cherries if cherry.commit is None]
        d = {
            "branch": self.branch,
            "base_ref": self.base_ref,
            "cherries": [
                {
                    "sha": cherry.commit,
                    "pr_number": cherry.pr.number,
                    "pr_title": cherry.pr.title,
                }
                for cherry in commits
            ],
        }
        if self.missing_pull_requests:
            d["missing_pull_requests"] = [
                {
                    "pr_number": cherry.pr.number,
                    "pr_title": cherry.pr.title,
                }
                for cherry in missing_prs
            ]
        return d
