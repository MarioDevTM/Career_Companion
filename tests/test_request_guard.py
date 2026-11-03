from src.services.request_guard import claim_request, finish_request


def test_request_guard_blocks_duplicate_in_flight_and_completed_requests():
    states = {}

    assert claim_request(states, "request-1") is True
    assert claim_request(states, "request-1") is False

    finish_request(states, "request-1", success=True)
    assert claim_request(states, "request-1") is False


def test_request_guard_allows_explicit_retry_after_failure_only():
    states = {}
    assert claim_request(states, "request-2") is True
    finish_request(states, "request-2", success=False)

    assert claim_request(states, "request-2") is False
    assert claim_request(states, "request-2", allow_retry=True) is True


def test_request_guard_evicts_old_completed_entries_but_keeps_in_flight_entries():
    states = {}
    states["still-running"] = "in_flight"
    for index in range(64):
        states[f"done-{index}"] = "completed"

    assert claim_request(states, "new-request") is True
    assert states["still-running"] == "in_flight"
    assert len(states) == 64