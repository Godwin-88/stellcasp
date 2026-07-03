// src/lib/api.ts
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

type RequestOptions = {
  method?: string
  body?: unknown
  headers?: Record<string, string>
}

class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const apiKey = localStorage.getItem('zkco_api_key')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(apiKey ? { 'X-API-Key': apiKey } : {}),
    ...options.headers,
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method: options.method || 'GET',
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new ApiError(err.error || 'Request failed', res.status)
  }

  return res.json()
}

// ─── Entity endpoints ───────────────────────────────────────────────────────
export const api = {
  health: () => request<{ status: string; timestamp: string }>('/health'),
  
  createEntity: (data: { id: string; type: string }) =>
    request('/api/v1/entity', { method: 'POST', body: data }),
  
  createRelationship: (data: { source_id: string; target_id: string; amount: number; currency: string; timestamp: number; tx_hash: string }) =>
    request('/api/v1/relationship', { method: 'POST', body: data }),
  
  getRelationships: (id: string) =>
    request<unknown>(`/api/v1/entity/${id}/relationships`),
  
  getFactors: (id: string) =>
    request<{ L: number; C: number; J: number; S: number; A: number; B: number; B_is_stub: boolean }>(`/api/v1/entity/${id}/factors`),
  
  getManifold: (id: string) =>
    request<{ cluster_label: number; cluster_risk_level: number; manifold_score: number }>(`/api/v1/entity/${id}/manifold`),
  
  getAnomalies: (id: string) =>
    request<{ entity_hash: string; anomalies: string[] }>(`/api/v1/entity/${id}/anomalies`),
  
  getCredential: (id: string) =>
    request<{ stellar_tx_hash: string | null; entity_hash: string; threshold_public: number; verified_at: string; proof_hex: string | null; status: string }>(`/api/v1/entity/${id}/credential`),
  
  generateProof: (id: string, threshold = 0.75, chain = 'stellar') =>
    request<{ entity_hash: string; nrs: number; proof_generated: boolean; verified: boolean; chain_target: string }>(`/api/v1/prove/${id}`, { method: 'POST', body: { threshold, chain } }),
  
  // ─── Entity List ──────────────────────────────────────────────────────
  getEntities: (params?: { limit?: number; offset?: number }) => {
    const qs = new URLSearchParams()
    if (params?.limit) qs.set('limit', String(params.limit))
    if (params?.offset) qs.set('offset', String(params.offset))
    return request<{ items: unknown[]; total: number; limit: number; offset: number }>(`/api/v1/entities?${qs}`)
  },

  // ─── Runs List ─────────────────────────────────────────────────────────
  getRuns: (params?: { limit?: number; offset?: number }) => {
    const qs = new URLSearchParams()
    if (params?.limit) qs.set('limit', String(params.limit))
    if (params?.offset) qs.set('offset', String(params.offset))
    return request<{ items: unknown[]; total: number; limit: number; offset: number }>(`/api/v1/runs?${qs}`)
  },

  // ─── Security Events ──────────────────────────────────────────────────
  getSecurityEvents: (params?: { severity?: string; limit?: number; offset?: number }) => {
    const qs = new URLSearchParams()
    if (params?.severity) qs.set('severity', params.severity)
    if (params?.limit) qs.set('limit', String(params.limit))
    if (params?.offset) qs.set('offset', String(params.offset))
    return request<{ items: unknown[]; total: number; limit: number; offset: number }>(`/api/v1/security/events?${qs}`)
  },

  // ─── Jurisdiction ─────────────────────────────────────────────────────
  getJurisdictions: () =>
    request<{ jurisdictions: { iso2: string; risk_score: number }[]; default_risk: number }>('/api/v1/admin/jurisdiction'),

  // ─── Mint Passport ────────────────────────────────────────────────────
  mintPassport: (id: string) =>
    request<{ entity_hash: string; stellar_tx_hash: string; status: string; dex_verify: boolean; lending_verify: boolean; ci: number; contracts: Record<string, string> }>(`/api/v1/entity/${id}/mint-passport`, { method: 'POST' }),

  // ─── Incidents ──────────────────────────────────────────────────────────
  getIncidents: (params?: { status?: string; limit?: number; offset?: number }) => {
    const qs = new URLSearchParams()
    if (params?.status) qs.set('status', params.status)
    if (params?.limit) qs.set('limit', String(params.limit))
    if (params?.offset) qs.set('offset', String(params.offset))
    return request<{ items: unknown[]; limit: number; offset: number; total: number }>(`/api/v1/incidents?${qs}`)
  },
  
  // ─── Audit ──────────────────────────────────────────────────────────────
  getAudit: (entityHash: string) =>
    request<{ entity_hash: string; nrs_history: unknown[]; proof_events: unknown[]; on_chain_records: unknown[] }>(`/api/v1/audit/${entityHash}`),
  
  getRun: (runId: string) =>
    request<{ run_id: string; entity_id: string; state: unknown; created_at: string }>(`/api/v1/runs/${runId}`),
  
  // ─── Admin ──────────────────────────────────────────────────────────────
  createApiKey: (name: string, rateLimit = 60) =>
    request<{ key_id: string; plaintext_key: string; name: string; rate_limit: number; created_at: string }>('/api/v1/keys', {
      method: 'POST',
      body: { name, rate_limit: rateLimit },
      headers: { 'X-Admin-Secret': localStorage.getItem('zkco_admin_secret') || '' },
    }),
  
  getPaymentSummary: (days = 30) =>
    request<{ days: { date: string; count: number; total_cspr: number }[]; total_cspr: number; total_count: number }>(`/api/v1/payments/summary?days=${days}`),
}