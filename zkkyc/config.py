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