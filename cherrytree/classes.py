from dataclasses import dataclass
from typing import NamedTuple, Optional

from git import Commit
from github.Issue import Issue


class CherryBranch(NamedTuple):
    repo: str
    branch: str

    def __repr__(self):
        return f"{self.repo}:{self.branch}"


class CherryLabel(NamedTuple):
    repo: str
    label: str

    def __repr__(self):
        return f"{self.repo}:{self.label}"


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


@dataclass
class CommitSummary:
    pr_number: int
    pr_title: str
    sha: str
    author: str
    merged_by: str



class CherryTreeExecutionException(Exception):
    pass
