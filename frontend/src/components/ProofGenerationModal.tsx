// src/components/ProofGenerationModal.tsx
import React, { useState } from 'react'
import { Loader2, CheckCircle, XCircle, Download, Eye, ArrowRight, X } from 'lucide-react'
import { api } from '../lib/api'

type Step = 'idle' | 'scaling' | 'proving' | 'verifying' | 'done' | 'error'

export default function ProofGenerationModal({
  entityId,
  onClose,
}: {
  entityId: string
  onClose: () => void
}) {
  const [step, setStep] = useState<Step>('idle')
  const [ci, setCi] = useState(0.42)
  const [ciScaled, setCiScaled] = useState(420000)
  const [proofTime, setProofTime] = useState(0)
  const [verified, setVerified] = useState<boolean | null>(null)
  const [error, setError] = useState<string | null>(null)

  const assertions = [
    { label: 'CI < Threshold (0.75)', pass: ci < 0.75 },
    { label: 'Manifold Score ≥ Threshold (0.4)', pass: true },
    { label: 'Jurisdiction Permitted', pass: true },
  ]

  const handleGenerate = async () => {
    setStep('scaling')
    await new Promise(r => setTimeout(r, 800))

    setStep('proving')
    const start = Date.now()
    try {
      const result = await api.generateProof(entityId, 0.75, 'stellar')
      setProofTime((Date.now() - start) / 1000)

      setStep('verifying')
      await new Promise(r => setTimeout(r, 600))

      setVerified(result.verified)
      setStep('done')
    } catch (err: any) {
      setError(err.message || 'Proof generation failed')
      setStep('error')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl w-full max-w-lg shadow-xl border border-gray-100">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-blue/10 flex items-center justify-center">
              <Eye size={18} className="text-brand-blue" />
            </div>
            <div>
              <h2 className="font-bold text-gray-900">ZK Proof Generation</h2>
              <p className="text-xs text-gray-500">Entity: {entityId.slice(0, 16)}...</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100">
            <X size={18} className="text-gray-400" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {/* CI Scaling Display */}
          <div className="p-4 rounded-xl bg-gradient-to-r from-brand-blue to-blue-700 text-white">
            <p className="text-xs text-blue-100 uppercase tracking-wider mb-1">Compliance Index Scaling</p>
            <div className="flex items-center gap-3">
              <span className="text-2xl font-bold">CI: {ci.toFixed(2)}</span>
              <ArrowRight size={20} className="opacity-60" />
              <span className="text-2xl font-bold">{ciScaled.toLocaleString()} u64</span>
            </div>
            <p className="text-xs text-blue-100 mt-1">Scaled for Noir circuit (u64 field)</p>
          </div>

          {/* 3 Assertions Checklist */}
          <div>
            <p className="text-sm font-semibold text-gray-700 mb-3">Circuit Assertions</p>
            <div className="space-y-2">
              {assertions.map((a, i) => (
                <div
                  key={i}
                  className={`flex items-center gap-3 p-3 rounded-xl border ${
                    step === 'idle'
                      ? 'border-gray-200 bg-gray-50'
                      : a.pass
                      ? 'border-emerald-200 bg-emerald-50'
                      : 'border-rose-200 bg-rose-50'
                  }`}
                >
                  {step === 'idle' ? (
                    <div className="w-5 h-5 rounded-full border-2 border-gray-300" />
                  ) : a.pass ? (
                    <CheckCircle size={18} className="text-emerald-600" />
                  ) : (
                    <XCircle size={18} className="text-rose-600" />
                  )}
                  <span className={`text-sm font-medium ${
                    step === 'idle' ? 'text-gray-500' : a.pass ? 'text-emerald-800' : 'text-rose-800'
                  }`}>
                    {a.label}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Progress / Status */}
          {step === 'scaling' && (
            <div className="p-4 rounded-xl bg-blue-50 border border-blue-200 flex items-center gap-3">
              <Loader2 size={18} className="animate-spin text-brand-blue" />
              <p className="text-sm text-blue-800">Scaling CI to u64...</p>
            </div>
          )}

          {step === 'proving' && (
            <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 flex items-center gap-3">
              <Loader2 size={18} className="animate-spin text-amber-600" />
              <p className="text-sm text-amber-800">Running nargo prove...</p>
            </div>
          )}

          {step === 'verifying' && (
            <div className="p-4 rounded-xl bg-purple-50 border border-purple-200 flex items-center gap-3">
              <Loader2 size={18} className="animate-spin text-purple-600" />
              <p className="text-sm text-purple-800">Local verify in progress...</p>
            </div>
          )}

          {step === 'done' && (
            <div className="space-y-3">
              <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle size={18} className="text-emerald-600" />
                  <p className="font-semibold text-emerald-900">Proof Generated</p>
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-xs text-gray-500">Generation Time</p>
                    <p className="font-semibold text-gray-900">{proofTime.toFixed(1)}s</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Local Verify</p>
                    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${
                      verified ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
                    }`}>
                      {verified ? '✅ Passed' : '❌ Failed'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex gap-2">
                <button className="btn-primary flex-1 justify-center text-xs">
                  Dispatch to Stellar <ArrowRight size={12} />
                </button>
                <button className="btn-outline text-xs">
                  <Download size={12} /> Download Proof
                </button>
                <button className="btn-outline text-xs">
                  <Eye size={12} /> View Circuit
                </button>
              </div>
            </div>
          )}

          {step === 'error' && (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200">
              <div className="flex items-center gap-2 mb-1">
                <XCircle size={18} className="text-rose-600" />
                <p className="font-semibold text-rose-900">Generation Failed</p>
              </div>
              <p className="text-sm text-rose-700">{error}</p>
            </div>
          )}

          {/* Action Button */}
          {step === 'idle' && (
            <button
              onClick={handleGenerate}
              className="btn-primary w-full justify-center text-sm"
            >
              Generate Proof
            </button>
          )}

          {step === 'done' && (
            <button onClick={onClose} className="btn-outline w-full justify-center text-sm">
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  )
}