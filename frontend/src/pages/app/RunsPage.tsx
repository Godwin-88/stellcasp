// src/pages/app/RunsPage.tsx
import React, { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Brain, Loader2, CheckCircle, AlertTriangle, Clock,
  ArrowRight, Search, Filter, ChevronDown, ChevronUp, Plus,
} from 'lucide-react'
import { api } from '../../lib/api'
import AgentPipelineModal from '../../components/AgentPipelineModal'

type Run = {
  run_id: string
  entity_id: string
  state: {
    compliance_decision?: 'PASS' | 'FAIL' | 'ERROR'
    chain_target?: 'stellar' | 'casper'
    on_chain_tx_hash?: string
    errors?: string[]
  }
  created_at: string
}

export default function RunsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [runs, setRuns] = useState<Run[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [showPipeline, setShowPipeline] = useState(false)

  useEffect(() => {
    // Mock data for demo — replace with real API call
    ;(async () => {
      try {
        const mock: Run[] = [
          {
            run_id: 'run_abc123',
            entity_id: '0xab...1234',
            state: { compliance_decision: 'PASS', chain_target: 'stellar', on_chain_tx_hash: 'tx_stellar_xyz' },
            created_at: '2026-07-03T10:30:00Z',
          },
          {
            run_id: 'run_def456',
            entity_id: 'KE-PIN-987654321',
            state: { compliance_decision: 'FAIL', errors: ['CI_EXCEEDED'] },
            created_at: '2026-07-02T14:20:00Z',
          },
        ]
        setRuns(mock)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const filtered = runs.filter(r =>
    !search || r.entity_id.toLowerCase().includes(search.toLowerCase()) || r.run_id.includes(search)
  )

  const decisionBadge = (decision?: string) => {
    if (!decision) return null
    const styles: Record<string, string> = {
      PASS: 'bg-emerald-50 text-emerald-700',
      FAIL: 'bg-rose-50 text-rose-700',
      ERROR: 'bg-gray-100 text-gray-700',
    }
    const icons: Record<string, JSX.Element> = {
      PASS: <CheckCircle size={12} />,
      FAIL: <AlertTriangle size={12} />,
      ERROR: <Clock size={12} />,
    }
    return (
      <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${styles[decision]}`}>
        {icons[decision]} {decision}
      </span>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Agent Runs</h1>
          <p className="text-sm text-gray-500 mt-1">Trace LangGraph agent pipeline executions</p>
        </div>
        <button
          onClick={() => setShowPipeline(true)}
          className="btn-primary text-sm"
        >
          <Plus size={14} /> Run Compliance Pipeline
        </button>
      </div>

      {/* Search */}
      <div className="relative w-full sm:w-80">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Search run ID or entity..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-blue/30 focus:border-brand-blue"
        />
      </div>

      {/* Runs List */}
      <div className="space-y-3">
        {loading ? (
          <div className="text-center py-12 text-gray-400">
            <Loader2 size={24} className="animate-spin mx-auto mb-3" />
            Loading runs...
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-2xl border border-gray-100">
            <Brain size={32} className="text-gray-300 mx-auto mb-3" />
            <p className="text-sm text-gray-500">No agent runs found</p>
          </div>
        ) : (
          filtered.map(run => (
            <div key={run.run_id} className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
              {/* Header */}
              <button
                onClick={() => setExpanded(expanded === run.run_id ? null : run.run_id)}
                className="w-full flex items-center justify-between p-5 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl bg-brand-blue/10 flex items-center justify-center">
                    <Brain size={18} className="text-brand-blue" />
                  </div>
                  <div className="text-left">
                    <p className="font-mono text-sm font-semibold text-gray-900">{run.run_id}</p>
                    <p className="text-xs text-gray-500">Entity: {run.entity_id.slice(0, 24)}...</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  {decisionBadge(run.state.compliance_decision)}
                  <span className="text-xs text-gray-400">
                    {new Date(run.created_at).toLocaleTimeString()}
                  </span>
                  {expanded === run.run_id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </div>
              </button>

              {/* Expanded Details */}
              {expanded === run.run_id && (
                <div className="px-5 pb-5 border-t border-gray-100 pt-4 space-y-4">
                  {/* State Summary */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <p className="text-xs text-gray-400 uppercase tracking-wider">Decision</p>
                      <p className="font-semibold text-gray-900">{run.state.compliance_decision || '—'}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400 uppercase tracking-wider">Chain</p>
                      <p className="font-semibold text-gray-900">{run.state.chain_target || '—'}</p>
                    </div>
                    <div className="col-span-2">
                      <p className="text-xs text-gray-400 uppercase tracking-wider">On-Chain Tx</p>
                      {run.state.on_chain_tx_hash ? (
                        <a
                          href={`https://stellar.expert/explorer/testnet/tx/${run.state.on_chain_tx_hash}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-mono text-xs text-brand-blue hover:underline break-all"
                        >
                          {run.state.on_chain_tx_hash.slice(0, 32)}...
                        </a>
                      ) : (
                        <p className="text-gray-400 text-sm">—</p>
                      )}
                    </div>
                  </div>

                  {/* Errors */}
                  {run.state.errors?.length && (
                    <div className="p-4 rounded-xl bg-rose-50 border border-rose-200">
                      <p className="text-xs font-semibold text-rose-700 mb-2">Errors</p>
                      <ul className="space-y-1">
                        {run.state.errors.map((err, i) => (
                          <li key={i} className="text-sm text-rose-800 font-mono">• {err}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-2 pt-2">
                    <Link
                      to={`/app/audit/${run.entity_id}`}
                      className="btn-outline text-xs"
                    >
                      View Audit Trail
                    </Link>
                    <Link
                      to={`/app/entities/${run.entity_id}`}
                      className="btn-primary text-xs"
                    >
                      View Entity <ArrowRight size={12} />
                    </Link>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Agent Pipeline Modal */}
      {showPipeline && (
        <AgentPipelineModal onClose={() => setShowPipeline(false)} />
      )}
    </div>
  )
}
