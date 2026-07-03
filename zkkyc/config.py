import functools
from dataclasses import dataclass
import os


@dataclass
class Settings:
    # ---------------------------------------------------------------------------
    # Database connections
    # ---------------------------------------------------------------------------
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "password")
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_user: str = os.getenv("POSTGRES_USER", "zkkyc")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "password")
    postgres_db: str = os.getenv("POSTGRES_DB", "zkkyc")

    # ---------------------------------------------------------------------------
    # Security & Privacy (EP-07)
    # ---------------------------------------------------------------------------
    entity_salt: str = os.getenv("ENTITY_SALT", "")
    platform_signing_key: str = os.getenv("PLATFORM_SIGNING_KEY", "")
    data_encryption_key: str = os.getenv("DATA_ENCRYPTION_KEY", "")
    disclosure_api_key: str = os.getenv("DISCLOSURE_API_KEY", "")

    # ---------------------------------------------------------------------------
    # Compliance thresholds (EP-01, EP-02)
    # ---------------------------------------------------------------------------
    high_risk_nrs_threshold: float = float(os.getenv("HIGH_RISK_NRS_THRESHOLD", "0.75"))
    manifold_threshold: float = float(os.getenv("MANIFOLD_THRESHOLD", "0.20"))

    # ---------------------------------------------------------------------------
    # Six-factor Compliance Index weights (EP-01 F-01.4.2)
    # Defaults: w1=0.10 (L), w2=0.20 (C), w3=0.15 (J),
    #           w4=0.25 (S), w5=0.20 (A), w6=0.10 (B)
    # Must sum to 1.0 — validated in __post_init__
    # ---------------------------------------------------------------------------
    ci_weight_l: float = float(os.getenv("CI_WEIGHT_L", "0.10"))
    ci_weight_c: float = float(os.getenv("CI_WEIGHT_C", "0.20"))
    ci_weight_j: float = float(os.getenv("CI_WEIGHT_J", "0.15"))
    ci_weight_s: float = float(os.getenv("CI_WEIGHT_S", "0.25"))
    ci_weight_a: float = float(os.getenv("CI_WEIGHT_A", "0.20"))
    ci_weight_b: float = float(os.getenv("CI_WEIGHT_B", "0.10"))

    # ---------------------------------------------------------------------------
    # API & Rate limiting (EP-05)
    # ---------------------------------------------------------------------------
    api_rate_limit_default: int = int(os.getenv("API_RATE_LIMIT_DEFAULT", "60"))
    api_rate_limit_max: int = int(os.getenv("API_RATE_LIMIT_MAX", "600"))
    admin_secret: str = os.getenv("ADMIN_SECRET", "")

    # ---------------------------------------------------------------------------
    # x402 Micropayment (EP-05 F-04.2)
    # ---------------------------------------------------------------------------
    x402_price_cspr: float = float(os.getenv("X402_PRICE_CSPR", "0.001"))
    x402_challenge_expiry_seconds: int = int(os.getenv("X402_CHALLENGE_EXPIRY_SECONDS", "30"))
    casper_treasury_public_key: str = os.getenv("CASPER_TREASURY_PUBLIC_KEY", "")
    casper_treasury_private_key: str = os.getenv("CASPER_TREASURY_PRIVATE_KEY", "")

    # ---------------------------------------------------------------------------
    # Alerting & Webhooks (EP-01 F-01.3, EP-07 F-06.2)
    # ---------------------------------------------------------------------------
    alert_webhook_url: str | None = os.getenv("ALERT_WEBHOOK_URL")
    security_alert_webhook_url: str | None = os.getenv("SECURITY_ALERT_WEBHOOK_URL")

    # ---------------------------------------------------------------------------
    # LLM Reasoning (EP-06)
    # ---------------------------------------------------------------------------
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")

    # ---------------------------------------------------------------------------
    # Stellar Soroban (EP-02, EP-03)
    # ---------------------------------------------------------------------------
    stellar_horizon_url: str = os.getenv(
        "STELLAR_HORIZON_URL", "https://soroban-testnet.stellar.org"
    )
    stellar_network_passphrase: str = os.getenv(
        "STELLAR_NETWORK_PASSPHRASE", "Test SDF Network ; September 2015"
    )
    stellar_verifier_contract_id: str = os.getenv("STELLAR_VERIFIER_CONTRACT_ID", "")
    stellar_passport_contract_id: str = os.getenv("STELLAR_PASSPORT_CONTRACT_ID", "")
    stellar_source_secret: str = os.getenv("STELLAR_SOURCE_SECRET", "")
    stellar_oracle_authority: str = os.getenv("STELLAR_ORACLE_AUTHORITY", "")
    stellar_base_fee: int = int(os.getenv("STELLAR_BASE_FEE", "100"))

    # ---------------------------------------------------------------------------
    # Casper Odra (EP-04)
    # ---------------------------------------------------------------------------
    casper_compliance_oracle_contract: str = os.getenv("CASPER_COMPLIANCE_ORACLE_CONTRACT", "")
    casper_identity_registry_contract: str = os.getenv("CASPER_IDENTITY_REGISTRY_CONTRACT", "")
    casper_node_address: str = os.getenv("CASPER_NODE_ADDRESS", "https://rpc.testnet.cspr.network")
    casper_chain_name: str = os.getenv("CASPER_CHAIN_NAME", "casper-test")
    casper_secret_key_path: str = os.getenv("CASPER_SECRET_KEY_PATH", "")

    # ---------------------------------------------------------------------------
    # EVM / L2 (EP-08 F-08.2)
    # ---------------------------------------------------------------------------
    ethereum_rpc_url: str = os.getenv("ETHEREUM_RPC_URL", "https://sepolia.infura.io/v3/YOUR_KEY")
    ethereum_verifier_contract_address: str = os.getenv("ETHEREUM_VERIFIER_CONTRACT_ADDRESS", "")
    ethereum_passport_contract_address: str = os.getenv("ETHEREUM_PASSPORT_CONTRACT_ADDRESS", "")
    ethereum_chain_id: int = int(os.getenv("ETHEREUM_CHAIN_ID", "11155111"))
    ethereum_oracle_authority_private_key: str = os.getenv("ETHEREUM_ORACLE_AUTHORITY_PRIVATE_KEY", "")

    # ---------------------------------------------------------------------------
    # Polkadot / ink! (EP-08 F-08.3)
    # ---------------------------------------------------------------------------
    polkadot_node_url: str = os.getenv("POLKADOT_NODE_URL", "wss://rococo-rpc.polkadot.io")
    polkadot_verifier_contract_address: str = os.getenv("POLKADOT_VERIFIER_CONTRACT_ADDRESS", "")
    polkadot_passport_contract_address: str = os.getenv("POLKADOT_PASSPORT_CONTRACT_ADDRESS", "")
    polkadot_chain: str = os.getenv("POLKADOT_CHAIN", "rococo")
    polkadot_suri: str = os.getenv("POLKADOT_SURI", "")

    # ---------------------------------------------------------------------------
    # Hedera Hashgraph (EP-08 F-08.4)
    # ---------------------------------------------------------------------------
    hedera_rpc_url: str = os.getenv("HEDERA_RPC_URL", "")
    hedera_operator_id: str = os.getenv("HEDERA_OPERATOR_ID", "")
    hedera_operator_key: str = os.getenv("HEDERA_OPERATOR_KEY", "")
    hedera_verifier_contract_id: str = os.getenv("HEDERA_VERIFIER_CONTRACT_ID", "")
    hedera_passport_token_id: str = os.getenv("HEDERA_PASSPORT_TOKEN_ID", "")
    hedera_mirror_node_url: str = os.getenv("HEDERA_MIRROR_NODE_URL", "https://testnet.mirrornode.hedera.com")

    # ---------------------------------------------------------------------------
    # Algorand (EP-08 F-08.5)
    # ---------------------------------------------------------------------------
    algorand_node_url: str = os.getenv("ALGORAND_NODE_URL", "https://testnet-api.algonode.cloud")
    algorand_indexer_url: str = os.getenv("ALGORAND_INDEXER_URL", "https://testnet-idx.algonode.cloud")
    algorand_verifier_app_id: int = int(os.getenv("ALGORAND_VERIFIER_APP_ID", "0"))
    algorand_passport_asa_id: int = int(os.getenv("ALGORAND_PASSPORT_ASA_ID", "0"))
    algorand_oracle_private_key: str = os.getenv("ALGORAND_ORACLE_PRIVATE_KEY", "")

    # ---------------------------------------------------------------------------
    # Sui (EP-08 F-08.5)
    # ---------------------------------------------------------------------------
    sui_rpc_url: str = os.getenv("SUI_RPC_URL", "https://fullnode.testnet.sui.io")
    sui_verifier_package_id: str = os.getenv("SUI_VERIFIER_PACKAGE_ID", "")
    sui_passport_object_id: str = os.getenv("SUI_PASSPORT_OBJECT_ID", "")
    sui_oracle_keypair: str = os.getenv("SUI_ORACLE_KEYPAIR", "")

    # ---------------------------------------------------------------------------
    # Aptos (EP-08 F-08.5)
    # ---------------------------------------------------------------------------
    aptos_rpc_url: str = os.getenv("APTOS_RPC_URL", "https://fullnode.testnet.aptoslabs.com")
    aptos_verifier_module_address: str = os.getenv("APTOS_VERIFIER_MODULE_ADDRESS", "")
    aptos_passport_module_address: str = os.getenv("APTOS_PASSPORT_MODULE_ADDRESS", "")
    aptos_oracle_private_key: str = os.getenv("APTOS_ORACLE_PRIVATE_KEY", "")

    # ---------------------------------------------------------------------------
    # ICP / DFINITY (EP-08 F-08.5)
    # ---------------------------------------------------------------------------
    icp_canister_url: str = os.getenv("ICP_CANISTER_URL", "")
    icp_verifier_canister_id: str = os.getenv("ICP_VERIFIER_CANISTER_ID", "")
    icp_passport_canister_id: str = os.getenv("ICP_PASSPORT_CANISTER_ID", "")
    icp_identity_principal: str = os.getenv("ICP_IDENTITY_PRINCIPAL", "")

    def __post_init__(self) -> None:
        """Validate that CI weights sum to 1.0 (EP-01 F-01.4.2)."""
        total = (
            self.ci_weight_l + self.ci_weight_c + self.ci_weight_j +
            self.ci_weight_s + self.ci_weight_a + self.ci_weight_b
        )
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"CI weights must sum to 1.0; got {total:.6f}. "
                "Check CI_WEIGHT_L/C/J/S/A/B environment variables."
            )

    @property
    def postgres_dsn(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def nrs_scale_factor(self) -> int:
        """Scale factor for converting float CI/manifold scores to u64 for ZK circuit."""
        return 1_000_000

    @property
    def ci_weights(self) -> dict[str, float]:
        """Return the six CI weights as a dict for CIEngine consumption."""
        return {
            "L": self.ci_weight_l,
            "C": self.ci_weight_c,
            "J": self.ci_weight_j,
            "S": self.ci_weight_s,
            "A": self.ci_weight_a,
            "B": self.ci_weight_b,
        }


@functools.lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()