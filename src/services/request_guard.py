from typing import MutableMapping


MAX_TRACKED_REQUESTS = 64


def claim_request(
    states: MutableMapping[str, str], request_hash: str, allow_retry: bool = False
) -> bool:
    current = states.get(request_hash)
    if current in {"in_flight", "completed"}:
        return False
    if current == "failed" and not allow_retry:
        return False

    states[request_hash] = "in_flight"
    while len(states) > MAX_TRACKED_REQUESTS:
        removable_hash = next(
            (key for key, value in states.items() if value != "in_flight"), None
        )
        if removable_hash is None:
            break
        del states[removable_hash]
    return True


def finish_request(states: MutableMapping[str, str], request_hash: str, success: bool) -> None:
    states[request_hash] = "completed" if success else "failed"
