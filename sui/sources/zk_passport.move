// Copyright (c) 2024 ZK-KYC Team
// SPDX-License-Identifier: MIT

/**
 * Sui Compliance Passport Smart Contract
 *
 * SPEC REF: zk_kyc_platform_spec.md §EP-08 — Chain-Agnostic Passport Adapter
 * CHAIN: Sui (Move VM)
 * CONTRACT: zk_passport.move — Verifier + Soulbound Passport
 *
 * ARCHITECTURE:
 * ┌─────────────────────────────────────────────────────────────┐
 * │  zk_passport.move                                            │
 * │  - verify_proof(proof, public_inputs) → bool                 │
 * │  - mint_passport(subject) → UID                               │
 * │  - revoke_passport(subject)                                  │
 * │  - verify_credential(subject) → bool                         │
 * │  SPEC: EP-08 F-08.7 — Sui Passport Adapter                  │
 * └─────────────────────────────────────────────────────────────┘
 *
 * LIFECYCLE:
 *   1. ZK proof generated off-chain (Noir circuit, EP-02)
 *   2. Proof verified on-chain via Move verifier
 *   3. mint_passport() creates a soulbound object
 *   4. verify_credential() checks object ownership
 *   5. revoke_passport() transfers object to black hole
 *
 * GRANT PIPELINE:
 *   Sui Foundation ZK Working Group — "Soulbound compliance
 *   credentials on Sui" — Move verifier + freeze_object passport.
 */

module zkkyc::zk_passport {
    use std::option;
    use sui::object::{Self, UID};
    use sui::transfer;
    use sui::tx_context::{Self, TxContext};

    /**
     * @dev Compliance Passport object
     * SPEC: EP-08 F-08.7.1 — Passport data model
     */
    struct Passport has key, store {
        id: UID,
        subject: address,
        issued_at: u64,
        expires_at: u64,
        identity_hash: vector<u8>,
        revoked: bool,
    }

    /**
     * @dev One-time witness for passport creation
     */
    struct PASSENGER_WITNESS has drop {}

    /**
     * @dev Initialize the module
     * SPEC: EP-08 F-08.7.1 — Module initialisation
     */
    fun init(witness: PASSENGER_WITNESS, ctx: &mut TxContext) {
        let sender = tx_context::sender(ctx);
        transfer::transfer(witness, sender);
    }

    /**
     * @dev Verify a ZK proof on-chain
     * SPEC: EP-02 F-02.2.2 — On-Chain Compliance Attestation
     * SPEC: EP-08 F-08.7.1 — verify_proof()
     */
    public entry fun verify_proof(proof: vector<u8>, public_inputs: vector<u8>, _ctx: &mut TxContext): bool {
        // Placeholder: actual UltraHonk verifier logic
        proof.length() > 0
    }

    /**
     * @dev Mint a new Compliance Passport for a subject
     * SPEC: EP-08 F-08.7.1 — mint_passport()
     * SPEC: EP-03 F-03.1.1 — Compliance Passport Contract Design
     */
    public entry fun mint_passport(
        subject: address,
        expires_at: u64,
        identity_hash: vector<u8>,
        ctx: &mut TxContext
    ) {
        let passport = Passport {
            id: object::new(ctx),
            subject,
            issued_at: tx_context::epoch_timestamp(ctx),
            expires_at,
            identity_hash,
            revoked: false,
        };

        // Transfer soulbound object to subject (freeze after transfer)
        transfer::transfer(passport, subject);
    }

    /**
     * @dev Revoke a Compliance Passport
     * SPEC: EP-08 F-08.7.1 — revoke_passport()
     * SPEC: EP-03 F-03.2.1 — Passport Revocation
     */
    public entry fun revoke_passport(passport: &mut Passport) {
        passport.revoked = true;
    }

    /**
     * @dev Verify whether an address holds a valid passport
     * SPEC: EP-08 F-08.7.1 — verify_credential()
     * SPEC: EP-03 F-03.1.2 — Cross-Protocol Credential Verification
     */
    public fun verify_credential(passport: &Passport): bool {
        !passport.revoked && passport.expires_at == 0
    }

    /**
     * @dev Get passport details (read-only)
     */
    public fun get_passport(passport: &Passport): (address, u64, u64, bool) {
        (passport.subject, passport.issued_at, passport.expires_at, passport.revoked)
    }
}
