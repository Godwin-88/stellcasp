// src/components/JurisdictionRiskManager.tsx
import React, { useState } from 'react'
import { Loader2, RefreshCw, Save, X, CheckCircle, AlertTriangle } from 'lucide-react'

type Jurisdiction = {
  iso2: string
  riskScore: number
  designation: 'FATF_BLACK' | 'FATF_GREY' | 'OFAC' | 'NEUTRAL'
  lastUpdated: string
}

const INITIAL_JURISDICTIONS: Jurisdiction[] = [
  { iso2: 'KE', riskScore: 0.45, designation: 'FATF_GREY', lastUpdated: '2026-06-15' },
  { iso2: 'US', riskScore: 0.15, designation: 'NEUTRAL', lastUpdated: '2026-06-10' },
  { iso2: 'IR', riskScore: 0.92, designation: 'FATF_BLACK', lastUpdated: '2026-06-20' },
  { iso2: 'KP', riskScore: 0.95, designation: 'OFAC', lastUpdated: '2026-06-20' },
  { iso2: 'GB', riskScore: 0.12, designation: 'NEUTRAL', lastUpdated: '2026-06-08' },
  { iso2: 'AE', riskScore: 0.35, designation: 'FATF_GREY', lastUpdated: '2026-06-12' },
  { iso2: 'CN', riskScore: 0.50, designation: 'NEUTRAL', lastUpdated: '2026-06-18' },
  { iso2: 'RU', riskScore: 0.70, designation: 'OFAC', lastUpdated: '2026-06-22' },
]

const DESIGNATION_COLORS: Record<string, string> = {
  FATF_BLACK: 'bg-red-100 text-red-700',
  FATF_GREY: 'bg-amber-100 text-amber-700',
  OFAC: 'bg-purple-100 text-purple-700',
  NEUTRAL: 'bg-emerald-100 text-emerald-700',
}

export default function JurisdictionRiskManager() {
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>(INITIAL_JURISDICTIONS)
  const [editing, setEditing] = useState<string | null>(null)
  const [editValues, setEditValues] = useState<Partial<Jurisdiction>>({})
  const [refreshing, setRefreshing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const handleRefresh = async () => {
    setRefreshing(true)
    await new Promise(r => setTimeout(r, 2000))
    setJurisdictions(prev => prev.map(j => ({
      ...j,
      riskScore: Math.min(1, Math.max(0, j.riskScore + (Math.random() - 0.5) * 0.1)),
      lastUpdated: new Date().toISOString().split('T')[0],
    })))
    setRefreshing(false)
  }

  const handleSave = async () => {
    setSaving(true)
    await new Promise(r => setTimeout(r, 1000))
    setSaving(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  const startEdit = (j: Jurisdiction) => {
    setEditing(j.iso2)
    setEditValues({ ...j })
  }

  const saveEdit = () => {
    if (!editing) return
    setJurisdictions(prev => prev.map(j =>
      j.iso2 === editing ? { ...j, ...editValues } : j
    ))
    setEditing(null)
    setEditValues({})
  }

  const riskColor = (v: number) => {
    if (v < 0.3) return 'text-emerald-600'
    if (v < 0.6) return 'text-amber-600'
    return 'text-rose-600'
  }

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          {jurisdictions.length} jurisdictions configured
        </p>
        <div className="flex items-center gap-2">
          {saved && (
            <span className="inline-flex items-center gap-1 text-xs text-emerald-600">
              <CheckCircle size={12} /> Saved
            </span>
          )}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="btn-outline text-xs"
          >
            <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} />
            {refreshing ? 'Refreshing...' : 'Refresh from FATF API'}
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-primary text-xs"
          >
            {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left font-semibold text-gray-600 px-6 py-4">ISO2</th>
                <th className="text-left font-semibold text-gray-600 px-6 py-4">Risk Score</th>
                <th className="text-left font-semibold text-gray-600 px-6 py-4">Designation</th>
                <th className="text-left font-semibold text-gray-600 px-6 py-4">Last Updated</th>
                <th className="text-right font-semibold text-gray-600 px-6 py-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {jurisdictions.map(j => (
                <tr key={j.iso2} className="border-b border-gray-50 hover:bg-gray-50/50">
                  {editing === j.iso2 ? (
                    <>
                      <td className="px-6 py-4 font-mono font-bold text-gray-900">{j.iso2}</td>
                      <td className="px-6 py-4">
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.05"
                          value={editValues.riskScore ?? j.riskScore}
                          onChange={e => setEditValues(v => ({ ...v, riskScore: parseFloat(e.target.value) }))}
                          className="w-24"
                        />
                        <span className={`ml-2 font-semibold ${riskColor(editValues.riskScore ?? j.riskScore)}`}>
                          {((editValues.riskScore ?? j.riskScore) * 100).toFixed(0)}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <select
                          value={editValues.designation ?? j.designation}
                          onChange={e => setEditValues(v => ({ ...v, designation: e.target.value as any }))}
                          className="text-xs px-2 py-1 rounded-lg border border-gray-200"
                        >
                          <option value="FATF_BLACK">FATF_BLACK</option>
                          <option value="FATF_GREY">FATF_GREY</option>
                          <option value="OFAC">OFAC</option>
                          <option value="NEUTRAL">NEUTRAL</option>
                        </select>
                      </td>
                      <td className="px-6 py-4 text-gray-500">{j.lastUpdated}</td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button onClick={saveEdit} className="text-xs font-semibold text-emerald-600 hover:underline">Save</button>
                          <button onClick={() => setEditing(null)} className="text-xs text-gray-400 hover:underline">Cancel</button>
                        </div>
                      </td>
                    </>
                  ) : (
                    <>
                      <td className="px-6 py-4">
                        <span className="font-mono font-bold text-gray-900">{j.iso2}</span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <div className="h-2 w-20 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                j.riskScore < 0.3 ? 'bg-emerald-500' :
                                j.riskScore < 0.6 ? 'bg-amber-500' : 'bg-rose-500'
                              }`}
                              style={{ width: `${j.riskScore * 100}%` }}
                            />
                          </div>
                          <span className={`font-semibold text-xs ${riskColor(j.riskScore)}`}>
                            {(j.riskScore * 100).toFixed(0)}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${DESIGNATION_COLORS[j.designation]}`}>
                          {j.designation}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-gray-500 text-xs">{j.lastUpdated}</td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => startEdit(j)}
                          className="text-xs font-semibold text-brand-blue hover:underline"
                        >
                          Edit
                        </button>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}