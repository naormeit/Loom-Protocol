"""Turn Loom handshake responses into results an AI agent can act on.

This module has no MCP dependency, so the logic can be tested and reused
anywhere (the MCP server, the demos, other agent frameworks). Every result has
the same shape:

    outcome        one of LOCKED, CONFLICT, UNSAFE, UNAUTHORIZED, INVALID,
                   RATE_LIMITED, ERROR
    locked         True only when this agent now holds the resource
    status         the raw Loom status code (0 when Loom could not be reached)
    message        Loom's message
    correlation_id Loom's correlation id, for matching audit log entries
    next_action    plain-language instruction for what the agent should do next

Conflict and rate-limit results also carry the machine-readable retry data.
"""

from typing import Any, Callable, Dict, Optional

MAX_EXPIRY_MS = 3_600_000


def summarize_response(response: Dict[str, Any]) -> Dict[str, Any]:
    status = int(response.get("status", 0) or 0)
    payload = response.get("negotiation_payload") or {}
    result: Dict[str, Any] = {
        "outcome": "ERROR",
        "locked": status == 201,
        "status": status,
        "message": response.get("message", ""),
        "correlation_id": response.get("correlation_id"),
    }

    if status == 201:
        result["outcome"] = "LOCKED"
        result["next_action"] = (
            "You hold the lock on this resource. Complete the transaction before "
            "the lock expires. Other agents were told to back off."
        )
    elif status == 409:
        result["outcome"] = "CONFLICT"
        result["held_by"] = response.get("conflict_with")
        result["retry_backoff_ms"] = payload.get("retry_backoff_ms")
        result["suggested_alternative_resource"] = payload.get(
            "suggested_alternative_resource"
        )
        result["next_action"] = (
            "Another agent holds this resource. Do not proceed with the transaction. "
            "Wait at least retry_backoff_ms, then either try again or call "
            "reserve_resource for suggested_alternative_resource. Check that the "
            "alternative is acceptable before reserving it."
        )
    elif status == 403:
        result["outcome"] = "UNSAFE"
        result["next_action"] = (
            "The request was rejected as unsafe. Do not retry the same intent; "
            "rephrase it or stop."
        )
    elif status == 401:
        result["outcome"] = "UNAUTHORIZED"
        result["next_action"] = (
            "Loom could not verify this agent's authority. Check the signing "
            "configuration; do not retry blindly."
        )
    elif status == 400:
        result["outcome"] = "INVALID"
        result["next_action"] = "The request was malformed. Fix the fields and try again."
    elif status == 429:
        result["outcome"] = "RATE_LIMITED"
        result["retry_after_ms"] = payload.get("retry_after_ms")
        result["next_action"] = (
            "This agent is sending requests too fast. Wait at least retry_after_ms "
            "before calling again."
        )
    else:
        result["next_action"] = "Loom returned an unexpected response. Do not assume a lock was granted."

    return result


def reserve(
    client: Any,
    agent_id: str,
    resource_id: str,
    intent: str,
    expiry_ms: Any = 5000,
    error_type: Optional[type] = None,
) -> Dict[str, Any]:
    """Reserve ``resource_id`` through ``client`` and return a summarized result.

    ``client`` is any object with ``reserve(agent_id, resource_id, intent, expiry_ms)``,
    such as ``loom_protocol.LoomClient``. Problems reaching Loom come back as an
    ``ERROR`` result instead of an exception, so an agent never mistakes a failure
    for a lock.
    """
    problems = []
    for name, value in (
        ("agent_id", agent_id),
        ("resource_id", resource_id),
        ("intent", intent),
    ):
        if not isinstance(value, str) or not value.strip():
            problems.append(f"{name} must be a non-empty string")

    try:
        expiry = int(expiry_ms)
        if expiry <= 0 or expiry > MAX_EXPIRY_MS:
            problems.append(f"expiry_ms must be between 1 and {MAX_EXPIRY_MS}")
    except (TypeError, ValueError):
        expiry = 0
        problems.append("expiry_ms must be an integer")

    if problems:
        return summarize_response(
            {"status": 400, "message": "Invalid request: " + "; ".join(problems)}
        )

    catch = (error_type,) if error_type else (Exception,)
    try:
        response = client.reserve(
            agent_id=agent_id.strip(),
            resource_id=resource_id.strip(),
            intent=intent.strip(),
            expiry_ms=expiry,
        )
    except catch as exc:  # noqa: PERF203 - one call, clarity over micro-optimisation
        return {
            "outcome": "ERROR",
            "locked": False,
            "status": 0,
            "message": f"Could not reach Loom: {exc}",
            "correlation_id": None,
            "next_action": (
                "Loom could not be reached. You do NOT hold a lock. Do not "
                "proceed with the transaction; try again later."
            ),
        }
    return summarize_response(response)


def health(base_url: str, fetch: Optional[Callable[[str], bytes]] = None) -> Dict[str, Any]:
    """Check the Loom gateway's /health endpoint."""
    import json
    from urllib import error, request

    url = base_url.rstrip("/") + "/health"
    try:
        if fetch is not None:
            body = fetch(url)
        else:
            with request.urlopen(url, timeout=5) as response:
                body = response.read()
        payload = json.loads(body.decode("utf-8"))
    except (error.URLError, OSError, ValueError) as exc:
        return {"reachable": False, "url": url, "detail": str(exc)}
    return {
        "reachable": payload.get("service") == "loom-atp",
        "url": url,
        "detail": payload,
    }
