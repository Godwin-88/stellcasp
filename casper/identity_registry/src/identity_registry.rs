use odra::prelude::*;
use odra::Event;
use odra::odra_type;

#[odra::module]
pub struct IdentityRegistry {
    identities: Mapping<Address, IdentityRecord>,
    compliance_oracle: Var<Address>,
    agent_key: Var<Address>,
}

#[derive(Event, Debug, Clone)]
pub struct IdentityRegistered {
    pub wallet: Address,
    pub entity_hash: String,
    pub registered_at: u64,
    pub agent_key: Address,
}

#[derive(Event, Debug, Clone)]
pub struct ComplianceTokenMinted {
    pub wallet: Address,
    pub entity_hash: String,
    pub minted_at: u64,
    pub expires_at: u64,
    pub agent_key: Address,
}

#[odra_type]
pub struct IdentityRecord {
    pub entity_hash: String,
    pub registered_at: u64,
    pub status: String,
    pub minted_at: Option<u64>,
    pub expires_at: Option<u64>,
    pub agent_key: Address,
}

#[odra::module]
impl IdentityRegistry {
    pub fn init(&mut self, compliance_oracle_address: Address, agent_key: Address) {
        self.compliance_oracle.set(compliance_oracle_address);
        self.agent_key.set(agent_key);
    }

    pub fn register_identity(&mut self, wallet: Address, entity_hash: String) {
        let agent = self.agent_key.get().unwrap();
        let record = match self.identities.get(&wallet) {
            Some(mut existing) => {
                existing.registered_at = self.env().get_block_time();
                existing.entity_hash = entity_hash.clone();
                existing.status = "PENDING".to_string();
                existing.agent_key = agent;
                existing
            }
            None => IdentityRecord {
                entity_hash: entity_hash.clone(),
                registered_at: self.env().get_block_time(),
                status: "PENDING".to_string(),
                minted_at: None,
                expires_at: None,
                agent_key: agent,
            },
        };

        let registered_at = record.registered_at;
        self.identities.set(&wallet, record);

        self.env().emit_event(IdentityRegistered {
            wallet,
            entity_hash,
            registered_at,
            agent_key: agent,
        });
    }

    pub fn mint_compliance_token(&mut self, wallet: Address, entity_hash: String) {
        let identity = match self.identities.get(&wallet) {
            Some(id) => id,
            None => self.env().revert(OdraError::user(2)),
        };

        if identity.entity_hash != entity_hash {
            self.env().revert(OdraError::user(2));
        }

        let _oracle_addr = self.compliance_oracle.get().unwrap();
        let now = self.env().get_block_time();
        let expires_at = now.saturating_add(30 * 24 * 60 * 60);
        let agent = self.agent_key.get().unwrap();

        let mut record = identity;
        record.status = "COMPLIANT".to_string();
        record.minted_at = Some(now);
        record.expires_at = Some(expires_at);
        record.agent_key = agent;

        self.identities.set(&wallet, record);

        self.env().emit_event(ComplianceTokenMinted {
            wallet,
            entity_hash,
            minted_at: now,
            expires_at,
            agent_key: agent,
        });
    }

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

    pub fn get_agent_key(&self) -> Address {
        self.agent_key.get().unwrap()
    }
}