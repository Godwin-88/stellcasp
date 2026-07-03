// src/components/SecurityEventLogViewer.tsx
import React, { useState } from 'react'
import { Search, Filter, Download, AlertTriangle, Info, Shield, X, ChevronDown, ChevronUp } from 'lucide-react'

type SecurityEvent = {
  occurredAt: string
  event: string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  entity: string
  ip: string
  description: string
  webhookStatus?: 'SENT' | 'PENDING' | 'FAILED'
}

const MOCK_EVENTS: SecurityEvent[] = [
  { occurredAt: '2026-07-03T18:22:00Z', event: 'UNAUTHORIZED_ACCESS_ATTEMPT', severity: 'CRITICAL', entity: '0xab...1234', ip: '185.220.101.42', description: 'Repeated failed API key attempts from Tor exit node', webhookStatus: 'SENT' },
  { occurredAt: '2026-07-03T16:10:00Z', event: 'PROOF_GENERATION_FAILED', severity: 'HIGH', entity: 'KE-PIN-987654321', ip: '192.168.1.50', description: 'Noir circuit proof generation timed out after 30s', webhookStatus: 'SENT' },
  { occurredAt: '2026-07-03T14:05:00Z', event: 'ENTITY_CREATED', severity: 'LOW', entity: 'CORP-KE-001', ip: '10.0.0.25', description: 'New corporate entity registered' },
  { occurredAt: '2026-07-03T12:30:00Z', event: 'PASSPORT_MINTED', severity: 'MEDIUM', entity: '0xab...1234', ip: '10.0.0.25', description: 'Compliance passport minted on Stellar testnet', webhookStatus: 'PENDING' },
  { occurredAt: '2026-07-03T09:15:00Z', event: 'JURISDICTION_REFRESH', severity: 'LOW', entity: 'SYSTEM', ip: '10.0.0.1', description: 'FATF jurisdiction list refreshed automatically' },
  { occurredAt: '2026-07-02T22:45:00Z', event: 'RATE_LIMIT_EXCEEDED', severity: 'HIGH', entity: '0xcd...5678', ip: '45.33.32.156', description: 'API rate limit exceeded (120 req/min)', webhookStatus: 'FAILED' },
  { occurredAt: '2026-07-02T18:30:00Z', event: 'DISCLOSURE_REQUEST', severity: 'MEDIUM', entity: '0xab...1234', ip: '192.168.1.100', description: 'Selective disclosure request from Stellar DEX', webhookStatus: 'SENT' },
  { occurredAt: '2026-07-02T14:20:00Z', event: 'ANOMALY_DETECTED', severity: 'CRITICAL', entity: 'KE-PIN-987654321', ip: '10.0.0.25', description: 'Structural anomaly detected: circular transaction pattern', webhookStatus: 'SENT' },
]

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-700',
  HIGH: 'bg-orange-100 text-orange-700',
  MEDIUM: 'bg-amber-100 text-amber-700',
  LOW: 'bg-gray-100 text-gray-700',
}

const SEVERITY_ICONS: Record<string, React.ElementType> = {
  CRITICAL: AlertTriangle,
  HIGH: AlertTriangle,
  MEDIUM: Info,
  LOW: Info,
}

const WEBHOOK_COLORS: Record<string, string> = {
  SENT: 'bg-emerald-100 text-emerald-700',
  PENDING: 'bg-amber-100 text-amber-700',
  FAILED: 'bg-rose-100 text-rose-700',
}

export default function SecurityEventLogViewer() {
  const [events] = useState<SecurityEvent[]>(MOCK_EVENTS)
  const [search, setSearch] = useState('')
  const [severityFilter, setSeverityFilter] = useState<string>('ALL')
  const [expanded, setExpanded] = useState<number | null>(null)

  const filtered = events.filter(e => {
    const matchesSearch = !search ||
      e.event.toLowerCase().includes(search.toLowerCase()) ||
      e.entity.toLowerCase().includes(search.toLowerCase()) ||
      e.description.toLowerCase().includes(search.toLowerCase())
    const matchesSeverity = severityFilter === 'ALL' || e.severity === severityFilter
    return matchesSearch && matchesSeverity
  })

  const exportCSV = () => {
    const headers = ['Occurred At', 'Event', 'Severity', 'Entity', 'IP', 'Description', 'Webhook Status']
    const rows = filtered.map(e => [
      new Date(e.occurredAt).toISOString(),
      e.event,
      e.severity,
      e.entity,
      e.ip,
      e.description,
      e.webhookStatus || '—',
    ])
    const csv = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'security_events.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="relative w-full sm:w-80">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search events, entities, descriptions..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-blue/30 focus:border-brand-blue"
          />
        </div>
        <div className="flex items-center gap-2">
          <select
            value={severityFilter}
            onChange={e => setSeverityFilter(e.target.value)}
            className="text-sm px-3 py-2.5 rounded-xl border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-brand-blue/30"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
          <button onClick={exportCSV} className="btn-outline text-xs px-3 py-2.5">
            <Download size={12} /> Export CSV
          </button>
        </div>
      </div>

      {/* Event List */}
      <div className="space-y-2">
        {filtered.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-2xl border border-gray-100">
            <Shield size={32} className="text-gray-300 mx-auto mb-3" />
            <p className="text-sm text-gray-500">No security events match your filters</p>
          </div>
        ) : (
          filtered.map((event, i) => {
            const SeverityIcon = SEVERITY_ICONS[event.severity]
            const isExpanded = expanded === i
            return (
              <div
                key={i}
                className={`bg-white rounded-2xl border overflow-hidden transition-all ${
                  event.severity === 'CRITICAL' ? 'border-red-200 ring-1 ring-red-100' : 'border-gray-100'
                }`}
              >
                <button
                  onClick={() => setExpanded(isExpanded ? null : i)}
                  className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                      event.severity === 'CRITICAL' ? 'bg-red-50' : 'bg-gray-50'
                    }`}>
                      <SeverityIcon size={14} className={
                        event.severity === 'CRITICAL' ? 'text-red-600' :
                        event.severity === 'HIGH' ? 'text-orange-600' :
                        'text-gray-500'
                      } />
                    </div>
                    <div className="text-left min-w-0">
                      <p className="text-sm font-semibold text-gray-900 truncate">{event.event}</p>
                      <p className="text-xs text-gray-500 truncate">{event.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 ml-4">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEVERITY_COLORS[event.severity]}`}>
                      {event.severity}
                    </span>
                    {event.webhookStatus && (
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${WEBHOOK_COLORS[event.webhookStatus]}`}>
                        {event.webhookStatus}
                      </span>
                    )}
                    <span className="text-xs text-gray-400 hidden sm:block">
                      {new Date(event.occurredAt).toLocaleString()}
                    </span>
                    {isExpanded ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
                  </div>
                </button>

                {isExpanded && (
                  <div className="px-4 pb-4 border-t border-gray-100 pt-3">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <p className="text-xs text-gray-400 uppercase tracking-wider">Occurred At</p>
                        <p className="font-medium text-gray-900">{new Date(event.occurredAt).toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400 uppercase tracking-wider">Entity</p>
                        <p className="font-mono text-xs text-gray-900">{event.entity}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400 uppercase tracking-wider">IP Address</p>
                        <p className="font-mono text-xs text-gray-900">{event.ip}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400 uppercase tracking-wider">Webhook</p>
                        {event.webhookStatus ? (
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${WEBHOOK_COLORS[event.webhookStatus]}`}>
                            {event.webhookStatus}
                          </span>
                        ) : (
                          <p className="text-gray-400">—</p>
                        )}
                      </div>
                    </div>
                    <div className="mt-3 p-3 rounded-xl bg-gray-50">
                      <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Description</p>
                      <p className="text-sm text-gray-700">{event.description}</p>
                    </div>
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}