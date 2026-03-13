from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from pymempool.metrics import bucket_fee_histogram


def format_sat_vb(value: float) -> str:
    """Format fee rates for terminal display."""

    if value >= 10:
        return f"{value:.1f}"
    if value >= 1:
        return f"{value:.2f}"
    return f"{value:.3f}"


def format_vbytes(value: int) -> str:
    """Format vsize values into compact units."""

    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f} vMB"
    if value >= 1_000:
        return f"{value / 1_000:.1f} kvB"
    return f"{value} vB"


def _build_fee_snapshot(fee_snapshot: Mapping[str, Any]) -> Text:
    text = Text()
    parts = [
        ("fast", fee_snapshot.get("fastest_fee")),
        ("30m", fee_snapshot.get("half_hour_fee")),
        ("60m", fee_snapshot.get("hour_fee")),
        ("econ", fee_snapshot.get("economy_fee")),
        ("min", fee_snapshot.get("minimum_fee")),
    ]

    for index, (label, value) in enumerate(parts):
        if index:
            text.append("  ")
        if value is None:
            text.append(f"{label}: n/a")
        else:
            text.append(f"{label}: {format_sat_vb(float(value))} sat/vB")
    return text


def build_overview_panel(
    mempool_info: Mapping[str, Any],
    fee_snapshot: Mapping[str, Any],
    projected_blocks: Sequence[Mapping[str, Any]],
    interpretation: str,
    backlog_blocks: float,
) -> Group:
    """Build the main overview dashboard layout."""

    stats = Table.grid(expand=True)
    stats.add_column(justify="left")
    stats.add_column(justify="left")
    stats.add_column(justify="left")
    stats.add_column(justify="left")
    stats.add_row(
        f"Txs: {mempool_info.get('count', 0):,}",
        f"VSize: {format_vbytes(int(mempool_info.get('vsize', 0)))}",
        f"Backlog: {backlog_blocks:.1f} blocks",
        f"Fees: {int(mempool_info.get('total_fee', 0)):,} sats",
    )

    headline = Panel(
        Group(stats, _build_fee_snapshot(fee_snapshot)),
        title="Overview",
        border_style="cyan",
    )

    ladder = build_ladder_table(projected_blocks)
    interpretation_panel = Panel(
        interpretation, title="Interpretation", border_style="green"
    )
    return Group(headline, ladder, interpretation_panel)


def build_ladder_table(projected_blocks: Sequence[Mapping[str, Any]]) -> Table:
    """Build a tabular projected block ladder."""

    table = Table(title="Projected Blocks")
    table.add_column("#", justify="right", style="cyan", no_wrap=True)
    table.add_column("Fill")
    table.add_column("Txs", justify="right")
    table.add_column("Min", justify="right")
    table.add_column("Median", justify="right")
    table.add_column("Max", justify="right")
    table.add_column("Spread", justify="right")
    table.add_column("Depth", justify="right")

    for block in projected_blocks:
        table.add_row(
            str(block["index"]),
            f"{block['fill_ratio'] * 100:.0f}% / {format_vbytes(block['block_vsize'])}",
            f"{block['tx_count']:,}",
            format_sat_vb(block["min_fee"]),
            format_sat_vb(block["median_fee"]),
            format_sat_vb(block["max_fee"]),
            format_sat_vb(block["fee_spread"]),
            f"{block['cumulative_depth']:.1f}",
        )

    return table


def build_pressure_table(mempool_info: Mapping[str, Any]) -> Table:
    """Build a fee-band pressure table from mempool histogram data."""

    table = Table(title="Fee Pressure")
    table.add_column("Band", style="cyan")
    table.add_column("vMB", justify="right")
    table.add_column("Percent", justify="right")
    table.add_column("Est. blocks", justify="right")
    table.add_column("Note")

    for bucket in bucket_fee_histogram(mempool_info.get("fee_histogram", [])):
        table.add_row(
            bucket["label"],
            f"{bucket['vsize'] / 1_000_000:.2f}",
            f"{bucket['percent']:.1f}%",
            f"{bucket['est_blocks']:.1f}",
            bucket["note"],
        )

    return table


def build_watch_layout(
    state: Mapping[str, Any],
    refresh_interval: float,
    verbose: bool = False,
) -> Group:
    """Build a compact live watch dashboard."""

    stats_data = state.get("stats", {})
    mempool_info = stats_data.get("mempoolInfo", {})
    fees = stats_data.get("fees", {})
    top_blocks = state.get("mempool_blocks", [])
    recent_events = state.get("recent_events", [])

    top = Table.grid(expand=True)
    top.add_column()
    top.add_column()
    fee_snapshot_renderable: RenderableType = _build_fee_snapshot(fees)
    effective_refresh = refresh_interval * float(
        state.get("refresh_interval_multiplier", 1.0)
    )
    top.add_row(
        f"Height: {state.get('height', 'n/a')}",
        f"Refresh: {effective_refresh:.1f}s",
    )
    top.add_row(
        f"Txs: {mempool_info.get('count', 0):,}",
        f"VSize: {format_vbytes(int(mempool_info.get('vsize', 0)))}",
    )
    top.add_row(fee_snapshot_renderable, "")
    if state.get("last_rate_limit_notice"):
        top.add_row(str(state["last_rate_limit_notice"]), "cached snapshot")

    events = Table(title="Recent Events")
    events.add_column("Event")
    for item in recent_events[-5:]:
        events.add_row(item)
    if not recent_events:
        events.add_row("Waiting for websocket updates...")

    if verbose and state.get("last_message_type"):
        events.add_row(f"Last packet: {state['last_message_type']}")

    return Group(
        Panel(top, title="Live Watch", border_style="cyan"),
        build_ladder_table(top_blocks[:4]),
        events,
    )
