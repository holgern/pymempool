import asyncio
import datetime
import logging
from typing import Any, Optional

import typer
from rich.console import Console
from rich.table import Table

from pymempool.api import MempoolAPI
from pymempool.ascii_mempool_blocks import AsciiMempoolBlocks
from pymempool.block_parser import BlockParser
from pymempool.halving import Halving
from pymempool.mempool_block_parser import MempoolBlockParser
from pymempool.recommended_fees import RecommendedFees
from pymempool.websocket import MempoolWebSocketClient

log = logging.getLogger(__name__)
app = typer.Typer()
console = Console()

state: dict[str, Any] = {}

# Default options for typer
DEFAULT_WANT = ["stats", "mempool-blocks"]
DEFAULT_ADDRESSES = None


async def display_consumer(queue: asyncio.Queue):
    """Consume messages from the queue and display in a Rich table."""
    while True:
        data = await queue.get()

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
def mempool_blocks(
    width: int = typer.Option(24, help="Width of each block"),
    height: int = typer.Option(9, help="Height of each block"),
    depth: int = typer.Option(3, help="3D effect depth"),
    padding: int = typer.Option(2, help="Space between blocks"),
    limit: int = typer.Option(0, help="Limit number of blocks to display (0 for all)"),
):
    """
    Displays mempool blocks as ASCII art with statistics.

    This command visualizes the current mempool blocks as ASCII 3D blocks.
    Each block contains information about transaction fees, count, and size.
    A summary table with aggregated statistics is shown below the visualization.

    Customize the display using the width, height, depth, and padding options
    to fit your terminal size.
    """
    mp = MempoolAPI(api_base_url=state["api"])

    try:
        ret = mp.get_mempool_blocks_fee()

        if ret is None or not ret:
            console.print("No mempool blocks data available.", style="bold red")
            return

        # Limit the number of blocks if requested
        if limit > 0 and isinstance(ret, list) and len(ret) > limit:
            ret = ret[:limit]

        # Create an AsciiMempoolBlocks instance with user-provided dimensions
        drawer = AsciiMempoolBlocks(
            block_width=width, block_height=height, block_depth=depth, padding=padding
        )

        # Generate the ASCII art representation of the mempool blocks
        ascii_art = drawer.draw_from_api(ret)

        if not ascii_art:
            console.print("No blocks to display.", style="bold yellow")
            return

        # Print the ASCII art
        console.print(ascii_art)

        try:
            # Print additional statistics
            blocks_parser = MempoolBlockParser(ret)

            if not blocks_parser.blocks:
                console.print("No block data to summarize.", style="bold yellow")
                return

            total_txs = sum(block["nTx"] for block in blocks_parser.blocks)
            total_size_mb = sum(
                block["block_size_mb"] for block in blocks_parser.blocks
            )
            total_fees_btc = sum(block["total_btc"] for block in blocks_parser.blocks)

            # Calculate fee statistics
            min_fees = [block["min_fee"] for block in blocks_parser.blocks]
            max_fees = [block["max_fee"] for block in blocks_parser.blocks]

            # Create a table for the summary
            table = Table("Statistic", "Value")
            table.add_row("Number of Blocks", str(len(blocks_parser.blocks)))
            table.add_row("Total Transactions", str(total_txs))
            table.add_row("Total Size", f"{total_size_mb:.2f} MB")
            table.add_row("Total Fees", f"{total_fees_btc:.8f} BTC")
            table.add_row(
                "Fee Range", f"{min(min_fees):.2f} - {max(max_fees):.2f} sat/vB"
            )

            console.print("\nMempool Summary:", style="bold")
            console.print(table)

        except (KeyError, ValueError, TypeError) as e:
            console.print(f"Error processing block data: {str(e)}", style="bold red")

    except Exception as e:
        console.print(f"Error retrieving mempool blocks: {str(e)}", style="bold red")


@app.command()
def blocks(
    limit: int = typer.Option(10, help="Number of blocks to retrieve"),
    start_height: int = typer.Option(
        None, help="Starting block height (default is latest)"
    ),
    width: int = typer.Option(24, help="Width of each block"),
    height: int = typer.Option(9, help="Height of each block"),
    depth: int = typer.Option(3, help="3D effect depth"),
    padding: int = typer.Option(2, help="Space between blocks"),
):
    """
    Displays recent Bitcoin blocks as ASCII art with statistics.

    This command visualizes recent blocks from the Bitcoin blockchain as ASCII 3D
    blocks.
    Each block contains information about block height, timestamp, transaction count,
    size, and other important metrics.

    Use the limit parameter to control how many blocks to display and
    start_height to specify a starting point in the blockchain.
    """
    mp = MempoolAPI(api_base_url=state["api"])

    try:
        # Get blocks data
        blocks_data = mp.get_blocks(start_height)

        if blocks_data is None or not blocks_data:
            console.print("No blocks data available.", style="bold red")
            return

        # Limit the number of blocks if requested
        if limit > 0 and isinstance(blocks_data, list) and len(blocks_data) > limit:
            blocks_data = blocks_data[:limit]

        # Parse the blocks using BlockParser
        parser = BlockParser(blocks_data)

        if not parser.blocks:
            console.print("No blocks to display.", style="bold yellow")
            return

        # Create an AsciiMempoolBlocks instance with user-provided dimensions
        drawer = AsciiMempoolBlocks(
            block_width=width, block_height=height, block_depth=depth, padding=padding
        )

        # Generate the ASCII art representation of the blocks
        ascii_art = drawer.draw_from_parser(parser)

        if not ascii_art:
            console.print("No blocks to display.", style="bold yellow")
            return

        # Print the ASCII art
        console.print(ascii_art)

        # Show summary statistics
        total_txs = sum(block["tx_count"] for block in parser.blocks)
        avg_size = sum(block["size_mb"] for block in parser.blocks) / len(parser.blocks)
        avg_tx_count = total_txs / len(parser.blocks)

        summary = Table(title="Summary Statistics")
        summary.add_column("Statistic", style="cyan")
        summary.add_column("Value", style="green")

        summary.add_row("Number of Blocks", str(len(parser.blocks)))
        summary.add_row("Total Transactions", str(total_txs))
        summary.add_row("Average Block Size", f"{avg_size:.2f} MB")
        summary.add_row("Average Transactions per Block", f"{avg_tx_count:.2f}")
        summary.add_row(
            "Block Height Range",
            f"{parser.blocks[-1]['height']} - {parser.blocks[0]['height']}",
        )

        console.print(summary)

    except Exception as e:
        console.print(f"Error retrieving blocks: {str(e)}", style="bold red")


@app.command()
def halving():
    """Returns details about next Bitcoin halving."""

    mp = MempoolAPI(api_base_url=state["api"])
    current_height = mp.get_block_tip_height()

    ret_diff = mp.get_difficulty_adjustment()
    # Use our new Halving class
    halving_info = Halving(current_height, ret_diff)

    # Print results
    table = Table("key", "value")
    table.add_row("Current Block Height", str(current_height))
    table.add_row("Halving Interval", str(halving_info.HALVING_INTERVAL))
    table.add_row("Current Halving Cycle", str(halving_info.current_halving))
    table.add_row("Next Halving Height", str(halving_info.next_halving_height))
    table.add_row("Blocks Remaining", str(halving_info.blocks_remaining))
    table.add_row("Current Block Reward", f"{halving_info.current_reward:.8f} BTC")
    table.add_row("Next Block Reward", f"{halving_info.next_reward:.8f} BTC")

    # Add time estimates if available
    if isinstance(halving_info.estimated_date, datetime.datetime):
        table.add_row(
            "Estimated Halving Date", halving_info.estimated_date.strftime("%Y-%m-%d")
        )
        table.add_row("Estimated Time Remaining", halving_info.estimated_time_until)
        table.add_row(
            "Estimated Days Remaining", f"{halving_info.estimated_days:.1f} days"
        )
    else:
        table.add_row("Estimated Halving Date", str(halving_info.estimated_date))
        table.add_row(
            "Estimated Time Remaining", str(halving_info.estimated_time_until)
        )

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


@app.command()
def stream(
    want: list[str] = DEFAULT_WANT,
    address: Optional[str] = None,
    addresses: Optional[list[str]] = None,
    mempool: bool = False,
    txids: bool = False,
    block_index: Optional[int] = None,
    rbf: Optional[str] = None,
    verbose: bool = False,
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
    state["api"] = str(api)
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
