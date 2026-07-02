use odra::prelude::*;
use odra::Address;

#[odra::contract]
pub struct IdentityRegistry {
    identities: VarBTreeMap<Address, IdentityRecord>,
    compliance_oracle: Var<Address>,
}

#[odra::event]
pub struct IdentityRegistered {
    pub wallet: Address,
    pub entity_hash: String,
    pub registered_at: u64,
}

#[odra::event]
pub struct ComplianceTokenMinted {
    pub wallet: Address,
    pub entity_hash: String,
    pub minted_at: u64,
    pub expires_at: u64,
}

#[derive(odra::odra::ODRAData, Debug, Clone)]
pub struct IdentityRecord {
    pub entity_hash: String,
    pub registered_at: u64,
    pub status: String,
    pub minted_at: Option<u64>,
    pub expires_at: Option<u64>,
}

impl IdentityRegistry {
    #[odra::constructor]
    pub fn constructor(compliance_oracle_address: Address) {
        self.compliance_oracle.set(compliance_oracle_address);
    }

    #[odra::external]
    pub fn register_identity(&mut self, wallet: Address, entity_hash: String) {
        let record = match self.identities.get(&wallet) {
            Some(mut existing) => {
                existing.registered_at = self.env().get_block_time();
                existing.entity_hash = entity_hash.clone();
                existing.status = "PENDING".to_string();
                existing
            }
            None => IdentityRecord {
                entity_hash: entity_hash.clone(),
                registered_at: self.env().get_block_time(),
                status: "PENDING".to_string(),
                minted_at: None,
                expires_at: None,
            },
        };

        self.identities.set(&wallet, record.clone());

        self.env().emit_event(&IdentityRegistered {
            wallet,
            entity_hash,
            registered_at: record.registered_at,
        });
    }

    #[odra::external]
    pub fn mint_compliance_token(&mut self, wallet: Address, entity_hash: String) {
        let identity = match self.identities.get(&wallet) {
            Some(id) => id,
            None => panic!("NO_VALID_VERDICT"),
        };

        if identity.entity_hash != entity_hash {
            panic!("NO_VALID_VERDICT");
        }

        let _oracle_addr = self.compliance_oracle.get();
        let now = self.env().get_block_time();
        let expires_at = now.saturating_add(30 * 24 * 60 * 60);

        let mut record = identity;
        record.status = "COMPLIANT".to_string();
        record.minted_at = Some(now);
        record.expires_at = Some(expires_at);

        self.identities.set(&wallet, record.clone());

        self.env().emit_event(&ComplianceTokenMinted {
            wallet,
            entity_hash,
            minted_at: now,
            expires_at,
        });
    }

    #[odra::external(read_only = true)]
    pub fn get_identity(&self, wallet: Address) -> Option<IdentityRecord> {
        let now = self.env().get_block_time();

        self.identities.get(&wallet).map(|mut record| {
            if let Some(expires_at) = record.expires_at {
                if now > expires_at {
                    record.status = "EXPIRED".to_string();
                }
            }
            record
        })
    }
}