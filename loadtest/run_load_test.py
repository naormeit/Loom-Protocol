"""Load-test harness for the Loom gateway.

Sends many agents' handshakes at the gateway at once and reports what happened:
how many got the lock, how many were told to renegotiate, how long each request
took, how many failed, and whether the one-winner rule held. It uses only the
Python standard library, so it runs anywhere, and it can target a local gateway
or a hosted one (including as a stand-in client for a cloud load test).

Examples:

    python -m core.api.server                       # in another terminal
    python loadtest/run_load_test.py --agents 100,1000,10000
    python loadtest/run_load_test.py --agents 1000 --resources 20 --rounds 5
    python loadtest/run_load_test.py --base-url https://host --agents 1000 --check

What the numbers mean (and do not mean):

* "agents" is how many requests are sent in a run. "concurrency" is how many are
  in flight at once from this client; the rest wait their turn. They are not the
  same thing, so both are reported.
* Latency is measured by this client from just before it opens a connection to
  the moment the response is read. It includes queueing at the server.
* Run against localhost, the client and server share one machine and compete for
  the same CPU, so results describe that setup, not a deployed one.
"""

import argparse
import concurrent.futures
import http.client
import json
import math
import os
import platform
import random
import shlex
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

SAFE_INTENT = "Purchase one unit of the limited item"
UNSAFE_INTENT = "Steal the inventory and bypass the checkout"


# --------------------------------------------------------------------------- helpers
def percentile(sorted_values: List[float], p: float) -> Optional[float]:
    """Linear-interpolated percentile of an already sorted list (p between 0 and 100)."""
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (p / 100.0) * (len(sorted_values) - 1)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return sorted_values[low]
    fraction = rank - low
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * fraction


def latency_summary(latencies_ms: List[float]) -> Dict[str, Optional[float]]:
    ordered = sorted(latencies_ms)
    if not ordered:
        return {"count": 0, "min": None, "mean": None, "p50": None, "p90": None, "p95": None, "p99": None, "max": None}
    return {
        "count": len(ordered),
        "min": round(ordered[0], 2),
        "mean": round(sum(ordered) / len(ordered), 2),
        "p50": round(percentile(ordered, 50), 2),
        "p90": round(percentile(ordered, 90), 2),
        "p95": round(percentile(ordered, 95), 2),
        "p99": round(percentile(ordered, 99), 2),
        "max": round(ordered[-1], 2),
    }


def classify_error(exc: BaseException) -> str:
    if isinstance(exc, (socket.timeout, TimeoutError)):
        return "timeout"
    if isinstance(exc, ConnectionRefusedError):
        return "refused"
    if isinstance(exc, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, http.client.RemoteDisconnected)):
        return "reset"
    if isinstance(exc, (json.JSONDecodeError, http.client.HTTPException)):
        return "bad_response"
    return "os_error"


_local = threading.local()
_registry: List[Any] = []
_registry_lock = threading.Lock()


def _new_connection(host: str, port: int, use_tls: bool, timeout: float):
    cls = http.client.HTTPSConnection if use_tls else http.client.HTTPConnection
    connection = cls(host, port, timeout=timeout)
    with _registry_lock:
        _registry.append(connection)
    return connection


def close_all_connections() -> None:
    """Close every connection this process opened, whichever thread owns it."""
    with _registry_lock:
        connections = list(_registry)
        _registry.clear()
    for connection in connections:
        try:
            connection.close()
        except Exception:  # noqa: BLE001
            pass
    _local.connection = None


def _drop_connection() -> None:
    connection = getattr(_local, "connection", None)
    _local.connection = None
    if connection is not None:
        try:
            connection.close()
        except Exception:  # noqa: BLE001
            pass


def send_packet(
    host: str,
    port: int,
    use_tls: bool,
    packet: Dict[str, Any],
    timeout: float,
    keepalive: bool = True,
) -> Tuple[Optional[int], float, Optional[str]]:
    """POST one handshake. Returns (http_status or None, latency_ms, error_kind or None).

    With ``keepalive`` each worker thread reuses one connection, as real HTTP client
    libraries do. Without it every request opens and closes its own connection.
    """
    started = time.perf_counter()
    body = json.dumps(packet).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if not keepalive:
        headers["Connection"] = "close"

    reused = False
    for attempt in (1, 2):
        connection = getattr(_local, "connection", None) if keepalive else None
        reused = connection is not None
        if connection is None:
            connection = _new_connection(host, port, use_tls, timeout)
            if keepalive:
                _local.connection = connection
        try:
            if connection.sock is None:
                connection.connect()
                # Headers and body go out as two writes; without TCP_NODELAY, Linux holds the
                # second for the peer's delayed ACK (about 40 ms) on a reused connection.
                connection.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            connection.request("POST", "/v1/handshake", body=body, headers=headers)
            response = connection.getresponse()
            raw = response.read()
            status = response.status
            json.loads(raw.decode("utf-8"))  # a response that is not JSON is an error
            if not keepalive:
                connection.close()
            elif response.will_close:
                _drop_connection()
            return status, (time.perf_counter() - started) * 1000, None
        except Exception as exc:  # noqa: BLE001 - every failure is classified and counted
            kind = classify_error(exc)
            _drop_connection()
            if not keepalive:
                try:
                    connection.close()
                except Exception:  # noqa: BLE001
                    pass
            # A reused connection can have been closed by the server while idle. Retry
            # once on a fresh connection, as HTTP clients do; never retry a timeout.
            if keepalive and reused and attempt == 1 and kind in ("reset", "bad_response"):
                continue
            return None, (time.perf_counter() - started) * 1000, kind
    return None, (time.perf_counter() - started) * 1000, "os_error"  # pragma: no cover


def build_packets(agents: int, resources: int, unsafe_percent: float, run_id: str, rng: random.Random) -> List[Dict[str, Any]]:
    """One packet per agent. Agent i competes for resource (i mod resources)."""
    unsafe_count = int(round(agents * unsafe_percent / 100.0))
    unsafe_indexes = set(rng.sample(range(agents), unsafe_count)) if unsafe_count else set()
    packets = []
    for index in range(agents):
        packets.append(
            {
                "agent_id": f"LOAD-{run_id}-A{index}",
                "intent": UNSAFE_INTENT if index in unsafe_indexes else SAFE_INTENT,
                "intent_hash": f"LOAD-{run_id}-R{index % resources}",
                "expiry": 60000,
                "_unsafe": index in unsafe_indexes,  # stripped before sending
            }
        )
    rng.shuffle(packets)
    return packets


def check_health(host: str, port: int, use_tls: bool, timeout: float) -> Tuple[bool, str]:
    try:
        connection = (http.client.HTTPSConnection if use_tls else http.client.HTTPConnection)(host, port, timeout=timeout)
        connection.request("GET", "/health", headers={"Connection": "close"})
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        connection.close()
        if response.status == 200 and payload.get("service") == "loom-atp":
            return True, "ok"
        return False, f"unexpected health response: HTTP {response.status} {payload}"
    except Exception as exc:  # noqa: BLE001
        return False, f"could not reach the gateway: {exc}"


# --------------------------------------------------------------------------- one run
def run_level(
    target: Tuple[str, int, bool],
    agents: int,
    concurrency: int,
    resources: int,
    unsafe_percent: float,
    timeout: float,
    seed: int,
    run_id: str,
    keepalive: bool = True,
) -> Dict[str, Any]:
    host, port, use_tls = target
    rng = random.Random(seed)
    packets = build_packets(agents, resources, unsafe_percent, run_id, rng)
    workers = max(1, min(concurrency, agents))

    outcomes: List[Dict[str, Any]] = []

    def task(packet: Dict[str, Any]) -> Dict[str, Any]:
        unsafe = packet["_unsafe"]
        wire = {key: value for key, value in packet.items() if key != "_unsafe"}
        status, latency_ms, error = send_packet(host, port, use_tls, wire, timeout, keepalive)
        return {
            "resource": wire["intent_hash"],
            "unsafe": unsafe,
            "status": status,
            "latency_ms": latency_ms,
            "error": error,
        }

    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(task, packet) for packet in packets]
        for future in concurrent.futures.as_completed(futures):
            outcomes.append(future.result())
    elapsed = time.perf_counter() - started
    close_all_connections()

    status_counts: Dict[str, int] = {}
    error_counts: Dict[str, int] = {}
    latencies: List[float] = []
    winners: Dict[str, int] = {f"LOAD-{run_id}-R{r}": 0 for r in range(resources)}
    for item in outcomes:
        if item["error"]:
            error_counts[item["error"]] = error_counts.get(item["error"], 0) + 1
            continue
        key = str(item["status"])
        status_counts[key] = status_counts.get(key, 0) + 1
        latencies.append(item["latency_ms"])
        if item["status"] == 201:
            winners[item["resource"]] = winners.get(item["resource"], 0) + 1

    errors_total = sum(error_counts.values())
    multi = sorted(resource for resource, count in winners.items() if count > 1)
    none = sorted(resource for resource, count in winners.items() if count == 0)
    responded = agents - errors_total
    unsafe_sent = sum(1 for item in outcomes if item["unsafe"])
    unsafe_rejected = sum(1 for item in outcomes if item["unsafe"] and item["status"] == 403)

    return {
        "agents": agents,
        "concurrency": workers,
        "keepalive": keepalive,
        "resources": resources,
        "unsafe_percent": unsafe_percent,
        "elapsed_s": round(elapsed, 3),
        "throughput_rps": round(responded / elapsed, 1) if elapsed > 0 else None,
        "responded": responded,
        "errors": errors_total,
        "error_rate_percent": round(100.0 * errors_total / agents, 2) if agents else 0.0,
        "error_kinds": error_counts,
        "status_counts": dict(sorted(status_counts.items())),
        "locks_granted": sum(winners.values()),
        "winners_per_resource": winners if resources <= 20 else {"resources": resources, "min": min(winners.values()), "max": max(winners.values())},
        "resources_with_multiple_winners": multi,
        "resources_with_no_winner": none,
        "one_winner_rule_held": not multi,
        "exactly_one_winner_each": not multi and not none,
        "unsafe_sent": unsafe_sent,
        "unsafe_rejected_403": unsafe_rejected,
        "latency_ms": latency_summary(latencies),
    }


# --------------------------------------------------------------------------- report
def git_commit() -> Optional[str]:
    try:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


def sanitize_command(argv: List[str]) -> str:
    """The command line for the report: quoted, and without local output paths."""
    kept: List[str] = []
    skip_next = False
    for token in argv:
        if skip_next:
            skip_next = False
            continue
        if token in ("--output-dir", "--report"):
            skip_next = True
            continue
        if token.startswith("--output-dir=") or token.startswith("--report="):
            continue
        kept.append(token)
    return "python loadtest/run_load_test.py " + " ".join(shlex.quote(token) for token in kept)


def fmt(value: Any, suffix: str = "") -> str:
    return "n/a" if value is None else f"{value}{suffix}"


def render_markdown(report: Dict[str, Any]) -> str:
    meta = report["meta"]
    lines = [
        f"# Loom load test: {meta['label']}",
        "",
        f"Run on {meta['started_at']} against `{meta['base_url']}`.",
        "",
        "## Setup",
        "",
        f"- Machine: {meta['platform']}, Python {meta['python']}, {meta['cpus']} logical CPUs",
        f"- Gateway commit (client checkout): `{meta['git_commit']}`",
        f"- Command: `{meta['command']}`",
        f"- Scenario: each agent sends one handshake; {meta['resources']} resource(s), agents are spread evenly across them",
        f"- Client in-flight limit: {meta['concurrency']}; connections {'reused (keep-alive)' if meta['keepalive'] else 'opened per request'}; per-request timeout {meta['timeout_s']} s; seed {meta['seed']}",
        "",
        "## Results",
        "",
        "| Agents | In flight | Resources | Round | Time (s) | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | Max (ms) | 201 | 409 | 403 | 429 | Errors | One-winner rule |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for run in report["runs"]:
        sc = run["status_counts"]
        lat = run["latency_ms"]
        rule = "held" if run["exactly_one_winner_each"] else ("held (a resource had no winner)" if run["one_winner_rule_held"] else "BROKEN")
        lines.append(
            f"| {run['agents']} | {run['concurrency']} | {run['resources']} | {run['round']} | {run['elapsed_s']} | {fmt(run['throughput_rps'])} | "
            f"{fmt(lat['p50'])} | {fmt(lat['p95'])} | {fmt(lat['p99'])} | {fmt(lat['max'])} | "
            f"{sc.get('201', 0)} | {sc.get('409', 0)} | {sc.get('403', 0)} | {sc.get('429', 0)} | {run['errors']} | {rule} |"
        )
    lines += ["", "## Summary", ""]
    levels = sorted({run["agents"] for run in report["runs"]})
    for agents in levels:
        group = [run for run in report["runs"] if run["agents"] == agents]
        held = sum(1 for run in group if run["one_winner_rule_held"])
        errs = sum(run["errors"] for run in group)
        lines.append(f"- {agents} agents: one-winner rule held in {held} of {len(group)} run(s); {errs} failed request(s) in total.")

    failures = [run for run in report["runs"] if run["errors"]]
    if failures:
        lines += ["", "## Failed requests", ""]
        for run in failures:
            kinds = ", ".join(f"{k}: {v}" for k, v in sorted(run["error_kinds"].items()))
            lines.append(f"- {run['agents']} agents (round {run['round']}): {run['errors']} failed ({run['error_rate_percent']}%): {kinds}")

    lines += ["", "## Read this before quoting the numbers", ""]
    for note in meta["notes"]:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def build_notes(base_url: str, args: argparse.Namespace) -> List[str]:
    notes = [
        "Latency is measured by the client from just before connecting to the end of the response; it includes queueing at the server.",
        f"'In flight' is a client-side cap ({args.concurrency}). Larger runs queue behind it, so '10,000 agents' means 10,000 requests, not 10,000 simultaneous connections.",
        ("Each worker thread reuses one connection (HTTP keep-alive), as typical HTTP client libraries do." if args.keepalive else "Every request opens and closes its own connection, the worst case for a client. On Windows, tens of thousands of these in a few minutes can exhaust the machine's ports and cause timeouts that are not the gateway's fault; space runs out or use keep-alive."),
    ]
    host = urlparse(base_url).hostname or ""
    if host in ("127.0.0.1", "localhost", "::1"):
        notes.append("Client and gateway ran on the same machine and shared its CPU, so these figures describe that setup, not a deployed service.")
    notes.append("The gateway ran in local mode unless stated otherwise: in-memory ledger and keyword safety check, with no Azure services in the path.")
    if args.unsafe_percent:
        notes.append(f"{args.unsafe_percent}% of agents sent an unsafe request; how many are rejected depends on the gateway's safety check.")
    return notes


# --------------------------------------------------------------------------- CLI
def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load-test the Loom gateway.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--agents", default="100,1000,10000", help="Comma-separated run sizes (default 100,1000,10000).")
    parser.add_argument("--concurrency", type=int, default=200, help="Requests in flight at once from this client (default 200).")
    parser.add_argument("--resources", type=int, default=1, help="Resources the agents compete for; expect one winner per resource (default 1).")
    parser.add_argument("--unsafe-percent", type=float, default=0.0, help="Share of agents sending an unsafe request (default 0).")
    parser.add_argument("--rounds", type=int, default=1, help="Repeat each run size this many times with fresh resources (default 1).")
    parser.add_argument("--timeout", type=float, default=30.0, help="Per-request timeout in seconds (default 30).")
    parser.add_argument("--seed", type=int, default=1, help="Seed for agent order and unsafe selection (default 1).")
    parser.add_argument("--warmup", type=int, default=20, help="Warm-up requests before measuring (default 20).")
    parser.add_argument("--no-keepalive", dest="keepalive", action="store_false", help="Open a new connection for every request (default: reuse connections).")
    parser.add_argument("--pause", type=float, default=2.0, help="Seconds to pause between runs so sockets can drain (default 2).")
    parser.add_argument("--label", default="local gateway")
    parser.add_argument("--output-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "results"))
    parser.add_argument("--report", default=None, help="Also write the Markdown report to this path.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero if the one-winner rule breaks or any request fails.")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    try:
        levels = [int(part) for part in args.agents.split(",") if part.strip()]
    except ValueError:
        print("--agents must be a comma-separated list of whole numbers", file=sys.stderr)
        return 2
    if not levels or any(level <= 0 for level in levels) or args.resources <= 0 or args.rounds <= 0 or args.concurrency <= 0:
        print("agents, resources, rounds and concurrency must all be positive", file=sys.stderr)
        return 2
    if args.resources > min(levels):
        print("--resources cannot exceed the smallest run size", file=sys.stderr)
        return 2

    parsed = urlparse(args.base_url)
    use_tls = parsed.scheme == "https"
    host = parsed.hostname
    port = parsed.port or (443 if use_tls else 80)
    if not host:
        print("--base-url must look like http://host:port", file=sys.stderr)
        return 2
    target = (host, port, use_tls)

    healthy, detail = check_health(host, port, use_tls, min(args.timeout, 10))
    if not healthy:
        print(f"Cannot start: {detail}\nStart the gateway first (python -m core.api.server).", file=sys.stderr)
        return 2

    if args.warmup > 0:
        warm_rng = random.Random(0)
        for packet in build_packets(args.warmup, 1, 0.0, f"warm{int(time.time())}", warm_rng):
            wire = {k: v for k, v in packet.items() if k != "_unsafe"}
            send_packet(host, port, use_tls, wire, args.timeout, args.keepalive)
        close_all_connections()

    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    runs: List[Dict[str, Any]] = []
    print(f"Load test against {args.base_url}: sizes {levels}, in flight {args.concurrency}, resources {args.resources}, rounds {args.rounds}")
    for agents in levels:
        for round_number in range(1, args.rounds + 1):
            run_id = f"{stamp}-{agents}-{round_number}"
            result = run_level(target, agents, args.concurrency, args.resources, args.unsafe_percent, args.timeout, args.seed + round_number, run_id, args.keepalive)
            result["round"] = round_number
            runs.append(result)
            lat = result["latency_ms"]
            print(
                f"  {agents:>6} agents, round {round_number}: {result['elapsed_s']}s, {fmt(result['throughput_rps'])} req/s, "
                f"p50 {fmt(lat['p50'])} ms, p95 {fmt(lat['p95'])} ms, p99 {fmt(lat['p99'])} ms, "
                f"201={result['status_counts'].get('201', 0)} 409={result['status_counts'].get('409', 0)} errors={result['errors']}, "
                f"one-winner rule {'held' if result['one_winner_rule_held'] else 'BROKEN'}"
            )
            time.sleep(args.pause)

    report = {
        "meta": {
            "label": args.label,
            "started_at": started_at,
            "base_url": args.base_url,
            "command": sanitize_command(argv if argv is not None else sys.argv[1:]),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "cpus": os.cpu_count(),
            "git_commit": git_commit(),
            "resources": args.resources,
            "concurrency": args.concurrency,
            "keepalive": args.keepalive,
            "timeout_s": args.timeout,
            "seed": args.seed,
            "notes": build_notes(args.base_url, args),
        },
        "runs": runs,
    }

    os.makedirs(args.output_dir, exist_ok=True)
    json_path = os.path.join(args.output_dir, f"loadtest-{stamp}.json")
    md_path = os.path.join(args.output_dir, f"loadtest-{stamp}.md")
    markdown = render_markdown(report)
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(markdown)
    print(f"Wrote {json_path}\nWrote {md_path}")
    if args.report:
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as handle:
            handle.write(markdown)
        print(f"Wrote {args.report}")

    if args.check:
        broken = [run for run in runs if not run["one_winner_rule_held"] or run["errors"]]
        if broken:
            print(f"CHECK FAILED: {len(broken)} run(s) broke the one-winner rule or had failed requests", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
