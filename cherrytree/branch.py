import click
from cherrytree.gihtub_utils import get_tags


class ReleaseBranch:
    def __init__(self, minor_version):
        self.minor_version
        click.secho(f"Fetching tags", fg="cyan")
        self.tags = get_tags()
