// src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import MarketplacePage from './pages/MarketplacePage'
import FeaturePage from './pages/FeaturePage'
import LoginPage from './pages/LoginPage'
import AppLayout from './pages/app/AppLayout'
import Dashboard from './pages/app/Dashboard'
import EntitiesPage from './pages/app/EntitiesPage'
import EntityDetail from './pages/app/EntityDetail'
import IncidentsPage from './pages/app/IncidentsPage'
import PassportsPage from './pages/app/PassportsPage'
import RunsPage from './pages/app/RunsPage'
import AuditPage from './pages/app/AuditPage'
import KeysPage from './pages/app/KeysPage'
import SettingsPage from './pages/app/SettingsPage'
import SecurityPage from './pages/app/SecurityPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Stage 1: Landing */}
        <Route path="/" element={<LandingPage />} />
        
        {/* Stage 2: Marketplace (pre-auth) */}
        <Route path="/marketplace" element={<MarketplacePage />} />
        <Route path="/marketplace/:slug" element={<FeaturePage />} />
        
        {/* Auth */}
        <Route path="/login" element={<LoginPage />} />
        
        {/* Stage 3: Authenticated App */}
        <Route path="/app" element={<AppLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="entities" element={<EntitiesPage />} />
          <Route path="entities/:id" element={<EntityDetail />} />
          <Route path="incidents" element={<IncidentsPage />} />
          <Route path="passports" element={<PassportsPage />} />
          <Route path="runs" element={<RunsPage />} />
          <Route path="audit" element={<AuditPage />} />
          <Route path="audit/:entityHash" element={<AuditPage />} />
          <Route path="keys" element={<KeysPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="security" element={<SecurityPage />} />
        </Route>
        
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}