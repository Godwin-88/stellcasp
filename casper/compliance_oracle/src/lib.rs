use odra::prelude::*;

#[odra::contract]
pub struct ComplianceOracle {
    verdicts: VarBTreeMap<String, VerdictRecord>,
    mint_authority: Var<Address>,
    policy_version: Var<u64>,
    agent_key: Var<Address>,
}

#[odra::event]
pub struct VerdictRecorded {
    pub entity_hash: String,
    pub verdict: bool,
    pub expires_at: u64,
    pub agent_key: Address,
}

#[odra::event]
pub struct VerdictRevoked {
    pub entity_hash: String,
    pub reason: String,
    pub revoked_at: u64,
    pub agent_key: Address,
}

#[derive(odra::odra::ODRAData, Debug, Clone)]
pub struct VerdictRecord {
    pub verdict: bool,
    pub recorded_at: u64,
    pub expires_at: u64,
    pub nrs_threshold: u64,
    pub revoked_at: Option<u64>,
    pub reason: Option<String>,
    pub policy_version: u64,
}

#[derive(odra::odra::ODRAData, Debug, Clone)]
pub struct VerdictStatus {
    pub verdict: Option<bool>,
    pub expires_at: u64,
    pub status: String,
    pub policy_version: u64,
}

impl ComplianceOracle {
    #[odra::constructor]
    pub fn constructor(mint_authority: Address, agent_key: Address) {
        self.mint_authority.set(mint_authority);
        self.agent_key.set(agent_key);
        self.policy_version.set(1);
    }

    #[odra::external]
    pub fn record_verdict(
        &mut self,
        entity_hash: String,
        verdict: bool,
        expires_at: u64,
        nrs_threshold: u64,
    ) {
        if self.env().caller() != self.mint_authority.get() {
            panic!("PermissionDenied");
        }

        let current_version = self.policy_version.get();
        let record = VerdictRecord {
            verdict,
            recorded_at: self.env().get_block_time(),
            expires_at,
            nrs_threshold,
            revoked_at: None,
            reason: None,
            policy_version: current_version,
        };

        self.verdicts.set(&entity_hash, record.clone());

        self.env().emit_event(&VerdictRecorded {
            entity_hash: entity_hash.clone(),
            verdict,
            expires_at,
            agent_key: self.agent_key.get(),
        });
    }

    #[odra::external]
    pub fn revoke_verdict(&mut self, entity_hash: String, reason: String) {
        if self.env().caller() != self.mint_authority.get() {
            panic!("PermissionDenied");
        }

        if let Some(mut record) = self.verdicts.get(&entity_hash) {
            record.verdict = false;
            record.revoked_at = Some(self.env().get_block_time());
            record.reason = Some(reason.clone());
            self.verdicts.set(&entity_hash, record);

            self.env().emit_event(&VerdictRevoked {
                entity_hash,
                reason,
                revoked_at: self.env().get_block_time(),
                agent_key: self.agent_key.get(),
            });
        }
    }

    #[odra::external]
    pub fn upgrade_policy(&mut self, new_version: u64) {
        if self.env().caller() != self.mint_authority.get() {
            panic!("PermissionDenied");
        }
        self.policy_version.set(new_version);
    }

    #[odra::external(read_only = true)]
    pub fn get_policy_version(&self) -> u64 {
        self.policy_version.get()
    }

    #[odra::external(read_only = true)]
    pub fn get_verdict(&self, entity_hash: String) -> VerdictStatus {
        let now = self.env().get_block_time();

        if let Some(record) = self.verdicts.get(&entity_hash) {
            if record.expires_at > 0 && now > record.expires_at {
                return VerdictStatus {
                    verdict: None,
                    expires_at: record.expires_at,
                    status: "EXPIRED".to_string(),
                    policy_version: record.policy_version,
                };
            }
            if record.revoked_at.is_some() {
                return VerdictStatus {
                    verdict: Some(false),
                    expires_at: record.expires_at,
                    status: "REVOKED".to_string(),
                    policy_version: record.policy_version,
                };
            }
            return VerdictStatus {
                verdict: Some(record.verdict),
                expires_at: record.expires_at,
                status: "VALID".to_string(),
                policy_version: record.policy_version,
            };
        }

        VerdictStatus {
            verdict: None,
            expires_at: 0,
            status: "NOT_FOUND".to_string(),
            policy_version: self.policy_version.get(),
        }
    }

    #[odra::external(read_only = true)]
    pub fn get_agent_key(&self) -> Address {
        self.agent_key.get()
    }
}