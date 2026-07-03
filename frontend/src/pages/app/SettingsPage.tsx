// src/pages/app/SettingsPage.tsx
import React, { useState } from 'react'
import { Globe, Shield, Key, Bell } from 'lucide-react'
import JurisdictionRiskManager from '../../components/JurisdictionRiskManager'

const SETTINGS_TABS = ['Jurisdiction Risk', 'API Keys', 'Notifications']

export default function SettingsPage() {
  const [tab, setTab] = useState(0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-1">Platform configuration</p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <div className="flex gap-6 overflow-x-auto">
          {SETTINGS_TABS.map((label, i) => (
            <button
              key={i}
              onClick={() => setTab(i)}
              className={`pb-3 text-sm font-semibold border-b-2 whitespace-nowrap transition-all ${
                tab === i
                  ? 'border-brand-blue text-brand-blue'
                  : 'border-transparent text-gray-500 hover:text-gray-800'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab 0: Jurisdiction Risk */}
      {tab === 0 && (
        <div className="bg-white rounded-2xl border border-gray-100 p-6">
          <div className="flex items-center gap-2 mb-5">
            <Globe size={16} className="text-brand-blue" />
            <h2 className="font-bold text-gray-900">Jurisdiction Risk Manager</h2>
          </div>
          <JurisdictionRiskManager />
        </div>
      )}

      {/* Tab 1: API Keys */}
      {tab === 1 && (
        <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center">
          <Key size={32} className="text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-500">Manage API keys from the <a href="/app/keys" className="text-brand-blue hover:underline">API Keys page</a></p>
        </div>
      )}

      {/* Tab 2: Notifications */}
      {tab === 2 && (
        <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center">
          <Bell size={32} className="text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-500">Notification preferences coming soon</p>
        </div>
      )}
    </div>
  )
}