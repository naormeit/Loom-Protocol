# Load test results

Measured on 6 Nov 2026 with the harness in [`loadtest/`](../../loadtest/run_load_test.py). **Everything here is the local gateway, in local mode, on one Windows machine that also ran the load generator.** No Azure services were in the path. Read the limits at the end before quoting any number.

## What the tests show

- **The one-winner rule held in every run.** Across all 22 saved runs, from 100 to 10,000 agents, exactly one agent got each lock and every other agent got a conflict answer. With agents spread across 50 resources, there were exactly 50 winners (at 1,000 and at 10,000 agents). With 10% of agents sending an unsafe request, 100 of 100 were rejected and one agent still won.
- **With the final gateway there were no failed requests,** at any size, in any saved run.
- **Final speed (one resource, connections reused, three rounds each):**

| Agents | Time per run | Requests per second | p50 | p95 | p99 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 0.07 to 0.10 s | 1,024 to 1,343 | 4 to 6 ms | 13 to 33 ms | 32 to 36 ms |
| 1,000 | 0.72 to 0.87 s | 1,150 to 1,381 | 10 to 11 ms | 31 to 52 ms | 113 to 226 ms |
| 10,000 | 6.5 to 7.2 s | 1,383 to 1,543 | 23 to 25 ms | 102 to 139 ms | 232 to 337 ms |

The full tables are in [`load_test_2026-11-06_one-resource.md`](load_test_2026-11-06_one-resource.md), with the 50-resource run in [`..._50-resources.md`](load_test_2026-11-06_50-resources.md), the unsafe mix in [`..._unsafe-mix.md`](load_test_2026-11-06_unsafe-mix.md), and the worst-case client (a new connection for every request) in [`..._new-connection-per-request.md`](load_test_2026-11-06_new-connection-per-request.md). Raw data is in [`data/`](data/).

## What the load test found, and what changed

The first run showed the gateway was not ready for a burst, even though the locking itself was correct.

| Run (same 200-in-flight client, same machine) | 100 agents | 1,000 agents | 10,000 agents |
| --- | --- | --- | --- |
| **Before:** Python's default connection queue (5 waiting connections), new connection per request | 2.1 s, p95 1,545 ms | 2.8 s, p95 2,039 ms, **12 refused (1.2%)** | 22.3 s, p95 1,556 ms, **1,104 refused (11.0%)** |
| **After fix 1:** connection queue of 1,024 | 0.09 s, p95 30 ms | 0.69 s, p95 136 ms, no errors | 21.9 s, p95 877 ms, no errors, about 456 requests per second |
| **After fix 2:** connection reuse (HTTP/1.1 keep-alive) | 0.07 to 0.10 s | 0.72 to 0.87 s | 6.5 to 7.2 s, about 1,400 to 1,500 requests per second |

1. **Refused connections.** Every failure in the first run was "connection refused". The standard server holds only 5 waiting connections, so a burst overflowed it, and the clients that did get through after a retry waited 1 to 2 seconds. The gateway now uses a server class with a queue of 1,024 (`LoomHTTPServer`).
2. **Port exhaustion from one connection per request.** The gateway closed the connection after every answer, so 10,000 requests meant 10,000 connections. On this machine, after about 20,000 connections in a few minutes, the connection table still listed about 10,000 entries for the gateway's port, against a default dynamic port range of 16,384, and two of ten back-to-back 1,000-agent rounds timed out ([data](data/back-to-back-rounds.json)). Real HTTP client libraries reuse connections, so the gateway now supports HTTP/1.1 keep-alive (idle connections are dropped after 15 seconds) and the harness reuses connections by default. At 10,000 agents that is about three times the throughput and a p95 about six to eight times lower than fix 1 alone.

The "before" and "after fix 1" runs are single runs from one session; the final numbers are three rounds each. Repeated runs vary by roughly 15 to 20% in speed, so the order of magnitude is the point, not the exact figures.

## Limits: what this does not show

- **One machine.** The load generator and the gateway shared the same CPU, so both were slower than they would be on separate machines. A deployed gateway will behave differently.
- **Local mode only.** The ledger was in memory and the safety check was the keyword list. The real test of "exactly one winner" across servers is Cosmos DB, which has not been load-tested. Azure OpenAI and Content Safety calls will add latency that is not in these numbers.
- **One gateway process.** Rate limits and the replay cache are per process; nothing here tests several instances.
- **In flight is not simultaneous.** Runs used a cap of 200 requests in flight. "10,000 agents" means 10,000 requests, not 10,000 simultaneous connections.
- **Short runs.** The longest run took about 22 seconds. Memory growth, CPU use and long-term stability were not measured.
- **Output noise.** The gateway prints several lines per request. Its output was sent to a file, which is how CI runs it; an interactive console would be slower.
- **No network, no encryption.** Traffic stayed on the loopback interface, without TLS.
- **No cost figure yet.** Cost per lock needs the live Azure deployment, so the pricing note's cost blank is still empty.

## Run it yourself

```powershell
python -m core.api.server                       # one terminal
python loadtest/run_load_test.py --agents 100,1000,10000 --rounds 3
python loadtest/run_load_test.py --agents 1000,10000 --resources 50
python loadtest/run_load_test.py --agents 1000 --unsafe-percent 10
python loadtest/run_load_test.py --agents 100,1000 --no-keepalive
```

Add `--check` to exit non-zero if the one-winner rule breaks or any request fails, `--report path.md` to also write the Markdown report somewhere, and `--base-url` to point at a hosted gateway. Results are written to `loadtest/results/` (ignored by git). When the gateway is deployed on Azure, run the same command against its address, and use Azure Load Testing for larger loads.
