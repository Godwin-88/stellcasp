// src/pages/LoginPage.tsx
import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Lock, ArrowRight, Eye, EyeOff, Code } from 'lucide-react'

export default function LoginPage() {
  const navigate = useNavigate()
  const [showDevLogin, setShowDevLogin] = useState(false)
  const [apiKey, setApiKey] = useState('')
  const [showKey, setShowKey] = useState(false)

  const launchDemo = () => {
    localStorage.setItem('zkco_api_key', 'demo_key')
    localStorage.setItem('zkco_admin_secret', 'demo_admin')
    navigate('/app', { replace: true })
  }

  const handleDevLogin = (e: React.FormEvent) => {
    e.preventDefault()
    localStorage.setItem('zkco_api_key', apiKey)
    localStorage.setItem('zkco_admin_secret', 'demo_admin')
    navigate('/app', { replace: true })
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-navy via-brand-navy-mid to-brand-blue flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <Link to="/" className="flex items-center gap-2.5 justify-center mb-8">
          <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm border border-white/30">
            <Lock size={18} className="text-white" />
          </div>
          <span className="font-bold text-white text-lg">ZKCO</span>
        </Link>

        <div className="bg-white rounded-3xl p-8 shadow-xl border border-gray-100">
          {!showDevLogin ? (
            <>
              <div className="text-center mb-8">
                <h1 className="text-2xl font-bold text-gray-900">Demo Environment</h1>
                <p className="text-sm text-gray-500 mt-2">
                  Jump straight into the platform. All endpoints are pre-configured.
                </p>
              </div>
              <button
                onClick={launchDemo}
                className="btn-primary w-full justify-center text-sm py-3"
              >
                Launch Demo <ArrowRight size={16} />
              </button>
              <button
                onClick={() => setShowDevLogin(true)}
                className="w-full mt-4 flex items-center justify-center gap-2 text-xs text-gray-400 hover:text-gray-600"
              >
                <Code size={12} /> Developer Login
              </button>
            </>
          ) : (
            <>
              <div className="text-center mb-6">
                <h1 className="text-xl font-bold text-gray-900">Developer Access</h1>
                <p className="text-xs text-gray-500 mt-1">Enter your production API key</p>
              </div>
              <form onSubmit={handleDevLogin} className="space-y-4">
                <div className="relative">
                  <input
                    type={showKey ? 'text' : 'password'}
                    placeholder="zkco_..."
                    value={apiKey}
                    onChange={e => setApiKey(e.target.value)}
                    className="w-full px-4 py-3 pr-10 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-blue/30"
                    required
                  />
                  <button type="button" onClick={() => setShowKey(s => !s)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                    {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                <button type="submit" className="btn-outline w-full justify-center text-sm">
                  Sign in with API Key
                </button>
                <button type="button" onClick={() => setShowDevLogin(false)} className="w-full text-xs text-gray-400 hover:text-gray-600">
                  ← Back to demo
                </button>
              </form>
            </>
          )}
        </div>

        <div className="mt-6 text-center">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/10 text-white/80 text-xs font-medium backdrop-blur-sm border border-white/20">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            Stellar Testnet · Demo Mode Active
          </span>
        </div>
      </div>
    </div>
  )
}