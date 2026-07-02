# Privacy Audit Report Template

## Data Flow Documentation

### PII Handling

1. **Entity Identification**
   - Raw entity IDs are salted and hashed with SHA-256 (`entity_salt` env var)
   - `hash_entity_id(entity_id) -> entity_hash` used for all on-chain references
   - Original `entity_id` stored only in encrypted `entity_mappings` table

2. **On-Chain Data**
   - Only `entity_hash` is emitted in contract events
   - NRS values never stored on-chain, only proof verification
   - No PII in event topics or data payloads

3. **API Logging**
   - All API logs use `entity_hash` as identifier
   - Request IDs for traceability without PII

4. **Agent Execution Logs**
   - `step_log` excludes `proof_hex` in API responses
   - Audit endpoint requires admin authentication

### Compliance Controls

- **Data Retention**: RESTRICTED data purged after 7 years (AML requirement)
- **Access Logging**: All access to RESTRICTED data logged in `security_events`
- **Encryption**: AES-256-GCM for data at rest, TLS 1.3 for transit
- **Minimisation**: Only essential data collected, no document storage

### Audit Checklist

- [ ] Entity hashing verified in all on-chain calls
- [ ] NRS values not present in API responses
- [ ] Proof hex filtered from audit endpoints
- [ ] Security events captured for all access
- [ ] Data encryption verified in PostgreSQL