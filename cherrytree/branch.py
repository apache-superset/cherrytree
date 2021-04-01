from collections import OrderedDict
from datetime import datetime
from typing import Dict, List, Optional, Sequence

import click
from git import Commit
from git.repo import Repo
from github.Issue import Issue

from cherrytree.github_utils import (
    commit_pr_number,
    deduplicate_prs,
    get_issues_from_labels,
    git_get_current_head,
    os_system,
    truncate_str,
)
from cherrytree.classes import (
    Cherry,
    CherryTreeExecutionException,
    CommitSummary,
)

SHORT_SHA_LEN = 12
TMP_BRANCH = "__tmp_branch"


class CherryTreeBranch:
    """Represents a release branch"""

    repo: str
    release_branch: str
    main_branch: str
    labels: List[str]
    branch_commits: Dict[str, Dict[int, Commit]]
    missing_pull_requests: List[Issue]

    def __init__(
        self,
        repo: str,
        release_branch: str,
        main_branch: str,
        labels: Optional[Sequence[str]],
    ):
        self.repo = repo
        self.labels = list(labels)
        self.missing_pull_requests = []
        self.release_branch = release_branch
        self.main_branch = main_branch
        self.git_repo = Repo()
        self.base_ref = self.get_base()
        click.secho(f"Base ref is {self.base_ref}", fg="cyan")

        self.branches = {}
        self.branch_commits = {}
        skipped_commits = 0
        for branch in (self.main_branch, self.release_branch):
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

        prs: List[Issue] = []
        for label in self.labels:
            prs += get_issues_from_labels(self.repo, label, prs_only=True)
            click.secho(f'Fetching labeled PRs: "{label}"', fg="cyan")
        prs = deduplicate_prs(prs)
        now = datetime.now()
        prs.sort(
            key=lambda x: x.closed_at if x.closed_at is not None else now,
        )
        click.secho(f"{len(prs)} PRs found", fg="cyan")
        self.cherries = []
        for pr in prs:
            main_commit = self.branch_commits[self.main_branch].get(pr.number)
            applied_commit = self.branch_commits[self.release_branch].get(pr.number)
            if main_commit is None and pr.closed_at is not None:
                # skip closed PRs that haven't been merged
                continue
            cherry = Cherry(
                commit=main_commit,
                pr=pr,
                is_applied=True if applied_commit is not None else False,
            )
            self.cherries.append(cherry)

    def get_base(self) -> str:
        base_commits = self.git_repo.merge_base(self.main_branch, self.release_branch)
        if len(base_commits) < 1:
            raise Exception("No common ancestor found!")
        elif len(base_commits) > 1:
            raise Exception("Multiple common ancestors found!?")
        return base_commits[0].hexsha

    def apply_cherries(
        self,
        target_branch: Optional[str],
        dryrun: bool,
        error_mode: str,
        force_rebuild_target: bool,
    ):
        current_head = git_get_current_head()
        click.secho("Fetching all branches", fg="cyan")
        os_system("git fetch --all")
        click.secho(f"Checking out base branch: {self.release_branch}", fg="cyan")
        os_system(f"git checkout {self.release_branch}")

        if target_branch is None and dryrun:
            target_branch = TMP_BRANCH
            click.secho(
                f"Recreating and checking out temporary branch: {target_branch}",
                fg="cyan",
            )
            os_system(f"git branch -D {target_branch}", raise_on_error=False)
            os_system(f"git checkout -b {target_branch}")
        elif (target_branch is None or target_branch == self.release_branch) and not dryrun:
            # base and target are the same - no need to recheckout
            target_branch = self.release_branch
        else:
            os_system(f"git branch {target_branch}", raise_on_error=False)
            if force_rebuild_target:
                click.secho(f"Recreating target branch: {target_branch}", fg="cyan")
                os_system(f"git branch -D {target_branch}", raise_on_error=False)
                os_system(f"git branch {target_branch}")
            click.secho(f"Checking out target branch: {target_branch}", fg="cyan")
            os_system(f"git checkout {target_branch}")

        applied_cherries: List[Cherry] = []
        applied_dryrun_cherries: List[Cherry] = []
        conflicted_cherries: List[CommitSummary] = []
        open_cherries: List[Cherry] = []

        for cherry in self.cherries:
            pr = cherry.pr
            commit = cherry.commit
            if commit is None:
                click.secho(
                    truncate_str(f"error-open #{pr.number}: {pr.title}"), fg="red"
                )
                open_cherries.append(cherry)
                continue
            sha = cherry.commit.hexsha
            if cherry.is_applied:
                click.secho(
                    truncate_str(f"skip-applied #{pr.number}: {pr.title}"), fg="yellow"
                )
                continue
            try:
                os_system(f"git cherry-pick -x {sha}")
                if dryrun:
                    applied_dryrun_cherries.append(cherry)
                else:
                    applied_cherries.append(cherry)
                click.secho(
                    truncate_str(f"apply-ok #{pr.number}: {pr.title}"),
                    fg="green",
                    nl=False,
                )
                if dryrun:
                    os_system(f"git reset --hard HEAD~1")
                    click.secho(" [DRY-RUN]", fg="cyan")
                else:
                    click.echo()

            except CherryTreeExecutionException:
                os_system("git cherry-pick --abort")
                try:
                    # try to ff to see if cherry was already applied
                    os_system(f"git cherry-pick --ff {sha}")
                    click.secho(f"skip-empty #{pr.number}: {pr.title}", fg="yellow")
                except CherryTreeExecutionException:
                    click.secho(
                        truncate_str(f"error-conflict #{pr.number}: {pr.title}"),
                        fg="red",
                    )
                    # These need to be put into a wrapper to avoid re-hitting the
                    # GH API later
                    conflicted_cherries.append(CommitSummary(
                        pr_number=pr.number,
                        pr_title=pr.title,
                        sha=commit.hexsha,
                        author=pr.user.login,
                        merged_by=pr.closed_by.login,
                    ))
                    os_system("git cherry-pick --abort")
                    if error_mode == "dryrun":
                        dryrun = True
                    elif error_mode == "break":
                        break

        os_system(f"git checkout {current_head}")
        if target_branch == TMP_BRANCH:
            os_system(f"git branch -D {target_branch}")

        if open_cherries:
            click.echo()
            click.secho(
                f"{len(open_cherries)} open PRs that need to be merged:",
                fg="red",
            )
            for cherry in open_cherries:
                pr = cherry.pr
                click.echo(f"#{pr.number} (author: {pr.user.login}): {pr.title}")

        if conflicted_cherries:
            click.echo()
            click.secho(
                f"{len(conflicted_cherries)} "
                "PRs that need to be manually cherried due to conflicts:",
                fg="red",
            )
            for commit in conflicted_cherries:
                click.echo(
                    f"#{commit.pr_number} (sha: {commit.sha[:12]}, "
                    f"author: {commit.author}, "
                    f"merged by: {commit.merged_by}): "
                    f"{truncate_str(commit.pr_title, 30)}"
                )

        click.echo()
        click.secho(f"Summary:", fg="cyan")
        click.secho(
            f"{len(applied_cherries)} successful cherries", fg="cyan",
        )
        if applied_dryrun_cherries:
            click.secho(
                f"{len(applied_dryrun_cherries)} dry-run cherries", fg="cyan",
            )
        if conflicted_cherries:
            click.secho(
                f"{len(conflicted_cherries)} conflicts", fg="cyan",
            )
        if open_cherries:
            click.secho(
                f"{len(open_cherries)} open PRs", fg="cyan",
            )
