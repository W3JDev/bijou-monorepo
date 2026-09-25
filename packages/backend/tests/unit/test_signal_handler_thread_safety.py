"""Regression tests for signal-handler installation off the main thread.

Background
----------
`BijouAI.__init__` used to call `signal.signal(...)` unconditionally. CPython
only permits that from the main thread of the main interpreter; anywhere else
it raises

    ValueError: signal only works in main thread of the main interpreter

`_include_routers()` and `BijouAI()` both run inside FastAPI's startup event,
so any host that runs startup off the main thread hit this. The concrete case
that made it visible: `fastapi.testclient.TestClient(app)` used as a context
manager runs the ASGI lifespan on a worker thread, so entering the context
crashed before a single request could be made. That blocked every in-process
integration test in the suite.

The fix is to install handlers when possible and degrade quietly when not.
Skipping registration off the main thread loses nothing: uvicorn installs its
own SIGINT/SIGTERM handling in that configuration, and the handler here only
flips `self.running = False`.

These tests exercise the helper directly rather than constructing a full
`BijouAI`, which would open network connections and start schedulers.
"""

import signal
import threading

import pytest

from src.core.bijou import _install_signal_handlers


class _Recorder:
    """Stand-in for BijouAI: just needs a bound handler method."""

    def __init__(self):
        self.running = True
        self.calls = []

    def _signal_handler(self, signum, frame):  # pragma: no cover - not invoked
        self.calls.append(signum)
        self.running = False


def _run_in_thread(fn):
    """Run fn on a worker thread; return (result, exception)."""
    box = {}

    def target():
        try:
            box["result"] = fn()
        except BaseException as exc:  # noqa: BLE001 - we are asserting on it
            box["error"] = exc

    t = threading.Thread(target=target, name="signal-install-probe")
    t.start()
    t.join(timeout=10)
    assert not t.is_alive(), "worker thread hung installing signal handlers"
    return box.get("result"), box.get("error")


def test_install_signal_handlers_off_main_thread_does_not_raise():
    """The actual regression: this raised ValueError before the fix."""
    obj = _Recorder()
    result, error = _run_in_thread(lambda: _install_signal_handlers(obj))

    assert error is None, (
        f"installing signal handlers off the main thread raised {error!r}; "
        "this is the bug that made TestClient(app) unusable"
    )
    assert result is False, (
        "off the main thread the helper should report that it installed "
        "nothing, so callers can tell the difference"
    )


def test_install_signal_handlers_on_main_thread_still_registers():
    """Guard against 'fixing' the crash by disabling handlers everywhere.

    Graceful shutdown in production depends on these actually being installed,
    so the fix must not be a blanket no-op.
    """
    obj = _Recorder()
    previous = {
        signal.SIGINT: signal.getsignal(signal.SIGINT),
        signal.SIGTERM: signal.getsignal(signal.SIGTERM),
    }
    try:
        installed = _install_signal_handlers(obj)

        assert installed is True, "handlers should be installed on the main thread"
        for sig in (signal.SIGINT, signal.SIGTERM):
            assert signal.getsignal(sig) == obj._signal_handler, (
                f"{sig!r} was not bound to the instance handler"
            )
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def test_install_signal_handlers_is_not_silently_swallowing_everything():
    """A bare `except Exception: pass` here would hide real programming errors.

    Passing an object with no `_signal_handler` is a genuine bug at the call
    site and must surface, not vanish.
    """
    with pytest.raises(AttributeError):
        _install_signal_handlers(object())
