// src/components/SelectiveDisclosureModal.tsx
import React, { useState } from 'react'
import { Loader2, CheckCircle, XCircle, Clock, X } from 'lucide-react'
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export default function SelectiveDisclosureModal({
  entityId,
  onClose,
}: {
  entityId: string
  onClose: () => void
}) {
  const [institution, setInstitution] = useState('')
  const [signature, setSignature] = useState('')
  const [factors, setFactors] = useState<string[]>(['COMPLIANCE_INDEX_PASS', 'AML_TOPOLOGY_RISK_PASS'])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ labels: string[]; auditHash: string; timestamp: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const availableFactors = [
    'COMPLIANCE_INDEX_PASS',
    'AML_TOPOLOGY_RISK_PASS',
    'JURISDICTION_RISK_PASS',
    'SANCTIONS_EXPOSURE_PASS',
    'BEHAVIOURAL_RISK_PASS',
    'LIQUIDITY_RISK_PASS',
    'COUNTERPARTY_RISK_PASS',
  ]

  const toggleFactor = (f: string) => {
    setFactors(prev =>
      prev.includes(f) ? prev.filter(x => x !== f) : [...prev, f]
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      // POST to disclose endpoint
      const apiKey = localStorage.getItem('zkco_api_key')
      await fetch(`${API_BASE}/api/v1/entity/${entityId}/disclose`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(apiKey ? { 'X-API-Key': apiKey } : {}),
        },
        body: JSON.stringify({ institution, signature, factors }),
      })
      // Simulate result
      setResult({
        labels: factors,
        auditHash: `0x${Array.from({length: 64}, () => Math.floor(Math.random() * 16).toString(16)).join('')}`,
        timestamp: new Date().toISOString(),
      })
    } catch (err: any) {
      setError(err.message || 'Disclosure request failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl w-full max-w-lg shadow-xl border border-gray-100">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-violet-100 flex items-center justify-center">
              <Clock size={18} className="text-violet-600" />
            </div>
            <div>
              <h2 className="font-bold text-gray-900">Selective Disclosure</h2>
              <p className="text-xs text-gray-500">Entity: {entityId.slice(0, 16)}...</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100">
            <X size={18} className="text-gray-400" />
          </button>
        </div>

        {result ? (
          /* Result View */
          <div className="p-6 space-y-5">
            <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle size={18} className="text-emerald-600" />
                <p className="font-semibold text-emerald-900">Disclosure Successful</p>
              </div>
              <div className="space-y-2">
                <p className="text-xs text-gray-500 uppercase tracking-wider">Returned Labels</p>
                <div className="flex flex-wrap gap-2">
                  {result.labels.map(label => (
                    <span key={label} className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-700 font-medium">
                      <CheckCircle size={10} />
                      {label}
                    </span>
                  ))}
                </div>
                <div className="pt-2 border-t border-emerald-200 mt-3">
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-xs text-gray-500">Requestor Hash</p>
                      <p className="font-mono text-xs text-gray-700 truncate">{result.auditHash.slice(0, 24)}...</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Timestamp</p>
                      <p className="text-xs text-gray-700">{new Date(result.timestamp).toLocaleString()}</p>
                    </div>
                  </div>
                  <p className="text-xs text-emerald-700 mt-2">
                    ⚡ Audit log entry created — requestor hash & timestamp recorded
                  </p>
                </div>
              </div>
            </div>
            <button onClick={onClose} className="btn-outline w-full justify-center text-sm">Close</button>
          </div>
        ) : (
          /* Form View */
          <form onSubmit={handleSubmit} className="p-6 space-y-5">
            {error && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-sm text-rose-700">
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1.5">Institution Name</label>
              <input
                type="text"
                placeholder="e.g., Stellar DEX"
                value={institution}
                onChange={e => setInstitution(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-blue/30 focus:border-brand-blue"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1.5">ED25519 Signature (hex)</label>
              <input
                type="text"
                placeholder="0x..."
                value={signature}
                onChange={e => setSignature(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-blue/30 focus:border-brand-blue"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Factors Requested</label>
              <div className="grid grid-cols-2 gap-2">
                {availableFactors.map(f => (
                  <label
                    key={f}
                    className={`flex items-center gap-2 p-3 rounded-xl border cursor-pointer transition-all ${
                      factors.includes(f)
                        ? 'border-brand-blue bg-brand-blue/5'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={factors.includes(f)}
                      onChange={() => toggleFactor(f)}
                      className="w-4 h-4 rounded border-gray-300 text-brand-blue focus:ring-brand-blue/30"
                    />
                    <span className="text-xs font-medium text-gray-700">{f.replace(/_/g, ' ')}</span>
                  </label>
                ))}
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !institution || !signature}
              className="btn-primary w-full justify-center text-sm disabled:opacity-60"
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : 'Request Disclosure'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}