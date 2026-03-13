from unittest.mock import patch

from typer.testing import CliRunner

from pymempool.cli import app
from pymempool.watch_state import build_watch_state, reduce_watch_message

runner = CliRunner()


def make_projected_block(block_vsize, median_fee, fee_range=None, ntx=1000):
    return {
        "blockSize": block_vsize,
        "blockVSize": block_vsize,
        "nTx": ntx,
        "totalFees": 123456,
        "medianFee": median_fee,
        "feeRange": fee_range or [1.0, median_fee, median_fee * 2],
    }


def make_api_payloads():
    return {
        "mempool": {
            "count": 12345,
            "vsize": 2_500_000,
            "total_fee": 7654321,
            "fee_histogram": [[25.0, 400_000], [6.0, 600_000], [1.5, 500_000]],
        },
        "mempool_blocks": [
            make_projected_block(1_000_000, 12.0, [6.0, 12.0, 24.0], ntx=2000),
            make_projected_block(900_000, 6.0, [3.0, 6.0, 12.0], ntx=1500),
            make_projected_block(600_000, 2.0, [1.0, 2.0, 4.0], ntx=1200),
        ],
        "fees": {
            "fastestFee": 10.5,
            "halfHourFee": 7.0,
            "hourFee": 4.0,
            "economyFee": 2.0,
            "minimumFee": 1.0,
        },
        "precise_fees": {
            "fastestFee": 10.25,
            "halfHourFee": 7.125,
            "hourFee": 4.5,
            "economyFee": 2.25,
            "minimumFee": 1.001,
        },
        "tip_height": 900000,
    }


class DummyAPI:
    def __init__(self, *args, **kwargs):
        self.payloads = make_api_payloads()

    def get_mempool(self):
        return self.payloads["mempool"]

    def get_mempool_blocks_fee(self):
        return self.payloads["mempool_blocks"]

    def get_recommended_fees(self):
        return self.payloads["fees"]

    def get_recommended_fees_precise(self):
        return self.payloads["precise_fees"]

    def get_block_tip_height(self):
        return self.payloads["tip_height"]


class DummyRateLimitAPI(DummyAPI):
    def __init__(self, *args, **kwargs):
        self.notifier = kwargs.get("rate_limit_notifier")
        super().__init__(*args, **kwargs)
        self._calls = 0

    def get_mempool(self):
        if self.notifier is not None and self._calls == 0:
            self.notifier("Rate limited by API; slowing requests.")
            self.notifier("Cooling down for 8s before retrying host mempool.space.")
            self.notifier("Using cached snapshot while upstream rate limit clears.")
        self._calls += 1
        return self.payloads["mempool"]


@patch("pymempool.cli.MempoolAPI", DummyAPI)
def test_overview_renders_core_sections():
    result = runner.invoke(app, ["overview", "--blocks", "3"])

    assert result.exit_code == 0
    assert "Overview" in result.output
    assert "Projected Blocks" in result.output
    assert "Interpretation" in result.output
    assert "Backlog" in result.output


@patch("pymempool.cli.MempoolAPI", DummyAPI)
def test_pressure_renders_expected_buckets():
    result = runner.invoke(app, ["pressure"])

    assert result.exit_code == 0
    assert "Fee Pressure" in result.output
    assert ">= 20 sat/vB" in result.output
    assert "1-2 sat/vB" in result.output


@patch("pymempool.cli.MempoolAPI", DummyAPI)
def test_ladder_renders_expected_columns():
    result = runner.invoke(app, ["ladder", "--limit", "2"])

    assert result.exit_code == 0
    assert "Projected Blocks" in result.output
    assert "Median" in result.output
    assert "Depth" in result.output


def test_stream_only_starts_one_client():
    run_calls = []

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        def run(self, **kwargs):
            run_calls.append(kwargs)

    with patch("pymempool.cli.MempoolWebSocketClient", DummyClient):
        result = runner.invoke(app, ["stream"])

    assert result.exit_code == 0
    assert len(run_calls) == 1


@patch("pymempool.cli.MempoolAPI", DummyRateLimitAPI)
def test_cli_shows_rate_limit_notices_and_uses_cached_snapshot():
    result = runner.invoke(app, ["overview"])

    assert result.exit_code == 0
    assert "Rate limited by API; slowing requests." in result.output
    assert "Cooling down for 8s before retrying host mempool.space." in result.output
    assert "Using cached snapshot while upstream rate limit clears." in result.output


def test_watch_state_tracks_rate_limit_notice_and_refresh_multiplier():
    state = build_watch_state(
        height=900000,
        mempool_info={"count": 10, "vsize": 1000},
        fees={"fastestFee": 3, "minimumFee": 1},
        projected_blocks=[],
    )

    reduce_watch_message(
        state,
        {
            "rate_limit_notice": (
                "Cooling down for 8s before retrying host mempool.space."
            )
        },
    )

    assert state["last_rate_limit_notice"] is not None
    assert state["refresh_interval_multiplier"] > 1.0

    reduce_watch_message(state, {"rate_limit_recovered": True})

    assert state["last_rate_limit_notice"] is None
    assert state["refresh_interval_multiplier"] == 1.0
