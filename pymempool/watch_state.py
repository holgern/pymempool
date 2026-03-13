from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any, Optional

from pymempool.metrics import summarize_projected_blocks
from pymempool.recommended_fees import normalize_recommended_fee_payload


def build_watch_state(
    height: int,
    mempool_info: Mapping[str, Any],
    fees: Mapping[str, Any],
    projected_blocks: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Create the initial state for the live watch dashboard."""

    return {
        "height": height,
        "stats": {
            "mempoolInfo": dict(mempool_info),
            "fees": normalize_recommended_fee_payload(fees),
            "da": {},
        },
        "mempool_blocks": summarize_projected_blocks(projected_blocks, limit=8),
        "recent_events": ["Loaded initial mempool snapshot"],
        "rbf_count": 0,
        "last_rbf_type": None,
        "last_message_type": None,
    }


def _push_event(state: MutableMapping[str, Any], event: str) -> None:
    events = state.setdefault("recent_events", [])
    events.append(event)
    if len(events) > 20:
        del events[:-20]


def reduce_watch_message(
    state: MutableMapping[str, Any], message: Mapping[str, Any]
) -> MutableMapping[str, Any]:
    """Normalize websocket messages into a compact dashboard state."""

    if "stats" in message and isinstance(message["stats"], Mapping):
        nested_message = dict(message)
        nested_message.update(message["stats"])
        message = nested_message

    message_keys = [key for key in message if message.get(key) not in (None, [], {})]
    state["last_message_type"] = ", ".join(message_keys) if message_keys else "empty"

    if "mempool-blocks" in message:
        state["mempool_blocks"] = summarize_projected_blocks(
            message["mempool-blocks"], limit=8
        )
        _push_event(state, "Projected blocks updated")

    if any(key in message for key in ("mempoolInfo", "fees", "da")):
        stats = state.setdefault("stats", {})
        if "mempoolInfo" in message:
            stats["mempoolInfo"] = dict(message["mempoolInfo"])
        if "fees" in message:
            stats["fees"] = normalize_recommended_fee_payload(message["fees"])
        if "da" in message:
            stats["da"] = dict(message["da"])
            height = _extract_height(message["da"])
            if height is not None:
                state["height"] = height
        _push_event(state, "Stats updated")

    if "rbfLatest" in message:
        replacements = message["rbfLatest"] or []
        state["rbf_count"] = len(replacements)
        state["last_rbf_type"] = _detect_rbf_type(replacements)
        if replacements:
            _push_event(
                state,
                f"RBF updates: {len(replacements)} ({state['last_rbf_type'] or 'unknown'})",
            )

    return state


def _extract_height(da_payload: Mapping[str, Any]) -> Optional[int]:
    for key in ("currentBlockHeight", "previousRetargetHeight", "height"):
        value = da_payload.get(key)
        if isinstance(value, int):
            return value
    return None


def _detect_rbf_type(replacements: Sequence[Mapping[str, Any]]) -> Optional[str]:
    if not replacements:
        return None
    latest = replacements[0]
    if latest.get("fullRbf"):
        return "fullRbf"
    return "all"
