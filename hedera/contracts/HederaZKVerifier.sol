// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title HederaZKVerifier
 * @dev UltraHonk ZK proof verifier for Hedera Smart Contract Service (HSCS)
 * @notice Delegates proof verification to pre-deployed verifier
 *
 * SPEC REF: zk_kyc_platform_spec.md §EP-02 — Zero-Knowledge Compliance Oracle Circuit
 *           EP-08 F-08.5 — Hedera Passport Adapter
 * CHAIN: Hedera (HSCS — Hedera Smart Contract Service)
 * CONTRACT: HederaZKVerifier.sol — Verifier contract for HTS passport
 *
 * ARCHITECTURE:
 * ┌─────────────────────────────────────────────────────────────┐
 * │  HederaZKVerifier.sol                                        │
 * │  - verifyProof(proof, publicInputs) → bool                   │
 * │  - Delegates to pre-deployed UltraVerifier on HSCS          │
 * │  SPEC: EP-02 F-02.2 — Soroban Verifier adapted for HSCS      │
 * └─────────────────────────────────────────────────────────────┘
 *                             │
 *                             ▼
 * ┌─────────────────────────────────────────────────────────────┐
 * │  ZKPassport.sol (HTS NFT)                                    │
 * │  - mint_passport(subject) → tokenId                          │
 * │  - revoke_passport(subject)                                  │
 * │  - verify_credential(subject) → bool                         │
 * │  SPEC: EP-08 F-08.5 — Hedera Passport Adapter               │
 * │  Uses HTS precompile for soulbound NFT minting               │
 * └─────────────────────────────────────────────────────────────┘
 *
 * GRANT PIPELINE:
 *   HBAR Foundation Grants — "Compliance infrastructure for Hedera
 *   enterprise DeFi" — HTS NFT passport + HSCS verifier.
 */

import {UltraVerifier} from "./UltraVerifier.sol";

contract HederaZKVerifier {
    UltraVerifier public immutable verifier;

    /**
     * @dev Constructor
     * @param verifierAddress Address of pre-deployed UltraVerifier on HSCS
     *
     * SPEC: EP-02 F-02.2.1 — Verifier deployment on Hedera
     */
    constructor(address verifierAddress) {
        verifier = UltraVerifier(verifierAddress);
    }

    /**
     * @dev Verify a Noir UltraHonk proof
     * @param proof Serialized UltraHonk proof bytes
     * @param publicInputs Serialized public inputs
     * @return True if proof is valid
     *
     * SPEC: EP-02 F-02.2.2 — On-Chain Compliance Attestation
     */
    function verifyProof(
        bytes calldata proof,
        bytes calldata publicInputs
    ) external view returns (bool) {
        return verifier.verify(proof, publicInputs);
    }
}
