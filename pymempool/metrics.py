from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

DEFAULT_BLOCK_VSIZE = 1_000_000


@dataclass(frozen=True)
class FeeBand:
    label: str
    minimum: float
    maximum: float | None
    note: str


DEFAULT_FEE_BANDS = (
    FeeBand(label=">= 20 sat/vB", minimum=20.0, maximum=None, note="hot zone"),
    FeeBand(label="10-20 sat/vB", minimum=10.0, maximum=20.0, note="active bidding"),
    FeeBand(label="5-10 sat/vB", minimum=5.0, maximum=10.0, note="queue building"),
    FeeBand(label="2-5 sat/vB", minimum=2.0, maximum=5.0, note="watch zone"),
    FeeBand(label="1-2 sat/vB", minimum=1.0, maximum=2.0, note="low urgency"),
    FeeBand(label="< 1 sat/vB", minimum=0.0, maximum=1.0, note="tail"),
)


def estimate_backlog_blocks(
    vsize: int, block_vsize: int = DEFAULT_BLOCK_VSIZE
) -> float:
    """Estimate backlog depth in projected blocks."""

    if vsize <= 0 or block_vsize <= 0:
        return 0.0
    return vsize / block_vsize


def summarize_projected_block(
    block: Mapping[str, Any],
    index: int,
    cumulative_vsize: int = 0,
    block_vsize_target: int = DEFAULT_BLOCK_VSIZE,
) -> dict[str, Any]:
    """Create a compact summary for a projected mempool block."""

    block_vsize = int(block.get("blockVSize", 0))
    fee_range = list(block.get("feeRange", []))
    min_fee = float(fee_range[0]) if fee_range else 0.0
    max_fee = float(fee_range[-1]) if fee_range else 0.0
    median_fee = float(block.get("medianFee", min_fee))
    next_cumulative_vsize = cumulative_vsize + block_vsize

    return {
        "index": index,
        "block_size": int(block.get("blockSize", 0)),
        "block_vsize": block_vsize,
        "fill_ratio": min(block_vsize / block_vsize_target, 1.0)
        if block_vsize_target
        else 0.0,
        "tx_count": int(block.get("nTx", 0)),
        "min_fee": min_fee,
        "median_fee": median_fee,
        "max_fee": max_fee,
        "fee_spread": max_fee - min_fee,
        "total_fees": int(block.get("totalFees", 0)),
        "cumulative_depth": estimate_backlog_blocks(
            next_cumulative_vsize, block_vsize_target
        ),
    }


def summarize_projected_blocks(
    projected_blocks: Sequence[Mapping[str, Any]],
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Summarize projected block data for CLI rendering."""

    summaries: list[dict[str, Any]] = []
    cumulative_vsize = 0

    use_blocks = projected_blocks[:limit] if limit else projected_blocks
    for index, block in enumerate(use_blocks, start=1):
        summary = summarize_projected_block(block, index, cumulative_vsize)
        summaries.append(summary)
        cumulative_vsize += summary["block_vsize"]

    return summaries


def classify_queue_shape(
    projected_blocks: Sequence[Mapping[str, Any]],
    fee_snapshot: Mapping[str, Any] | None = None,
) -> str:
    """Classify how fee pressure is distributed across the queue."""

    summaries = summarize_projected_blocks(projected_blocks, limit=4)
    if not summaries:
        return "unknown"

    first = summaries[0]["median_fee"]
    second = summaries[1]["median_fee"] if len(summaries) > 1 else first
    tail = summaries[-1]["median_fee"]
    minimum_fee = float((fee_snapshot or {}).get("minimum_fee", 1.0) or 1.0)

    if (
        len(summaries) >= 4
        and tail <= max(minimum_fee * 2, 2.0)
        and first < max(second + 6, second * 2)
    ):
        return "deep low-fee tail"
    if len(summaries) >= 3 and first >= max(tail * 2, minimum_fee + 3):
        return "front-loaded"
    if first >= max(second + 3, second * 1.35):
        return "spiking"
    return "balanced"


def interpret_mempool_condition(
    mempool_info: Mapping[str, Any],
    projected_blocks: Sequence[Mapping[str, Any]],
    fee_snapshot: Mapping[str, Any] | None = None,
) -> str:
    """Generate a one-line interpretation of current mempool conditions."""

    backlog_blocks = estimate_backlog_blocks(int(mempool_info.get("vsize", 0)))
    shape = classify_queue_shape(projected_blocks, fee_snapshot)

    if shape == "front-loaded":
        return (
            "Congestion is front-loaded: the first projected blocks are materially "
            "more expensive than the backlog tail."
        )
    if shape == "deep low-fee tail":
        return (
            "Backlog is deep but mostly low-fee; urgency only matters for the first "
            "block or two."
        )
    if shape == "spiking":
        return (
            "Fee pressure is repricing quickly: the front of the queue is moving "
            "faster than the rest of the backlog."
        )
    if backlog_blocks <= 1.5:
        return (
            "Congestion is light: most fee pressure is concentrated in the next block."
        )
    return (
        "The mempool looks balanced: fees step down gradually across the next "
        "few blocks."
    )


def bucket_fee_histogram(
    fee_histogram: Sequence[Sequence[float]],
    bands: Sequence[FeeBand] = DEFAULT_FEE_BANDS,
) -> list[dict[str, Any]]:
    """Bucket mempool histogram data into human-readable fee bands."""

    buckets: list[dict[str, Any]] = [
        {
            "label": band.label,
            "minimum": band.minimum,
            "maximum": band.maximum,
            "note": band.note,
            "vsize": 0,
        }
        for band in bands
    ]

    total_vsize = 0
    for item in fee_histogram:
        if len(item) < 2:
            continue

        fee_rate = float(item[0])
        vsize = int(item[1])
        total_vsize += vsize

        for bucket in buckets:
            minimum = float(bucket["minimum"])
            maximum = bucket["maximum"]
            if fee_rate >= minimum and (maximum is None or fee_rate < maximum):
                bucket["vsize"] = int(bucket["vsize"]) + vsize
                break

    for bucket in buckets:
        vsize = int(bucket["vsize"])
        bucket["percent"] = (vsize / total_vsize * 100) if total_vsize else 0.0
        bucket["est_blocks"] = estimate_backlog_blocks(vsize)

    return buckets
