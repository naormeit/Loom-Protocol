# Loom Protocol Overview

Last updated: 2026-08-04

## What Loom Protocol Is

Loom Protocol is an atomic reservation layer for AI agents that compete for scarce resources.

In plain terms, it sits in front of a transaction that could fail under heavy contention, such as buying a limited product, reserving a ticket, claiming inventory, or booking a slot. Instead of letting hundreds or thousands of autonomous agents rush the vendor checkout at the same time, Loom asks them to declare intent first, verifies that intent, and decides who gets the lock.

The goal is not to replace checkout systems or marketplaces. The goal is to give them a reliable pre-transaction decision layer for agent-driven traffic.

## The Problem It Solves

Modern APIs were mostly designed for human-triggered traffic or ordinary application workflows. They were not designed for a world where many autonomous agents can detect the same opportunity and act on it at nearly the same moment.

That creates a predictable failure mode:

- many agents target the same scarce item
- vendor systems receive a burst of near-identical reservation attempts
- duplicate holds, retry storms, and ambiguous state become likely
- losing agents do not receive a machine-friendly path forward

Loom Protocol is meant to reduce that chaos by resolving the conflict before the final transaction step.

## The First Wedge

The current MVP is intentionally narrow.

Loom starts with limited-inventory agent commerce:

- a scarce product drop opens
- many shopping agents attempt to claim the same item
- each agent submits an ATP packet to Loom
- Loom returns one winner with a lock
- the remaining agents receive a structured conflict response with retry guidance

This wedge matters because it makes the value obvious. A judge, developer, or marketplace operator can immediately understand why concurrency control, safety checks, and machine-readable negotiation matter here.

## How It Works

At the center of the project is the ATP handshake flow.

1. An agent or SDK sends a packet to `POST /v1/handshake`.
2. Loom validates the packet shape.
3. Loom verifies authority when signature mode is enabled.
4. Loom parses and normalizes intent.
5. Loom screens the intent for unsafe behavior.
6. Loom attempts an atomic lock on the target resource.
7. Loom returns a result:
   `201` for lock secured, `409` for conflict negotiation, `403` for unsafe intent, `401` for authority failure, or `400` for invalid input.

The important point is that Loom is not just a lock service. It combines intent, safety, authority, and atomic state resolution in a single transaction gate designed for agent traffic.

## Why The Project Exists

The long-term thesis behind Loom is that autonomous agents will increasingly interact with real-world transactional systems. When they do, there must be a trustworthy coordination layer between agent intent and scarce resources.

Without that layer, the ecosystem will inherit brittle behavior:

- overbooking
- duplicated reservations
- wasteful retries
- poor auditability
- unclear failure handling
- unsafe or unauthorized transaction attempts

Loom is an attempt to define that missing layer as protocol infrastructure.

## What Exists Today

The repository already contains a working local proof of the core idea.

Implemented locally today:

- ATP packet validation
- local handshake kernel
- local HTTP API gateway
- local intent parser and content-safety checker
- optional packet signing with replay protection
- local atomic ledger with one-winner behavior
- Python SDK client
- tests for API behavior, safety, signing, replay protection, and conflict handling
- scenario and stress-style demos for limited inventory collisions

This means the project is not just slides or architecture intent. The local protocol behavior is real and testable.

## What Is Planned Next

The production path is larger than the current local proof.

Planned production direction:

- Azure OpenAI or Azure AI Foundry for structured intent parsing
- Azure AI Content Safety for risk screening
- Azure Cosmos DB for globally distributed conditional locks
- Azure Functions or Azure Container Apps for hosted API delivery
- Microsoft Entra ID for enterprise identity and authority verification

As of 2026-08-04, those services are part of the intended production path, but they should not be described as fully proven live deployment until credentials, cloud resources, and integration validation are completed.

## What Loom Protocol Is Not

It is useful to be precise about what the project is not.

Loom is not:

- a consumer shopping app
- a marketplace itself
- a final checkout replacement
- a generic distributed lock wrapper with no domain logic
- a proof that every agent transaction on the internet should route through one system

It is middleware and protocol infrastructure for a specific class of high-contention, agent-driven transactions.

## Why It Matters For Imagine Cup

For competition purposes, Loom has a strong shape when presented honestly:

- the problem is concrete
- the Microsoft cloud path is meaningful
- the demo is easy to understand
- the technical proof can be measured
- the long-term ambition is larger than the first wedge

That combination is important. The project becomes more credible when it does not claim universal infrastructure on day one, but instead proves one painful workflow well.

## Short Version

Loom Protocol is a pre-transaction coordination layer for AI agents competing over scarce resources.

Its first job is simple:
when many agents want the same limited item, Loom decides who gets the lock, rejects unsafe or unauthorized attempts, and gives the losers a structured response instead of a broken checkout race.
