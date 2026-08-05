import argparse
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict

sys.path.append(str(Path(__file__).resolve().parents[2] / "sdk" / "python"))
from loom_protocol import LoomClient, LoomClientError


def run_drop(base_url: str, agents: int, resource_id: str) -> Dict[str, Any]:
    client = LoomClient(base_url)
    responses = []
    responses_lock = threading.Lock()
    start = time.perf_counter()

    def reserve(agent_number):
        try:
            response = client.reserve(
                agent_id=f"SHOPPING-AGENT-{agent_number}",
                resource_id=resource_id,
                intent=f"Purchase one unit from limited drop {resource_id}",
            )
        except LoomClientError as exc:
            response = {"status": 0, "message": str(exc)}
        with responses_lock:
            responses.append(response)

    threads = [threading.Thread(target=reserve, args=(index,)) for index in range(agents)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    elapsed_ms = (time.perf_counter() - start) * 1000
    winners = sum(1 for response in responses if response["status"] == 201)
    conflicts = sum(1 for response in responses if response["status"] == 409)

    print("=== Loom Limited Inventory Drop ===")
    print(f"Agents: {agents}")
    print(f"Resource: {resource_id}")
    print(f"Elapsed: {elapsed_ms:.2f}ms")
    print(f"Locks secured: {winners}")
    print(f"Conflicts negotiated: {conflicts}")
    return {
        "agents": agents,
        "responses": responses,
        "winners": winners,
        "conflicts": conflicts,
        "elapsed_ms": elapsed_ms,
    }


def main():
    parser = argparse.ArgumentParser(description="Simulate an agent-driven product drop.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--agents", type=int, default=100)
    parser.add_argument("--resource-id", default="DROP-SURFACE-001")
    parser.add_argument(
        "--require-one-winner",
        action="store_true",
        help="Fail unless exactly one agent wins and every other agent receives a conflict.",
    )
    args = parser.parse_args()
    result = run_drop(args.base_url, args.agents, args.resource_id)
    if args.require_one_winner:
        expected_conflicts = args.agents - 1
        if result["winners"] != 1 or result["conflicts"] != expected_conflicts:
            raise SystemExit(
                "expected exactly one winner and "
                f"{expected_conflicts} conflicts, got "
                f"{result['winners']} winners and {result['conflicts']} conflicts"
            )


if __name__ == "__main__":
    main()
