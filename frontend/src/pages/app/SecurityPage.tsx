// src/pages/app/SecurityPage.tsx
import React from 'react'
import { Shield } from 'lucide-react'
import SecurityEventLogViewer from '../../components/SecurityEventLogViewer'

export default function SecurityPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Security Events</h1>
        <p className="text-sm text-gray-500 mt-1">Monitor security events, webhook statuses, and export logs for SOC/SIEM ingestion</p>
      </div>
      <SecurityEventLogViewer />
    </div>
  )
}