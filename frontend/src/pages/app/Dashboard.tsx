// src/pages/app/Dashboard.tsx
import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Users, AlertTriangle, FileCheck, Brain, TrendingUp,
  ArrowRight, Activity, CheckCircle, XCircle, Clock,
} from 'lucide-react'
import { api } from '../../lib/api'

const DEMO_INCIDENTS = [
  { entity_hash: '0xab...1234', ci: 0.82, threshold: 0.75, status: 'PENDING_REVIEW', created_at: '2026-07-03T09:12:00Z' },
  { entity_hash: '0xcd...5678', ci: 0.79, threshold: 0.75, status: 'PENDING_REVIEW', created_at: '2026-07-02T14:45:00Z' },
]

export default function Dashboard() {
  const [stats, setStats] = useState({ entities: 12, incidents: 2, passports: 8, runs: 15 })
  const [recentIncidents, setRecentIncidents] = useState<any[]>(DEMO_INCIDENTS)
  const [loading, setLoading] = useState(false) // ⚡ Demo mode: skip real fetch

  useEffect(() => {
    ;(async () => {
      try {
        const [incidents] = await Promise.all([
          api.getIncidents({ limit: 5 }).catch(() => ({ items: DEMO_INCIDENTS, total: 2 })),
        ])
        setRecentIncidents(incidents.items || DEMO_INCIDENTS)
        setStats(s => ({ ...s, incidents: incidents.total || 2 }))
      } catch {
        // Use demo data on any error
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const statCards = [
    { icon: Users, label: 'Entities', value: stats.entities, color: 'from-blue-500 to-blue-600', path: '/app/entities' },
    { icon: AlertTriangle, label: 'Open Incidents', value: stats.incidents, color: 'from-amber-500 to-amber-600', path: '/app/incidents' },
    { icon: FileCheck, label: 'Active Passports', value: stats.passports, color: 'from-emerald-500 to-emerald-600', path: '/app/passports' },
    { icon: Brain, label: 'Agent Runs', value: stats.runs, color: 'from-rose-500 to-rose-600', path: '/app/runs' },
  ]

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">Compliance intelligence at a glance</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card, i) => {
          const Icon = card.icon
          return (
            <Link key={i} to={card.path} className="bg-white rounded-2xl p-5 border border-gray-100 hover:shadow-md transition-shadow">
              <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${card.color} flex items-center justify-center mb-3`}>
                <Icon size={18} className="text-white" />
              </div>
              <p className="text-2xl font-bold text-gray-900">{loading ? '—' : card.value}</p>
              <p className="text-xs text-gray-500 mt-1">{card.label}</p>
            </Link>
          )
        })}
      </div>

      {/* Main grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Recent incidents */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-gray-100 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-bold text-gray-900">Recent Incidents</h2>
            <Link to="/app/incidents" className="text-xs font-semibold text-brand-blue flex items-center gap-1 hover:gap-2 transition-all">
              View all <ArrowRight size={12} />
            </Link>
          </div>
          {recentIncidents.length === 0 ? (
            <div className="text-center py-12">
              <CheckCircle size={32} className="text-emerald-500 mx-auto mb-3" />
              <p className="text-sm text-gray-500">No open incidents — all entities compliant</p>
            </div>
          ) : (
            <div className="space-y-2">
              {recentIncidents.map((inc: any, i: number) => (
                <div key={i} className="flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50">
                  <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center">
                    <AlertTriangle size={14} className="text-amber-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{inc.entity_hash?.slice(0, 16)}...</p>
                    <p className="text-xs text-gray-500">CI: {inc.ci} · Threshold: {inc.threshold}</p>
                  </div>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 font-medium">
                    {inc.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Quick actions */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6">
          <h2 className="font-bold text-gray-900 mb-5">Quick Actions</h2>
          <div className="space-y-2">
            <Link to="/app/entities?action=new" className="flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 border border-gray-100">
              <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center">
                <Users size={14} className="text-blue-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">Add Entity</p>
                <p className="text-xs text-gray-500">Create wallet or ID node</p>
              </div>
              <ArrowRight size={14} className="text-gray-400" />
            </Link>
            <Link to="/app/runs?action=new" className="flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 border border-gray-100">
              <div className="w-8 h-8 rounded-lg bg-rose-50 flex items-center justify-center">
                <Brain size={14} className="text-rose-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">Run Pipeline</p>
                <p className="text-xs text-gray-500">Execute 5-agent workflow</p>
              </div>
              <ArrowRight size={14} className="text-gray-400" />
            </Link>
            <Link to="/app/keys?action=new" className="flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 border border-gray-100">
              <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center">
                <FileCheck size={14} className="text-emerald-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">Issue Passport</p>
                <p className="text-xs text-gray-500">Mint compliance credential</p>
              </div>
              <ArrowRight size={14} className="text-gray-400" />
            </Link>
          </div>

          {/* System status */}
          <div className="mt-6 pt-6 border-t border-gray-100">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">System Status</p>
            <div className="space-y-2">
              {[
                { label: 'Neo4j Aura', status: 'healthy' },
                { label: 'PostgreSQL', status: 'healthy' },
                { label: 'Stellar Testnet', status: 'healthy' },
                { label: 'Casper Testnet', status: 'healthy' },
              ].map((s, i) => (
                <div key={i} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">{s.label}</span>
                  <span className="flex items-center gap-1.5 text-xs text-emerald-600 font-medium">
                    <Activity size={10} />
                    {s.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}