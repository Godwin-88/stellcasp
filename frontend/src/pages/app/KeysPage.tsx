// src/pages/app/KeysPage.tsx
import React, { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Key, Plus, Copy, Eye, EyeOff, Trash2, Loader2,
  CheckCircle, AlertCircle, X,
} from 'lucide-react'
import { api } from '../../lib/api'

type ApiKey = {
  key_id: string
  name: string
  rate_limit: number
  is_active: boolean
  created_at: string
  plaintext_key?: string // Only returned once on creation
}

export default function KeysPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(searchParams.get('action') === 'new')
  const [showPlaintext, setShowPlaintext] = useState<Record<string, boolean>>({})

  // Create form
  const [newKey, setNewKey] = useState({ name: '', rate_limit: 60 })
  const [creating, setCreating] = useState(false)
  const [createdKey, setCreatedKey] = useState<ApiKey | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Mock data for demo
    ;(async () => {
      try {
        const mock: ApiKey[] = [
          {
            key_id: 'key_abc123',
            name: 'Demo Integration',
            rate_limit: 60,
            is_active: true,
            created_at: '2026-07-01T10:00:00Z',
          },
        ]
        setKeys(mock)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setCreating(true)

    try {
      const res = await api.createApiKey(newKey.name, newKey.rate_limit)
      setCreatedKey(res)
      setKeys(prev => [res, ...prev])
      setShowCreate(false)
      setSearchParams({})
      setNewKey({ name: '', rate_limit: 60 })
    } catch (err: any) {
      setError(err.message || 'Failed to create API key')
    } finally {
      setCreating(false)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    // Could show toast here
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">API Keys</h1>
          <p className="text-sm text-gray-500 mt-1">Manage authentication credentials for platform access</p>
        </div>
        <button
          onClick={() => { setShowCreate(true); setSearchParams({ action: 'new' }) }}
          className="btn-primary text-sm"
        >
          <Plus size={14} /> Create API Key
        </button>
      </div>

      {/* Keys List */}
      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="text-center py-12 text-gray-400">
            <Loader2 size={24} className="animate-spin mx-auto mb-3" />
            Loading API keys...
          </div>
        ) : keys.length === 0 ? (
          <div className="text-center py-12">
            <Key size={32} className="text-gray-300 mx-auto mb-3" />
            <p className="text-sm text-gray-500">No API keys created yet</p>
            <button
              onClick={() => { setShowCreate(true); setSearchParams({ action: 'new' }) }}
              className="btn-primary text-xs mt-4"
            >
              Create your first key
            </button>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {keys.map(key => (
              <div key={key.key_id} className="p-5 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="font-semibold text-gray-900">{key.name}</p>
                      {key.is_active ? (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-medium">
                          Active
                        </span>
                      ) : (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 font-medium">
                          Inactive
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 font-mono mb-2">{key.key_id}</p>
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span>Rate limit: {key.rate_limit}/min</span>
                      <span>•</span>
                      <span>Created: {new Date(key.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600">
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Modal */}
      {showCreate && !createdKey && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl w-full max-w-md shadow-xl border border-gray-100">
            <div className="flex items-center justify-between p-6 border-b border-gray-100">
              <h2 className="font-bold text-gray-900">Create API Key</h2>
              <button onClick={() => { setShowCreate(false); setSearchParams({}) }} className="p-1 rounded-lg hover:bg-gray-100">
                <X size={18} className="text-gray-400" />
              </button>
            </div>
            <form onSubmit={handleCreate} className="p-6 space-y-5">
              {error && (
                <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700 flex items-start gap-2">
                  <AlertCircle size={14} className="flex-shrink-0 mt-0.5" />
                  {error}
                </div>
              )}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1.5">Key Name</label>
                <input
                  type="text"
                  placeholder="e.g., Production Integration"
                  value={newKey.name}
                  onChange={e => setNewKey(k => ({ ...k, name: e.target.value }))}
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-blue/30 focus:border-brand-blue"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1.5">Rate Limit (requests/min)</label>
                <select
                  value={newKey.rate_limit}
                  onChange={e => setNewKey(k => ({ ...k, rate_limit: parseInt(e.target.value) }))}
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-blue/30 focus:border-brand-blue"
                >
                  <option value={60}>60 RPM (default)</option>
                  <option value={120}>120 RPM</option>
                  <option value={300}>300 RPM</option>
                  <option value={600}>600 RPM (max)</option>
                </select>
                <p className="text-xs text-gray-400 mt-1">Higher limits require admin approval</p>
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowCreate(false); setSearchParams({}) }}
                  className="btn-outline flex-1 justify-center text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating || !newKey.name}
                  className="btn-primary flex-1 justify-center text-sm disabled:opacity-60"
                >
                  {creating ? <Loader2 size={14} className="animate-spin" /> : 'Create Key'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Created Key Success Modal */}
      {createdKey && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl w-full max-w-lg shadow-xl border border-gray-100">
            <div className="p-6 border-b border-gray-100">
              <div className="flex items-center gap-3 mb-2">
                <CheckCircle size={20} className="text-emerald-600" />
                <h2 className="font-bold text-gray-900">API Key Created</h2>
              </div>
              <p className="text-sm text-gray-500">
                Save this key securely — it will not be shown again.
              </p>
            </div>
            <div className="p-6 space-y-5">
              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5">
                  Plaintext API Key
                </label>
                <div className="relative">
                  <input
                    type={showPlaintext[createdKey.key_id] ? 'text' : 'password'}
                    value={createdKey.plaintext_key}
                    readOnly
                    className="w-full px-4 py-3 pr-10 rounded-xl border border-gray-200 bg-gray-50 font-mono text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPlaintext(p => ({ ...p, [createdKey.key_id]: !p[createdKey.key_id] }))}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showPlaintext[createdKey.key_id] ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                <button
                  onClick={() => copyToClipboard(createdKey.plaintext_key || '')}
                  className="mt-2 text-xs text-brand-blue hover:underline flex items-center gap-1"
                >
                  <Copy size={12} /> Copy to clipboard
                </button>
              </div>
              <div className="p-4 rounded-xl bg-amber-50 border border-amber-200">
                <p className="text-xs text-amber-800">
                  <strong>Security reminder:</strong> Store this key in a secure location. It grants access to the ZKCO platform and cannot be recovered if lost.
                </p>
              </div>
              <button
                onClick={() => setCreatedKey(null)}
                className="btn-primary w-full justify-center text-sm"
              >
                I've saved the key — Continue
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}