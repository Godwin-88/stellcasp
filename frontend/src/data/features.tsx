// src/data/features.ts
import {
  Network, Lock, FileCheck, Brain, Shield, Zap,
  Layers, GitBranch, Eye, Key, TrendingUp,
  BarChart2, CreditCard, BookOpen, Building2,
  Globe, Award,
} from 'lucide-react'

export type Capability = {
  icon: React.ElementType
  title: string
  desc: string
}

export type FeatureData = {
  slug: string
  name: string
  tagline: string
  category: string
  icon: React.ElementType
  heroColor: string
  categoryColor: string
  overview: string[]
  capabilities: Capability[]
  why: { icon: React.ElementType; title: string; body: string }[]
  whyBadge: string
  steps: { n: number; title: string; desc: string }[]
  stats: { value: string; label: string }[]
}

export const FEATURES: FeatureData[] = [
  {
    slug: 'graph-risk-engine',
    name: 'Graph Risk Engine',
    tagline: 'Neo4j transaction graph with NetworkX algorithms for multi-factor compliance intelligence.',
    category: 'Compliance',
    icon: Network,
    heroColor: 'from-blue-600 to-blue-800',
    categoryColor: 'bg-blue-50 text-blue-700',
    overview: [
      'The Graph Risk Engine ingests entity and transaction data into a Neo4j Aura graph, then exports subgraphs to NetworkX for algorithmic analysis. PageRank, Louvain community detection, and betweenness centrality feed into the six-factor Compliance Index.',
      'Unlike single-score risk models, this engine decomposes risk into six independent financial dimensions — each derived from graph-structural computations — producing an investment-grade compliance signal suitable for regulated DeFi.',
    ],
    capabilities: [
      { icon: Network, title: 'Entity Ingestion', desc: 'POST /api/v1/entity — create or upsert wallet nodes' },
      { icon: GitBranch, title: 'Relationship Mapping', desc: 'POST /api/v1/relationship — TRANSACTED_WITH edges with amounts, timestamps, tx_hash' },
      { icon: TrendingUp, title: 'PageRank Scoring', desc: 'α=0.85, max_iter=100, min-max normalised to [0,1]' },
      { icon: Layers, title: 'Louvain Communities', desc: 'Community risk flag when >30% of nodes exceed 90th percentile PR' },
      { icon: BarChart2, title: 'Betweenness Centrality', desc: 'Identifies structural bridges and sanctions-path overlap' },
      { icon: Eye, title: 'Anomaly Detection', desc: 'Rapid fan-out (>20 recipients/24h) flagged as STRUCTURAL_ANOMALY' },
    ],
    why: [
      { icon: Award, title: 'Investment-grade', body: 'Six independent factors replace single-score heuristics — the same model institutional risk teams use.' },
      { icon: Globe, title: 'Live jurisdiction data', body: 'FATF grey/black list refreshable via admin API without service restart.' },
      { icon: Building2, title: 'Regulatory-ready', body: 'Full audit trail of every computation persisted to PostgreSQL.' },
      { icon: Zap, title: 'Fast by design', body: 'Sub-15s computation for entities with up to 500 transactions.' },
    ],
    whyBadge: 'Neo4j Aura Free + NetworkX',
    steps: [
      { n: 1, title: 'Ingest entity', desc: 'POST wallet address or hashed national ID to /api/v1/entity' },
      { n: 2, title: 'Map relationships', desc: 'Add transaction edges via /api/v1/relationship (single or batch)' },
      { n: 3, title: 'Compute factors', desc: 'GET /api/v1/entity/{id}/factors returns L, C, J, S, A, B' },
      { n: 4, title: 'Aggregate CI', desc: 'Weighted sum produces Compliance Index (private witness)' },
      { n: 5, title: 'Trigger incident', desc: 'CI ≥ threshold auto-creates compliance_incidents record + webhook' },
    ],
    stats: [
      { value: '6', label: 'Risk Factors' },
      { value: '<15s', label: 'Computation' },
      { value: '500+', label: 'Tx Capacity' },
    ],
  },
  {
    slug: 'zk-proof-generator',
    name: 'ZK Proof Generator',
    tagline: 'Noir UltraHonk circuit proving three regulatory conditions simultaneously.',
    category: 'Privacy',
    icon: Lock,
    heroColor: 'from-purple-600 to-purple-800',
    categoryColor: 'bg-purple-50 text-purple-700',
    overview: [
      'The ZK Proof Generator implements a three-condition Noir circuit that simultaneously asserts: (1) Compliance Index below policy ceiling, (2) wallet in low-risk behavioural manifold, (3) jurisdiction in FATF permitted set.',
      'All of: the CI value, individual factor weights, graph topology, and entity identity remain private. Only the compliance policy result is on-chain. This is the load-bearing cryptographic claim of the platform.',
    ],
    capabilities: [
      { icon: Lock, title: 'Three Assertions', desc: 'CI < threshold ∧ manifold ≥ threshold ∧ jurisdiction permitted' },
      { icon: Key, title: 'Policy Binding', desc: 'policy_id in public inputs prevents replay across policy versions' },
      { icon: Zap, title: 'Fast Proving', desc: '<30s proof generation on standard laptop (US-02.1.2 SLA)' },
      { icon: Shield, title: 'Local Verification', desc: 'verify_proof_local() before on-chain submission' },
      { icon: Eye, title: 'Witness Isolation', desc: 'Per-call tempdir prevents Prover.toml leakage' },
      { icon: BarChart2, title: 'Float Precision', desc: 'round() not trunc() — avoids boundary errors at CI threshold' },
    ],
    why: [
      { icon: Award, title: 'Genuine multi-condition', body: 'Not a single threshold check — three simultaneous assertions constitute a real regulatory attestation.' },
      { icon: Shield, title: 'PII never exposed', body: 'Private inputs never leave the prover. Public inputs contain only thresholds and policy_id.' },
      { icon: Building2, title: 'Soroban-verifiable', body: 'UltraHonk proofs verified on-chain by rs-soroban-ultrahonk contract.' },
      { icon: Zap, title: 'Production-ready', body: 'Async subprocess execution, timeout handling, structured errors.' },
    ],
    whyBadge: 'Noir + UltraHonk',
    steps: [
      { n: 1, title: 'Compute CI', desc: 'Intelligence Agent produces compliance_index + manifold_score + jurisdiction_flag' },
      { n: 2, title: 'Scale to u64', desc: 'Floats × 1_000_000 become circuit-compatible integers' },
      { n: 3, title: 'Write Prover.toml', desc: 'Isolated tempdir per call — no shared state' },
      { n: 4, title: 'Run nargo prove', desc: 'Async subprocess with 30s timeout' },
      { n: 5, title: 'Return proof_hex', desc: 'Public inputs + proof bytes ready for Soroban dispatch' },
    ],
    stats: [
      { value: '3', label: 'Assertions' },
      { value: '<30s', label: 'Prove Time' },
      { value: '0', label: 'PII Leaked' },
    ],
  },
  {
    slug: 'compliance-passport',
    name: 'Compliance Passport',
    tagline: 'Non-transferable, policy-bound credential minted on Stellar after ZK verification.',
    category: 'Identity',
    icon: FileCheck,
    heroColor: 'from-emerald-600 to-emerald-800',
    categoryColor: 'bg-emerald-50 text-emerald-700',
    overview: [
      'The Compliance Passport is a Soroban smart contract that mints a non-transferable credential for a wallet after successful ZK verification. Any Stellar protocol can call verify_credential(wallet, policy_id) to gate access — no KYC re-run, no PII access.',
      'This is the architecture that positions ZKCO as compliance infrastructure rather than a compliance application. One proof, many protocols: DEX, lending, RWA, payroll, remittance.',
    ],
    capabilities: [
      { icon: FileCheck, title: 'mint_passport', desc: 'Oracle-authority-only. Creates non-transferable credential per (wallet, policy_id)' },
      { icon: Eye, title: 'verify_credential', desc: 'Read-only. Returns {valid, expires_at, policy_id} in one call' },
      { icon: Shield, title: 'revoke_passport', desc: 'Immediate invalidation on AML incident detection' },
      { icon: Lock, title: 'Non-transferable', desc: 'transfer() returns ERR_NON_TRANSFERABLE — soul-bound' },
      { icon: Key, title: 'Policy-bound', desc: 'One active passport per (wallet, policy_id) — upserts on remint' },
      { icon: Zap, title: 'Auto-expiry', desc: 'ledger().timestamp() enforced at contract level' },
    ],
    why: [
      { icon: Award, title: 'One proof, many protocols', body: 'DEX, lending, RWA, payroll, remittance — all verify the same passport with one contract call.' },
      { icon: Shield, title: 'Soul-bound', body: 'Non-transferable by design. Cannot be sold, gifted, or delegated.' },
      { icon: Building2, title: '10-line integration', body: 'Any Stellar protocol integrates in fewer than 10 lines of Soroban code.' },
      { icon: Zap, title: 'No re-KYC', body: 'Downstream protocols never run KYC — they just verify the passport.' },
    ],
    whyBadge: 'Stellar Soroban',
    steps: [
      { n: 1, title: 'Generate ZK proof', desc: 'Three-condition Noir proof for entity' },
      { n: 2, title: 'Verify on-chain', desc: 'ComplianceVerifier.verify_and_attest() emits compliance/verified event' },
      { n: 3, title: 'Mint passport', desc: 'Oracle authority calls mint_passport() with proof_hash + expires_at' },
      { n: 4, title: 'Protocol verifies', desc: 'Any protocol calls verify_credential(wallet, policy_id)' },
      { n: 5, title: 'Access granted', desc: 'Wallet gains access without re-running KYC' },
    ],
    stats: [
      { value: '1', label: 'Proof per Wallet' },
      { value: '∞', label: 'Protocol Uses' },
      { value: '0', label: 'Re-KYC Needed' },
    ],
  },
  {
    slug: 'casper-oracle',
    name: 'Casper ComplianceOracle',
    tagline: 'On-chain verdict storage + IdentityRegistry + x402 micropayment gate on Casper.',
    category: 'Blockchain',
    icon: Layers,
    heroColor: 'from-amber-600 to-amber-800',
    categoryColor: 'bg-amber-50 text-amber-700',
    overview: [
      'The Casper ComplianceOracle stores compliance verdicts immutably on-chain. Paired with the IdentityRegistry, it enables compliance token minting for registered wallets. The x402 micropayment gate turns the API into a pay-per-request service for AI agents.',
      'Casper is the primary chain for the Agentic Buildathon submission, complementing the Stellar Compliance Passport deployment.',
    ],
    capabilities: [
      { icon: FileCheck, title: 'record_verdict', desc: 'Mint-authority-only. Stores {verdict, expires_at, nrs_threshold}' },
      { icon: Eye, title: 'get_verdict', desc: 'Read-only. Returns {verdict, expires_at, status}' },
      { icon: Shield, title: 'revoke_verdict', desc: 'Sets verdict=false with reason, emits VerdictRevoked' },
      { icon: Key, title: 'IdentityRegistry', desc: 'Maps wallet → entity_hash → compliance token status' },
      { icon: CreditCard, title: 'x402 Gate', desc: 'HTTP 402 challenge → CSPR payment → NRS data' },
      { icon: Zap, title: 'REST Proxy', desc: 'GET /api/v1/casper/verdict/{hash} with 60s cache' },
    ],
    why: [
      { icon: Award, title: 'Dual-chain', body: 'Stellar for passports, Casper for verdicts + micropayments. Same pipeline, autonomous routing.' },
      { icon: Building2, title: 'Agent-ready', body: 'x402 protocol designed for machine-to-machine micropayments.' },
      { icon: Shield, title: 'Immutable audit', body: 'Every verdict recorded on-chain with deploy hash.' },
      { icon: Zap, title: 'Fast queries', body: 'get_verdict returns within one Casper block (~8s).' },
    ],
    whyBadge: 'Casper Odra',
    steps: [
      { n: 1, title: 'Register identity', desc: 'register_identity(wallet, entity_hash)' },
      { n: 2, title: 'Record verdict', desc: 'record_verdict(entity_hash, verdict, expires_at)' },
      { n: 3, title: 'Mint token', desc: 'mint_compliance_token() cross-references verdict' },
      { n: 4, title: 'Query status', desc: 'get_verdict() returns current compliance state' },
      { n: 5, title: 'Revoke if needed', desc: 'revoke_verdict() on AML incident' },
    ],
    stats: [
      { value: '2', label: 'Contracts' },
      { value: '~8s', label: 'Block Time' },
      { value: '60s', label: 'Cache TTL' },
    ],
  },
  {
    slug: 'langgraph-agents',
    name: 'Specialist AI Agents',
    tagline: 'Five autonomous LangGraph agents collaborating through shared state.',
    category: 'AI',
    icon: Brain,
    heroColor: 'from-rose-600 to-rose-800',
    categoryColor: 'bg-rose-50 text-rose-700',
    overview: [
      'Not a simple three-step pipeline — five autonomous specialist agents collaborate through a typed ComplianceState. Each is a domain expert: Intelligence, Compliance, ZK, Settlement, Auditor.',
      'The Compliance Agent applies deterministic FATF/MiCA/Travel Rule rules and uses Groq (Llama 3.3 70B) for edge-case reasoning. The Settlement Agent autonomously selects Stellar or Casper based on policy context.',
    ],
    capabilities: [
      { icon: Network, title: 'Intelligence Agent', desc: 'Six-factor CI + manifold scoring in <20s' },
      { icon: BookOpen, title: 'Compliance Agent', desc: 'FATF R10/R16, MiCA Art.83, jurisdiction blocklist + Groq reasoning' },
      { icon: Lock, title: 'ZK Agent', desc: 'Policy-aware circuit selection + witness construction' },
      { icon: Layers, title: 'Settlement Agent', desc: 'Autonomous chain dispatch with 5s retry' },
      { icon: Eye, title: 'Auditor Agent', desc: 'Human-readable reports + selective disclosure labels' },
      { icon: GitBranch, title: 'Shared State', desc: 'ComplianceState TypedDict with full field provenance' },
    ],
    why: [
      { icon: Award, title: 'Domain-specialised', body: 'Each agent is a focused expert — not a generalist LLM doing everything.' },
      { icon: Building2, title: 'Regulatory-aware', body: 'Compliance Agent applies named frameworks: FATF, MiCA, Travel Rule.' },
      { icon: Zap, title: 'Autonomous routing', body: 'Settlement Agent picks chain from policy context — no manual routing.' },
      { icon: Shield, title: 'Auditable', body: 'Every step logged to agent_executions with full trace.' },
    ],
    whyBadge: 'LangGraph + Groq (Llama 3.3 70B)',
    steps: [
      { n: 1, title: 'Intelligence', desc: 'Compute CI + manifold + jurisdiction_flag' },
      { n: 2, title: 'Compliance', desc: 'Apply FATF/MiCA/Travel Rule rules + Groq reasoning' },
      { n: 3, title: 'ZK', desc: 'Select circuit + generate proof' },
      { n: 4, title: 'Settlement', desc: 'Dispatch to Stellar or Casper' },
      { n: 5, title: 'Auditor', desc: 'Generate report + disclosure labels' },
    ],
    stats: [
      { value: '5', label: 'Agents' },
      { value: '70B', label: 'LLM Params' },
      { value: '<60s', label: 'Pipeline' },
    ],
  },
  {
    slug: 'audit-trail',
    name: 'Audit Trail',
    tagline: 'Immutable compliance decision lineage from graph data to on-chain proof.',
    category: 'Compliance',
    icon: GitBranch,
    heroColor: 'from-slate-600 to-slate-800',
    categoryColor: 'bg-slate-100 text-slate-700',
    overview: [
      'Every compliance decision is traceable back to its originating graph data and proof. The audit trail combines NRS/CI computation history, proof generation events, on-chain dispatch records, and incidents — sorted descending by occurred_at.',
      'GET /api/v1/audit/{entity_hash} returns the full lineage with run_id references linkable to agent execution logs.',
    ],
    capabilities: [
      { icon: Eye, title: 'Full lineage', desc: 'GET /api/v1/audit/{entity_hash} returns complete audit trail' },
      { icon: GitBranch, title: 'Run traces', desc: 'GET /api/v1/runs/{run_id} returns agent execution log' },
      { icon: Shield, title: 'Immutable', desc: 'Audit records cannot be deleted — only archived after 12 months' },
      { icon: Key, title: 'Admin-gated', desc: 'Audit endpoint requires admin API key authentication' },
      { icon: BarChart2, title: 'Payment audit', desc: 'GET /api/v1/payments/summary — 90-day retention' },
      { icon: FileCheck, title: 'Incident log', desc: 'GET /api/v1/incidents with pagination + status filter' },
    ],
    why: [
      { icon: Award, title: 'Regulatory-ready', body: 'Full lineage from graph data → CI → proof → on-chain dispatch.' },
      { icon: Building2, title: 'SOC-integrable', body: 'Structured security_events table for SIEM ingestion.' },
      { icon: Shield, title: 'Tamper-proof', body: 'On-chain records + immutable audit tables.' },
      { icon: Zap, title: 'Queryable', body: 'Filter by entity, decision, chain, time range.' },
    ],
    whyBadge: 'PostgreSQL + On-chain',
    steps: [
      { n: 1, title: 'Entity created', desc: 'POST /api/v1/entity logged' },
      { n: 2, title: 'CI computed', desc: 'compliance_index_computations record persisted' },
      { n: 3, title: 'Proof generated', desc: 'verifications record with proof_hex + status' },
      { n: 4, title: 'On-chain dispatch', desc: 'stellar_tx_hash or casper deploy_hash recorded' },
      { n: 5, title: 'Audit query', desc: 'GET /api/v1/audit/{entity_hash} returns full lineage' },
    ],
    stats: [
      { value: '12mo', label: 'Retention' },
      { value: '100%', label: 'Traceable' },
      { value: '0', label: 'Deletable' },
    ],
  },
  {
    slug: 'selective-disclosure',
    name: 'Selective Disclosure',
    tagline: 'Boolean pass/fail labels only — never factor values or weights.',
    category: 'Privacy',
    icon: Eye,
    heroColor: 'from-indigo-600 to-indigo-800',
    categoryColor: 'bg-indigo-50 text-indigo-700',
    overview: [
      'Regulated institutions can request selective disclosure of the compliance factors that produced a wallet\'s passport. The platform returns only boolean pass/fail per named dimension — e.g., ["AML_PASS", "SANCTIONS_CLEAR", "JURISDICTION_PERMITTED"].',
      'Factor values and weights are never disclosed. Disclosure responses are logged to the disclosure_audit table with requestor_key_hash, entity_hash, factors_disclosed, and request_signature.',
    ],
    capabilities: [
      { icon: Eye, title: 'POST /disclose', desc: 'Returns boolean labels only — never values or weights' },
      { icon: Key, title: 'Separate API key', desc: 'DISCLOSURE_API_KEY distinct from standard API key' },
      { icon: Shield, title: 'Signed requests', desc: 'disclosure_request signed by institution\'s registered key' },
      { icon: FileCheck, title: 'Audit logged', desc: 'disclosure_audit table with full request metadata' },
      { icon: Lock, title: 'PII-safe', desc: 'Only entity_hash exposed — never raw entity_id' },
      { icon: Zap, title: 'Fast response', desc: 'Sub-second disclosure for cached compliance state' },
    ],
    why: [
      { icon: Award, title: 'Privacy by default', body: 'Factor values never leave the platform. Only boolean labels.' },
      { icon: Building2, title: 'Audit-ready', body: 'Every disclosure request logged with requestor + signature.' },
      { icon: Shield, title: 'Regulator-friendly', body: 'Institutions get the labels they need for compliance audits.' },
      { icon: Zap, title: 'Minimal surface', body: 'Separate API key + signed requests = defence in depth.' },
    ],
    whyBadge: 'ED25519 Signed',
    steps: [
      { n: 1, title: 'Request signed', desc: 'Institution signs disclosure_request with registered key' },
      { n: 2, title: 'Auth validated', desc: 'DISCLOSURE_API_KEY + signature verified' },
      { n: 3, title: 'CI computed', desc: 'Current compliance state evaluated against thresholds' },
      { n: 4, title: 'Labels returned', desc: '["AML_PASS", "SANCTIONS_CLEAR", ...] — no values' },
      { n: 5, title: 'Audit logged', desc: 'disclosure_audit record persisted' },
    ],
    stats: [
      { value: '0', label: 'Values Disclosed' },
      { value: '100%', label: 'Audit Logged' },
      { value: 'ED25519', label: 'Signed' },
    ],
  },
  {
    slug: 'api-gateway',
    name: 'API Gateway',
    tagline: 'FastAPI REST gateway with bcrypt auth, rate limiting, and structured logging.',
    category: 'Integration',
    icon: Key,
    heroColor: 'from-cyan-600 to-cyan-800',
    categoryColor: 'bg-cyan-50 text-cyan-700',
    overview: [
      'The FastAPI REST gateway is the single entry point for all platform services. It enforces bcrypt-hashed API key authentication, per-key rate limiting (60 RPM default, 600 RPM max), and structured security event logging.',
      'OpenAPI documentation is auto-generated at /docs. All endpoints return application/json with X-Request-ID headers for traceability.',
    ],
    capabilities: [
      { icon: Key, title: 'API Key Auth', desc: 'POST /api/v1/keys — bcrypt-hashed, plaintext returned once' },
      { icon: Shield, title: 'Rate Limiting', desc: 'Token bucket, 60 RPM default, 429 with Retry-After' },
      { icon: Zap, title: 'Admin Endpoints', desc: 'X-Admin-Secret gated key management + jurisdiction refresh' },
      { icon: BookOpen, title: 'OpenAPI Docs', desc: 'GET /docs — auto-generated, no auth required' },
      { icon: FileCheck, title: 'Request Tracing', desc: 'X-Request-ID UUID in every response header' },
      { icon: Eye, title: 'Security Events', desc: 'AUTH_FAILURE, RATE_LIMIT_EXCEEDED logged to security_events' },
    ],
    why: [
      { icon: Award, title: 'Production-grade', body: 'bcrypt hashing, rate limiting, structured logging — enterprise-ready.' },
      { icon: Building2, title: 'Developer-friendly', body: 'OpenAPI docs + request tracing = easy integration.' },
      { icon: Shield, title: 'Abuse-resistant', body: 'Per-key rate limits prevent resource exhaustion.' },
      { icon: Zap, title: 'Fast', body: 'Sub-5s response for standard requests (30s SLA for proof generation).' },
    ],
    whyBadge: 'FastAPI + Uvicorn',
    steps: [
      { n: 1, title: 'Create API key', desc: 'POST /api/v1/keys with admin secret' },
      { n: 2, title: 'Authenticate', desc: 'X-API-Key header on every request' },
      { n: 3, title: 'Call endpoints', desc: 'Entity, relationship, NRS, proof, credential' },
      { n: 4, title: 'Monitor usage', desc: 'GET /api/v1/payments/summary for audit' },
      { n: 5, title: 'Adjust limits', desc: 'POST /api/v1/keys/{id}/limit up to 600 RPM' },
    ],
    stats: [
      { value: '60', label: 'Default RPM' },
      { value: '600', label: 'Max RPM' },
      { value: '<5s', label: 'Response' },
    ],
  },
  {
    slug: 'enterprise-security',
    name: 'Enterprise Security',
    tagline: 'AES-256-GCM encryption, SHA-256 hashing, SOC-ready logging.',
    category: 'Security',
    icon: Shield,
    heroColor: 'from-gray-700 to-gray-900',
    categoryColor: 'bg-gray-100 text-gray-700',
    overview: [
      'Built for regulated markets. RESTRICTED fields (raw entity IDs, NRS values) are encrypted at rest with AES-256-GCM. SHA-256 entity hashing ensures PII never appears on-chain or in logs.',
      'Structured security event logging supports SOC/SIEM ingestion. CRITICAL events (VERDICT_REVOKED, multiple AUTH_FAILURE) trigger webhooks to SECURITY_ALERT_WEBHOOK_URL.',
    ],
    capabilities: [
      { icon: Lock, title: 'AES-256-GCM', desc: 'Encryption at rest for RESTRICTED fields' },
      { icon: Eye, title: 'SHA-256 Hashing', desc: 'entity_hash = SHA256(entity_id + ENTITY_SALT)' },
      { icon: Shield, title: 'Data Classification', desc: 'PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED' },
      { icon: FileCheck, title: 'Security Events', desc: 'AUTH_FAILURE, RATE_LIMIT_EXCEEDED, PROOF_GENERATED, etc.' },
      { icon: Zap, title: 'Async Logging', desc: 'Non-blocking, <500ms, CRITICAL webhooks' },
      { icon: Key, title: 'SOC-Ready', desc: 'Structured security_events table for SIEM ingestion' },
    ],
    why: [
      { icon: Award, title: 'Regulatory-grade', body: 'Built to meet KYC/AML data handling standards in regulated markets.' },
      { icon: Building2, title: 'PII minimised', body: 'SHA-256 hashing everywhere on-chain and in logs.' },
      { icon: Shield, title: 'Encrypted at rest', body: 'AES-256-GCM for sensitive fields — keys from env vars.' },
      { icon: Zap, title: 'SOC-integrable', body: 'Structured events + CRITICAL webhooks = SIEM-ready.' },
    ],
    whyBadge: 'AES-256-GCM + SHA-256',
    steps: [
      { n: 1, title: 'Classify data', desc: 'PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED' },
      { n: 2, title: 'Hash PII', desc: 'SHA-256(entity_id + ENTITY_SALT) for all on-chain refs' },
      { n: 3, title: 'Encrypt at rest', desc: 'AES-256-GCM for RESTRICTED fields' },
      { n: 4, title: 'Log events', desc: 'security_events table with async writes' },
      { n: 5, title: 'Alert on CRITICAL', desc: 'Webhook to SECURITY_ALERT_WEBHOOK_URL' },
    ],
    stats: [
      { value: 'AES-256', label: 'Encryption' },
      { value: 'SHA-256', label: 'Hashing' },
      { value: '<500ms', label: 'Log Latency' },
    ],
  },
]

export function getFeature(slug: string): FeatureData | undefined {
  return FEATURES.find(f => f.slug === slug)
}