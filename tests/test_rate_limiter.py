import threading

from pymempool.rate_limiter import RateLimiter


class FakeClock:
    def __init__(self, start: float = 0.0):
        self.current = start
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.current

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.current += seconds


def test_token_refill_behavior():
    clock = FakeClock()
    limiter = RateLimiter(
        rate_limit_per_sec=1.0,
        rate_limit_burst=2,
        time_func=clock.time,
        sleep_func=clock.sleep,
        random_func=lambda _a, _b: 0.0,
    )

    limiter.wait_until_allowed("mempool.space")
    limiter.wait_until_allowed("mempool.space")
    limiter.wait_until_allowed("mempool.space")

    assert clock.sleeps == [1.0]


def test_burst_exhaustion_waits_before_next_request():
    clock = FakeClock()
    limiter = RateLimiter(
        rate_limit_per_sec=2.0,
        rate_limit_burst=1,
        time_func=clock.time,
        sleep_func=clock.sleep,
        random_func=lambda _a, _b: 0.0,
    )

    limiter.wait_until_allowed("mempool.space")
    limiter.wait_until_allowed("mempool.space")

    assert clock.sleeps == [0.5]


def test_hard_cooldown_enforcement():
    clock = FakeClock()
    limiter = RateLimiter(
        rate_limit_per_sec=10.0,
        rate_limit_burst=5,
        time_func=clock.time,
        sleep_func=clock.sleep,
        random_func=lambda _a, _b: 0.0,
    )

    cooldown = limiter.punish_429("mempool.space", retry_after=4.0, attempt=1)
    limiter.wait_until_allowed("mempool.space")

    assert cooldown == 4.0
    assert clock.sleeps == [4.0]


def test_pick_host_prefers_non_cooling_host():
    clock = FakeClock()
    limiter = RateLimiter(
        time_func=clock.time,
        sleep_func=clock.sleep,
        random_func=lambda _a, _b: 0.0,
    )
    limiter.punish_429("host-a", retry_after=5.0, attempt=1)

    host = limiter.pick_host(["host-a", "host-b"])

    assert host == "host-b"
    assert clock.sleeps == []


def test_pick_host_waits_for_earliest_host_when_all_cooling_down():
    clock = FakeClock()
    limiter = RateLimiter(
        time_func=clock.time,
        sleep_func=clock.sleep,
        random_func=lambda _a, _b: 0.0,
    )
    limiter.punish_429("host-a", retry_after=5.0, attempt=1)
    limiter.punish_429("host-b", retry_after=2.0, attempt=1)

    host = limiter.pick_host(["host-a", "host-b"])

    assert host == "host-b"
    assert clock.sleeps == [2.0]


def test_same_key_requests_are_coalesced():
    from pymempool.response_cache import ResponseCache

    cache = ResponseCache(ttl_seconds=10.0)
    calls: list[str] = []
    gate = threading.Event()

    def loader():
        calls.append("load")
        gate.wait(timeout=1)
        return {"ok": True}

    results: list[dict[str, bool]] = []

    def worker():
        results.append(cache.get_or_load("GET:mempool", loader))

    first = threading.Thread(target=worker)
    second = threading.Thread(target=worker)
    first.start()
    second.start()
    gate.set()
    first.join()
    second.join()

    assert calls == ["load"]
    assert results == [{"ok": True}, {"ok": True}]
