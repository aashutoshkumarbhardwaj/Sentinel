import pytest
from agent.reliability.retry import call_with_retry
from sim.simulator import ToolTimeout, ToolError


def test_call_with_retry_success():
    attempts = 0

    def mock_fn():
        nonlocal attempts
        attempts += 1
        return "success"

    res = call_with_retry(mock_fn, max_retries=3)
    assert res == "success"
    assert attempts == 1


def test_call_with_retry_recovers_from_timeout():
    attempts = 0

    def mock_fn():
        nonlocal attempts
        attempts += 1
        if attempts <= 2:
            raise ToolTimeout("Timeout on attempt")
        return "recovered"

    res = call_with_retry(mock_fn, max_retries=3)
    assert res == "recovered"
    assert attempts == 3


def test_call_with_retry_exceeds_max_retries():
    def mock_fn():
        raise ToolTimeout("Persistent timeout")

    with pytest.raises(ToolTimeout):
        call_with_retry(mock_fn, max_retries=2)


def test_call_with_retry_does_not_retry_tool_error():
    attempts = 0

    def mock_fn():
        nonlocal attempts
        attempts += 1
        raise ToolError("Permanent failure")

    with pytest.raises(ToolError):
        call_with_retry(mock_fn, max_retries=3)
    assert attempts == 1
