"""
EIP-712 typed-data signing for Casper — ZK-KYC Compliance Agent (zkkyc.signing)

Implements casper-eip-712 style typed-data signing for off-chain compliance
attestations. Structured payloads are signed so downstream protocols can verify
attestation provenance without trusting a raw ED25519 signature.

Spec reference: EP-08 augmentation (casper-eip-712), EP-02 (F-02.2.3),
                EP-03 (F-03.2.2)
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TypedDataField:
    name: str
    type: str


@dataclass
class EIP712Domain:
    name: str
    version: str
    chain_id: int
    verifying_contract: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "chainId": self.chain_id,
            "verifyingContract": self.verifying_contract,
        }


@dataclass
class TypedData:
    domain: EIP712Domain
    types: dict[str, list[TypedDataField]]
    primary_type: str
    message: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain.to_dict(),
            "types": {
                k: [{"name": f.name, "type": f.type} for f in v]
                for k, v in self.types.items()
            },
            "primaryType": self.primary_type,
            "message": self.message,
        }


@dataclass
class SignedAttestation:
    signed_payload: str
    signature: str
    domain_separator: str
    message_hash: str
    signer_public_key: str
    signed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# Domain separator + hashing
# ---------------------------------------------------------------------------

def _hash_struct(struct_type: str, data: dict[str, Any]) -> bytes:
    """Encode a typed struct and return its keccak-256 hash (EIP-712 style).

    Casper uses ED25519, not ECDSA, so the actual signature scheme differs,
    but the typed-data envelope and domain separator follow EIP-712 conventions
    so that downstream verifiers can validate payload structure independently
    of the signature algorithm.
    """
    encoded = json.dumps(data, separators=(",", ":"), sort_keys=True).encode()
    type_hash = hashlib.sha256(struct_type.encode()).digest()
    data_hash = hashlib.sha256(encoded).digest()
    return hashlib.sha256(type_hash + data_hash).digest()


def compute_domain_separator(domain: EIP712Domain) -> bytes:
    domain_hash = _hash_struct("EIP712Domain", domain.to_dict())
    return hashlib.sha256(b"EIP712Domain()" + domain_hash).digest()


def build_message_hash(typed_data: TypedData) -> bytes:
    domain_sep = compute_domain_separator(typed_data.domain)
    struct_hash = _hash_struct(typed_data.primary_type, typed_data.message)
    return hashlib.sha256(domain_sep + struct_hash).digest()


# ---------------------------------------------------------------------------
# Signer
# ---------------------------------------------------------------------------

class ComplianceAttestationSigner:
    """Signs structured compliance attestations using ED25519 keys.

    The signer follows the casper-eip-712 envelope so that payloads carry
    a verifiable domain separator and type information, while the actual
    signature uses Casper-native ED25519.
    """

    def __init__(
        self,
        private_key_hex: str | None = None,
        domain: EIP712Domain | None = None,
    ):
        if private_key_hex:
            self._private_key = Ed25519PrivateKey.from_private_bytes(
                bytes.fromhex(private_key_hex)
            )
        else:
            self._private_key = Ed25519PrivateKey.generate()

        self._public_key_bytes = self._private_key.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )
        self._public_key_hex = self._public_key_bytes.hex()
        self._domain = domain or EIP712Domain(
            name="ZKCO Compliance Oracle",
            version="1",
            chain_id=1,
            verifying_contract="",
        )

    @property
    def public_key_hex(self) -> str:
        return self._public_key_hex

    def sign(self, typed_data: TypedData) -> SignedAttestation:
        message_hash = build_message_hash(typed_data)
        signature_bytes = self._private_key.sign(message_hash)
        signature_hex = signature_bytes.hex()
        payload_hex = message_hash.hex()
        domain_sep_hex = compute_domain_separator(self._domain).hex()

        return SignedAttestation(
            signed_payload=payload_hex,
            signature=signature_hex,
            domain_separator=domain_sep_hex,
            message_hash=payload_hex,
            signer_public_key=self._public_key_hex,
        )

    def sign_compliance_attestation(
        self,
        entity_hash: str,
        policy_id: str,
        expires_at: int,
        chain_target: str,
        decision: str = "PASS",
        confidence: float = 1.0,
    ) -> SignedAttestation:
        typed_data = TypedData(
            domain=self._domain,
            types={
                "ComplianceAttestation": [
                    TypedDataField("entityHash", "bytes32"),
                    TypedDataField("policyId", "string"),
                    TypedDataField("expiresAt", "uint64"),
                    TypedDataField("chainTarget", "string"),
                    TypedDataField("decision", "string"),
                    TypedDataField("confidence", "uint256"),
                ],
                "EIP712Domain": [
                    TypedDataField("name", "string"),
                    TypedDataField("version", "string"),
                    TypedDataField("chainId", "uint256"),
                    TypedDataField("verifyingContract", "address"),
                ],
            },
            primary_type="ComplianceAttestation",
            message={
                "entityHash": entity_hash,
                "policyId": policy_id,
                "expiresAt": expires_at,
                "chainTarget": chain_target,
                "decision": decision,
                "confidence": int(confidence * 10000),
            },
        )
        return self.sign(typed_data)
