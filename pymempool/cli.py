import asyncio
import logging
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from pymempool.api import MempoolAPI
from pymempool.difficulty_adjustment import DifficultyAdjustment
from pymempool.recommended_fees import RecommendedFees
from pymempool.websocket import MempoolWebSocketClient

log = logging.getLogger(__name__)
app = typer.Typer()
console = Console()

state = {}


async def display_consumer(queue: asyncio.Queue):
    """Consume messages from the queue and display in a Rich table."""
    while True:
        data = await queue.get()
        keys = list(data.keys())

        table = Table(title="Mempool WebSocket Event")
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")

        for k, v in data.items():
            display_value = str(v)
            if isinstance(v, (dict, list)):
                display_value = f"{str(v)[:80]}..."
            table.add_row(str(k), display_value)

        console.print(table)
        queue.task_done()


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
        table.add_row("Found Blocks", f"{da.found_blocks}")
        table.add_row("Blocks behind", f"{da.blocks_behind}")
        table.add_row("Last retarget Height", f"{da.last_retarget}")
        table.add_row("Estimated Retarget Date", f"{da.estimated_retarged_date}")
        table.add_row("Estimated Retarget Period", f"{da.estimated_retarged_period}")
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
def halving():
    mp = MempoolAPI(api_base_url=state["api"])


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


@app.command()
def stream(
    want: List[str] = typer.Option(
        ["stats", "mempool-blocks"], help="Data channels to subscribe to."
    ),
    address: Optional[str] = typer.Option(None, help="Single address to track."),
    addresses: List[str] = typer.Option(None, help="Multiple addresses to track."),
    mempool: bool = typer.Option(False, help="Track full mempool."),
    txids: bool = typer.Option(False, help="Track mempool txids only."),
    block_index: Optional[int] = typer.Option(
        None, help="Track mempool block index (e.g., 0)."
    ),
    rbf: Optional[str] = typer.Option(None, help="Track RBF type: 'all' or 'fullRbf'."),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging."
    ),
):
    """
    Connect to Mempool WebSocket API and stream live Bitcoin data.
    """

    client = MempoolWebSocketClient(
        want_data=want,
        track_address=address,
        track_addresses=addresses,
        track_mempool=mempool,
        track_mempool_txids=txids,
        track_mempool_block_index=block_index,
        track_rbf=rbf,
        enable_logging=verbose,
    )

    client.run(stream_to_queue=True, queue_consumer=display_consumer)


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
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, verbosity.upper()))
    ch.setFormatter(formatter)
    log.addHandler(ch)


if __name__ == "__main__":
    app()
