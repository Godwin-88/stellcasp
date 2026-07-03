// src/pages/app/EntityDetail.tsx
import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft, Network, Lock, FileCheck, AlertTriangle,
  CheckCircle, XCircle, TrendingUp, Globe, Shield,
  Brain, Activity, Copy, ExternalLink, Eye, Table,
} from 'lucide-react'
import { api } from '../../lib/api'
import EntityGraph from '../../components/EntityGraph'
import ProofGenerationModal from '../../components/ProofGenerationModal'
import PassportMintModal from '../../components/PassportMintModal'
import SelectiveDisclosureModal from '../../components/SelectiveDisclosureModal'

const TABS = ['Risk Factors', 'Manifold', 'Relationships', 'Passport']

export default function EntityDetail() {
  const { id } = useParams<{ id: string }>()
  const [tab, setTab] = useState(0)
  const [factors, setFactors] = useState<any>(null)
  const [manifold, setManifold] = useState<any>(null)
  const [anomalies, setAnomalies] = useState<string[]>([])
  const [credential, setCredential] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [relationships, setRelationships] = useState<any[]>([])
  const [view, setView] = useState<'graph' | 'table'>('graph')

  // Modal states
  const [showProofModal, setShowProofModal] = useState(false)
  const [showPassportModal, setShowPassportModal] = useState(false)
  const [showDisclosureModal, setShowDisclosureModal] = useState(false)

  useEffect(() => {
    if (!id) return
    ;(async () => {
      try {
        const [f, m, a, c, r] = await Promise.all([
          api.getFactors(id).catch(() => null),
          api.getManifold(id).catch(() => null),
          api.getAnomalies(id).catch(() => ({ anomalies: [] })),
          api.getCredential(id).catch(() => null),
          api.getRelationships(id).catch(() => []),
        ])
        setFactors(f)
        setManifold(m)
        setAnomalies(a.anomalies || [])
        setCredential(c)
        setRelationships(Array.isArray(r) ? r : [])
      } finally {
        setLoading(false)
      }
    })()
  }, [id])

  const factorMeta = [
    { key: 'L', label: 'Liquidity Risk', icon: TrendingUp, color: 'blue' },
    { key: 'C', label: 'Counterparty Risk', icon: Network, color: 'purple' },
    { key: 'J', label: 'Jurisdiction Risk', icon: Globe, color: 'amber' },
    { key: 'S', label: 'Sanctions Exposure', icon: Shield, color: 'rose' },
    { key: 'A', label: 'AML Topology', icon: Activity, color: 'indigo' },
    { key: 'B', label: 'Behavioural Risk', icon: Brain, color: 'emerald' },
  ]

  const riskColor = (v: number) => {
    if (v < 0.3) return 'text-emerald-600 bg-emerald-50'
    if (v < 0.6) return 'text-amber-600 bg-amber-50'
    return 'text-rose-600 bg-rose-50'
  }

  // Build graph data from relationships
  const graphData = {
    nodes: relationships.map(r => ({
      id: r.source === id ? r.target : r.source,
      type: 'WALLET' as const,
      risk: 0.4,
    })),
    links: relationships.map(r => ({
      source: r.source,
      target: r.target,
      amount: r.amount,
      timestamp: r.timestamp,
    })),
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
            <h1 className="text-2xl font-bold text-gray-900 font-mono">{id?.slice(0, 24)}...</h1>
            <p className="text-sm text-gray-500 mt-1">Entity compliance profile</p>
          </div>
          <div className="flex gap-2">
            <button className="btn-outline text-xs px-3 py-1.5">
              <Copy size={12} /> Copy Hash
            </button>
            <Link to={`/app/audit/${id}`} className="btn-primary text-xs px-3 py-1.5">
              View Audit <ExternalLink size={12} />
            </Link>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <div className="flex gap-6 overflow-x-auto">
          {TABS.map((label, i) => (
            <button
              key={i}
              onClick={() => setTab(i)}
              className={`pb-3 text-sm font-semibold border-b-2 whitespace-nowrap transition-all ${
                tab === i
                  ? 'border-brand-blue text-brand-blue'
                  : 'border-transparent text-gray-500 hover:text-gray-800'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading...</div>
      ) : (
        <>
          {/* Tab 0: Risk Factors */}
          {tab === 0 && factors && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-gray-900">Six-Factor Compliance Index</h3>
                <button
                  onClick={() => setShowProofModal(true)}
                  className="btn-primary text-xs"
                >
                  <Eye size={12} /> Trigger ZK Proof
                </button>
              </div>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {factorMeta.map(fm => {
                  const Icon = fm.icon
                  const value = factors[fm.key] ?? 0
                  return (
                    <div key={fm.key} className="bg-white rounded-2xl border border-gray-100 p-5">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <div className={`w-8 h-8 rounded-lg bg-${fm.color}-50 flex items-center justify-center`}>
                            <Icon size={14} className={`text-${fm.color}-600`} />
                          </div>
                          <div>
                            <p className="text-xs font-semibold text-gray-400 uppercase">{fm.key}</p>
                            <p className="text-sm font-bold text-gray-900">{fm.label}</p>
                          </div>
                        </div>
                        <span className={`text-lg font-bold px-2 py-0.5 rounded-lg ${riskColor(value)}`}>
                          {(value * 100).toFixed(1)}
                        </span>
                      </div>
                      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full bg-gradient-to-r ${
                            value < 0.3 ? 'from-emerald-400 to-emerald-600' :
                            value < 0.6 ? 'from-amber-400 to-amber-600' :
                            'from-rose-400 to-rose-600'
                          }`}
                          style={{ width: `${value * 100}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>

              {anomalies.length > 0 && (
                <div className="mt-6 bg-amber-50 border border-amber-200 rounded-2xl p-5">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle size={16} className="text-amber-600" />
                    <p className="font-bold text-amber-900 text-sm">Structural Anomalies Detected</p>
                  </div>
                  <ul className="space-y-1">
                    {anomalies.map((a, i) => (
                      <li key={i} className="text-sm text-amber-800">• {a}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Tab 1: Manifold */}
          {tab === 1 && manifold && (
            <div className="bg-white rounded-2xl border border-gray-100 p-6">
              <h2 className="font-bold text-gray-900 mb-5">Behavioural Manifold Classification</h2>
              <div className="grid md:grid-cols-3 gap-4 mb-6">
                <div className="p-5 rounded-xl bg-gradient-to-br from-brand-blue to-blue-700 text-white">
                  <p className="text-xs text-blue-100 uppercase tracking-wider">Cluster Label</p>
                  <p className="text-3xl font-bold mt-2">{manifold.cluster_label}</p>
                </div>
                <div className="p-5 rounded-xl bg-gradient-to-br from-purple-600 to-purple-800 text-white">
                  <p className="text-xs text-purple-100 uppercase tracking-wider">Risk Level</p>
                  <p className="text-3xl font-bold mt-2">{manifold.cluster_risk_level}/4</p>
                </div>
                <div className="p-5 rounded-xl bg-gradient-to-br from-emerald-600 to-emerald-800 text-white">
                  <p className="text-xs text-emerald-100 uppercase tracking-wider">Manifold Score</p>
                  <p className="text-3xl font-bold mt-2">{(manifold.manifold_score * 100).toFixed(1)}</p>
                </div>
              </div>
              <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
                <p className="text-sm text-gray-600 leading-relaxed">
                  <strong>Interpretation:</strong> The entity belongs to cluster {manifold.cluster_label} with risk level {manifold.cluster_risk_level}.
                  The manifold score of {(manifold.manifold_score * 100).toFixed(1)} indicates{' '}
                  {manifold.manifold_score > 0.7 ? 'low-risk behavioural patterns' :
                   manifold.manifold_score > 0.4 ? 'moderate behavioural deviation' :
                   'high behavioural anomaly — review recommended'}.
                </p>
              </div>
            </div>
          )}

          {/* Tab 2: Relationships */}
          {tab === 2 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-gray-900">Transaction Relationships</h3>
                <div className="flex bg-gray-100 rounded-lg p-1">
                  <button
                    onClick={() => setView('graph')}
                    className={`px-3 py-1.5 text-xs rounded-md font-medium flex items-center gap-1 ${
                      view === 'graph' ? 'bg-white shadow-sm' : ''
                    }`}
                  >
                    <Network size={12} /> Graph
                  </button>
                  <button
                    onClick={() => setView('table')}
                    className={`px-3 py-1.5 text-xs rounded-md font-medium flex items-center gap-1 ${
                      view === 'table' ? 'bg-white shadow-sm' : ''
                    }`}
                  >
                    <Table size={12} /> Table
                  </button>
                </div>
              </div>
              {view === 'graph' ? (
                relationships.length > 0 ? (
                  <EntityGraph data={graphData} targetId={id || ''} />
                ) : (
                  <div className="bg-white rounded-2xl border border-gray-100 p-6 text-center py-12 text-gray-400">
                    <Network size={32} className="mx-auto mb-3 opacity-50" />
                    <p className="text-sm">No relationships found for this entity</p>
                  </div>
                )
              ) : (
                <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
                  {relationships.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-gray-50 border-b border-gray-100">
                          <tr>
                            <th className="text-left font-semibold text-gray-600 px-6 py-4">Source</th>
                            <th className="text-left font-semibold text-gray-600 px-6 py-4">Target</th>
                            <th className="text-left font-semibold text-gray-600 px-6 py-4">Amount</th>
                            <th className="text-left font-semibold text-gray-600 px-6 py-4">Currency</th>
                            <th className="text-left font-semibold text-gray-600 px-6 py-4">Timestamp</th>
                          </tr>
                        </thead>
                        <tbody>
                          {relationships.map((r, i) => (
                            <tr key={i} className="border-b border-gray-50 hover:bg-gray-50/50">
                              <td className="px-6 py-4 font-mono text-xs">{r.source?.slice(0, 16)}...</td>
                              <td className="px-6 py-4 font-mono text-xs">{r.target?.slice(0, 16)}...</td>
                              <td className="px-6 py-4 font-medium">{r.amount?.toLocaleString()}</td>
                              <td className="px-6 py-4">{r.currency || '—'}</td>
                              <td className="px-6 py-4 text-xs text-gray-500">
                                {r.timestamp ? new Date(r.timestamp).toLocaleString() : '—'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="text-center py-12 text-gray-400">
                      <Network size={32} className="mx-auto mb-3 opacity-50" />
                      <p className="text-sm">No relationships found</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Tab 3: Passport */}
          {tab === 3 && (
            <div className="bg-white rounded-2xl border border-gray-100 p-6">
              <div className="flex items-center justify-between mb-5">
                <h2 className="font-bold text-gray-900">Compliance Passport</h2>
                <div className="flex gap-2">
                  <button
                    onClick={() => setShowDisclosureModal(true)}
                    className="btn-outline text-xs"
                  >
                    Request Disclosure
                  </button>
                  <button
                    onClick={() => setShowPassportModal(true)}
                    className="btn-primary text-xs"
                  >
                    Mint Passport
                  </button>
                </div>
              </div>
              {credential ? (
                <div className="space-y-4">
                  <div className={`p-5 rounded-xl border-2 ${
                    credential.status === 'VALID' ? 'border-emerald-200 bg-emerald-50' :
                    credential.status === 'EXPIRED' ? 'border-amber-200 bg-amber-50' :
                    'border-rose-200 bg-rose-50'
                  }`}>
                    <div className="flex items-center gap-3 mb-3">
                      {credential.status === 'VALID' ? <CheckCircle className="text-emerald-600" /> :
                       credential.status === 'EXPIRED' ? <AlertTriangle className="text-amber-600" /> :
                       <XCircle className="text-rose-600" />}
                      <p className={`font-bold ${
                        credential.status === 'VALID' ? 'text-emerald-900' :
                        credential.status === 'EXPIRED' ? 'text-amber-900' :
                        'text-rose-900'
                      }`}>
                        {credential.status}
                      </p>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-xs text-gray-500">Entity Hash</p>
                        <p className="font-mono text-xs truncate">{credential.entity_hash}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">Threshold (public)</p>
                        <p className="font-mono">{credential.threshold_public}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">Verified At</p>
                        <p className="text-xs">{new Date(credential.verified_at).toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">Stellar Tx</p>
                        <p className="font-mono text-xs truncate">{credential.stellar_tx_hash || '—'}</p>
                      </div>
                    </div>
                  </div>
                  {credential.proof_hex && (
                    <details className="bg-gray-50 rounded-xl p-4">
                      <summary className="text-sm font-semibold text-gray-700 cursor-pointer">Proof Hex (click to expand)</summary>
                      <pre className="mt-3 text-xs text-gray-600 overflow-x-auto font-mono break-all">
                        {credential.proof_hex}
                      </pre>
                    </details>
                  )}
                </div>
              ) : (
                <div className="text-center py-12">
                  <FileCheck size={32} className="text-gray-300 mx-auto mb-3" />
                  <p className="text-sm text-gray-500">No passport issued yet</p>
                  <button
                    onClick={() => setShowPassportModal(true)}
                    className="btn-primary text-xs mt-4"
                  >
                    Generate Proof & Mint Passport
                  </button>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Modals */}
      {showProofModal && id && (
        <ProofGenerationModal entityId={id} onClose={() => setShowProofModal(false)} />
      )}
      {showPassportModal && id && (
        <PassportMintModal entityId={id} onClose={() => setShowPassportModal(false)} />
      )}
      {showDisclosureModal && id && (
        <SelectiveDisclosureModal entityId={id} onClose={() => setShowDisclosureModal(false)} />
      )}
    </div>
  )
}