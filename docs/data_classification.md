# Data Classification Manifest

## Classification Schema

| Classification | Description | Handling Requirements |
|----------------|-------------|---------------------|
| PUBLIC | Non-sensitive data safe for public release | No special controls |
| INTERNAL | Operational data for internal use | Access control required |
| CONFIDENTIAL | Business-sensitive data | Encryption at rest, access logging |
| RESTRICTED | PII, risk scores, compliance data | AES-256-GCM encryption, strict access control |

## Data Asset Classification

| Asset | Table/Field | Classification | Controls Applied |
|-------|-------------|----------------|----------------|
| Entity Graph | `Entity.id` | RESTRICTED | SHA-256 hashing with salt, never logged |
| | `Entity.type` | INTERNAL | Access control via API key |
| | Transaction relationships | INTERNAL | Graph-level access control |
| NRS Computation | `nrs_computations.nrs` | RESTRICTED | AES-256-GCM encrypted |
| | `nrs_computations.components_json` | CONFIDENTIAL | Database access control |
| ZK Proofs | Proof hex | RESTRICTED | Encrypted in transit, never stored in plaintext |
| API Keys | `api_keys.key_hash` | RESTRICTED | bcrypt hashed, rotated annually |
| Payment Data | `payment_receipts.*` | CONFIDENTIAL | Database access control |
| Security Events | `security_events.*` | CONFIDENTIAL | SIEM integration, retention 90 days |
| Agent Execution | `agent_executions.step_log` | INTERNAL | PII filtered in logs |

## Encryption Implementation

All RESTRICTED fields use AES-256-GCM with keys loaded from `DATA_ENCRYPTION_KEY` environment variable.