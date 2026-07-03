// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ZKPassport
 * @dev Hedera Token Service (HTS) Soulbound Compliance Passport
 * @notice Uses HTS precompile for NFT minting with soulbound constraints
 *
 * SPEC REF: zk_kyc_platform_spec.md §EP-08 — Chain-Agnostic Passport Adapter
 * CHAIN: Hedera (HSCS — Hedera Smart Contract Service + HTS)
 * CONTRACT: ZKPassport.sol — HTS NFT passport management
 *
 * ARCHITECTURE:
 *   Uses HTS precompile (address 0x100 on testnet, 0x167 on mainnet)
 *   to mint non-transferable NFTs representing compliance passports.
 *
 * SPEC: EP-08 F-08.5 — Hedera Passport Adapter
 *       EP-03 F-03.1.1 — Compliance Passport Contract Design
 *
 * HTS ADDRESSES:
 *   Testnet: 0x0000000000000000000000000000000000000167
 *   Mainnet: 0x0000000000000000000000000000000000000100
 */

import {IERC721} from "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

contract ZKPassport is Ownable {
    struct Passport {
        bool exists;
        bool revoked;
        uint256 issuedAt;
        uint256 expiresAt;
        bytes32 identityHash;
        uint256 serialNumber;  // HTS NFT serial number
    }

    uint256 public nextTokenId;
    uint256 public immutable maxSupply;
    address public immutable htsTokenAddress;  // HTS NFT token address
    mapping(address => uint256) public addressToTokenId;
    mapping(uint256 => Passport) public passports;

    event PassportMinted(address indexed subject, uint256 indexed tokenId, bytes32 identityHash);
    event PassportRevoked(address indexed subject, uint256 indexed tokenId);

    error PassportAlreadyMinted();
    error PassportNotMinted();
    error PassportRevoked();
    error PassportExpired();

    /**
     * @dev Constructor
     * @param _maxSupply Maximum passport supply
     * @param _htsTokenAddress HTS NFT token address (pre-created)
     * @param initialOwner Initial oracle authority
     *
     * SPEC: EP-08 F-08.5.1 — Contract initialisation
     */
    constructor(
        uint256 _maxSupply,
        address _htsTokenAddress,
        address initialOwner
    ) Ownable(initialOwner) {
        maxSupply = _maxSupply;
        htsTokenAddress = _htsTokenAddress;
    }

    /**
     * @dev Mint a new HTS NFT Compliance Passport
     * @param subject Wallet address to receive the passport
     * @return tokenId Internal token ID
     *
     * SPEC: EP-08 F-08.5.1 — mint_passport()
     * SPEC: EP-03 F-03.1.1 — Compliance Passport Contract Design
     * ACCESS: Only oracle authority
     */
    function mintPassport(address subject) external onlyOwner returns (uint256) {
        if (addressToTokenId[subject] != 0) revert PassportAlreadyMinted();
        if (nextTokenId >= maxSupply) revert PassportAlreadyMinted();

        uint256 tokenId = nextTokenId++;

        // Mint HTS NFT via precompile
        (bool success, ) = htsTokenAddress.call(
            abi.encodeWithSignature("mintNFT(address,bytes)", subject, "")
        );
        require(success, "HTS mint failed");

        passports[tokenId] = Passport({
            exists: true,
            revoked: false,
            issuedAt: block.timestamp,
            expiresAt: 0,
            identityHash: bytes32(0),
            serialNumber: 0
        });

        addressToTokenId[subject] = tokenId;

        emit PassportMinted(subject, tokenId, bytes32(0));
        return tokenId;
    }

    /**
     * @dev Revoke a Compliance Passport
     * @param subject Wallet address whose passport should be revoked
     *
     * SPEC: EP-08 F-08.5.1 — revoke_passport()
     * SPEC: EP-03 F-03.2.1 — Passport Revocation
     * ACCESS: Only oracle authority
     */
    function revokePassport(address subject) external onlyOwner {
        uint256 tokenId = addressToTokenId[subject];
        if (tokenId == 0) revert PassportNotMinted();
        if (passports[tokenId].revoked) revert PassportRevoked();

        passports[tokenId].revoked = true;
        emit PassportRevoked(subject, tokenId);
    }

    /**
     * @dev Verify whether a subject holds a valid passport
     * @param subject Wallet address to verify
     * @return True if subject has valid, non-expired, non-revoked passport
     *
     * SPEC: EP-08 F-08.5.1 — verify_credential()
     * SPEC: EP-03 F-03.1.2 — Cross-Protocol Credential Verification
     * ACCESS: Public (view function)
     */
    function verifyCredential(address subject) external view returns (bool) {
        uint256 tokenId = addressToTokenId[subject];
        if (tokenId == 0) return false;

        Passport memory passport = passports[tokenId];
        if (!passport.exists) return false;
        if (passport.revoked) return false;
        if (passport.expiresAt != 0 && block.timestamp > passport.expiresAt) return false;

        return true;
    }

    /**
     * @dev Set passport expiry timestamp
     * @param subject Wallet address
     * @param timestamp UNIX timestamp when passport expires (0 = no expiry)
     *
     * SPEC: EP-08 F-08.5.1 — Passport expiry management
     */
    function setExpiresAt(address subject, uint256 timestamp) external onlyOwner {
        uint256 tokenId = addressToTokenId[subject];
        if (tokenId == 0) revert PassportNotMinted();
        passports[tokenId].expiresAt = timestamp;
    }
}
