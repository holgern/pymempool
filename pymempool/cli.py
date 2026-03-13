import asyncio
import datetime
import logging
from typing import Any, Optional

import typer
from rich.console import Console
from rich.live import Live
from rich.table import Table

from pymempool.api import MempoolAPI
from pymempool.ascii_mempool_blocks import AsciiMempoolBlocks
from pymempool.block_parser import BlockParser
from pymempool.cli_views import (
    build_ladder_table,
    build_overview_panel,
    build_pressure_table,
    build_watch_layout,
)
from pymempool.halving import Halving
from pymempool.mempool_block_parser import MempoolBlockParser
from pymempool.metrics import (
    estimate_backlog_blocks,
    interpret_mempool_condition,
    summarize_projected_blocks,
)
from pymempool.recommended_fees import RecommendedFees
from pymempool.watch_state import build_watch_state, reduce_watch_message
from pymempool.websocket import MempoolWebSocketClient

log = logging.getLogger(__name__)
app = typer.Typer()
console = Console()

state: dict[str, Any] = {}

DEFAULT_API = (
    "https://mempool.space/api/,https://mempool.emzy.de/api/,"
    "https://mempool.bitcoin-21.org/api/"
)
DEFAULT_WANT = ["stats", "mempool-blocks"]


def get_api() -> MempoolAPI:
    """Return the configured API client."""

    return MempoolAPI(api_base_url=state.get("api", DEFAULT_API))


def _normalized_fee_snapshot(
    mp: MempoolAPI, precise: bool = False
) -> dict[str, Optional[float]]:
    """Fetch current fee recommendations and normalize their field names."""

    payload = (
        mp.get_recommended_fees_precise() if precise else mp.get_recommended_fees()
    )
    fees = RecommendedFees(recommended_fees=payload)
    return fees.as_dict()


def _flatten_value(prefix: str, value: Any, table: Table) -> None:
    """Render nested API payloads into a simple key/value table."""

    if isinstance(value, dict):
        for sub_key, sub_value in value.items():
            joined = f"{prefix}.{sub_key}" if prefix else str(sub_key)
            _flatten_value(joined, sub_value, table)
        return

    if isinstance(value, list):
        for item in value:
            table.add_row(prefix, str(item))
        return

    table.add_row(prefix, str(value))


def _render_key_value_payload(payload: dict[str, Any]) -> None:
    table = Table("key", "value")
    for key, value in payload.items():
        _flatten_value(str(key), value, table)
    console.print(table)


async def display_consumer(queue: asyncio.Queue):
    """Consume websocket messages and render them in tables."""

    while True:
        data = await queue.get()

        table = Table(title="Mempool WebSocket Event")
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")

        for key, value in data.items():
            display_value = str(value)
            if isinstance(value, (dict, list)):
                display_value = f"{str(value)[:80]}..."
            table.add_row(str(key), display_value)

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
    mp = get_api()

    try:
        ret = mp.get_mempool_blocks_fee()

        if ret is None or not ret:
            console.print("No mempool blocks data available.", style="bold red")
            return

        if limit > 0 and isinstance(ret, list) and len(ret) > limit:
            ret = ret[:limit]

        drawer = AsciiMempoolBlocks(
            block_width=width, block_height=height, block_depth=depth, padding=padding
        )

        ascii_art = drawer.draw_from_api(ret)

        if not ascii_art:
            console.print("No blocks to display.", style="bold yellow")
            return

        console.print(ascii_art)

        try:
            blocks_parser = MempoolBlockParser(ret)

            if not blocks_parser.blocks:
                console.print("No block data to summarize.", style="bold yellow")
                return

            total_txs = sum(block["nTx"] for block in blocks_parser.blocks)
            total_size_mb = sum(
                block["block_size_mb"] for block in blocks_parser.blocks
            )
            total_fees_btc = sum(block["total_btc"] for block in blocks_parser.blocks)
            min_fees = [block["min_fee"] for block in blocks_parser.blocks]
            max_fees = [block["max_fee"] for block in blocks_parser.blocks]

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

        except (KeyError, ValueError, TypeError) as exc:
            console.print(f"Error processing block data: {exc}", style="bold red")

    except Exception as exc:
        console.print(f"Error retrieving mempool blocks: {exc}", style="bold red")


@app.command()
def ladder(
    limit: int = typer.Option(8, help="Number of projected blocks to display"),
    ascii: bool = typer.Option(False, help="Render the legacy ASCII block view"),
):
    """Show projected mempool blocks as an operational fee ladder."""

    mp = get_api()
    projected_blocks = mp.get_mempool_blocks_fee()
    if not projected_blocks:
        console.print("No projected blocks available.", style="bold red")
        return

    projected_blocks = projected_blocks[:limit]
    if ascii:
        drawer = AsciiMempoolBlocks()
        console.print(drawer.draw_from_api(projected_blocks))
        return

    console.print(
        build_ladder_table(summarize_projected_blocks(projected_blocks, limit=limit))
    )


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
    mp = get_api()

    try:
        blocks_data = mp.get_blocks(start_height)

        if blocks_data is None or not blocks_data:
            console.print("No blocks data available.", style="bold red")
            return

        if limit > 0 and isinstance(blocks_data, list) and len(blocks_data) > limit:
            blocks_data = blocks_data[:limit]

        parser = BlockParser(blocks_data)

        if not parser.blocks:
            console.print("No blocks to display.", style="bold yellow")
            return

        drawer = AsciiMempoolBlocks(
            block_width=width, block_height=height, block_depth=depth, padding=padding
        )
        ascii_art = drawer.draw_from_parser(parser)

        if not ascii_art:
            console.print("No blocks to display.", style="bold yellow")
            return

        console.print(ascii_art)

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

    except Exception as exc:
        console.print(f"Error retrieving blocks: {exc}", style="bold red")


@app.command()
def halving():
    """Returns details about next Bitcoin halving."""

    mp = get_api()
    current_height = mp.get_block_tip_height()
    ret_diff = mp.get_difficulty_adjustment()
    halving_info = Halving(current_height, ret_diff)

    table = Table("key", "value")
    table.add_row("Current Block Height", str(current_height))
    table.add_row("Halving Interval", str(halving_info.HALVING_INTERVAL))
    table.add_row("Current Halving Cycle", str(halving_info.current_halving))
    table.add_row("Next Halving Height", str(halving_info.next_halving_height))
    table.add_row("Blocks Remaining", str(halving_info.blocks_remaining))
    table.add_row("Current Block Reward", f"{halving_info.current_reward:.8f} BTC")
    table.add_row("Next Block Reward", f"{halving_info.next_reward:.8f} BTC")

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

    ret = get_api().get_mempool()
    if ret is not None:
        _render_key_value_payload(ret)


@app.command()
def fees(
    precise: bool = typer.Option(
        False,
        "--precise/--rounded",
        help="Use precise or rounded fee recommendations",
    ),
):
    """Returns details about current fees."""

    mp = get_api()
    ret_fees = (
        mp.get_recommended_fees_precise() if precise else mp.get_recommended_fees()
    )
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
def overview(
    precise_fees: bool = typer.Option(
        False,
        "--precise-fees/--rounded-fees",
        help="Use precise or rounded recommended fees",
    ),
    blocks: int = typer.Option(6, min=1, help="Number of projected blocks to show"),
):
    """Show the current mempool situation in one dense terminal screen."""

    mp = get_api()
    mempool_info = mp.get_mempool()
    projected_blocks = mp.get_mempool_blocks_fee()
    fee_snapshot = _normalized_fee_snapshot(mp, precise=precise_fees)

    block_summaries = summarize_projected_blocks(projected_blocks, limit=blocks)
    backlog_blocks = estimate_backlog_blocks(int(mempool_info.get("vsize", 0)))
    interpretation = interpret_mempool_condition(
        mempool_info, projected_blocks, fee_snapshot
    )

    console.print(
        build_overview_panel(
            mempool_info,
            fee_snapshot,
            block_summaries,
            interpretation,
            backlog_blocks,
        )
    )


@app.command()
def pressure():
    """Show where mempool backlog sits across fee-rate bands."""

    console.print(build_pressure_table(get_api().get_mempool()))


@app.command()
def address(address: str):
    """Returns details about an address."""

    ret = get_api().get_address(address)
    if ret is not None:
        _render_key_value_payload(ret)


@app.command()
def block(hash: str):
    """Returns details about a block."""

    ret = get_api().get_block(hash)
    if ret is not None:
        _render_key_value_payload(ret)


class WatchRenderer:
    """Update a Rich live dashboard from websocket messages."""

    def __init__(
        self, initial_state: dict[str, Any], refresh_interval: float, verbose: bool
    ):
        self.state = initial_state
        self.refresh_interval = refresh_interval
        self.verbose = verbose
        self.live: Optional[Live] = None

    async def __call__(self, message: dict[str, Any]) -> None:
        reduce_watch_message(self.state, message)
        if self.live is not None:
            self.live.update(
                build_watch_layout(
                    self.state,
                    refresh_interval=self.refresh_interval,
                    verbose=self.verbose,
                )
            )


@app.command()
def watch(
    rbf: str = typer.Option("off", help="Track RBF replacements: all, fullRbf, off"),
    refresh_interval: float = typer.Option(1.0, min=0.1, help="Live refresh interval"),
    no_color: bool = typer.Option(
        False, "--no-color", help="Disable Rich color output"
    ),
    verbose: bool = typer.Option(False, help="Show extra live diagnostics"),
):
    """Run a compact live mempool dashboard that refreshes in place."""

    if rbf not in {"off", "all", "fullRbf"}:
        raise typer.BadParameter("rbf must be one of: off, all, fullRbf")

    mp = get_api()
    initial_state = build_watch_state(
        height=int(mp.get_block_tip_height()),
        mempool_info=mp.get_mempool(),
        fees=mp.get_recommended_fees_precise(),
        projected_blocks=mp.get_mempool_blocks_fee(),
    )
    renderer = WatchRenderer(
        initial_state, refresh_interval=refresh_interval, verbose=verbose
    )
    watch_console = Console(no_color=no_color)

    client = MempoolWebSocketClient(
        want_data=DEFAULT_WANT,
        track_rbf=None if rbf == "off" else rbf,
        enable_logging=verbose,
    )

    with Live(
        build_watch_layout(
            initial_state, refresh_interval=refresh_interval, verbose=verbose
        ),
        console=watch_console,
        refresh_per_second=max(1, int(round(1 / refresh_interval)))
        if refresh_interval
        else 4,
    ) as live:
        renderer.live = live
        try:
            client.run(handler=renderer)
        except KeyboardInterrupt:
            console.print("Stopped watch dashboard.", style="bold yellow")


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


@app.callback()
def main(
    verbose: int = 3,
    api: str = DEFAULT_API,
):
    """Python CLI for mempool.space, enjoy."""
    state["verbose"] = verbose
    state["api"] = str(api)
    logger = logging.getLogger(__name__)
    verbosity = ["critical", "error", "warn", "info", "debug"][int(min(verbose, 4))]
    logger.setLevel(getattr(logging, verbosity.upper()))
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, verbosity.upper()))
    ch.setFormatter(formatter)
    logger.addHandler(ch)


if __name__ == "__main__":
    app()
