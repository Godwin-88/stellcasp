// src/components/PassportMintModal.tsx
import React, { useState } from 'react'
import { Loader2, CheckCircle, XCircle, Copy, ExternalLink, X } from 'lucide-react'

type Step = 'idle' | 'minting' | 'verifying_dex' | 'verifying_lending' | 'done' | 'error'

export default function PassportMintModal({
  entityId,
  onClose,
}: {
  entityId: string
  onClose: () => void
}) {
  const [step, setStep] = useState<Step>('idle')
  const [txHash, setTxHash] = useState<string | null>(null)
  const [dexValid, setDexValid] = useState<boolean | null>(null)
  const [lendingValid, setLendingValid] = useState<boolean | null>(null)
  const [error, setError] = useState<string | null>(null)

  const contractAddresses = {
    passport: 'CAQYAAAABAAAAAAAAAAAAAACDG2VK3UJ5K4J5K4J5K4J5K4J5K4',
    complianceOracle: 'CAQYAAAABAAAAAAAAAAAAAACXXXXXXXXXXXXXX',
    identityRegistry: 'CAQYAAAABAAAAAAAAAAAAAACYYYYYYYYYYYYYY',
  }

  const integrationSnippet = `// StellCasp Passport Integration
import { PassportSDK } from '@stellcasp/passport-sdk';

const passport = new PassportSDK({
  contractId: '${contractAddresses.passport.slice(0, 20)}...',
  network: 'testnet'
});

// Verify credential
const result = await passport.verifyCredential('${entityId.slice(0, 16)}...');
console.log(result.valid); // true/false
`

  const handleMint = async () => {
    setStep('minting')
    // Simulate minting
    await new Promise(r => setTimeout(r, 1500))
    setTxHash(`stellar_tx_${Math.random().toString(36).slice(2, 10)}`)

    setStep('verifying_dex')
    await new Promise(r => setTimeout(r, 1000))
    setDexValid(true)

    setStep('verifying_lending')
    await new Promise(r => setTimeout(r, 1000))
    setLendingValid(true)

    setStep('done')
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl w-full max-w-lg shadow-xl border border-gray-100">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-100 flex items-center justify-center">
              <CheckCircle size={18} className="text-emerald-600" />
            </div>
            <div>
              <h2 className="font-bold text-gray-900">Mint Compliance Passport</h2>
              <p className="text-xs text-gray-500">Entity: {entityId.slice(0, 16)}...</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100">
            <X size={18} className="text-gray-400" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {/* Contract Addresses */}
          <div>
            <p className="text-sm font-semibold text-gray-700 mb-3">Deployed Contracts</p>
            <div className="space-y-2">
              {Object.entries(contractAddresses).map(([name, addr]) => (
                <div key={name} className="flex items-center justify-between p-3 rounded-xl bg-gray-50 border border-gray-100">
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase">{name}</p>
                    <p className="font-mono text-xs text-gray-700 mt-0.5">{addr.slice(0, 24)}...</p>
                  </div>
                  <button
                    onClick={() => copyToClipboard(addr)}
                    className="p-1.5 rounded-lg hover:bg-gray-200 text-gray-400 hover:text-gray-600"
                  >
                    <Copy size={12} />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Status Steps */}
          <div className="space-y-3">
            {/* Mint Step */}
            <div className={`flex items-center gap-3 p-3 rounded-xl border ${
              step === 'idle' ? 'border-gray-200' :
              step === 'minting' ? 'border-blue-200 bg-blue-50' :
              ['done', 'verifying_dex', 'verifying_lending'].includes(step) ? 'border-emerald-200 bg-emerald-50' :
              'border-gray-200'
            }`}>
              {step === 'idle' ? (
                <div className="w-5 h-5 rounded-full border-2 border-gray-300" />
              ) : step === 'minting' ? (
                <Loader2 size={18} className="animate-spin text-brand-blue" />
              ) : ['done', 'verifying_dex', 'verifying_lending'].includes(step) ? (
                <CheckCircle size={18} className="text-emerald-600" />
              ) : (
                <XCircle size={18} className="text-rose-600" />
              )}
              <div className="flex-1">
                <p className={`text-sm font-medium ${
                  step === 'idle' ? 'text-gray-500' : 'text-gray-900'
                }`}>Mint Passport (mint_passport)</p>
                {txHash && (
                  <p className="text-xs text-gray-500 font-mono mt-0.5">
                    Tx: {txHash.slice(0, 24)}...
                    <a
                      href={`https://stellar.expert/explorer/testnet/tx/${txHash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-brand-blue hover:underline ml-1 inline-flex items-center gap-0.5"
                    >
                      <ExternalLink size={10} /> View
                    </a>
                  </p>
                )}
              </div>
            </div>

            {/* DEX Verify Step */}
            <div className={`flex items-center gap-3 p-3 rounded-xl border ${
              ['idle', 'minting'].includes(step) ? 'border-gray-200 bg-gray-50 opacity-50' :
              step === 'verifying_dex' ? 'border-blue-200 bg-blue-50' :
              dexValid ? 'border-emerald-200 bg-emerald-50' :
              'border-rose-200 bg-rose-50'
            }`}>
              {['idle', 'minting'].includes(step) ? (
                <div className="w-5 h-5 rounded-full border-2 border-gray-300" />
              ) : step === 'verifying_dex' ? (
                <Loader2 size={18} className="animate-spin text-brand-blue" />
              ) : dexValid ? (
                <CheckCircle size={18} className="text-emerald-600" />
              ) : (
                <XCircle size={18} className="text-rose-600" />
              )}
              <div>
                <p className="text-sm font-medium text-gray-900">Verify Credential (DEX Context)</p>
                {dexValid !== null && (
                  <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium mt-0.5 ${
                    dexValid ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
                  }`}>
                    {dexValid ? '✅ valid: true' : '❌ valid: false'}
                  </span>
                )}
              </div>
            </div>

            {/* Lending Verify Step */}
            <div className={`flex items-center gap-3 p-3 rounded-xl border ${
              ['idle', 'minting', 'verifying_dex'].includes(step) ? 'border-gray-200 bg-gray-50 opacity-50' :
              step === 'verifying_lending' ? 'border-blue-200 bg-blue-50' :
              lendingValid ? 'border-emerald-200 bg-emerald-50' :
              'border-rose-200 bg-rose-50'
            }`}>
              {['idle', 'minting', 'verifying_dex'].includes(step) ? (
                <div className="w-5 h-5 rounded-full border-2 border-gray-300" />
              ) : step === 'verifying_lending' ? (
                <Loader2 size={18} className="animate-spin text-brand-blue" />
              ) : lendingValid ? (
                <CheckCircle size={18} className="text-emerald-600" />
              ) : (
                <XCircle size={18} className="text-rose-600" />
              )}
              <div>
                <p className="text-sm font-medium text-gray-900">Verify Credential (Lending Context)</p>
                {lendingValid !== null && (
                  <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium mt-0.5 ${
                    lendingValid ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
                  }`}>
                    {lendingValid ? '✅ valid: true' : '❌ valid: false'}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Integration Snippet (when done) */}
          {step === 'done' && (
            <div className="p-4 rounded-xl bg-gray-900 text-gray-100">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-semibold text-gray-400 uppercase">Integration Snippet</p>
                <button
                  onClick={() => copyToClipboard(integrationSnippet)}
                  className="p-1 rounded hover:bg-gray-700"
                >
                  <Copy size={12} />
                </button>
              </div>
              <pre className="text-xs font-mono text-gray-300 whitespace-pre-wrap">{integrationSnippet}</pre>
            </div>
          )}

          {error && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-sm text-rose-700">
              {error}
            </div>
          )}

          {/* Action Button */}
          {step === 'idle' && (
            <button onClick={handleMint} className="btn-primary w-full justify-center text-sm">
              Mint Passport
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