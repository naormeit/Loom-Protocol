import argparse
import sys
import threading
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2] / "sdk" / "python"))
from loom_protocol import LoomClient


def run_drop(base_url: str, agents: int, resource_id: str):
    client = LoomClient(base_url)
    responses = []
    responses_lock = threading.Lock()
    start = time.perf_counter()

    def reserve(agent_number):
        response = client.reserve(
            agent_id=f"SHOPPING-AGENT-{agent_number}",
            resource_id=resource_id,
            intent=f"Purchase one unit from limited drop {resource_id}",
        )
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


def main():
    parser = argparse.ArgumentParser(description="Simulate an agent-driven product drop.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--agents", type=int, default=100)
    parser.add_argument("--resource-id", default="DROP-SURFACE-001")
    args = parser.parse_args()
    run_drop(args.base_url, args.agents, args.resource_id)


if __name__ == "__main__":
    main()
