import logging

import typer
from rich.console import Console
from rich.table import Table

from pymempool.api import MempoolAPI

log = logging.getLogger(__name__)
app = typer.Typer()
console = Console()

state = {"verbose": 3}


@app.command()
def difficulty():
    """Returns details about difficulty adjustment."""
    mp = MempoolAPI()
    ret = mp.get_difficulty_adjustment()
    if ret is not None:
        table = Table("key", "value")
        for key, value in ret.items():
            table.add_row(key, str(value))
        console.print(table)


@app.command()
def address(address: str):
    """Returns details about an address."""
    mp = MempoolAPI()
    ret = mp.get_address(address)
    if ret is not None:
        table = Table("key", "value")
        for key, value in ret.items():
            if isinstance(value, dict):
                for key2, value2 in value.items():
                    table.add_row(f"{key}.{key2}", str(value2))
            else:
                table.add_row(key, str(value))
        console.print(table)


@app.command()
def block(hash: str):
    """Returns details about a block."""
    mp = MempoolAPI()
    ret = mp.get_block(hash)
    if ret is not None:
        table = Table("key", "value")
        for key, value in ret.items():
            if isinstance(value, dict):
                for key2, value2 in value.items():
                    table.add_row(f"{key}.{key2}", str(value2))
            else:
                table.add_row(key, str(value))
        console.print(table)


@app.callback()
def main(verbose: int = 3):
    """Python CLI for mempool.space, enjoy."""
    # Logging
    state["verbose"] = verbose
    log = logging.getLogger(__name__)
    verbosity = ["critical", "error", "warn", "info", "debug"][int(min(verbose, 4))]
    log.setLevel(getattr(logging, verbosity.upper()))
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, verbosity.upper()))
    ch.setFormatter(formatter)
    log.addHandler(ch)


if __name__ == "__main__":
    app()
