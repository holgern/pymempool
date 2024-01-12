import logging

import typer
from rich.console import Console
from rich.table import Table

from pymempool.api import MempoolAPI
from pymempool.difficulty_adjustment import DifficultyAdjustment
from pymempool.recommended_fees import RecommendedFees

log = logging.getLogger(__name__)
app = typer.Typer()
console = Console()

state = {}


@app.command()
def difficulty():
    """Returns details about difficulty adjustment."""
    mp = MempoolAPI(api_base_url=state["api"])
    ret_height = mp.get_block_tip_height()
    ret_diff = mp.get_difficulty_adjustment()
    da = DifficultyAdjustment(ret_height, ret_diff)
    if ret_diff is not None:
        table = Table("key", "value")
        for key, value in ret_diff.items():
            table.add_row(key, str(value))
        table.add_row("Last retarget Height", f"{da.last_retarget}")
        table.add_row("time Avg in Minutes", f"{da.minutes_between_blocks:.2f} min")
        console.print(table)


@app.command()
def mempool():
    """Returns details about mempool."""
    mp = MempoolAPI(api_base_url=state["api"])
    ret = mp.get_mempool()
    if ret is not None:
        table = Table("key", "value")
        for key, value in ret.items():
            if isinstance(value, list):
                for x in value:
                    table.add_row(key, str(x))
            else:
                table.add_row(key, str(value))
        console.print(table)


@app.command()
def fees():
    """Returns details about current fees."""
    mp = MempoolAPI(api_base_url=state["api"])
    ret_fees = mp.get_recommended_fees()
    ret_memblocks = mp.get_mempool_blocks_fee()
    mem = RecommendedFees(ret_fees, ret_memblocks)
    table = Table("key", "value")
    table.add_row("Fastest Fee", f"{mem.fastest_fee:.2f}")
    table.add_row("Half hour fee", f"{mem.half_hour_fee:.2f}")
    table.add_row("Hour fee", f"{mem.hour_fee:.2f}")
    table.add_row("Economy fee", f"{mem.economy_fee:.2f}")
    table.add_row("Minimum fee", f"{mem.minimum_fee:.2f} at {mem.max_mempool_mb} MB")
    table.add_row("Mempool size", f"{mem.mempool_size_mb:.2f} MB")
    table.add_row("Mempool blocks", f"{mem.mempool_blocks}")
    table.add_row("Mempool tx count", f"{mem.mempool_tx_count}")
    console.print(table)


@app.command()
def address(address: str):
    """Returns details about an address."""
    mp = MempoolAPI(api_base_url=state["api"])
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
    mp = MempoolAPI(api_base_url=state["api"])
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
def main(
    verbose: int = 3,
    api: str = "https://mempool.space/api/,https://mempool.emzy.de/api/,"
    "https://mempool.bitcoin-21.org/api/",
):
    """Python CLI for mempool.space, enjoy."""
    # Logging
    state["verbose"] = verbose
    state["api"] = api
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
