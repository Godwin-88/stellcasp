# Zero-Knowledge Compliance Oracle for Regulated Finance — Platform Specification

**Document Type:** Product Requirements Specification (Epics, Features, User Stories, Acceptance Criteria)
**Target Submissions:** Casper Agentic Buildathon 2026 (Jul 8) · Stellar Hacks: Real-World ZK (Jul 3)
**Enterprise Architecture Reference:** Digital Capability Canvas v3 (DICM Framework)
**Author:** Ed Godwin · AI Engineer & Digital Transformation Consultant
**Date:** 1 July 2026
**Version:** 2.0 — Augmented for Stellar Competitive Positioning

---

## Platform Overview

The **Zero-Knowledge Compliance Oracle** (ZKCO) is the world's first AI-native, graph-intelligence-driven compliance oracle that allows regulated financial protocols to consume compliance decisions without ever accessing customer PII. Rather than building another KYC system, ZKCO builds **compliance infrastructure** — a shared oracle layer that any DeFi protocol, DEX, lending platform, RWA tokenizer, payroll system, or remittance corridor can query to gate access using a single, portable, reusable Compliance Passport.

**Core Innovation:** The platform's genuine differentiation is not KYC itself — it is *proving that a multi-factor, AI-driven compliance decision is correct without revealing any of the underlying financial intelligence that produced it.* Graph topology, risk weights, regulatory rule application, and entity identity all remain private. What the blockchain sees is only: "this wallet satisfies the required compliance policy."

**Stellar Positioning:** For the Stellar Hacks: Real-World ZK submission, ZKCO addresses three Stellar idea categories simultaneously: (1) **Verifiable Off-Chain Computation** — graph analytics and AI produce the compliance decision entirely off-chain; Noir proves the computation satisfies required policy; (2) **Private Credential / Reputation** — the verified result is minted as a reusable Compliance Passport token that any Stellar protocol can verify without re-running KYC; (3) **Compliant Private Transfer with Selective Disclosure** — the credential supports selective disclosure so regulated institutions can audit when required while preserving user privacy by default. Stellar is not merely a verification layer here — it is the trust anchor that makes the compliance credential portable, composable, and ecosystem-wide.

**Architecture Summary**

```
[Entity / Wallet Input]
        ↓
[Graph Intelligence Layer]
  Neo4j Aura + NetworkX
  PageRank · Louvain · Betweenness Centrality
  Node2Vec Embeddings (behavioural manifold)
        ↓
[Multi-Factor Financial Risk Engine]
  L: Liquidity Risk       w1
  C: Counterparty Risk    w2
  J: Jurisdiction Risk    w3
  S: Sanctions Exposure   w4
  A: AML Topology Risk    w5
  B: Behavioural Risk     w6
  ─────────────────────────────
  Compliance Index CI = Σ(wᵢ × Fᵢ)  [private]
        ↓
[ZK Proof Layer — Noir Circuit]
  prove: CI < threshold
  AND: wallet ∈ low-risk behavioural manifold
  AND: jurisdiction ∈ permitted_set
  WITHOUT revealing: weights, factors, graph, entity
        ↓
      ┌───────────────────────────────────────┐
      │                                       │
[Stellar Soroban]                  [Casper Odra Contracts]
ZK Verifier Contract               ComplianceOracle + IdentityRegistry
Compliance Passport Mint           Compliance Token (CSPR)
  → DEX · Lending · RWA · Payroll  x402 Micropayment Gate
  → Remittance · Any Protocol
(Stellar primary submission)       (Casper primary submission)
      └───────────────────────────────────────┘
        ↓
[LangGraph Specialist Agent Pipeline]
  Intelligence Agent → Compliance Agent → ZK Agent
  → Settlement Agent → Auditor Agent
[LLM]   Groq API (Llama 3.3 70B) — free tier
[API]   FastAPI REST gateway
```

**Canvas Domain Alignment (DICM)**

| Canvas Domain | Platform Layer |
|---|---|
| Manage Digital Intelligence → Compliance Intelligence (GRC) | Graph Risk Engine |
| Manage Digital Security → Identity & Access Security | ZK Identity Credential |
| Manage Digital Inter-Operability & Automation → Blockchain Infrastructure | On-Chain Verifiability |
| Manage Digital Inter-Operability & Automation → API Integration | FastAPI + x402 Gateway |
| Manage Digital Intelligence → Cognitive Intelligence | Agentic Orchestration |
| Manage Digital GPRC → Enterprise Compliance | Compliance Governance |
| Manage Digital IT → Data Lifecycle | Data Design & Security |

---

## Epic Index

| # | Epic | Canvas Capability Anchor | Chain Target |
|---|---|---|---|
| EP-01 | Graph Intelligence & Multi-Factor Financial Risk Engine | Compliance Intelligence (GRC), AML & CFT Enforcement, Finance Analytics | Shared Core |
| EP-02 | Zero-Knowledge Compliance Oracle Circuit | Identity & Access Security, Cryptographic Keys/Signatures, Data Privacy Governance | **Stellar (primary)** |
| EP-03 | Stellar Compliance Passport & Protocol Gateway | Accountability & Verifiability, Blockchain & Transaction Integrity, Customer Asset Wallet | **Stellar (primary)** |
| EP-04 | Casper ComplianceOracle & On-Chain Verifiability | Manage Accountability & Verifiability, IdentityRegistry, Contract Lifecycle | Casper |
| EP-05 | API Gateway & Micropayment Rail | API Lifecycle, API Gateway, Payment Rail Operations | Casper (x402) |
| EP-06 | Specialist Agentic Compliance Orchestration | Cognitive Intelligence, Machine Learning, Deep Learning | Shared Core |
| EP-07 | Data Governance & Security Lifecycle | Data Protection & Privacy, Security Event Logging | Shared Core |

---

## EP-01 — Graph Intelligence & Multi-Factor Financial Risk Engine

**Canvas Capability Anchor:**
- Manage Digital Intelligence → Horizontal Intelligence → **Compliance Intelligence (GRC)** → Manage Incident Detection
- Manage Digital Intelligence → Horizontal Intelligence → **Manage AML & CFT Enforcement**
- Manage Digital Intelligence → Vertical Intelligence → **Manage Customer Analytics**, **Manage Finance Analytics**
- Manage Digital GPRC → Manage Enterprise Compliance → **Manage Compliance Monitoring**
- Manage Digital Intelligence → Intelligence Infrastructure → **Manage Diagnostic Analytics** → Manage Root Cause Isolation
- Manage Digital Intelligence → Intelligence Infrastructure → **Manage Cognitive Intelligence** → Manage Machine Learning Intelligence

**Epic Description:**
Implement a multi-layer graph intelligence pipeline using Neo4j Aura Free and NetworkX that produces a six-factor Compliance Index (CI) rather than a single scalar risk score. The CI is a weighted sum of independent financial risk dimensions — Liquidity Risk, Counterparty Risk, Jurisdiction Risk, Sanctions Exposure, AML Topology Risk, and Behavioural Risk — each derived from graph-structural computations. This multi-factor model is what the ZK circuit proves, making the proof statement far stronger than a single threshold check and positioning the platform as genuine financial engineering infrastructure. The CI is the private input to the Noir circuit; weights and factor values are never exposed on-chain.

---

### F-01.1 — Entity Graph Construction

**Description:** Ingest entity/wallet data and build a relationship graph in Neo4j Aura representing transaction flows, counterparty relationships, and behavioural attributes.

#### US-01.1.1 — Entity Node Ingestion
> *As a compliance analyst, I want to submit an entity identifier (wallet address or national ID hash) so that the system creates or updates a node in the compliance graph.*

**Acceptance Criteria:**
- Given a valid wallet address or hashed entity ID, a POST to `/api/v1/entity` creates or upserts a `:Entity` node in Neo4j Aura with attributes `{id, type, created_at, updated_at}`.
- The endpoint returns HTTP 201 on creation and HTTP 200 on upsert, with the node ID and timestamp in the response body.
- Duplicate submissions within a 60-second window are deduplicated and do not create phantom nodes.
- Invalid input (missing ID, malformed address) returns HTTP 422 with a structured error body indicating the failing field.

#### US-01.1.2 — Transaction Relationship Mapping
> *As a risk analyst, I want the system to map transaction relationships between entities so that the graph reflects real-world economic connectivity.*

**Acceptance Criteria:**
- A POST to `/api/v1/relationship` accepts `{source_id, target_id, amount, currency, timestamp, tx_hash}` and creates a `[:TRANSACTED_WITH {amount, currency, timestamp, tx_hash}]` relationship in Neo4j.
- Relationships with amounts equal to zero are rejected with HTTP 400 and the error message `"Zero-value transactions are not indexed"`.
- A bulk ingestion endpoint `/api/v1/relationships/batch` accepts up to 1,000 relationship objects per request and processes them within 10 seconds on a free-tier Neo4j Aura instance.
- All created relationships are retrievable via `GET /api/v1/entity/{id}/relationships` within 5 seconds of creation.

#### US-01.1.3 — Graph Data Validation & Schema Enforcement
> *As a platform operator, I want the graph schema to enforce node and relationship constraints so that data quality is maintained without GDS or enterprise plugins.*

**Acceptance Criteria:**
- The Neo4j schema enforces a uniqueness constraint on `Entity.id` and a composite index on `(source_id, target_id, tx_hash)` on the TRANSACTED_WITH relationship.
- Attempts to insert duplicate entity IDs update the existing node rather than throwing a constraint error.
- A health-check endpoint `GET /api/v1/graph/health` returns node count, relationship count, and Neo4j Aura connection status with a response time under 2 seconds.
- Schema migration scripts are version-controlled in `/migrations/` and are idempotent when run multiple times.

---

### F-01.2 — Network Risk Score Computation

**Description:** Implement graph algorithms via NetworkX (loaded from Neo4j subgraph exports) to compute a composite Network Risk Score (NRS) between 0.0 and 1.0 for any entity.

#### US-01.2.1 — PageRank-Based Influence Scoring
> *As a risk engine, I want to compute PageRank over the transaction graph so that highly connected entities receive proportionally elevated risk signals.*

**Acceptance Criteria:**
- The system exports the subgraph for a queried entity (up to 3 hops) from Neo4j via Cypher and loads it into a NetworkX DiGraph within 3 seconds for graphs of up to 500 nodes.
- `nx.pagerank()` executes with `alpha=0.85` and `max_iter=100` and returns a per-node score dictionary without raising a convergence error.
- The PageRank score for the queried entity is normalised to range [0.0, 1.0] using min-max scaling across the returned subgraph.
- If the entity has fewer than 3 neighbours, a minimum floor score of 0.05 is assigned and logged with reason `"insufficient_graph_density"`.

#### US-01.2.2 — Community Detection for Cluster Risk
> *As a compliance analyst, I want to detect communities of high-risk entities so that cluster-level sanctions can be applied efficiently.*

**Acceptance Criteria:**
- `nx.community.louvain_communities()` is applied to the undirected projection of the subgraph and returns at least one community partition.
- If the queried entity belongs to a community where more than 30% of nodes have a PageRank above the 90th percentile, the community_risk_flag is set to `True`.
- Community assignment is persisted to Neo4j as a node property `community_id` and updated on every NRS computation.
- Community detection completes within 5 seconds for subgraphs of up to 1,000 nodes.

#### US-01.2.3 — Composite NRS Aggregation
> *As a risk engine, I want to combine PageRank, community risk, and betweenness centrality into a single NRS float so that downstream ZK circuits receive a single comparable input.*

**Acceptance Criteria:**
- NRS is computed as a weighted sum: `NRS = 0.4 * pagerank_score + 0.35 * betweenness_score + 0.25 * community_risk_score`, all normalised to [0.0, 1.0].
- The NRS value and its component breakdown are returned in the API response body under the key `nrs_details`.
- A `GET /api/v1/entity/{id}/nrs` endpoint returns the cached NRS if it was computed within the last 60 minutes, or triggers a fresh computation otherwise.
- NRS computation results are written to a PostgreSQL audit table `nrs_computations` with columns `{entity_id, nrs, components_json, computed_at, triggered_by}`.

---

### F-01.3 — AML Incident Detection

**Description:** Trigger compliance incident flags when NRS exceeds configurable thresholds or when specific graph structural anomalies are detected.

#### US-01.3.1 — Threshold-Based Incident Alerting
> *As a compliance officer, I want to be alerted when an entity's NRS crosses a configurable high-risk threshold so that manual review can be triggered promptly.*

**Acceptance Criteria:**
- A configurable threshold `HIGH_RISK_NRS_THRESHOLD` (default `0.75`) is set via environment variable and read at service startup.
- When NRS ≥ `HIGH_RISK_NRS_THRESHOLD`, the system writes an incident record to `compliance_incidents` table with status `PENDING_REVIEW` and sends a webhook POST to the configured `ALERT_WEBHOOK_URL` within 10 seconds.
- If the webhook call fails, the system retries up to 3 times with exponential back-off (1s, 2s, 4s) before marking the incident `ALERT_FAILED`.
- The compliance officer can query open incidents via `GET /api/v1/incidents?status=PENDING_REVIEW` with pagination (limit/offset).

#### US-01.3.2 — Anomalous Structural Pattern Detection
> *As a risk analyst, I want the system to flag structurally anomalous patterns (star topologies, rapid fan-out) so that smurfing and layering behaviours are surfaced automatically.*

**Acceptance Criteria:**
- The system computes out-degree for each entity's 1-hop neighbourhood; if any single entity fans out to more than 20 unique recipients within a 24-hour window, a `STRUCTURAL_ANOMALY` flag is set.
- Anomaly detection runs as a scheduled task every 6 hours and processes all entities modified in the preceding window.
- Flagged entities are tagged with `anomaly_type` in Neo4j and included in the AML Topology Risk factor as a +0.15 additive penalty capped at 1.0.
- Anomaly detection results are retrievable per entity via `GET /api/v1/entity/{id}/anomalies`.

---

### F-01.4 — Multi-Factor Compliance Index (CI) Computation

**Description:** Aggregate graph-derived signals into six independent financial risk factors and combine them into a single Compliance Index using configurable weights. This replaces the single NRS scalar with an investment-grade multi-factor model — the actual private witness fed into the ZK circuit.

#### US-01.4.1 — Six-Factor Risk Decomposition
> *As a financial engineer, I want the compliance decision to be derived from six independent risk factors so that the ZK proof statement reflects a genuine multi-dimensional regulatory assessment rather than a single heuristic score.*

**Acceptance Criteria:**
- The risk engine computes the following six factor scores, each normalised to [0.0, 1.0], for any given entity: **Liquidity Risk (L)** — derived from transaction volume volatility over the trailing 30-day window; **Counterparty Risk (C)** — PageRank-weighted average risk of all 1-hop counterparties; **Jurisdiction Risk (J)** — fraction of counterparties domiciled in FATF grey-list or non-cooperative jurisdictions; **Sanctions Exposure (S)** — betweenness centrality path overlap with known sanctioned-entity nodes; **AML Topology Risk (A)** — Louvain community risk score elevated by structural anomaly flags; **Behavioural Risk (B)** — deviation of transaction pattern from the entity's historical baseline (z-score of recent vs. trailing average).
- Each factor is computed independently and stored in the `risk_factors` table with columns `{entity_id, L, C, J, S, A, B, computed_at}`.
- Factor computation completes within 15 seconds for an entity with up to 500 transactions in the graph.
- A `GET /api/v1/entity/{id}/factors` endpoint returns all six factors with their normalised values.

#### US-01.4.2 — Weighted Compliance Index Aggregation
> *As a ZK circuit consumer, I want to receive a single Compliance Index (CI) float rather than six separate values so that the Noir circuit maintains a simple, auditable proof statement.*

**Acceptance Criteria:**
- CI is computed as `CI = w1*L + w2*C + w3*J + w4*S + w5*A + w6*B` where weights are configurable via environment variables `CI_WEIGHT_L`, `CI_WEIGHT_C`, `CI_WEIGHT_J`, `CI_WEIGHT_S`, `CI_WEIGHT_A`, `CI_WEIGHT_B` and must sum to 1.0 (validated at startup).
- Default weights are `w1=0.10, w2=0.20, w3=0.15, w4=0.25, w5=0.20, w6=0.10` reflecting typical regulatory emphasis on sanctions and counterparty exposure.
- The CI value and full factor breakdown are stored in `compliance_index_computations` table alongside the weight vector used at computation time (immutable audit record).
- **The CI float, individual factors, and weight vector are never returned to external API callers** — only the proof that `CI < threshold` is exposed, preserving the confidentiality of the compliance intelligence model.

#### US-01.4.3 — Jurisdiction Risk Lookup
> *As a compliance engineer, I want jurisdiction risk scores for each counterparty to be derived from a maintained FATF reference list so that the J factor reflects current regulatory designations.*

**Acceptance Criteria:**
- A `jurisdiction_risk` lookup table is seeded from the FATF grey list and OFAC high-risk jurisdiction list at deployment time, with `{iso2_code, risk_score, last_updated}` columns.
- Unknown or missing jurisdictions are assigned a default `risk_score` of 0.5 (neutral) with a `JURISDICTION_UNKNOWN` flag logged to the entity's anomaly record.
- The jurisdiction list is refreshable via `POST /api/v1/admin/jurisdiction/refresh` (admin-only) without requiring a service restart.
- CI recomputation is triggered automatically for any entity with counterparties in a jurisdiction whose risk score changed by more than 0.1 since the last CI computation.

---

### F-01.5 — Graph Embeddings for Behavioural Manifold Classification

**Description:** Augment the structural graph algorithms with Node2Vec-style random-walk embeddings to characterise wallets by their behavioural manifold. This enables the ZK proof to assert "this wallet belongs to a low-risk behavioural cluster" rather than merely "PageRank was low" — a meaningfully stronger cryptographic claim.

#### US-01.5.1 — Node2Vec Embedding Generation
> *As a graph intelligence engineer, I want to compute Node2Vec embeddings for entities in the transaction graph so that behavioural similarity between wallets can be quantified beyond structural centrality metrics.*

**Acceptance Criteria:**
- A Python function `compute_embeddings(graph: nx.Graph, dimensions: int = 64) -> dict` implements a simplified random-walk embedding using `node2vec` (PyPI) or a lightweight custom random-walk + Word2Vec implementation if the library is unavailable.
- Embeddings are computed over the full subgraph (up to 1,000 nodes) and stored as 64-dimensional float vectors in the `entity_embeddings` table with `{entity_id, embedding_vector, computed_at}`.
- Embedding computation completes within 30 seconds for a 500-node subgraph.
- Embeddings are refreshed whenever the entity's subgraph changes by more than 10 new relationships.

#### US-01.5.2 — Low-Risk Manifold Membership Scoring
> *As the ZK proof layer, I want a binary or graded manifold membership score for each entity so that the Noir circuit can assert cluster-level compliance rather than only individual-level threshold compliance.*

**Acceptance Criteria:**
- K-means clustering (k=5, representing Low/Moderate-Low/Moderate/Moderate-High/High risk behavioural clusters) is applied to the 64-dimensional embeddings; cluster centroids are stored in `embedding_clusters` table.
- Each entity is assigned a `cluster_label` and `cluster_risk_level` (0–4) based on cosine distance to the nearest centroid.
- A `manifold_score` — the inverse of cosine distance to the Low-risk centroid — is normalised to [0.0, 1.0] and stored as the Behavioural Risk (B) factor input.
- A `GET /api/v1/entity/{id}/manifold` endpoint returns `{cluster_label, cluster_risk_level, manifold_score}` without returning the raw embedding vector.

---

## EP-02 — Zero-Knowledge Compliance Oracle Circuit

**Canvas Capability Anchor:**
- Manage Digital Security → Manage Identity & Access Security → **Manage Privilege Identity & Access Administration** → Manage Privileged Sessions
- Manage Digital Security → Manage Data Security → **Manage Data Protection & Privacy** → Manage Data Classification
- Manage Digital Experience Orchestration → Manage Experience Governance → **Manage Experience Identity Security**
- Manage Digital Inter-Operability & Automation → Manage Automation Infrastructure (Blockchain) → **Manage Cryptographic Hashes / Keys / Signatures**
- Manage Digital Security → Manage Identity & Access Security → **Manage Client Regulatory Verification**
- Manage Digital Intelligence → Intelligence Infrastructure → **Manage Data & Message Integration**

**Epic Description:**
Implement a Noir ZK circuit that proves a multi-condition compliance policy is satisfied — not merely that a single score is below a threshold. The circuit asserts simultaneously that (1) the Compliance Index is below the policy threshold, (2) the wallet belongs to a low-risk behavioural manifold, and (3) the entity's jurisdiction is in a permitted set. All of: the CI value, individual factor weights, graph topology, and entity identity remain private. Only the compliance policy result is on-chain. A Soroban smart contract on Stellar testnet verifies the proof and issues an on-chain Compliance Passport. This is the **primary Stellar Hacks: Real-World ZK submission** and represents verifiable off-chain computation at the intersection of financial engineering and zero-knowledge cryptography.

---

### F-02.1 — Noir ZK Circuit Design

**Description:** Implement a Noir circuit that proves a three-condition compliance policy is satisfied without revealing the Compliance Index, factor values, weights, or entity identity. The proof statement is: "this wallet satisfies AML, KYC, Sanctions, Jurisdiction, and FATF compliance policy" — not merely that a single number is small.

#### US-02.1.1 — Multi-Condition Compliance Policy Circuit
> *As a ZK engineer, I want to write a Noir circuit that simultaneously proves the Compliance Index is below threshold, the wallet belongs to a low-risk behavioural manifold, and the jurisdiction is permitted — so that the proof constitutes a genuine multi-regulatory compliance attestation.*

**Acceptance Criteria:**
- The Noir circuit in `circuits/src/main.nr` compiles without error using `nargo compile` (Noir ≥ v0.30).
- The circuit signature is:
  ```rust
  fn main(
      compliance_index: u64,           // private: CI × 1_000_000 as u64
      manifold_score: u64,             // private: manifold membership score × 1_000_000
      jurisdiction_flag: u64,          // private: 0 = permitted, 1 = restricted
      ci_threshold: pub u64,           // public: policy CI ceiling
      manifold_threshold: pub u64,     // public: minimum manifold score required
      policy_id: pub Field,            // public: identifier of the compliance policy version
  )
  ```
- The circuit body asserts all three conditions: `assert(compliance_index < ci_threshold)`, `assert(manifold_score >= manifold_threshold)`, `assert(jurisdiction_flag == 0)`.
- `nargo check` passes with zero warnings; the circuit uses no loops or dynamic arrays that would increase constraint count unnecessarily.
- The compiled circuit artefact and constraint count are documented in `circuits/README.md`.

#### US-02.1.2 — Multi-Input Proof Generation Pipeline
> *As a compliance agent, I want to generate a Noir proof for a given entity that encodes all three compliance conditions so that the Stellar verifier receives a comprehensive policy attestation in a single proof.*

**Acceptance Criteria:**
- A Python function `generate_zk_proof(ci: float, manifold_score: float, jurisdiction_flag: int, ci_threshold: float, manifold_threshold: float, policy_id: str) -> dict` scales float inputs to `u64`, constructs a `Prover.toml`, and shells out to `nargo prove`.
- Proof generation completes within 30 seconds on a standard laptop/VPS for the three-assertion circuit defined in F-02.1.1.
- The function returns `{proof_hex: str, public_inputs: list, policy_id: str, generated_at: datetime}` on success; private inputs (`ci`, `manifold_score`, `jurisdiction_flag`) are not included in the return value.
- If `nargo` is not found on PATH, the function raises `ProofGenerationError` with message `"nargo not installed or not on PATH"` rather than a raw subprocess exception.
- The `Prover.toml` file is written to a temporary directory and deleted after proof generation to prevent private witness leakage.

#### US-02.1.3 — Proof Verification (Local)
> *As a developer, I want to verify a generated proof locally before submitting to Stellar so that I can confirm circuit correctness without incurring on-chain costs.*

**Acceptance Criteria:**
- A Python function `verify_proof_local(proof_hex: str, public_inputs: list) -> bool` calls `nargo verify` and returns `True` if verification passes.
- Local verification completes within 10 seconds.
- If verification fails (invalid proof), the function returns `False` and logs the failure with the proof hash and timestamp.
- A CLI entrypoint `python -m zkkyc.prove --entity-id <id>` orchestrates NRS fetch → proof generation → local verification and prints a summary to stdout.

---

### F-02.2 — Soroban Verifier Contract (Stellar)

**Description:** Deploy an UltraHonk verifier contract on Stellar testnet (Soroban) that accepts a Noir proof and public inputs, verifies the proof, and emits an on-chain compliance attestation event.

#### US-02.2.1 — Verifier Contract Deployment
> *As a developer, I want to deploy the UltraHonk Soroban verifier contract to Stellar testnet so that on-chain proof verification is operational for the hackathon submission.*

**Acceptance Criteria:**
- The Soroban verifier contract is compiled from the `rs-soroban-ultrahonk` reference implementation using `cargo build --target wasm32-unknown-unknown --release`.
- The contract is deployed to Stellar testnet using the Stellar CLI; the deployment transaction hash is recorded in `deployments.json`.
- A `stellar contract invoke` call with a valid proof and public inputs returns status `success` within 60 seconds on testnet.
- The contract address is committed to the repository README under the section `Deployments`.

#### US-02.2.2 — On-Chain Compliance Attestation
> *As a DeFi protocol operator, I want the Soroban contract to emit an on-chain attestation event when a proof is valid so that downstream smart contracts can gate access based on compliance status.*

**Acceptance Criteria:**
- Upon successful proof verification, the contract emits a Soroban event `{ topic: ["compliance", "verified"], data: { entity_hash: bytes32, threshold: u64, verified_at: u64 } }`.
- The `entity_hash` is the SHA-256 hash of the entity ID, not the raw ID, ensuring PII is never stored on-chain.
- The attestation event is queryable via the Stellar Horizon API within 30 seconds of transaction confirmation.
- A failed proof verification causes the contract to return an error code `ERR_INVALID_PROOF` without emitting any event.

#### US-02.2.3 — Selective Disclosure API
> *As an end user, I want to present my compliance attestation to a DeFi protocol without revealing which specific KYC attributes were checked so that I retain privacy while proving eligibility.*

**Acceptance Criteria:**
- A `GET /api/v1/entity/{id}/credential` endpoint returns a JSON payload containing `{stellar_tx_hash, entity_hash, threshold_public, verified_at, proof_hex}` — the NRS is not included.
- The endpoint requires the caller to provide an API key that is validated against the `api_keys` table before returning proof data.
- The credential payload is signed with the platform's ED25519 key (loaded from `PLATFORM_SIGNING_KEY` env var) to allow downstream verification of payload integrity.
- Credential payloads older than 24 hours are marked `EXPIRED` and a fresh proof generation is suggested in the response.

---

## EP-03 — Stellar Compliance Passport & Protocol Gateway

**Canvas Capability Anchor:**
- Manage Digital Inter-Operability & Automation → Manage Automation Infrastructure (Blockchain) → **Manage Accountability & Verifiability**
- Manage Digital Inter-Operability & Automation → **Manage Blockchain & Transaction Integrity**
- Manage Digital Experience Orchestration → Manage Customer Interactions → **Manage Customer Asset Wallet** → Manage Customer Document Asset
- Manage Digital Channels → **Manage Omni-Channel Delivery** → Manage User Interface Consistency
- Manage Digital GPRC → Manage Enterprise Compliance → **Manage Compliance Design**
- Manage Digital Experience Orchestration → Manage Experience Governance → **Manage Experience Growth Analytics** → Manage CLV Analytics

**Epic Description:**
Implement the Stellar-native Compliance Passport — a reusable, portable compliance credential minted on Stellar after ZK proof verification. Unlike a one-time KYC check, the Compliance Passport is an on-chain attestation that *any* Stellar-based protocol can verify by calling `verifyCredential(wallet)` without re-running KYC. One proof, many protocols: DEX, lending, RWA tokenization, payroll, remittance. This is the architecture that positions ZKCO as **compliance infrastructure** rather than a compliance application, and it is the most Stellar-native aspect of the submission — making Stellar essential rather than optional.

---

### F-03.1 — Compliance Passport Token (Stellar)

**Description:** Design and deploy a Soroban smart contract that mints a non-transferable Compliance Passport token for a wallet address upon successful ZK proof verification, encoding policy metadata and expiry on-chain.

#### US-03.1.1 — Compliance Passport Contract Design
> *As a protocol developer, I want a Soroban contract that issues a non-transferable Compliance Passport token so that any downstream protocol on Stellar can verify a wallet's compliance status with a single contract call rather than running their own KYC.*

**Acceptance Criteria:**
- A Soroban contract `CompliancePassport` exposes `mint_passport(wallet: Address, policy_id: Symbol, expires_at: u64, proof_hash: BytesN<32>)` callable only by the authorised `oracle_authority` address.
- The minted passport is non-transferable: the contract blocks standard `transfer()` calls with error code `ERR_NON_TRANSFERABLE`.
- Each wallet can hold only one active passport per `policy_id`; a new mint for an existing wallet+policy pair updates the existing record rather than creating a duplicate.
- Passport minting emits a `PassportMinted { wallet, policy_id, expires_at, proof_hash, minted_at }` Soroban event retrievable via Horizon within 30 seconds of confirmation.

#### US-03.1.2 — Cross-Protocol Credential Verification
> *As a DeFi protocol on Stellar, I want to call a single view function to check whether a wallet holds a valid Compliance Passport so that I can gate token swaps, lending, or RWA access without running my own KYC infrastructure.*

**Acceptance Criteria:**
- The contract exposes `verify_credential(wallet: Address, policy_id: Symbol) -> { valid: bool, expires_at: u64, policy_id: Symbol }` as a read-only function requiring no transaction fee.
- `verify_credential` returns `{valid: false, expires_at: 0}` for wallets with no passport or an expired passport; it never panics on missing records.
- Passport expiry is enforced at the contract level using `ledger().timestamp()` — expired passports automatically return `valid: false` without requiring explicit revocation.
- The verification interface is documented as a Stellar Asset Contract standard interface in `docs/passport_interface.md` so any Stellar developer can integrate without reading ZKCO source code.

#### US-03.1.3 — Multi-Protocol Demo Integration
> *As a hackathon judge, I want to see the Compliance Passport verified by at least two simulated protocol contexts so that the reusability claim is demonstrated concretely rather than described.*

**Acceptance Criteria:**
- A test script `scripts/demo_passport.sh` demonstrates: (1) proof generation and Soroban verification for wallet A, (2) passport mint, (3) `verify_credential` called from a simulated DEX context returning `{valid: true}`, (4) `verify_credential` called from a simulated lending context returning `{valid: true}`.
- The same passport is reused across both simulated protocol contexts without re-running KYC or generating a new proof.
- The script prints a structured summary including all Stellar testnet transaction hashes.
- A `README` section "Compliance Passport — Protocol Integration Guide" explains how a Stellar protocol integrates in fewer than 10 lines of Soroban code.

---

### F-03.2 — Compliance Passport Lifecycle Management

**Description:** Implement revocation, renewal, and selective disclosure capabilities that make the Compliance Passport suitable for regulated financial use — not just demo purposes.

#### US-03.2.1 — Passport Revocation
> *As a compliance officer, I want to revoke a wallet's Compliance Passport when a new adverse event is detected so that downstream protocols immediately see the wallet as non-compliant.*

**Acceptance Criteria:**
- `revoke_passport(wallet: Address, policy_id: Symbol, reason: Symbol)` entry point is callable only by `oracle_authority` and sets passport status to `REVOKED` with `revoked_at` and `reason` in the on-chain record.
- After revocation, `verify_credential` returns `{valid: false}` within the same block — no grace period.
- Revocation emits `PassportRevoked { wallet, policy_id, reason, revoked_at }` event.
- When the ZK Compliance Oracle detects a CI crossing the high-risk threshold for an entity with an active passport (triggered by the AML incident detection in F-01.3.1), it automatically triggers passport revocation via the `oracle_authority` Soroban call.

#### US-03.2.2 — Selective Disclosure for Regulatory Audit
> *As a regulated financial institution, I want to request selective disclosure of the compliance factors that produced a wallet's passport so that I can satisfy regulatory audit requirements without receiving the full compliance model.*

**Acceptance Criteria:**
- The ZKCO platform exposes a `POST /api/v1/entity/{entity_hash}/disclose` endpoint that accepts a `disclosure_request` signed by the regulated institution's registered key and returns only the specific factor names (not values) that contributed to a PASS decision: e.g., `["AML_PASS", "SANCTIONS_CLEAR", "JURISDICTION_PERMITTED"]`.
- Factor values and weights are never disclosed; only boolean pass/fail per named dimension is returned.
- Disclosure responses are logged to the `disclosure_audit` table with `{requestor_key_hash, entity_hash, factors_disclosed, disclosed_at, request_signature}`.
- Selective disclosure is gated behind a separate `DISCLOSURE_API_KEY` distinct from the standard API key, enforceable at the platform level.

---

## EP-04 — Casper ComplianceOracle & On-Chain Verifiability

**Canvas Capability Anchor:**
- Manage Digital Inter-Operability & Automation → Manage Automation Infrastructure (Blockchain) → **Manage Accountability & Verifiability** → Manage DPoS Algorithm
- Manage Digital Inter-Operability & Automation → **Manage Blockchain & Transaction Integrity**
- Manage Digital Experience Orchestration → Manage Customer Interactions → **Manage Customer Asset Wallet**
- Manage Digital GPRC → Manage Enterprise Compliance → **Manage Compliance Design**
- Manage Digital Security → Manage Identity & Access Security → **Manage Identity & Access Logs**

**Epic Description:**
Deploy Casper Odra smart contracts implementing a ComplianceOracle (receives and stores compliance verdicts on-chain) and an IdentityRegistry (maps wallet addresses to compliance token statuses). This is the primary on-chain layer for the **Casper Agentic Buildathon** submission.

---

### F-03.1 — Casper ComplianceOracle Contract

**Description:** A Casper Odra smart contract that accepts compliance verdicts from the authorised agent, stores them on-chain as upgradeable records, and emits events for downstream consumers.

#### US-03.1.1 — Compliance Verdict Storage
> *As a compliance agent, I want to write a compliance verdict (PASS/FAIL) for an entity to the Casper ComplianceOracle contract so that the decision is immutably recorded on-chain.*

**Acceptance Criteria:**
- The ComplianceOracle contract exposes a `record_verdict(entity_hash: String, verdict: bool, expires_at: u64, nrs_threshold: u64)` entry point callable only by the authorised `mint_authority` key.
- Successful calls create or update an on-chain record keyed by `entity_hash` with fields `{verdict, recorded_at, expires_at, nrs_threshold}`.
- The contract emits a `VerdictRecorded` event with the same fields (excluding `nrs_threshold` — public compliance threshold only) within the same deploy.
- Unauthorised callers (non-`mint_authority`) receive a `PermissionDenied` error and the transaction is rejected.

#### US-03.1.2 — Verdict Revocation & Expiry
> *As a compliance officer, I want verdicts to expire after a configurable duration and be revocable by the platform so that outdated compliance statuses are not honoured by downstream protocols.*

**Acceptance Criteria:**
- The contract stores `expires_at` as a UNIX timestamp; any query to `get_verdict(entity_hash)` after expiry returns `{verdict: null, status: "EXPIRED"}`.
- The `revoke_verdict(entity_hash: String, reason: String)` entry point is callable only by `mint_authority` and sets verdict to `false` with `revoked_at` and `reason` in the record.
- Revocation events `VerdictRevoked { entity_hash, reason, revoked_at }` are emitted and queryable via CSPR.cloud within 30 seconds of finalisation.
- A Casper testnet deploy hash for a test revocation is recorded in the repository `deployments.json`.

#### US-03.1.3 — Compliance Status Querying
> *As a DeFi protocol smart contract, I want to query the ComplianceOracle for an entity's current compliance status so that I can gate token transfers without implementing KYC logic myself.*

**Acceptance Criteria:**
- The contract exposes a `get_verdict(entity_hash: String) -> { verdict: bool, expires_at: u64, status: String }` read-only entry point.
- Queries return within one block (~8 seconds on Casper 2.1) when called via CSPR.cloud middleware.
- The platform exposes a REST proxy `GET /api/v1/casper/verdict/{entity_hash}` that wraps the on-chain query and caches results for 60 seconds.
- A Postman collection demonstrating the query flow is included in the repository `/docs/` directory.

---

### F-03.2 — Casper IdentityRegistry Contract

**Description:** A Casper Odra contract that maintains a registry of wallet addresses mapped to compliance token mint status, enabling the ComplianceOracle verdict to trigger a mintable compliance credential.

#### US-03.2.1 — Identity Registration
> *As a platform onboarding agent, I want to register a wallet address in the IdentityRegistry so that the address is eligible to receive a compliance token upon passing KYC.*

**Acceptance Criteria:**
- `register_identity(wallet: Key, entity_hash: String)` entry point creates a registry entry keyed by `wallet` with `{entity_hash, registered_at, status: "PENDING"}`.
- Duplicate registrations (same wallet) update `registered_at` and reset `status` to `"PENDING"` rather than failing.
- Registration emits `IdentityRegistered { wallet, entity_hash, registered_at }` event.
- A read-only `get_identity(wallet: Key)` returns the full registry record or `null` if not found.

#### US-03.2.2 — Compliance Token Minting
> *As a compliance agent, I want to trigger a compliance token mint for a registered wallet after a PASS verdict is recorded in the ComplianceOracle so that the wallet holds an on-chain attestation asset.*

**Acceptance Criteria:**
- `mint_compliance_token(wallet: Key, entity_hash: String)` cross-references the ComplianceOracle for a valid PASS verdict before minting; it aborts with `NO_VALID_VERDICT` if none exists.
- Upon successful mint, the IdentityRegistry entry for `wallet` transitions to `status: "COMPLIANT"` with `minted_at` timestamp.
- The mint emits `ComplianceTokenMinted { wallet, entity_hash, minted_at, expires_at }`.
- Token expiry mirrors the verdict expiry in the ComplianceOracle; querying a wallet with an expired token returns `status: "EXPIRED"`.

#### US-03.2.3 — Cross-Contract Interaction Test
> *As a developer, I want to demonstrate ComplianceOracle and IdentityRegistry interacting in a single end-to-end flow on Casper testnet so that the submission is provably functional.*

**Acceptance Criteria:**
- A bash script `scripts/e2e_casper.sh` deploys both contracts, registers an identity, records a verdict, mints a compliance token, and queries the final status — all on Casper testnet.
- The script exits 0 (success) with printed deploy hashes for each step.
- All deploy hashes are written to `deployments.json` under the `casper_testnet` key.
- The script completes end-to-end within 5 minutes accounting for Casper testnet block finalisation.

---

## EP-05 — API Gateway & Micropayment Rail

**Canvas Capability Anchor:**
- Manage Digital Inter-Operability & Automation → Manage Integration Infrastructure (API) → **Manage API Lifecycle** → Manage API Security & Access
- Manage Digital Inter-Operability & Automation → **Manage API Gateway** → Manage Single Entry
- Manage Digital Inter-Operability & Automation → **Manage Payment Rail Operations**
- Manage Digital Inter-Operability & Automation → Manage Interoperability Governance → **Manage Orchestration Analytics**
- Manage Digital Security → Manage Channels Governance → **Manage Channel Security** → Manage Channel Access Governance

**Epic Description:**
Build a FastAPI REST gateway that serves as the single entry point for all platform services. Integrate the Casper x402 Protocol so that risk query endpoints require a micropayment per call, turning the compliance oracle into a pay-per-request API for AI agents operating on Casper.

---

### F-04.1 — FastAPI REST Gateway

**Description:** Implement a production-grade FastAPI application with authentication, rate limiting, structured logging, and endpoint routing for all platform services.

#### US-04.1.1 — Authenticated API Access
> *As a DeFi protocol developer, I want to authenticate against the KYC API using an API key so that only authorised callers can trigger risk assessments and proof generation.*

**Acceptance Criteria:**
- All endpoints except `GET /health` and `GET /docs` require an `X-API-Key` header validated against the `api_keys` PostgreSQL table.
- Invalid or missing API keys return HTTP 401 with body `{"error": "Invalid or missing API key"}`.
- API keys are stored as bcrypt hashes with a salt; plaintext keys are never stored in the database.
- A `POST /api/v1/keys` endpoint (admin-only, authenticated via `X-Admin-Secret` header) generates and returns a new plaintext API key while storing only its hash.

#### US-04.1.2 — Core Endpoint Routing
> *As an API consumer, I want a well-structured set of REST endpoints so that I can discover and call all platform capabilities without reading source code.*

**Acceptance Criteria:**
- The following endpoints are implemented and return documented response schemas: `POST /api/v1/entity`, `POST /api/v1/relationship`, `GET /api/v1/entity/{id}/nrs`, `GET /api/v1/entity/{id}/credential`, `GET /api/v1/casper/verdict/{entity_hash}`, `POST /api/v1/prove/{id}`.
- All endpoints respond within 5 seconds for standard requests (excluding proof generation which has a documented 30-second SLA).
- OpenAPI documentation is auto-generated and accessible at `GET /docs` without authentication.
- All endpoints return `application/json` and include a `request_id` UUID in the response headers for traceability.

#### US-04.1.3 — Rate Limiting & Abuse Prevention
> *As a platform operator, I want to enforce per-key rate limits so that individual API consumers cannot exhaust server resources or exploit proof generation infrastructure.*

**Acceptance Criteria:**
- A default rate limit of 60 requests per minute per API key is enforced using an in-memory token bucket (or Redis-backed if available).
- Requests exceeding the limit receive HTTP 429 with a `Retry-After` header indicating the seconds until the next allowed request.
- Rate limit counters are logged to the `api_rate_events` table for abuse forensics.
- The admin endpoint `POST /api/v1/keys/{key_id}/limit` allows updating the rate limit for a specific key to a maximum of 600 RPM.

---

### F-04.2 — x402 Micropayment Gate (Casper)

**Description:** Integrate the Casper x402 Protocol into the FastAPI gateway so that the NRS query endpoint requires a micropayment in CSPR per call, demonstrating the machine-to-machine payment primitive for AI agents.

#### US-04.2.1 — x402 Challenge-Response Handshake
> *As an AI agent operating on Casper, I want the compliance query endpoint to respond with an HTTP 402 payment challenge so that I know exactly how much CSPR to pay for the risk assessment.*

**Acceptance Criteria:**
- `GET /api/v1/entity/{id}/nrs` without a payment proof header returns HTTP 402 with body `{"payment_required": true, "amount_cspr": "0.001", "payment_address": "<platform_wallet>", "expires_in_seconds": 30}`.
- The challenge response is returned within 500ms.
- The `amount_cspr` value is configurable via `X402_PRICE_CSPR` environment variable (default `"0.001"`).
- The payment address is the platform's Casper testnet public key loaded from `CASPER_TREASURY_PUBLIC_KEY` env var.

#### US-04.2.2 — Payment Proof Verification
> *As an AI agent, I want to attach a signed CSPR micropayment proof to my request so that the gateway verifies payment and returns the NRS data without a separate billing step.*

**Acceptance Criteria:**
- The gateway accepts an `X-Payment-Proof` header containing a base64-encoded Casper deploy hash for a CSPR transfer to the platform wallet.
- The gateway verifies the deploy hash via CSPR.cloud RPC (`GET /rpc/info_get_deploy`) that the transfer amount ≥ `X402_PRICE_CSPR` and destination matches the platform wallet.
- Verification completes within 10 seconds; if CSPR.cloud is unreachable, the request is queued with status `PAYMENT_PENDING` and resolved on retry.
- Duplicate deploy hashes (replayed payments) are rejected with HTTP 409 and body `{"error": "Payment proof already consumed"}`.

#### US-04.2.3 — Payment Audit Logging
> *As a platform finance team, I want every micropayment to be recorded in an audit log so that revenue can be reconciled and agent-level usage tracked.*

**Acceptance Criteria:**
- Every verified payment is written to the `payment_receipts` table with `{deploy_hash, entity_id, amount_cspr, paid_at, api_key_id, verified_at}`.
- A `GET /api/v1/payments/summary` admin endpoint returns total CSPR received per day for the last 30 days.
- Failed payment verifications are logged to `payment_failures` with `{deploy_hash, failure_reason, attempted_at, api_key_id}`.
- The audit log is retained for a minimum of 90 days and is not subject to automatic purging.

---

## EP-06 — Specialist Agentic Compliance Orchestration

**Canvas Capability Anchor:**
- Manage Digital Intelligence → Intelligence Infrastructure → **Manage Cognitive Intelligence** → Manage Machine Learning Intelligence
- Manage Digital Intelligence → Intelligence Infrastructure → **Manage Deep Learning Intelligence**
- Manage Digital Service Orchestration → Manage Service Orchestration Governance → **Manage Service Engagement Optimisation**
- Manage Digital Inter-Operability & Automation → Manage Automation Infrastructure (RPA) → **Manage Orchestrators** → Manage Extraction Engine
- Manage Digital Intelligence → Intelligence Governance → **Manage Data Stewardship**
- Manage Digital Intelligence → Horizontal Intelligence → **Manage Compliance Intelligence (GRC)**

**Epic Description:**
Implement a LangGraph multi-agent pipeline with Groq (Llama 3.3 70B free tier) as the reasoning engine. Rather than a simple three-step pipeline, the system deploys **five autonomous specialist agents** — each with a focused domain of responsibility — that collaborate through shared state. This architecture transforms the platform from a "compliance pipeline" into genuine multi-agent compliance infrastructure capable of handling regulatory complexity, chain selection, and audit generation autonomously.

---

### F-06.1 — Five-Specialist LangGraph Agent Architecture

**Description:** Define the LangGraph state machine with five autonomous specialist agent nodes and the state schema governing data flow between them. Each agent is a domain expert: Intelligence (graph + risk), Compliance (regulatory rules), ZK (circuit selection + witness), Settlement (chain dispatch), Auditor (explanation + trail).

#### US-06.1.1 — Expanded Agent State Schema
> *As a platform architect, I want to define a typed LangGraph state schema that captures the outputs of all five specialist agents so that data provenance is complete and auditable throughout the compliance workflow.*

**Acceptance Criteria:**
- A `ComplianceState` TypedDict is defined with keys: `{entity_id, compliance_index, factor_breakdown, manifold_score, jurisdiction_flag, regulatory_rules_applied, rule_violations, circuit_selected, proof_hex, public_inputs, chain_target, on_chain_tx_hash, passport_token_id, audit_report, selective_disclosure_labels, errors, step_log}`.
- All fields are Optional except `entity_id`; default values are provided for list and dict fields to prevent `KeyError` in the graph.
- The state schema is imported and reused by all five agent nodes with no local redefinition.
- Unit tests in `tests/test_state.py` verify state initialisation, field mutation, and cross-agent handoff for all five agents.

#### US-06.1.2 — Intelligence Agent
> *As the LangGraph orchestrator, I want an Intelligence Agent that runs multi-factor risk scoring and behavioural manifold classification so that the compliance state is populated with investment-grade financial intelligence before any regulatory reasoning begins.*

**Acceptance Criteria:**
- The Intelligence Agent calls the six-factor computation (F-01.4) and manifold scoring (F-01.5), populating `state.compliance_index`, `state.factor_breakdown`, and `state.manifold_score`.
- If graph data is insufficient (fewer than 3 counterparties), the Intelligence Agent sets `state.errors.append("INSUFFICIENT_GRAPH_DATA")` and routes to the error terminal.
- The Intelligence Agent logs `{agent: "intelligence", started_at, completed_at, compliance_index, manifold_score}` to `state.step_log`.
- The agent completes within 20 seconds including graph export, NetworkX computation, and embedding scoring.

#### US-06.1.3 — Compliance Agent with Regulatory Rule Engine
> *As the LangGraph orchestrator, I want a Compliance Agent that applies named regulatory frameworks (FATF, MiCA, Travel Rule) to the factor breakdown and uses Groq to reason about edge cases so that the compliance decision reflects real regulatory standards, not just a threshold comparison.*

**Acceptance Criteria:**
- The Compliance Agent applies a deterministic rule set covering: FATF Recommendation 10 (CDD), FATF Recommendation 16 (Travel Rule — flags transactions > USD 1,000 without counterparty info), MiCA Article 83 (sanctions screening), and a jurisdiction blocklist check.
- Groq (Llama 3.3 70B) is called with the factor breakdown and rule evaluation results to produce a rationale string and a final `PASS`/`FAIL` decision with confidence score.
- `state.regulatory_rules_applied` is populated with a list of rule IDs checked; `state.rule_violations` lists any triggered violations.
- The agent falls back to deterministic PASS if `CI < 0.4` and no rule violations exist, bypassing Groq if the API is unavailable, and logs `"GROQ_SKIPPED"` to `state.step_log`.

#### US-06.1.4 — ZK Agent for Circuit Selection & Witness Generation
> *As the LangGraph orchestrator, I want a ZK Agent that selects the appropriate Noir circuit variant based on the compliance policy and constructs the proof witness so that ZK proof generation is autonomous and policy-aware.*

**Acceptance Criteria:**
- The ZK Agent reads `state.chain_target` and the compliance policy context to select the correct circuit: `policy_v1.nr` (three-condition: CI + manifold + jurisdiction) for the current implementation, with the framework supporting additional circuit variants in future.
- The ZK Agent constructs the Prover.toml witness from `state.compliance_index`, `state.manifold_score`, `state.jurisdiction_flag` and the policy public inputs, then triggers proof generation (F-02.1.2).
- `state.proof_hex` and `state.public_inputs` are populated upon successful proof generation.
- If proof generation fails or exceeds 45 seconds, the ZK Agent retries once with a reduced subgraph before setting `state.errors.append("PROOF_GENERATION_FAILED")`.

#### US-06.1.5 — Settlement Agent for Chain Dispatch
> *As the LangGraph orchestrator, I want a Settlement Agent that autonomously selects the target chain based on policy context and dispatches the proof or verdict so that the same pipeline serves Stellar and Casper without manual routing logic in the orchestrator.*

**Acceptance Criteria:**
- If `state.chain_target == "stellar"`, the Settlement Agent submits `state.proof_hex` to the Soroban verifier and calls `mint_passport` on the CompliancePassport contract (EP-03.1), populating `state.passport_token_id`.
- If `state.chain_target == "casper"`, the Settlement Agent calls `record_verdict` on the Casper ComplianceOracle and triggers `mint_compliance_token` on the IdentityRegistry (EP-04.2), populating `state.on_chain_tx_hash`.
- The Settlement Agent retries on-chain submission once after 5 seconds on failure before routing to the error terminal.
- `state.on_chain_tx_hash` is populated for Casper and `state.passport_token_id` for Stellar; both are logged to `state.step_log` with confirmation timestamps.

#### US-06.1.6 — Auditor Agent for Explanation & Selective Disclosure
> *As a compliance officer and hackathon judge, I want an Auditor Agent that produces a human-readable compliance explanation and a selective disclosure label list so that the audit trail is complete and the demo communicates what the system decided and why.*

**Acceptance Criteria:**
- The Auditor Agent uses Groq to generate a `state.audit_report` — a structured natural-language explanation of the compliance decision referencing the regulatory rules applied, confidence level, and which of the six factors most influenced the outcome. Format: `{summary: str, key_factors: list[str], rules_applied: list[str], decision: str, confidence: float}`.
- `state.selective_disclosure_labels` is populated as a list of boolean pass/fail dimension labels: e.g. `["AML_PASS", "SANCTIONS_CLEAR", "KYC_PASS", "JURISDICTION_PERMITTED", "FATF_COMPLIANT"]` — no scores or values.
- The audit report and disclosure labels are written to the `agent_executions` table alongside the full step log.
- The Auditor Agent completes within 15 seconds and never includes raw CI values, factor scores, or graph data in its output.

---

### F-06.2 — Agent Observability & Audit Trail

**Description:** Implement structured logging and execution tracing for the agentic pipeline to support debugging, audit compliance, and demo recording.

#### US-06.2.1 — Structured Execution Tracing
> *As a developer preparing the hackathon demo, I want every agent execution to be logged with timing, inputs, outputs, and chain results so that the demo video can show a clear data lineage.*

**Acceptance Criteria:**
- Each agent appends a structured record to `state.step_log`: `{agent, started_at, completed_at, input_keys, output_keys, errors}`.
- After graph completion, the full `step_log` is written to the `agent_executions` PostgreSQL table with a unique `run_id` UUID.
- A `GET /api/v1/runs/{run_id}` endpoint returns the complete execution trace including final state (excluding `proof_hex` for security).
- Execution traces are retained for 30 days and support filtering by `entity_id`, `compliance_decision`, and `chain_target`.

#### US-06.2.2 — Demo CLI Runner
> *As a hackathon submitter, I want a single CLI command to run the full agentic workflow end-to-end so that the demo video shows a clean, reproducible flow.*

**Acceptance Criteria:**
- A CLI command `python -m zkkyc.run --entity-id <id> --chain [stellar|casper]` executes the full LangGraph pipeline and prints a structured summary to stdout.
- The summary includes: entity_id, NRS, compliance_decision, chain_target, on_chain_tx_hash, and total_elapsed_seconds.
- The CLI exits 0 on PASS verdict with on-chain confirmation, 1 on FAIL verdict, and 2 on internal error.
- The full execution trace `run_id` is printed so reviewers can inspect the agent log via the REST API.

---

## EP-07 — Data Governance & Security Lifecycle

**Canvas Capability Anchor:**
- Manage Digital Security → Manage Data Security → **Manage Data Protection & Privacy** → Manage Data Classification
- Manage Digital IT → Manage Data Lifecycle → **Manage Data Design** → Manage RDBMS Data Design
- Manage Digital Security → Manage Security Monitoring and Compliance → **Manage Security Event Logging** → Manage Log Aggregation
- Manage Digital IT → Manage Data Lifecycle → **Manage Data Security** → Manage Data Release Security
- Manage Digital GPRC → Manage Enterprise Compliance → **Manage Compliance Monitoring** → Manage Testing Frameworks
- Manage Digital Inter-Operability & Automation → Manage Interoperability Governance → **Manage Orchestration Security** → Manage Auditing & Compliance

**Epic Description:**
Implement the data governance, classification, security logging, and compliance audit infrastructure that ensures the platform meets the data handling standards expected of KYC/AML infrastructure in regulated markets — particularly relevant for the Casper judging criteria on enterprise-grade deployability.

---

### F-06.1 — Data Classification & Privacy Controls

**Description:** Classify all data handled by the platform, implement encryption at rest for sensitive fields, and enforce data minimisation principles across all storage layers.

#### US-06.1.1 — Data Classification Schema
> *As a data governance officer, I want all platform data assets to be classified by sensitivity level so that appropriate handling controls can be applied consistently.*

**Acceptance Criteria:**
- A data classification manifest `docs/data_classification.md` is committed to the repository categorising each data type as `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, or `RESTRICTED`.
- `RESTRICTED` fields (raw entity IDs, NRS values, document contents) are never stored in plaintext in any database table.
- `RESTRICTED` fields at rest use AES-256-GCM encryption with keys loaded from `DATA_ENCRYPTION_KEY` environment variable.
- An automated test `tests/test_data_classification.py` verifies that no `RESTRICTED` field appears in plaintext in the PostgreSQL schema inspection.

#### US-06.1.2 — PII Minimisation & Entity Hashing
> *As a privacy-conscious platform, I want all on-chain and API log references to entities to use SHA-256 hashes of entity IDs so that raw PII is never exposed in public ledgers or logs.*

**Acceptance Criteria:**
- A utility function `hash_entity_id(entity_id: str) -> str` returns `SHA256(entity_id + ENTITY_SALT)` where `ENTITY_SALT` is loaded from environment.
- All on-chain contract calls, event emissions, and API response bodies use `entity_hash` not `entity_id`.
- The mapping between `entity_id` and `entity_hash` is stored only in the encrypted `entity_mappings` table with column-level encryption on the `entity_id` field.
- A privacy audit report template `docs/privacy_audit.md` is included in the repository documenting the data flow for PII.

---

### F-06.2 — Security Event Logging & SOC Integration

**Description:** Implement structured security event logging for all authentication failures, unauthorised access attempts, proof generation events, and on-chain dispatch events.

#### US-06.2.1 — Security Event Schema
> *As a security engineer, I want all security-relevant events to be logged in a structured format so that they can be ingested by a SIEM or queried for incident response.*

**Acceptance Criteria:**
- A `security_events` PostgreSQL table is created with columns `{id, event_type, severity, entity_hash, api_key_id, source_ip, description, metadata_json, occurred_at}`.
- The following event types are logged: `AUTH_FAILURE`, `RATE_LIMIT_EXCEEDED`, `PROOF_GENERATED`, `ON_CHAIN_DISPATCH`, `VERDICT_RECORDED`, `VERDICT_REVOKED`, `PAYMENT_VERIFIED`, `PAYMENT_FAILED`.
- All events are logged within 500ms of occurrence and do not block the primary request-response cycle (async logging).
- Security events with severity `CRITICAL` (e.g., `VERDICT_REVOKED`, multiple `AUTH_FAILURE` from the same IP) trigger a webhook to `SECURITY_ALERT_WEBHOOK_URL`.

#### US-06.2.2 — Audit Trail Completeness
> *As a compliance auditor, I want to trace any compliance decision back to the originating graph data and proof so that the full audit lineage is available for regulatory inspection.*

**Acceptance Criteria:**
- A `GET /api/v1/audit/{entity_hash}` endpoint returns the full audit trail: NRS computation history, proof generation events, on-chain dispatch records, and any incidents — sorted descending by `occurred_at`.
- Audit trail responses include `run_id` references linkable to agent execution logs (EP-05.2.1).
- The audit endpoint requires admin API key authentication.
- Audit records cannot be deleted via any API endpoint; they can only be flagged as `ARCHIVED` after 12 months by the admin.

---

### F-06.3 — Compliance Testing Framework

**Description:** Implement automated tests that validate compliance logic, graph algorithm correctness, ZK circuit integrity, and smart contract interactions against testnet.

#### US-06.3.1 — Unit Test Coverage
> *As a developer, I want unit tests for all core business logic functions so that regressions are caught before submission and the codebase demonstrates engineering maturity to judges.*

**Acceptance Criteria:**
- Unit tests cover: `hash_entity_id`, `generate_zk_proof`, `verify_proof_local`, NRS computation (PageRank, Louvain, centrality aggregation), Groq fallback logic, and x402 payment verification.
- Test coverage (measured by `pytest --cov`) is ≥ 70% for the `zkkyc/` package excluding auto-generated code.
- All tests pass in a clean environment using `pytest tests/unit/` without requiring Neo4j Aura or Groq credentials (mocks provided).
- A `pytest.ini` configuration is committed to the repository with test markers for `unit`, `integration`, and `e2e`.

#### US-06.3.2 — Integration Test: Graph → ZK Flow
> *As a QA engineer, I want an integration test that runs a full graph → NRS → proof generation → local verification flow so that the core value chain is continuously verified.*

**Acceptance Criteria:**
- `pytest tests/integration/test_graph_to_zk.py` executes against a live Neo4j Aura Free connection (credentials from `.env.test`) and a local Noir installation.
- The test creates a test entity, adds 5 relationships, computes NRS, generates a Noir proof, verifies it locally, and asserts the final proof verification returns `True`.
- The test completes within 60 seconds and cleans up test nodes from Neo4j on both pass and failure.
- The integration test is excluded from CI until a testnet environment is configured (guarded by `@pytest.mark.integration`).

---

## Submission Checklist

### Stellar Hacks: Real-World ZK — Submission by 3 July 2026 17:00 UTC

**Submission framing:** "Zero-Knowledge Compliance Oracle — Verifiable Off-Chain Financial Intelligence for Regulated Stellar DeFi"

| Item | Status |
|---|---|
| EP-01 Multi-factor Compliance Index (six factors) operational | ☐ |
| EP-01 Graph embeddings + manifold scoring operational | ☐ |
| EP-02 Noir three-condition circuit (`circuits/src/main.nr`) compiles | ☐ |
| EP-02 Multi-input proof generation (CI + manifold + jurisdiction) tested locally | ☐ |
| EP-03 CompliancePassport Soroban contract deployed to Stellar testnet | ☐ |
| EP-03 `verify_credential()` returns `{valid: true}` for two simulated protocol contexts | ☐ |
| EP-03 Selective disclosure labels endpoint operational | ☐ |
| `deployments.json` updated with Stellar contract address and mint tx hash | ☐ |
| `scripts/demo_passport.sh` runs: proof → Soroban verify → passport mint → dual-protocol verify | ☐ |
| 2–3 min demo video structure: CI computation → Noir proof (3 conditions) → Stellar verification → Compliance Passport mint → DEX + Lending verify | ☐ |
| Open-source GitHub repo with clear README | ☐ |
| README section "What ZK is proving" explains the three-condition circuit (load-bearing ZK) | ☐ |
| README section "Compliance Passport — Protocol Integration Guide" with 10-line Soroban integration snippet | ☐ |
| DoraHacks submission narrative uses framing: "Verifiable Off-Chain Computation + Private Credential + Compliant Private Transfer" | ☐ |

### Casper Agentic Buildathon — Submission by 8 July 2026

| Item | Status |
|---|---|
| EP-01 Six-factor CI engine and NetworkX pipeline operational | ☐ |
| EP-04 ComplianceOracle + IdentityRegistry deployed to Casper testnet | ☐ |
| EP-05 x402 micropayment gate functional | ☐ |
| EP-06 Five-specialist LangGraph agent pipeline complete | ☐ |
| EP-06 Auditor Agent producing audit report and selective disclosure labels | ☐ |
| `deployments.json` updated with Casper contract addresses | ☐ |
| `python -m zkkyc.run --entity-id test --chain casper` succeeds end-to-end | ☐ |
| Demo video: Intelligence Agent → Compliance Agent → ZK Agent → Settlement Agent → Auditor Agent → Casper on-chain confirmation | ☐ |
| Community votes solicited via CSPR.fans | ☐ |

---

## Technology Stack Reference

| Component | Technology | Cost |
|---|---|---|
| Graph Database | Neo4j Aura Free | Free |
| Graph Algorithms | NetworkX (Python) | Free/OSS |
| ZK Circuit | Noir (noirup) | Free/OSS |
| Soroban Verifier | rs-soroban-ultrahonk | Free/OSS |
| Casper Contracts | Odra Framework (Rust) | Free/OSS |
| Agent Orchestration | LangGraph | Free/OSS |
| LLM Reasoning | Groq API — Llama 3.3 70B | Free tier |
| API Layer | FastAPI + Uvicorn | Free/OSS |
| Relational Storage | PostgreSQL | Free/OSS |
| Casper Middleware | CSPR.cloud | Free testnet |
| Stellar SDK | stellar-sdk (Python) | Free/OSS |
| Testing | pytest + pytest-cov | Free/OSS |

---

---

## Competitive Positioning Notes (Internal)

**Stellar hackathon narrative (for DoraHacks submission text):**
> "We built the world's first AI-native Zero-Knowledge Compliance Oracle that allows regulated financial institutions and DeFi protocols to consume compliance decisions without ever accessing customer PII. Our multi-factor Compliance Index — derived from six independent financial risk dimensions computed across a Neo4j transaction graph — is proved correct using a Noir ZK circuit that simultaneously verifies AML, KYC, sanctions, jurisdiction, and FATF policy compliance. The result is minted as a portable, non-transferable Compliance Passport on Stellar that any protocol can verify with a single Soroban call. One proof. Many protocols. Stellar is the trust anchor."

**VC pitch framing:**
> Current: "We built private KYC." → Incorrect.
> Correct: "We built compliance infrastructure. Any DeFi protocol on Stellar can call `verifyCredential()` and know a wallet is compliant — without running KYC, without accessing PII, without trusting the operator. The ZK proof is the trust mechanism."

**Hackathon category alignment:**
- Primary: Verifiable Off-Chain Computation
- Secondary: Private Credential / Reputation
- Roadmap: Compliant Private Transfer with Selective Disclosure

*Document version 2.0 — Augmented 1 July 2026 | Zero-Knowledge Compliance Oracle for Regulated Finance*
