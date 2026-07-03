// src/pages/app/AppLayout.tsx
import React, { useState } from 'react'
import { Link, useLocation, Outlet, Navigate } from 'react-router-dom'
import {
  LayoutDashboard, Users, AlertTriangle, FileCheck, Brain,
  GitBranch, Key, Settings, LogOut, Lock, Menu, X, ChevronRight,
} from 'lucide-react'

const NAV_ITEMS = [
  { icon: LayoutDashboard, label: 'Dashboard', path: '/app' },
  { icon: Users, label: 'Entities', path: '/app/entities' },
  { icon: AlertTriangle, label: 'Incidents', path: '/app/incidents' },
  { icon: FileCheck, label: 'Passports', path: '/app/passports' },
  { icon: Brain, label: 'Agent Runs', path: '/app/runs' },
  { icon: GitBranch, label: 'Audit Trail', path: '/app/audit' },
  { icon: Key, label: 'API Keys', path: '/app/keys' },
  { icon: Settings, label: 'Settings', path: '/app/settings' },
]

export default function AppLayout() {
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const isAuthed = localStorage.getItem('zkco_api_key')
  
  if (!isAuthed) return <Navigate to="/login" replace />

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside className={`fixed md:static inset-y-0 left-0 z-40 w-64 bg-white border-r border-gray-200 transform ${mobileOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0 transition-transform`}>
        <div className="h-16 flex items-center gap-2.5 px-6 border-b border-gray-100">
          <div className="w-8 h-8 bg-gradient-to-br from-brand-blue to-blue-700 rounded-lg flex items-center justify-center">
            <Lock size={14} className="text-white" />
          </div>
          <span className="font-bold text-gray-900">ZKCO</span>
        </div>
        <nav className="p-4 space-y-1">
          {NAV_ITEMS.map(item => {
            const Icon = item.icon
            const active = location.pathname === item.path || 
              (item.path !== '/app' && location.pathname.startsWith(item.path))
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMobileOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                  active
                    ? 'bg-brand-blue/10 text-brand-blue'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <Icon size={16} />
                {item.label}
                {active && <ChevronRight size={14} className="ml-auto" />}
              </Link>
            )
          })}
        </nav>
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-100">
          <button
            onClick={() => {
              localStorage.removeItem('zkco_api_key')
              window.location.href = '/login'
            }}
            className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-50 w-full"
          >
            <LogOut size={16} />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
          <button className="md:hidden p-2 rounded-lg text-gray-600 hover:bg-gray-100" onClick={() => setMobileOpen(o => !o)}>
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          <div className="hidden md:block text-sm text-gray-500">
            {NAV_ITEMS.find(i => i.path === location.pathname)?.label || 'Dashboard'}
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 font-medium">Testnet</span>
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-blue to-blue-700 flex items-center justify-center text-white text-xs font-bold">
              EG
            </div>
          </div>
        </header>
        <main className="flex-1 p-6 md:p-8 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}