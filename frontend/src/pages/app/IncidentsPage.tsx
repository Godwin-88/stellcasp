// src/pages/app/IncidentsPage.tsx
import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle, CheckCircle, Clock, Filter, Search,
  ArrowRight, ChevronLeft, ChevronRight, Loader2,
} from 'lucide-react'
import { api } from '../../lib/api'

type Incident = {
  id: string
  entity_hash: string
  ci: number
  threshold: number
  status: 'PENDING_REVIEW' | 'RESOLVED' | 'ALERT_FAILED'
  created_at: string
}

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<'ALL' | Incident['status']>('ALL')
  const [page, setPage] = useState(1)
  const limit = 10

  useEffect(() => {
    ;(async () => {
      try {
        const res = await api.getIncidents({
          status: statusFilter === 'ALL' ? undefined : statusFilter,
          limit,
          offset: (page - 1) * limit,
        })
        setIncidents(res.items || [])
      } finally {
        setLoading(false)
      }
    })()
  }, [statusFilter, page])

  const filtered = incidents.filter(i =>
    !search || i.entity_hash.toLowerCase().includes(search.toLowerCase())
  )

  const statusBadge = (status: Incident['status']) => {
    const styles: Record<Incident['status'], string> = {
      PENDING_REVIEW: 'bg-amber-50 text-amber-700',
      RESOLVED: 'bg-emerald-50 text-emerald-700',
      ALERT_FAILED: 'bg-rose-50 text-rose-700',
    }
    const icons: Record<Incidents['status'], JSX.Element> = {
      PENDING_REVIEW: <Clock size={12} />,
      RESOLVED: <CheckCircle size={12} />,
      ALERT_FAILED: <AlertTriangle size={12} />,
    }
    return (
      <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${styles[status]}`}>
        {icons[status]} {status.replace('_', ' ')}
      </span>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Compliance Incidents</h1>
        <p className="text-sm text-gray-500 mt-1">Review and manage flagged compliance events</p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="relative w-full sm:w-80">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search entity hash..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-blue/30 focus:border-brand-blue"
          />
        </div>
        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value as any)}
            className="text-sm px-3 py-2 rounded-xl border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-brand-blue/30"
          >
            <option value="ALL">All Statuses</option>
            <option value="PENDING_REVIEW">Pending Review</option>
            <option value="RESOLVED">Resolved</option>
            <option value="ALERT_FAILED">Alert Failed</option>
          </select>
          <button className="btn-outline text-xs px-3 py-2">
            <Filter size={12} /> Advanced
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="text-center py-12 text-gray-400">
            <Loader2 size={24} className="animate-spin mx-auto mb-3" />
            Loading incidents...
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12">
            <CheckCircle size={32} className="text-emerald-500 mx-auto mb-3" />
            <p className="text-sm text-gray-500">No incidents match your filters</p>
            <p className="text-xs text-gray-400 mt-1">All entities are currently compliant</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-100">
                  <tr>
                    <th className="text-left font-semibold text-gray-600 px-6 py-4">Entity Hash</th>
                    <th className="text-left font-semibold text-gray-600 px-6 py-4">CI</th>
                    <th className="text-left font-semibold text-gray-600 px-6 py-4">Threshold</th>
                    <th className="text-left font-semibold text-gray-600 px-6 py-4">Status</th>
                    <th className="text-left font-semibold text-gray-600 px-6 py-4">Created</th>
                    <th className="text-right font-semibold text-gray-600 px-6 py-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((inc, i) => (
                    <tr key={i} className="border-b border-gray-50 hover:bg-gray-50/50">
                      <td className="px-6 py-4 font-mono text-xs text-gray-900">
                        {inc.entity_hash.slice(0, 16)}...
                      </td>
                      <td className="px-6 py-4">
                        <span className={`font-semibold ${inc.ci >= inc.threshold ? 'text-rose-600' : 'text-gray-900'}`}>
                          {inc.ci.toFixed(3)}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-gray-500">{inc.threshold.toFixed(3)}</td>
                      <td className="px-6 py-4">{statusBadge(inc.status)}</td>
                      <td className="px-6 py-4 text-gray-500">
                        {new Date(inc.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <Link
                          to={`/app/audit/${inc.entity_hash}`}
                          className="text-xs font-semibold text-brand-blue hover:underline flex items-center justify-end gap-1"
                        >
                          Audit <ArrowRight size={12} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-6 py-4 border-t border-gray-100">
              <p className="text-xs text-gray-500">
                Page {page} of {Math.ceil((incidents.length || 1) / limit)}
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-2 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft size={16} />
                </button>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={filtered.length < limit}
                  className="p-2 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}