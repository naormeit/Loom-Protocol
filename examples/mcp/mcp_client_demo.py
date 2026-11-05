"""Call Loom through its MCP server, the way an MCP-capable agent would.

This starts integrations/mcp_server/loom_mcp_server.py over stdio with the
official MCP Python client, lists its tools, and has two agent ids reserve the
same resource. It does not use an LLM: it shows the tool contract an LLM-driven
agent (Claude Desktop, an agent framework, ...) would see.

Needs the MCP SDK (pip install "loom-protocol[mcp]", Python 3.10+) and a running
gateway (python -m core.api.server):

    python examples/mcp/mcp_client_demo.py
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    raise SystemExit('The MCP SDK is not installed. Run: pip install "loom-protocol[mcp]"')

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_PATH = REPO_ROOT / "integrations" / "mcp_server" / "loom_mcp_server.py"


def tool_data(result: Any) -> Dict[str, Any]:
    """Return a tool call's payload as a dict, whichever way the SDK delivered it."""
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict) and structured:
        return structured.get("result", structured) if set(structured) == {"result"} else structured
    for block in getattr(result, "content", []):
        text = getattr(block, "text", None)
        if text:
            return json.loads(text)
    return {}


async def run(base_url: str, resource_id: str, agents: List[str]) -> Dict[str, Any]:
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_PATH)],
        env={**os.environ, "LOOM_API_URL": base_url},
    )
    outcomes: Dict[str, Any] = {}
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            outcomes["tools"] = [tool.name for tool in tools.tools]
            outcomes["status"] = tool_data(await session.call_tool("loom_status", {}))
            for agent_id in agents:
                outcomes[agent_id] = tool_data(
                    await session.call_tool(
                        "reserve_resource",
                        {
                            "agent_id": agent_id,
                            "resource_id": resource_id,
                            "intent": f"Purchase one unit of {resource_id}",
                        },
                    )
                )
    return outcomes


def main() -> None:
    parser = argparse.ArgumentParser(description="Call Loom through its MCP server.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--resource-id", default=f"MCP-DROP-{int(time.time())}")
    args = parser.parse_args()

    agents = ["mcp-agent-A", "mcp-agent-B"]
    outcomes = asyncio.run(run(args.base_url, args.resource_id, agents))

    print("Tools offered by the MCP server:", ", ".join(outcomes["tools"]))
    print("loom_status:", outcomes["status"])
    for agent_id in agents:
        result = outcomes[agent_id]
        print(f"\n{agent_id} -> {result.get('outcome')} (status {result.get('status')})")
        print(f"  next_action: {result.get('next_action')}")


if __name__ == "__main__":
    main()
