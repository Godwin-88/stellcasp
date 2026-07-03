// src/pages/app/EntitiesPage.tsx
import React, { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Plus, Search, Filter, ArrowRight, Wallet, Hash,
  Calendar, MoreVertical, CheckCircle, AlertTriangle,
  Loader2, X, Upload,
} from 'lucide-react'
import { api } from '../../lib/api'
import RelationshipIngestionModal from '../../components/RelationshipIngestionModal'

type Entity = {
  id: string
  type: 'WALLET' | 'NATIONAL_ID' | 'CORPORATE'
  created_at: string
  risk_level?: 'LOW' | 'MEDIUM' | 'HIGH'
}

export default function EntitiesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [entities, setEntities] = useState<Entity[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'ALL' | 'WALLET' | 'NATIONAL_ID' | 'CORPORATE'>('ALL')
  const [showCreate, setShowCreate] = useState(searchParams.get('action') === 'new')
  const [showImport, setShowImport] = useState(false)

  // Create form state
  const [newEntity, setNewEntity] = useState({ id: '', type: 'WALLET' as const })
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  useEffect(() => {
    // Fetch entities (stub — replace with real endpoint when available)
    ;(async () => {
      try {
        // Mock data for demo
        const mock: Entity[] = [
          { id: '0xab...1234', type: 'WALLET', created_at: '2026-07-01T10:30:00Z', risk_level: 'LOW' },
          { id: 'KE-PIN-987654321', type: 'NATIONAL_ID', created_at: '2026-06-28T14:20:00Z', risk_level: 'MEDIUM' },
          { id: 'CORP-KE-001', type: 'CORPORATE', created_at: '2026-06-25T09:15:00Z', risk_level: 'HIGH' },
        ]
        setEntities(mock)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const filtered = entities.filter(e => {
    const matchesSearch = !search || e.id.toLowerCase().includes(search.toLowerCase())
    const matchesFilter = filter === 'ALL' || e.type === filter
    return matchesSearch && matchesFilter
  })

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreateError(null)
    setCreating(true)

    try {
      await api.createEntity({ id: newEntity.id, type: newEntity.type })
      setShowCreate(false)
      setSearchParams({})
      // Refresh list
      setEntities(prev => [{
        id: newEntity.id,
        type: newEntity.type,
        created_at: new Date().toISOString(),
      }, ...prev])
      setNewEntity({ id: '', type: 'WALLET' })
    } catch (err: any) {
      setCreateError(err.message || 'Failed to create entity')
    } finally {
      setCreating(false)
    }
  }

  const riskBadge = (level?: string) => {
    if (!level) return null
    const styles: Record<string, string> = {
      LOW: 'bg-emerald-50 text-emerald-700',
      MEDIUM: 'bg-amber-50 text-amber-700',
      HIGH: 'bg-rose-50 text-rose-700',
    }
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${styles[level]}`}>
        {level}
      </span>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Entities</h1>
          <p className="text-sm text-gray-500 mt-1">Manage wallets, national IDs, and corporate entities</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowImport(true)}
            className="btn-outline text-sm"
          >
            <Upload size={14} /> Import Transactions
          </button>
          <button
            onClick={() => { setShowCreate(true); setSearchParams({ action: 'new' }) }}
            className="btn-primary text-sm"
          >
            <Plus size={14} /> Add Entity
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="relative w-full sm:w-80">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search entities..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-blue/30 focus:border-brand-blue"
          />
        </div>
        <div className="flex items-center gap-2">
          <button className="btn-outline text-xs px-3 py-2">
            <Filter size={12} /> Filter
          </button>
          <select
            value={filter}
            onChange={e => setFilter(e.target.value as any)}
            className="text-sm px-3 py-2 rounded-xl border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-brand-blue/30"
          >
            <option value="ALL">All Types</option>
            <option value="WALLET">Wallets</option>
            <option value="NATIONAL_ID">National IDs</option>
            <option value="CORPORATE">Corporate</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="text-center py-12 text-gray-400">
            <Loader2 size={24} className="animate-spin mx-auto mb-3" />
            Loading entities...
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12">
            <Wallet size={32} className="text-gray-300 mx-auto mb-3" />
            <p className="text-sm text-gray-500">No entities found</p>
            <button
              onClick={() => { setShowCreate(true); setSearchParams({ action: 'new' }) }}
              className="btn-primary text-xs mt-4"
            >
              Add your first entity
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="text-left font-semibold text-gray-600 px-6 py-4">Entity ID</th>
                  <th className="text-left font-semibold text-gray-600 px-6 py-4">Type</th>
                  <th className="text-left font-semibold text-gray-600 px-6 py-4">Created</th>
                  <th className="text-left font-semibold text-gray-600 px-6 py-4">Risk</th>
                  <th className="text-right font-semibold text-gray-600 px-6 py-4">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((entity, i) => (
                  <tr key={i} className="border-b border-gray-50 hover:bg-gray-50/50">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-brand-blue/10 flex items-center justify-center">
                          {entity.type === 'WALLET' ? <Wallet size={14} className="text-brand-blue" /> : <Hash size={14} className="text-brand-blue" />}
                        </div>
                        <span className="font-mono text-xs text-gray-900">{entity.id}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 font-medium">
                        {entity.type}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-gray-500">
                      {new Date(entity.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4">{riskBadge(entity.risk_level)}</td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        to={`/app/entities/${entity.id}`}
                        className="text-xs font-semibold text-brand-blue hover:underline flex items-center justify-end gap-1"
                      >
                        View <ArrowRight size={12} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Import Transactions Modal */}
      {showImport && (
        <RelationshipIngestionModal
          onClose={() => setShowImport(false)}
          onSuccess={() => {
            // Could refresh entities list here
          }}
        />
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl w-full max-w-md shadow-xl border border-gray-100">
            <div className="flex items-center justify-between p-6 border-b border-gray-100">
              <h2 className="font-bold text-gray-900">Add New Entity</h2>
              <button onClick={() => { setShowCreate(false); setSearchParams({}) }} className="p-1 rounded-lg hover:bg-gray-100">
                <X size={18} className="text-gray-400" />
              </button>
            </div>
            <form onSubmit={handleCreate} className="p-6 space-y-5">
              {createError && (
                <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700">
                  {createError}
                </div>
              )}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1.5">Entity ID</label>
                <input
                  type="text"
                  placeholder="Wallet address or national ID"
                  value={newEntity.id}
                  onChange={e => setNewEntity(n => ({ ...n, id: e.target.value }))}
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-blue/30 focus:border-brand-blue"
                  required
                />
                <p className="text-xs text-gray-400 mt-1">Wallet address, hashed national ID, or corporate identifier</p>
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1.5">Type</label>
                <select
                  value={newEntity.type}
                  onChange={e => setNewEntity(n => ({ ...n, type: e.target.value as any }))}
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-blue/30 focus:border-brand-blue"
                >
                  <option value="WALLET">Wallet Address</option>
                  <option value="NATIONAL_ID">National ID (hashed)</option>
                  <option value="CORPORATE">Corporate Entity</option>
                </select>
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
                  disabled={creating || !newEntity.id}
                  className="btn-primary flex-1 justify-center text-sm disabled:opacity-60"
                >
                  {creating ? <Loader2 size={14} className="animate-spin" /> : 'Create Entity'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}