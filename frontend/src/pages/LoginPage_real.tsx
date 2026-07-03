// src/pages/LoginPage.tsx
import React, { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Lock, Eye, EyeOff, ArrowRight, AlertCircle } from 'lucide-react'
import { api } from '../lib/api'

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [apiKey, setApiKey] = useState('')
  const [adminSecret, setAdminSecret] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [showAdmin, setShowAdmin] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const isRegister = location.search.includes('mode=register')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      // Validate API key by calling health endpoint
      localStorage.setItem('zkco_api_key', apiKey)
      if (adminSecret) {
        localStorage.setItem('zkco_admin_secret', adminSecret)
      }
      
      await api.health()
      
      // Success — redirect to app or registration flow
      if (isRegister) {
        navigate('/app/keys?action=new', { replace: true })
      } else {
        navigate('/app', { replace: true })
      }
    } catch (err: any) {
      localStorage.removeItem('zkco_api_key')
      localStorage.removeItem('zkco_admin_secret')
      setError(err.message || 'Authentication failed. Check your API key.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-navy via-brand-navy-mid to-brand-blue flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2.5 justify-center mb-8">
          <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm border border-white/30">
            <Lock size={18} className="text-white" />
          </div>
          <span className="font-bold text-white text-lg">ZKCO</span>
        </Link>

        {/* Card */}
        <div className="bg-white rounded-3xl p-8 shadow-xl border border-gray-100">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-gray-900">
              {isRegister ? 'Create API Key' : 'Sign in to ZKCO'}
            </h1>
            <p className="text-sm text-gray-500 mt-2">
              {isRegister 
                ? 'Get your API key from an admin to start using the platform' 
                : 'Enter your API key to access the compliance dashboard'}
            </p>
          </div>

          {error && (
            <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 flex items-start gap-3">
              <AlertCircle size={16} className="text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* API Key */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1.5">
                API Key
              </label>
              <div className="relative">
                <input
                  type={showKey ? 'text' : 'password'}
                  placeholder="zkco_..."
                  value={apiKey}
                  onChange={e => setApiKey(e.target.value)}
                  className="w-full px-4 py-3 pr-10 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-blue/30 focus:border-brand-blue transition-colors"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowKey(s => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Admin Secret (optional) */}
            {!isRegister && (
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1.5">
                  Admin Secret <span className="text-gray-400 font-normal">(optional)</span>
                </label>
                <div className="relative">
                  <input
                    type={showAdmin ? 'text' : 'password'}
                    placeholder="admin_..."
                    value={adminSecret}
                    onChange={e => setAdminSecret(e.target.value)}
                    className="w-full px-4 py-3 pr-10 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-blue/30 focus:border-brand-blue transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => setShowAdmin(s => !s)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showAdmin ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  Required for admin endpoints (key management, jurisdiction refresh)
                </p>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading || !apiKey}
              className="btn-primary w-full justify-center text-sm disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Authenticating...
                </span>
              ) : (
                <>
                  {isRegister ? 'Request API Key' : 'Sign in'}
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>

          {/* Footer links */}
          <div className="mt-8 pt-6 border-t border-gray-100 text-center">
            <p className="text-sm text-gray-500">
              {isRegister ? (
                <>
                  Already have a key?{' '}
                  <Link to="/login" className="text-brand-blue hover:underline font-medium">
                    Sign in
                  </Link>
                </>
              ) : (
                <>
                  Need access?{' '}
                  <Link to="/login?mode=register" className="text-brand-blue hover:underline font-medium">
                    Request API key
                  </Link>
                </>
              )}
            </p>
            <p className="text-xs text-gray-400 mt-4">
              By signing in, you agree to the{' '}
              <a href="#" className="text-gray-500 hover:underline">Terms of Service</a>
              {' '}and{' '}
              <a href="#" className="text-gray-500 hover:underline">Privacy Policy</a>
            </p>
          </div>
        </div>

        {/* Testnet badge */}
        <div className="mt-6 text-center">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/10 text-white/80 text-xs font-medium backdrop-blur-sm border border-white/20">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            Stellar Testnet · Casper Testnet
          </span>
        </div>
      </div>
    </div>
  )
}