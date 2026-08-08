from src.connectors.circuit_breaker import CircuitBreaker


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_opens_after_threshold():
    cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=30, now=FakeClock())
    assert not cb.is_open()
    cb.record_failure()
    assert not cb.is_open()
    cb.record_failure()
    assert cb.is_open()


def test_half_open_after_cooldown_then_closes_on_success():
    clk = FakeClock()
    cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=30, now=clk)
    cb.record_failure()
    assert cb.is_open()
    clk.t = 31
    assert not cb.is_open()          # half-open allows a trial
    assert cb.state == "half_open"
    cb.record_success()
    assert cb.state == "closed"


def test_success_resets_failures():
    cb = CircuitBreaker(failure_threshold=2, now=FakeClock())
    cb.record_failure()
    cb.record_success()
    cb.record_failure()
    assert not cb.is_open()
