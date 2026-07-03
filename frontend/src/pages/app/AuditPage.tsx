// src/pages/app/AuditPage.tsx - Full Compliance Lineage
import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft, GitBranch, FileText, Lock, CheckCircle,
  AlertTriangle, Clock, ExternalLink, Loader2,
} from 'lucide-react'
import { api } from '../../lib/api'

type AuditTrail = {
  entity_hash: string
  nrs_history: Array<{ computed_at: string; nrs: number }>
  proof_events: Array<{
    type: 'proof_generated' | 'selective_disclosure'
    verified_at?: string
    status?: string
    factors?: string[]
  }>
  on_chain_records: Array<{
    chain: 'stellar' | 'casper'
    tx_hash: string
    verified_at: string
  }>
}

export default function AuditPage() {
  const { entityHash } = useParams<{ entityHash: string }>()
  const [audit, setAudit] = useState<AuditTrail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!entityHash) return
    ;(async () => {
      try {
        const data = await api.getAudit(entityHash)
        setAudit(data)
      } catch {
        // ⚡ Demo mode: use mock audit data
        const mock: AuditTrail = {
          entity_hash: entityHash,
          nrs_history: [
            { computed_at: '2026-07-03T10:30:00Z', nrs: 0.42 },
            { computed_at: '2026-07-02T14:20:00Z', nrs: 0.38 },
          ],
          proof_events: [
            { type: 'proof_generated' as const, verified_at: '2026-07-03T10:30:00Z', status: 'VALID' },
            { type: 'selective_disclosure' as const, factors: ['COMPLIANCE_INDEX_PASS', 'BEHAVIOURAL_MANIFOLD_PASS'] },
          ],
          on_chain_records: [
            { chain: 'stellar' as const, tx_hash: 'f1a0e6f8b2c3d4e5a6b7c8d9e0f1a2b3c4d5e6f7', verified_at: '2026-07-03T10:30:00Z' },
          ],
        }
        setAudit(mock)
      } finally {
        setLoading(false)
      }
    })()
  }, [entityHash])

  if (!entityHash) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">No entity hash provided</p>
        <Link to="/app/audit" className="btn-primary text-sm mt-4">
          <ArrowLeft size={14} /> Back to Audit
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link to="/app/entities" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900 mb-4">
          <ArrowLeft size={14} /> Back to Entities
        </Link>
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 font-mono">{entityHash.slice(0, 32)}...</h1>
            <p className="text-sm text-gray-500 mt-1">Full compliance decision lineage</p>
          </div>
          <Link to={`/app/entities/${entityHash}`} className="btn-outline text-sm">
            View Entity Profile
          </Link>
        </div>
      </div>

      {/* Timeline */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6">
        {loading ? (
          <div className="text-center py-12 text-gray-400">
            <Loader2 size={24} className="animate-spin mx-auto mb-3" />
            Loading audit trail...
          </div>
        ) : !audit ? (
          <div className="text-center py-12">
            <GitBranch size={32} className="text-gray-300 mx-auto mb-3" />
            <p className="text-sm text-gray-500">No audit trail found for this entity</p>
          </div>
        ) : (
          <div className="relative">
            {/* Vertical connector */}
            <div className="absolute left-6 top-6 bottom-6 w-px bg-gray-100 hidden md:block" />

            <div className="space-y-8">
              {/* NRS History */}
              {audit.nrs_history?.length && (
                <div className="flex items-start gap-5">
                  <div className="relative z-10 w-12 h-12 rounded-full bg-blue-50 flex items-center justify-center flex-shrink-0">
                    <FileText size={18} className="text-brand-blue" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-bold text-gray-900 mb-2">Risk Computations</h3>
                    <div className="space-y-2">
                      {audit.nrs_history.slice(0, 3).map((h, i) => (
                        <div key={i} className="flex items-center justify-between p-3 rounded-xl bg-gray-50 border border-gray-100">
                          <div>
                            <p className="text-sm font-semibold text-gray-900">NRS: {h.nrs.toFixed(3)}</p>
                            <p className="text-xs text-gray-500">{new Date(h.computed_at).toLocaleString()}</p>
                          </div>
                          <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 font-medium">
                            Computed
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Proof Events */}
              {audit.proof_events?.length && (
                <div className="flex items-start gap-5">
                  <div className="relative z-10 w-12 h-12 rounded-full bg-purple-50 flex items-center justify-center flex-shrink-0">
                    <Lock size={18} className="text-purple-600" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-bold text-gray-900 mb-2">Proof Events</h3>
                    <div className="space-y-2">
                      {audit.proof_events.map((e, i) => (
                        <div key={i} className="p-3 rounded-xl bg-gray-50 border border-gray-100">
                          <div className="flex items-center justify-between mb-1">
                            <p className="text-sm font-semibold text-gray-900">
                              {e.type === 'proof_generated' ? 'ZK Proof Generated' : 'Selective Disclosure'}
                            </p>
                            {e.status && (
                              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                                e.status === 'VALID' ? 'bg-emerald-50 text-emerald-700' :
                                e.status === 'EXPIRED' ? 'bg-amber-50 text-amber-700' :
                                'bg-gray-100 text-gray-700'
                              }`}>
                                {e.status}
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-gray-500 mb-2">
                            {e.verified_at ? new Date(e.verified_at).toLocaleString() : '—'}
                          </p>
                          {e.factors && (
                            <div className="flex flex-wrap gap-1">
                              {e.factors.map((f, j) => (
                                <span key={j} className="text-xs px-2 py-0.5 rounded-full bg-brand-blue/10 text-brand-blue font-medium">
                                  {f}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* On-Chain Records */}
              {audit.on_chain_records?.length && (
                <div className="flex items-start gap-5">
                  <div className="relative z-10 w-12 h-12 rounded-full bg-emerald-50 flex items-center justify-center flex-shrink-0">
                    <CheckCircle size={18} className="text-emerald-600" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-bold text-gray-900 mb-2">On-Chain Records</h3>
                    <div className="space-y-2">
                      {audit.on_chain_records.map((r, i) => (
                        <div key={i} className="flex items-center justify-between p-3 rounded-xl bg-gray-50 border border-gray-100">
                          <div>
                            <p className="text-sm font-semibold text-gray-900 capitalize">{r.chain} Transaction</p>
                            <p className="text-xs text-gray-500 font-mono">{r.tx_hash.slice(0, 24)}...</p>
                          </div>
                          <a
                            href={r.chain === 'stellar'
                              ? `https://stellar.expert/explorer/testnet/tx/${r.tx_hash}`
                              : `https://cspr.live/deploy/${r.tx_hash}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-brand-blue hover:underline flex items-center gap-1"
                          >
                            View <ExternalLink size={10} />
                          </a>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}