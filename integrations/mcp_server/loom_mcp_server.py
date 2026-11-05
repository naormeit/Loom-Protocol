"""MCP server that lets any MCP-capable agent reserve a resource through Loom.

Run it over stdio (the usual way an MCP client launches a server):

    python integrations/mcp_server/loom_mcp_server.py

Configuration (environment variables):

    LOOM_API_URL        Loom gateway to call (default http://127.0.0.1:8080)
    LOOM_SHARED_SECRET  If set, packets are signed with it (match the gateway's
                        LOOM_SHARED_SECRET / LOOM_REQUIRE_SIGNATURE)
    LOOM_AGENT_ID       If set, every reservation is made as this agent and the
                        model-supplied agent_id is ignored. Set it in production:
                        otherwise a model (or a prompt injected into it) can claim
                        any agent id.

Install the MCP SDK first:  pip install "loom-protocol[mcp]"
(or just: pip install "mcp>=1.2,<2"). Requires Python 3.10 or newer.

Important: this is a stdio server, so nothing may be printed to stdout; that is
the protocol channel.
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for extra in (REPO_ROOT, REPO_ROOT / "sdk" / "python", Path(__file__).resolve().parent):
    if str(extra) not in sys.path:
        sys.path.append(str(extra))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - exercised only without the SDK
    sys.stderr.write(
        'The MCP SDK is not installed. Run: pip install "loom-protocol[mcp]" '
        '(or pip install "mcp>=1.2,<2"; Python 3.10+).\n'
    )
    raise SystemExit(1) from exc

from loom_protocol import LoomClient, LoomClientError
import loom_tools

INSTRUCTIONS = (
    "Loom decides which one agent gets a scarce resource when several agents want "
    "it at once. Call reserve_resource BEFORE you try to buy, book, or claim the "
    "resource. Only proceed with the transaction if outcome is LOCKED. If outcome "
    "is CONFLICT, another agent holds it: wait for retry_backoff_ms, then retry or "
    "reserve the suggested alternative if it is acceptable. Never assume you hold a "
    "lock unless outcome is LOCKED."
)


def build_server(client, base_url: str, pinned_agent_id: str = "") -> FastMCP:
    server = FastMCP("loom", instructions=INSTRUCTIONS)

    @server.tool()
    def reserve_resource(
        resource_id: str,
        intent: str,
        agent_id: str = "",
        expiry_ms: int = 5000,
    ) -> dict:
        """Ask Loom for an exclusive, time-limited lock on a scarce resource.

        Args:
            resource_id: The identifier of the thing you want, shared by every
                agent competing for it, for example "DROP-SURFACE-001".
            intent: One plain sentence saying what you want to do with it, for
                example "Purchase one Surface Pro from the limited drop".
            agent_id: A stable identifier for you (the agent), for example
                "shopping-agent-7". Each agent should use its own id. Ignored
                if the server operator has fixed the agent identity.
            expiry_ms: How long you want to hold the lock, in milliseconds
                (1 to 3,600,000). Default 5000.

        Returns a result whose `outcome` is LOCKED, CONFLICT, UNSAFE,
        UNAUTHORIZED, INVALID, RATE_LIMITED, or ERROR. Only `outcome == "LOCKED"`
        (with `locked == true`) means you hold the lock. Follow `next_action`.
        """
        effective_agent = pinned_agent_id or agent_id
        result = loom_tools.reserve(
            client,
            effective_agent,
            resource_id,
            intent,
            expiry_ms,
            error_type=LoomClientError,
        )
        result["agent_id"] = effective_agent.strip() if isinstance(effective_agent, str) else effective_agent
        return result

    @server.tool()
    def loom_status() -> dict:
        """Check whether the Loom gateway is reachable. Takes no arguments."""
        return loom_tools.health(base_url)

    return server


def main() -> None:
    base_url = os.environ.get("LOOM_API_URL", "http://127.0.0.1:8080")
    secret = os.environ.get("LOOM_SHARED_SECRET") or None
    client = LoomClient(base_url, shared_secret=secret)
    pinned = (os.environ.get("LOOM_AGENT_ID") or "").strip()
    build_server(client, base_url, pinned_agent_id=pinned).run()


if __name__ == "__main__":
    main()
