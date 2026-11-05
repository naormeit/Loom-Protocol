"""Two scripted agents compete for one resource through Loom.

The agents are plain Python (no LLM): each follows a small policy that reads
Loom's machine-readable answer and acts on it.

  1. Both agents ask Loom for the same limited item at the same moment.
  2. One gets the lock (201). The other gets a conflict (409) with a retry hint.
  3. The loser waits the suggested back-off, then asks for the suggested
     alternative resource, and gets it if it is free.

Start the gateway first (python -m core.api.server), then:

    python examples/scenarios/two_agent_demo.py

The retry hint Loom returns today is simple (a jittered back-off and a
"<resource>_ALT" suggestion), so this demo shows the loop working end to end,
not a smart negotiation policy.
"""

import argparse
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
for extra in (REPO_ROOT, REPO_ROOT / "sdk" / "python", REPO_ROOT / "integrations" / "mcp_server"):
    if str(extra) not in sys.path:
        sys.path.append(str(extra))

from loom_protocol import LoomClient, LoomClientError
import loom_tools

MAX_ATTEMPTS = 3


class ScriptedAgent:
    def __init__(self, name: str, client: LoomClient, started: float, sleep: Callable[[float], None]):
        self.name = name
        self.client = client
        self.started = started
        self.sleep = sleep
        self.holds: Optional[str] = None
        self.attempts: List[Dict[str, Any]] = []
        self._lines: List[str] = []

    def say(self, text: str) -> None:
        elapsed = (time.perf_counter() - self.started) * 1000
        self._lines.append(f"[{elapsed:7.1f}ms] {self.name}: {text}")

    @property
    def lines(self) -> List[str]:
        return self._lines

    def want(self, resource_id: str, barrier: threading.Barrier) -> None:
        wanted = resource_id
        barrier.wait()
        for attempt in range(1, MAX_ATTEMPTS + 1):
            self.say(f"asking Loom for {wanted} (attempt {attempt})")
            result = loom_tools.reserve(
                self.client,
                self.name,
                wanted,
                f"Purchase one unit of {wanted}",
                expiry_ms=5000,
                error_type=LoomClientError,
            )
            self.attempts.append({"resource": wanted, **result})

            if result["outcome"] == "LOCKED":
                self.holds = wanted
                self.say(f"LOCKED {wanted} -> proceeding with the purchase")
                return

            if result["outcome"] == "CONFLICT":
                backoff = (result.get("retry_backoff_ms") or 200) / 1000
                alternative = result.get("suggested_alternative_resource")
                self.say(
                    f"CONFLICT, held by {result.get('held_by')}; waiting {backoff * 1000:.0f}ms "
                    f"then trying {alternative}"
                )
                self.sleep(backoff)
                if alternative:
                    wanted = alternative
                continue

            self.say(f"{result['outcome']}: {result['message']} -> giving up")
            return

        self.say("out of attempts -> giving up")


def run_demo(
    base_url: str,
    resource_id: Optional[str] = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Dict[str, Any]:
    resource_id = resource_id or f"DROP-{int(time.time())}"
    client = LoomClient(base_url)
    started = time.perf_counter()
    agents = [
        ScriptedAgent("alice-bot", client, started, sleep),
        ScriptedAgent("bob-bot", client, started, sleep),
    ]
    barrier = threading.Barrier(len(agents))
    threads = [threading.Thread(target=agent.want, args=(resource_id, barrier)) for agent in agents]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    timeline = sorted(line for agent in agents for line in agent.lines)
    return {
        "resource": resource_id,
        "agents": {
            agent.name: {"holds": agent.holds, "attempts": agent.attempts} for agent in agents
        },
        "timeline": timeline,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Two scripted agents compete through Loom.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--resource-id", default=None)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero unless each agent ends up holding exactly one distinct resource.",
    )
    args = parser.parse_args()

    print("=== Two scripted agents (plain Python, no LLM) compete through Loom ===")
    try:
        outcome = run_demo(args.base_url, args.resource_id)
    except LoomClientError as exc:
        raise SystemExit(f"Could not reach Loom: {exc}. Start it with: python -m core.api.server")

    print(f"Resource: {outcome['resource']}\n")
    for line in outcome["timeline"]:
        print(line)
    print("\nResult:")
    for name, data in outcome["agents"].items():
        print(f"  {name} holds: {data['holds']}")

    if args.check:
        holds = [data["holds"] for data in outcome["agents"].values()]
        if None in holds or len(set(holds)) != len(holds):
            raise SystemExit("expected each agent to hold exactly one distinct resource")


if __name__ == "__main__":
    main()
