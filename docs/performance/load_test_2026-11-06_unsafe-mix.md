# Loom load test: local gateway, 10 percent unsafe

Run on 2026-11-06 05:03:12 UTC against `http://127.0.0.1:8095`.

## Setup

- Machine: Windows-11-10.0.26300-SP0, Python 3.14.4, 32 logical CPUs
- Gateway commit (client checkout): `aa2a74e`
- Command: `python loadtest/run_load_test.py --base-url http://127.0.0.1:8095 --agents 1000 --concurrency 200 --unsafe-percent 10 --label 'local gateway, 10 percent unsafe'`
- Scenario: each agent sends one handshake; 1 resource(s), agents are spread evenly across them
- Client in-flight limit: 200; connections reused (keep-alive); per-request timeout 30.0 s; seed 1

## Results

| Agents | In flight | Resources | Round | Time (s) | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | Max (ms) | 201 | 409 | 403 | 429 | Errors | One-winner rule |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1000 | 200 | 1 | 1 | 0.654 | 1528.2 | 10.17 | 203.77 | 441.86 | 468.25 | 1 | 899 | 100 | 0 | 0 | held |

## Summary

- 1000 agents: one-winner rule held in 1 of 1 run(s); 0 failed request(s) in total.

## Read this before quoting the numbers

- Latency is measured by the client from just before connecting to the end of the response; it includes queueing at the server.
- 'In flight' is a client-side cap (200). Larger runs queue behind it, so '10,000 agents' means 10,000 requests, not 10,000 simultaneous connections.
- Each worker thread reuses one connection (HTTP keep-alive), as typical HTTP client libraries do.
- Client and gateway ran on the same machine and shared its CPU, so these figures describe that setup, not a deployed service.
- The gateway ran in local mode unless stated otherwise: in-memory ledger and keyword safety check, with no Azure services in the path.
- 10.0% of agents sent an unsafe request; how many are rejected depends on the gateway's safety check.
