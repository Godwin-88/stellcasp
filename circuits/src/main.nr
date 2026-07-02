// Zero-Knowledge Compliance Oracle — Multi-Condition Policy Circuit
// circuits/src/main.nr
//
// Spec: EP-02, F-02.1, US-02.1.1
//
// Proof statement (what a valid proof asserts to the verifier):
//   "The entity's Compliance Index is below the policy ceiling,
//    the entity belongs to a sufficiently low-risk behavioural manifold,
//    and the entity's jurisdiction is in the permitted set —
//    WITHOUT revealing the CI value, individual factor weights, graph
//    topology, manifold score, or entity identity."
//
// Private inputs (known only to the prover, never on-chain):
//   compliance_index  — CI × 1_000_000, scaled to u64 to avoid field arithmetic.
//                       Derived from six-factor weighted sum (EP-01 F-01.4).
//   manifold_score    — Behavioural manifold membership score × 1_000_000.
//                       Derived from Node2Vec k-means cluster distance (EP-01 F-01.5).
//   jurisdiction_flag — 0 if entity jurisdiction is in the FATF permitted set,
//                       1 if restricted. Derived from jurisdiction_risk table (EP-01 F-01.4.3).
//
// Public inputs (visible on-chain, embedded in the proof's public_inputs vector):
//   ci_threshold        — Policy ceiling for the Compliance Index (× 1_000_000).
//                         Default: 750_000 (i.e. CI < 0.75).
//   manifold_threshold  — Minimum manifold score required (× 1_000_000).
//                         Default: 200_000 (i.e. manifold_score ≥ 0.20).
//   policy_id           — Field element identifying the compliance policy version.
//                         Allows the verifier contract to reject proofs generated
//                         against a superseded policy without redeploying the circuit.
//
// Constraint count: 3 constraints (one per assert). No loops, no dynamic arrays,
// no recursion. Constraint count is deliberately minimal — the computational
// complexity lives entirely in the off-chain Python intelligence layer that
// produces the private witnesses; the circuit only enforces the policy boundary.
// Document verified constraint count in circuits/README.md after `nargo compile`.
//
// Compile:  nargo compile
// Check:    nargo check          (must pass with zero warnings)
// Prove:    nargo prove          (requires Prover.toml in circuit root)
// Verify:   nargo verify         (requires Verifier.toml in circuit root)
//
// Prover.toml format:
//   compliance_index = <u64>      # e.g. 420000  (CI = 0.42)
//   manifold_score   = <u64>      # e.g. 650000  (manifold = 0.65)
//   jurisdiction_flag = <u64>     # 0 or 1
//   ci_threshold     = <u64>      # e.g. 750000
//   manifold_threshold = <u64>    # e.g. 200000
//   policy_id        = <Field>    # e.g. 1  (policy version integer as field element)
//
// Verifier.toml format (public inputs only):
//   ci_threshold       = <u64>
//   manifold_threshold = <u64>
//   policy_id          = <Field>

fn main(
    // --- Private witnesses (not in proof; known only to prover) ---
    compliance_index: u64,      // CI × 1_000_000
    manifold_score:   u64,      // manifold membership × 1_000_000
    jurisdiction_flag: u64,     // 0 = permitted, 1 = restricted

    // --- Public inputs (embedded in proof; visible to verifier contract) ---
    ci_threshold:        pub u64,   // policy CI ceiling × 1_000_000
    manifold_threshold:  pub u64,   // minimum required manifold score × 1_000_000
    policy_id:           pub Field, // compliance policy version identifier
) {
    // Condition 1 — AML / KYC / Sanctions / FATF: Compliance Index below policy ceiling.
    // The CI encodes weighted sanctions exposure, AML topology, counterparty risk,
    // liquidity risk, jurisdiction risk, and behavioural risk (EP-01 F-01.4).
    // A lower CI is better; the proof asserts the entity is below the policy threshold.
    assert(compliance_index < ci_threshold);

    // Condition 2 — Behavioural Manifold: wallet belongs to a sufficiently
    // low-risk behavioural cluster per Node2Vec embedding analysis (EP-01 F-01.5).
    // A higher manifold_score is better (closer to low-risk centroid).
    // The proof asserts the entity exceeds the minimum manifold score required
    // by this policy — a meaningfully stronger claim than "PageRank was low".
    assert(manifold_score >= manifold_threshold);

    // Condition 3 — Jurisdiction: entity's domicile is in the FATF permitted set.
    // jurisdiction_flag == 0 means permitted; == 1 means restricted (grey/black list).
    // This assertion ensures the proof is invalid for any restricted-jurisdiction entity
    // regardless of how low their CI or how high their manifold score.
    assert(jurisdiction_flag == 0);

    // policy_id is bound into the public inputs of the proof. The Soroban verifier
    // contract checks that the policy_id in the proof matches the active policy
    // before accepting the attestation — preventing proofs generated against a
    // superseded policy from being replayed under a newer, stricter policy version.
    // No explicit assertion needed here: binding it as `pub` is sufficient to
    // include it in the proof's public input vector and make it verifier-checkable.
    // The _ suppresses any unused-variable warning from nargo check.
    let _ = policy_id;
}