// src/components/RelationshipIngestionModal.tsx
import React, { useState, useRef } from 'react'
import { Loader2, CheckCircle, XCircle, Upload, AlertTriangle, X } from 'lucide-react'
import { api } from '../lib/api'

type CsvRow = {
  source_id: string
  target_id: string
  amount: number
  currency: string
  timestamp: number
  tx_hash: string
}

type RowValidation = {
  row: number
  errors: string[]
}

export default function RelationshipIngestionModal({
  onClose,
  onSuccess,
}: {
  onClose: () => void
  onSuccess?: () => void
}) {
  const [preview, setPreview] = useState<CsvRow[]>([])
  const [validations, setValidations] = useState<RowValidation[]>([])
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<{ success: number; failed: number } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const parseCSV = (text: string) => {
    const lines = text.split('\n').filter(l => l.trim())
    const headers = lines[0].split(',').map(h => h.trim())
    const requiredHeaders = ['source_id', 'target_id', 'amount', 'currency', 'timestamp', 'tx_hash']
    
    // Validate headers
    const missingHeaders = requiredHeaders.filter(h => !headers.includes(h))
    if (missingHeaders.length > 0) {
      setError(`Missing columns: ${missingHeaders.join(', ')}`)
      return
    }

    const rows: CsvRow[] = []
    const validationErrors: RowValidation[] = []

    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(',').map(v => v.trim())
      if (values.length !== headers.length) continue
      
      const row: any = {}
      const errors: string[] = []
      
      headers.forEach((h, idx) => {
        row[h] = values[idx]
      })

      if (!row.source_id) errors.push('Missing source_id')
      if (!row.target_id) errors.push('Missing target_id')
      if (isNaN(Number(row.amount)) || Number(row.amount) <= 0) errors.push('Invalid amount')
      if (!row.currency) errors.push('Missing currency')
      if (isNaN(Number(row.timestamp))) errors.push('Invalid timestamp')
      if (!row.tx_hash) errors.push('Missing tx_hash')

      rows.push({
        source_id: row.source_id,
        target_id: row.target_id,
        amount: Number(row.amount),
        currency: row.currency,
        timestamp: Number(row.timestamp),
        tx_hash: row.tx_hash,
      })

      if (errors.length > 0) {
        validationErrors.push({ row: i, errors })
      }
    }

    setPreview(rows)
    setValidations(validationErrors)
    setError(null)
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (event) => {
      const text = event.target?.result as string
      parseCSV(text)
    }
    reader.readAsText(file)
  }

  const handleImport = async () => {
    setImporting(true)
    setError(null)

    try {
      let successCount = 0
      let failCount = 0

      // Filter valid rows
      const invalidIndices = new Set(validations.map(v => v.row - 1))
      const validRows = preview.filter((_, i) => !invalidIndices.has(i))

      for (const row of validRows) {
        try {
          await api.createRelationship(row)
          successCount++
        } catch {
          failCount++
        }
      }

      setImportResult({ success: successCount, failed: failCount })
      if (onSuccess) onSuccess()
    } catch (err: any) {
      setError(err.message || 'Import failed')
    } finally {
      setImporting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl w-full max-w-3xl shadow-xl border border-gray-100 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center">
              <Upload size={18} className="text-amber-600" />
            </div>
            <div>
              <h2 className="font-bold text-gray-900">Batch Relationship Import</h2>
              <p className="text-xs text-gray-500">Upload CSV to bulk-import transaction relationships</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100">
            <X size={18} className="text-gray-400" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {/* File Upload */}
          {preview.length === 0 && !importResult && (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-gray-300 rounded-2xl p-12 text-center hover:border-brand-blue hover:bg-brand-blue/5 cursor-pointer transition-all"
            >
              <Upload size={32} className="mx-auto mb-3 text-gray-400" />
              <p className="text-sm font-semibold text-gray-700">Click to upload CSV</p>
              <p className="text-xs text-gray-500 mt-1">Format: source_id, target_id, amount, currency, timestamp, tx_hash</p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                onChange={handleFileUpload}
                className="hidden"
              />
            </div>
          )}

          {/* Preview Table */}
          {preview.length > 0 && !importResult && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-gray-700">
                  {preview.length} rows parsed
                  {validations.length > 0 && (
                    <span className="text-amber-600 ml-2">
                      ({validations.length} with errors)
                    </span>
                  )}
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => { setPreview([]); setValidations([]); setError(null) }}
                    className="btn-outline text-xs"
                  >
                    Re-upload
                  </button>
                  <button
                    onClick={handleImport}
                    disabled={importing}
                    className="btn-primary text-xs"
                  >
                    {importing ? <Loader2 size={12} className="animate-spin" /> : null}
                    {importing ? 'Importing...' : `Import ${preview.length - validations.length} valid rows`}
                  </button>
                </div>
              </div>

              {error && (
                <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-sm text-rose-700 flex items-center gap-2">
                  <AlertTriangle size={14} />
                  {error}
                </div>
              )}

              <div className="overflow-x-auto rounded-xl border border-gray-200">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left font-semibold text-gray-600 px-4 py-3 text-xs">#</th>
                      <th className="text-left font-semibold text-gray-600 px-4 py-3 text-xs">Source</th>
                      <th className="text-left font-semibold text-gray-600 px-4 py-3 text-xs">Target</th>
                      <th className="text-left font-semibold text-gray-600 px-4 py-3 text-xs">Amount</th>
                      <th className="text-left font-semibold text-gray-600 px-4 py-3 text-xs">Currency</th>
                      <th className="text-left font-semibold text-gray-600 px-4 py-3 text-xs">Timestamp</th>
                      <th className="text-left font-semibold text-gray-600 px-4 py-3 text-xs">Validation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.slice(0, 20).map((row, i) => {
                      const validation = validations.find(v => v.row === i + 1)
                      return (
                        <tr key={i} className={`border-t border-gray-50 ${validation ? 'bg-rose-50' : ''}`}>
                          <td className="px-4 py-3 text-xs text-gray-400">{i + 1}</td>
                          <td className="px-4 py-3 font-mono text-xs">{row.source_id.slice(0, 16)}...</td>
                          <td className="px-4 py-3 font-mono text-xs">{row.target_id.slice(0, 16)}...</td>
                          <td className="px-4 py-3 text-xs font-medium">{row.amount.toLocaleString()}</td>
                          <td className="px-4 py-3 text-xs">{row.currency}</td>
                          <td className="px-4 py-3 text-xs font-mono">{new Date(row.timestamp).toLocaleDateString()}</td>
                          <td className="px-4 py-3">
                            {validation ? (
                              <span className="inline-flex items-center gap-1 text-xs text-rose-600" title={validation.errors.join(', ')}>
                                <AlertTriangle size={10} /> {validation.errors.length} errors
                              </span>
                            ) : (
                              <CheckCircle size={12} className="text-emerald-500" />
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
              {preview.length > 20 && (
                <p className="text-xs text-gray-400">Showing first 20 of {preview.length} rows</p>
              )}
            </div>
          )}

          {/* Result */}
          {importResult && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle size={18} className="text-emerald-600" />
                  <p className="font-semibold text-emerald-900">Import Complete</p>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-xs text-gray-500">Successfully Imported</p>
                    <p className="text-2xl font-bold text-emerald-600">{importResult.success}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Failed</p>
                    <p className="text-2xl font-bold text-rose-600">{importResult.failed}</p>
                  </div>
                </div>
              </div>
              <button onClick={onClose} className="btn-primary w-full justify-center text-sm">
                Done
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}