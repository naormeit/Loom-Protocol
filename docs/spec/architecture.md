# Loom Protocol: N-Tier Cloud Architecture

[cite_start]Loom is architected as an enterprise-grade middleware to prevent agentic collision.

## 1. Architecture Layers
* [cite_start]**Tier 1: Ingress (Azure AI Foundry)**: Captures raw agent intent and translates it into ATP packets[cite: 172].
* [cite_start]**Tier 2: Logic (Azure Functions)**: Processes the "Atomic Handshake" and checks for resource conflicts[cite: 175].
* [cite_start]**Tier 3: Data (Azure Cosmos DB)**: A globally distributed ledger that handles sub-10ms resource locking[cite: 175].

## 2. Data Flow
1. **Intent Submission**: Agent sends a request to the Loom Ingress.
2. [cite_start]**Safety Scrub**: Azure Content Safety verifies the intent is non-malicious[cite: 172].
3. **Atomic Lock**: Loom Kernel attempts to secure a lock on the unique resource hash in Cosmos DB.
4. **Execution**: If the lock is successful, the transaction is finalized.