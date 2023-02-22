import logging

import typer
from rich.console import Console

log = logging.getLogger(__name__)
app = typer.Typer()
console = Console()

state = {"verbose": 3}


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
