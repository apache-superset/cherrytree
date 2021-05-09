from dataclasses import dataclass
from typing import NamedTuple, Optional

from git import Commit
from github.Issue import Issue


@dataclass
class Cherry:
    commit: Optional[Commit]
    pr: Issue
    is_applied: bool


@dataclass
class CommitSummary:
    """
    This dataclass is needed to speed up processing
    """
    pr_number: int
    pr_title: str
    sha: str
    author: str
    merged_by: str


class CherryTreeExecutionException(Exception):
    pass
