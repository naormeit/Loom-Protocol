# Loom load test: local gateway, new connection per request

Run on 2026-11-06 05:04:13 UTC against `http://127.0.0.1:8095`.

## Setup

- Machine: Windows-11-10.0.26300-SP0, Python 3.14.4, 32 logical CPUs
- Gateway commit (client checkout): `aa2a74e`
- Command: `python loadtest/run_load_test.py --base-url http://127.0.0.1:8095 --agents 100,1000 --rounds 2 --concurrency 200 --no-keepalive --label 'local gateway, new connection per request'`
- Scenario: each agent sends one handshake; 1 resource(s), agents are spread evenly across them
- Client in-flight limit: 200; connections opened per request; per-request timeout 30.0 s; seed 1

## Results

| Agents | In flight | Resources | Round | Time (s) | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | Max (ms) | 201 | 409 | 403 | 429 | Errors | One-winner rule |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 100 | 100 | 1 | 1 | 0.118 | 847.1 | 30.63 | 53.2 | 54.91 | 55.62 | 1 | 99 | 0 | 0 | 0 | held |
| 100 | 100 | 1 | 2 | 0.232 | 431.9 | 40.25 | 142.6 | 145.13 | 146.61 | 1 | 99 | 0 | 0 | 0 | held |
| 1000 | 200 | 1 | 1 | 2.656 | 376.5 | 340.47 | 674.68 | 727.9 | 731.02 | 1 | 999 | 0 | 0 | 0 | held |
| 1000 | 200 | 1 | 2 | 1.506 | 664.0 | 278.27 | 401.93 | 783.57 | 795.07 | 1 | 999 | 0 | 0 | 0 | held |

## Summary

- 100 agents: one-winner rule held in 2 of 2 run(s); 0 failed request(s) in total.
- 1000 agents: one-winner rule held in 2 of 2 run(s); 0 failed request(s) in total.

## Read this before quoting the numbers

- Latency is measured by the client from just before connecting to the end of the response; it includes queueing at the server.
- 'In flight' is a client-side cap (200). Larger runs queue behind it, so '10,000 agents' means 10,000 requests, not 10,000 simultaneous connections.
- Every request opens and closes its own connection, the worst case for a client. On Windows, tens of thousands of these in a few minutes can exhaust the machine's ports and cause timeouts that are not the gateway's fault; space runs out or use keep-alive.
- Client and gateway ran on the same machine and shared its CPU, so these figures describe that setup, not a deployed service.
- The gateway ran in local mode unless stated otherwise: in-memory ledger and keyword safety check, with no Azure services in the path.
