# Loom Protocol Python SDK

The Python SDK lets an agent reserve a finite resource through a Loom ATP gateway.

```python
from loom_protocol import LoomClient

client = LoomClient("http://127.0.0.1:8080", shared_secret="dev-secret")
result = client.reserve(
    agent_id="SHOPPING-AGENT-42",
    resource_id="DROP-SURFACE-001",
    intent="Purchase one Surface Pro from the limited drop",
)
print(result)
```

When `shared_secret` is set, the SDK signs packets with HMAC-SHA256 and includes a nonce and timestamp for replay protection.
