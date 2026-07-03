// Copyright (c) 2024 ZK-KYC Team
// SPDX-License-Identifier: MIT

/**
 * ICP Compliance Passport Canister
 *
 * SPEC REF: zk_kyc_platform_spec.md §EP-08 — Chain-Agnostic Passport Adapter
 * CHAIN: ICP/DFINITY (Internet Computer)
 * CONTRACT: lib.rs — Canister verifier + Internet Identity passport
 *
 * ARCHITECTURE:
 * ┌─────────────────────────────────────────────────────────────┐
 * │  lib.rs (Rust Canister)                                      │
 * │  - verify_proof(proof, public_inputs) → bool                 │
 * │  - mint_passport(principal) → passport_id                    │
 * │  - revoke_passport(passport_id)                              │
 * │  - verify_credential(principal) → bool                       │
 * │  SPEC: EP-08 F-08.9 — ICP Passport Adapter                  │
 * └─────────────────────────────────────────────────────────────┘
 *
 * LIFECYCLE:
 *   1. ZK proof generated off-chain (Noir circuit, EP-02)
 *   2. Proof verified on-chain via canister verifier
 *   3. mint_passport() creates a passport record linked to II principal
 *   4. verify_credential() checks passport status
 *   5. revoke_passport() marks passport as revoked
 *
 * GRANT PIPELINE:
 *   DFINITY Foundation — "ZK-verified compliance on Internet Computer"
 *   — Canister verifier + Internet Identity-linked passport.
 */

use ic_cdk_macros::{query, update};
use ic_cdk::storage;
use std::cell::RefCell;
use std::collections::HashMap;

/// Passport data structure
/// SPEC: EP-08 F-08.9.1 — Passport data model
#[derive(Clone, Debug, candid::CandidType, serde::Serialize, serde::Deserialize)]
pub struct Passport {
    pub id: u64,
    pub subject: String,  // Internet Identity principal
    pub issued_at: u64,
    pub expires_at: u64,
    pub identity_hash: String,
    pub revoked: bool,
}

/// ZK proof input structure
#[derive(Clone, Debug, candid::CandidType, serde::Serialize, serde::Deserialize)]
pub struct ProofInput {
    pub proof_hex: String,
    pub public_inputs: Vec<String>,
}

thread_local! {
    static PASSPORTS: RefCell<HashMap<u64, Passport>> = RefCell::new(HashMap::new());
    static NEXT_ID: RefCell<u64> = RefCell::new(1);
    static SUBJECT_TO_ID: RefCell<HashMap<String, u64>> = RefCell::new(HashMap::new());
}

/**
 * @dev Verify a ZK proof on-chain
 * SPEC: EP-02 F-02.2.2 — On-Chain Compliance Attestation
 * SPEC: EP-08 F-08.9.1 — verify_proof()
 */
#[query]
fn verify_proof(proof: ProofInput) -> bool {
    // Placeholder: actual UltraHonk verifier logic
    !proof.proof_hex.is_empty()
}

/**
 * @dev Mint a new Compliance Passport for a subject
 * SPEC: EP-08 F-08.9.1 — mint_passport()
 * SPEC: EP-03 F-03.1.1 — Compliance Passport Contract Design
 */
#[update]
fn mint_passport(subject: String, expires_at: u64, identity_hash: String) -> u64 {
    let id = NEXT_ID.with(|n| {
        let current = *n.borrow();
        *n.borrow_mut() = current + 1;
        current
    });

    let passport = Passport {
        id,
        subject: subject.clone(),
        issued_at: ic_cdk::api::time(),
        expires_at,
        identity_hash,
        revoked: false,
    };

    PASSPORTS.with(|p| {
        p.borrow_mut().insert(id, passport);
    });

    SUBJECT_TO_ID.with(|m| {
        m.borrow_mut().insert(subject, id);
    });

    id
}

/**
 * @dev Revoke a Compliance Passport
 * SPEC: EP-08 F-08.9.1 — revoke_passport()
 * SPEC: EP-03 F-03.2.1 — Passport Revocation
 */
#[update]
fn revoke_passport(passport_id: u64) -> bool {
    PASSPORTS.with(|p| {
        if let Some(passport) = p.borrow_mut().get_mut(&passport_id) {
            passport.revoked = true;
            true
        } else {
            false
        }
    })
}

/**
 * @dev Verify whether a subject holds a valid passport
 * SPEC: EP-08 F-08.9.1 — verify_credential()
 * SPEC: EP-03 F-03.1.2 — Cross-Protocol Credential Verification
 */
#[query]
fn verify_credential(subject: String) -> bool {
    SUBJECT_TO_ID.with(|m| {
        if let Some(&passport_id) = m.borrow().get(&subject) {
            PASSPORTS.with(|p| {
                if let Some(passport) = p.borrow().get(&passport_id) {
                    !passport.revoked && passport.expires_at == 0
                } else {
                    false
                }
            })
        } else {
            false
        }
    })
}

/**
 * @dev Get passport details
 */
#[query]
fn get_passport(passport_id: u64) -> Option<Passport> {
    PASSPORTS.with(|p| p.borrow().get(&passport_id).cloned())
}

ic_cdk::export_candid!();
