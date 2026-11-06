# Loom load test: local gateway, one resource

Run on 2026-11-06 05:02:06 UTC against `http://127.0.0.1:8095`.

## Setup

- Machine: Windows-11-10.0.26300-SP0, Python 3.14.4, 32 logical CPUs
- Gateway commit (client checkout): `aa2a74e`
- Command: `python loadtest/run_load_test.py --base-url http://127.0.0.1:8095 --agents 100,1000,10000 --rounds 3 --concurrency 200 --label 'local gateway, one resource'`
- Scenario: each agent sends one handshake; 1 resource(s), agents are spread evenly across them
- Client in-flight limit: 200; connections reused (keep-alive); per-request timeout 30.0 s; seed 1

## Results

| Agents | In flight | Resources | Round | Time (s) | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | Max (ms) | 201 | 409 | 403 | 429 | Errors | One-winner rule |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 100 | 100 | 1 | 1 | 0.074 | 1343.4 | 3.64 | 32.61 | 34.24 | 34.49 | 1 | 99 | 0 | 0 | 0 | held |
| 100 | 100 | 1 | 2 | 0.085 | 1181.7 | 4.05 | 13.37 | 31.92 | 32.25 | 1 | 99 | 0 | 0 | 0 | held |
| 100 | 100 | 1 | 3 | 0.098 | 1024.2 | 5.72 | 28.14 | 35.59 | 40.76 | 1 | 99 | 0 | 0 | 0 | held |
| 1000 | 200 | 1 | 1 | 0.742 | 1348.1 | 10.01 | 31.12 | 113.01 | 163.0 | 1 | 999 | 0 | 0 | 0 | held |
| 1000 | 200 | 1 | 2 | 0.87 | 1150.0 | 10.74 | 52.17 | 225.56 | 365.78 | 1 | 999 | 0 | 0 | 0 | held |
| 1000 | 200 | 1 | 3 | 0.724 | 1380.9 | 10.08 | 34.41 | 116.31 | 181.38 | 1 | 999 | 0 | 0 | 0 | held |
| 10000 | 200 | 1 | 1 | 6.881 | 1453.3 | 24.54 | 106.03 | 337.34 | 1180.28 | 1 | 9999 | 0 | 0 | 0 | held |
| 10000 | 200 | 1 | 2 | 6.479 | 1543.4 | 22.9 | 101.85 | 231.59 | 592.57 | 1 | 9999 | 0 | 0 | 0 | held |
| 10000 | 200 | 1 | 3 | 7.229 | 1383.3 | 22.65 | 139.45 | 298.59 | 946.04 | 1 | 9999 | 0 | 0 | 0 | held |

## Summary

- 100 agents: one-winner rule held in 3 of 3 run(s); 0 failed request(s) in total.
- 1000 agents: one-winner rule held in 3 of 3 run(s); 0 failed request(s) in total.
- 10000 agents: one-winner rule held in 3 of 3 run(s); 0 failed request(s) in total.

## Read this before quoting the numbers

- Latency is measured by the client from just before connecting to the end of the response; it includes queueing at the server.
- 'In flight' is a client-side cap (200). Larger runs queue behind it, so '10,000 agents' means 10,000 requests, not 10,000 simultaneous connections.
- Each worker thread reuses one connection (HTTP keep-alive), as typical HTTP client libraries do.
- Client and gateway ran on the same machine and shared its CPU, so these figures describe that setup, not a deployed service.
- The gateway ran in local mode unless stated otherwise: in-memory ledger and keyword safety check, with no Azure services in the path.
