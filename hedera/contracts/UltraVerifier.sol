// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title UltraVerifier
 * @dev Interface for UltraHonk ZK proof verifier on Hedera HSCS
 *
 * SPEC REF: zk_kyc_platform_spec.md §EP-02 — Zero-Knowledge Compliance Oracle Circuit
 *           EP-08 F-08.5 — Hedera Passport Adapter
 * CHAIN: Hedera (HSCS)
 * CONTRACT: UltraVerifier.sol — Interface for pre-deployed verifier
 *
 * SPEC: EP-02 F-02.2.1 — Verifier Contract Deployment (Hedera)
 */

interface IUltraVerifier {
    function verify(bytes calldata proof, bytes calldata publicInputs) external view returns (bool);
}

interface UltraVerifier is IUltraVerifier {}
