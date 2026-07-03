import React, { useState, useRef, useEffect } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft, ArrowRight, CheckCircle, ChevronDown, Menu, X,
  Network, Lock, FileCheck, Brain, Shield, Layers, Eye, Key, HelpCircle,
  Building2, BookOpen, ArrowUpRight, Loader2, ExternalLink, Code,
} from 'lucide-react'
import { getFeature, FeatureData } from '../data/features'

// ─── CONSTANTS ────────────────────────────────────────────────────────────────
const TAB_LABELS = ['Overview', 'Features', 'Why ZKCO', 'How It Works', 'Get Started']
const EXPLORE_NAV_ITEMS = [
  { icon: Network,    label: 'Graph Risk Engine',    slug: 'graph-risk-engine' },
  { icon: Lock,       label: 'ZK Proof Generator',   slug: 'zk-proof-generator' },
  { icon: FileCheck,  label: 'Compliance Passport',  slug: 'compliance-passport' },
  { icon: Layers,     label: 'Casper Oracle',        slug: 'casper-oracle' },
  { icon: Brain,      label: 'LangGraph Agents',     slug: 'langgraph-agents' },
  { icon: Layers,     label: 'Audit Trail',          slug: 'audit-trail' },
  { icon: Eye,        label: 'Selective Disclosure', slug: 'selective-disclosure' },
  { icon: Key,        label: 'API Gateway',          slug: 'api-gateway' },
  { icon: Shield,     label: 'Enterprise Security',  slug: 'enterprise-security' },
]

// ─── EXPLORE DROPDOWN ─────────────────────────────────────────────────────────
function ExploreDropdown() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])
  return (
    <div ref={ref} className="relative">
      <button onClick={() => setOpen(o => !o)} className="flex items-center gap-1 text-sm font-medium text-gray-700 hover:text-brand-blue transition-colors">
        Explore <ChevronDown size={15} className={`transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="absolute left-0 top-full mt-2 w-72 bg-white rounded-2xl shadow-xl border border-gray-100 p-2 z-50">
          {EXPLORE_NAV_ITEMS.map(item => {
            const Icon = item.icon
            return (
              <Link key={item.slug} to={`/marketplace/${item.slug}`} onClick={() => setOpen(false)} className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-gray-50 group transition-colors">
                <span className="flex-shrink-0 w-7 h-7 rounded-lg bg-blue-50 flex items-center justify-center"><Icon size={14} className="text-brand-blue" /></span>
                <span className="text-sm text-gray-700 font-medium group-hover:text-brand-blue transition-colors">{item.label}</span>
                <ArrowUpRight size={12} className="ml-auto opacity-0 group-hover:opacity-100 text-brand-blue transition-opacity" />
              </Link>
            )
          })}
          <div className="border-t border-gray-100 mt-1 pt-2 px-3 pb-1">
            <Link to="/marketplace" onClick={() => setOpen(false)} className="text-xs text-brand-blue font-medium hover:underline">View full platform →</Link>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── NAVBAR ───────────────────────────────────────────────────────────────────
function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false)
  return (
    <nav className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-gradient-to-br from-brand-blue to-blue-700 rounded-lg flex items-center justify-center"><Lock size={14} className="text-white" /></div>
            <span className="font-bold text-gray-900 text-base">ZKCO</span>
          </Link>
          <div className="hidden md:flex items-center gap-8">
            <ExploreDropdown />
            <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-sm font-medium text-gray-700 hover:text-brand-blue transition-colors"><Building2 size={14} /> GitHub</a>
            <a href="#docs" className="flex items-center gap-1.5 text-sm font-medium text-gray-700 hover:text-brand-blue transition-colors"><BookOpen size={14} /> Docs</a>
          </div>
          <div className="hidden md:flex items-center gap-3">
            <Link to="/login" className="text-sm font-medium text-gray-700 hover:text-brand-blue transition-colors">Sign in</Link>
            <Link to="/app" className="btn-primary text-xs px-4 py-2">Launch App</Link>
          </div>
          <button className="md:hidden p-2 rounded-lg text-gray-600 hover:bg-gray-100" onClick={() => setMobileOpen(o => !o)}>
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>
      {mobileOpen && (
        <div className="md:hidden bg-white border-t border-gray-100 px-4 py-4 space-y-1">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-2 mb-2">Platform</p>
          {EXPLORE_NAV_ITEMS.map(item => {
            const Icon = item.icon
            return (
              <Link key={item.slug} to={`/marketplace/${item.slug}`} onClick={() => setMobileOpen(false)} className="flex items-center gap-3 px-2 py-2.5 rounded-xl hover:bg-gray-50 text-sm text-gray-700 font-medium">
                <Icon size={16} className="text-brand-blue" /> {item.label}
              </Link>
            )
          })}
          <div className="border-t border-gray-100 pt-3 mt-3 space-y-1">
            <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 px-2 py-2.5 text-sm text-gray-700 font-medium rounded-xl hover:bg-gray-50"><Building2 size={16} /> GitHub</a>
            <a href="#docs" className="flex items-center gap-2 px-2 py-2.5 text-sm text-gray-700 font-medium rounded-xl hover:bg-gray-50"><BookOpen size={16} /> Docs</a>
            <Link to="/app" className="btn-primary w-full justify-center mt-2">Launch App</Link>
          </div>
        </div>
      )}
    </nav>
  )
}

// ─── TAB 4: GET STARTED (DEV ACCESS / API KEY) ───────────────────────────────
function GetStartedTab({ feature }: { feature: FeatureData }) {
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  if (submitted) {
    return (
      <div className="max-w-md mx-auto text-center py-12">
        <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <CheckCircle size={32} className="text-emerald-600" />
        </div>
        <h3 className="text-2xl font-bold text-gray-900 mb-2">Ready to Integrate</h3>
        <p className="text-gray-500 mb-6">
          <strong>{feature.name}</strong> is fully operational on the platform. Sign in with your API key to access endpoints and run live proofs.
        </p>
        <div className="flex flex-col gap-3">
          <Link to="/login" className="btn-primary justify-center text-sm">Sign in & Test Endpoints</Link>
          <Link to="/app" className="btn-outline justify-center text-sm">Launch Dashboard <ExternalLink size={14} /></Link>
        </div>
        <div className="mt-8 p-4 bg-gray-50 rounded-xl border border-gray-100 text-left">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Example Endpoint</p>
          <code className="text-xs text-gray-600 block break-all">
            GET /api/v1/entity/{"{"}id{"}"}/{feature.slug.split('-')[0]}
          </code>
          <a href="https://stellar.expert" target="_blank" rel="noopener noreferrer" className="mt-3 inline-flex items-center gap-1 text-xs text-brand-blue hover:underline">
            View on-chain contract <ArrowUpRight size={12} />
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-md mx-auto">
      <div className="mb-8">
        <h3 className="text-xl font-bold text-gray-900 mb-2">Access {feature.name}</h3>
        <p className="text-gray-500 text-sm leading-relaxed">
          Authenticate with your API key to test endpoints, generate proofs, or deploy to testnet.
        </p>
      </div>
      {/* Tier progress indicator (adapted for dev onboarding) */}
      <div className="flex items-center gap-2 mb-8">
        {['Sign In', 'Test Endpoint', 'Deploy to Testnet'].map((step, i) => (
          <React.Fragment key={step}>
            <div className={`flex items-center gap-1.5 ${i === 0 ? 'text-brand-blue' : 'text-gray-300'}`}>
              <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold border-2 ${i === 0 ? 'border-brand-blue bg-brand-blue text-white' : 'border-gray-200 text-gray-300'}`}>
                {i === 0 ? '✓' : i + 1}
              </span>
              <span className="text-xs font-medium hidden sm:block whitespace-nowrap">{step}</span>
            </div>
            {i < 2 && <div className="flex-1 h-px bg-gray-200" />}
          </React.Fragment>
        ))}
      </div>

      <button
        onClick={() => { setLoading(true); setTimeout(() => { setLoading(false); setSubmitted(true) }, 800) }}
        disabled={loading}
        className="btn-primary w-full justify-center text-sm disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {loading ? <><Loader2 size={16} className="animate-spin" /> Preparing environment…</> : <>Launch {feature.name} <ArrowRight size={16} /></>}
      </button>

      <p className="text-center text-xs text-gray-400 mt-4">
        Need an API key? <Link to="/login?mode=register" className="text-brand-blue hover:underline font-medium">Request access</Link>
      </p>

      {/* What you unlock */}
      <div className="mt-10 p-5 rounded-2xl bg-gray-50 border border-gray-100">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">What you get access to</p>
        <ul className="space-y-2">
          {[
            `${feature.name} endpoints (FastAPI)`,
            'Live ZK proof generation & local verify',
            'Soroban/Casper testnet deployment',
            'Agent pipeline orchestration (LangGraph)',
          ].map(item => (
            <li key={item} className="flex items-center gap-2 text-sm text-gray-600">
              <CheckCircle size={14} className="text-emerald-500 flex-shrink-0" /> {item}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

// ─── FEATURE PAGE ─────────────────────────────────────────────────────────────
export default function FeaturePage() {
  const { slug } = useParams<{ slug: string }>()
  const feature = getFeature(slug || '')
  const [activeTab, setActiveTab] = useState(0)

  if (!feature) {
    return (
      <div className="min-h-screen bg-white flex flex-col items-center justify-center gap-4 px-4">
        <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-2"><HelpCircle size={28} className="text-gray-400" /></div>
        <h1 className="text-2xl font-bold text-gray-900">Capability not found</h1>
        <p className="text-gray-400 text-sm">The component you're looking for doesn't exist.</p>
        <Link to="/marketplace" className="btn-primary text-sm mt-2"><ArrowLeft size={14} /> Browse Platform</Link>
      </div>
    )
  }

  const FeatureIcon = feature.icon
  const tabLabels = TAB_LABELS.map((t, i) => (i === 2 ? `Why ZKCO ${feature.name}?` : t))

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      
      {/* ── Feature hero strip ───────────────────────────────────────────────── */}
      <div className={`bg-gradient-to-br ${feature.heroColor} pt-10 pb-14 px-4`}>
        <div className="max-w-5xl mx-auto">
          <Link to="/marketplace" className="inline-flex items-center gap-1.5 text-white/70 hover:text-white text-sm mb-8 transition-colors">
            <ArrowLeft size={14} /> Back to Marketplace
          </Link>
          <div className="flex items-start gap-5 md:gap-7">
            <div className="flex-shrink-0 w-14 h-14 md:w-16 md:h-16 bg-white/20 rounded-2xl flex items-center justify-center backdrop-blur-sm border border-white/30">
              <FeatureIcon size={28} className="text-white" />
            </div>
            <div>
              <span className="inline-block bg-white/20 text-white text-xs font-semibold px-3 py-1 rounded-full mb-2 backdrop-blur-sm">{feature.category}</span>
              <h1 className="text-3xl md:text-4xl font-bold text-white mb-1.5 leading-tight">{feature.name}</h1>
              <p className="text-base md:text-lg text-white/80 leading-relaxed">{feature.tagline}</p>
            </div>
          </div>
        </div>
      </div>
      
      {/* ── Tab bar ──────────────────────────────────────────────────────────── */}
      <div className="sticky top-16 z-30 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 overflow-x-auto scrollbar-hide">
          <div className="flex min-w-max">
            {tabLabels.map((label, i) => (
              <button key={i} onClick={() => setActiveTab(i)} className={`px-4 md:px-5 py-4 text-sm font-semibold border-b-2 whitespace-nowrap transition-all duration-200 ${activeTab === i ? 'border-brand-blue text-brand-blue' : 'border-transparent text-gray-500 hover:text-gray-800 hover:border-gray-300'}`}>
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>
      
      {/* ── Tab content ──────────────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* ─ Tab 0: Overview ─────────────────────────────────────────────────── */}
        {activeTab === 0 && (
          <div>
            <div className={`rounded-2xl bg-gradient-to-r ${feature.heroColor} p-6 md:p-8 mb-10 grid grid-cols-3 gap-4 text-center`}>
              {feature.stats.map((stat, i) => (
                <div key={i}>
                  <p className="text-2xl md:text-3xl font-bold text-white">{stat.value}</p>
                  <p className="text-xs md:text-sm text-white/70 mt-1">{stat.label}</p>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-10 md:gap-14 mb-12">
              <div className="space-y-4">
                {feature.overview.map((para, i) => (
                  <p key={i} className="text-gray-600 leading-relaxed">{para}</p>
                ))}
              </div>
              <div className="space-y-3">
                {feature.capabilities.slice(0, 4).map((cap, i) => {
                  const CapIcon = cap.icon
                  return (
                    <div key={i} className="flex items-start gap-3 p-4 rounded-xl bg-gray-50 border border-gray-100">
                      <span className="flex-shrink-0 w-8 h-8 rounded-lg bg-white border border-gray-200 shadow-sm flex items-center justify-center"><CapIcon size={14} className="text-brand-blue" /></span>
                      <div>
                        <p className="text-sm font-semibold text-gray-800">{cap.title}</p>
                        <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{cap.desc}</p>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
            <div className="flex flex-col sm:flex-row gap-3">
              <button onClick={() => setActiveTab(4)} className="btn-primary text-sm">Get API Access <ArrowRight size={15} /></button>
              <button onClick={() => setActiveTab(1)} className="btn-outline text-sm">See all capabilities</button>
            </div>
          </div>
        )}
        
        {/* ─ Tab 1: Features ─────────────────────────────────────────────────── */}
        {activeTab === 1 && (
          <div>
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">{feature.name} — Full Capability Set</h2>
              <p className="text-gray-500">Everything {feature.name} brings to the ZKCO platform.</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 mb-10">
              {feature.capabilities.map((cap, i) => {
                const CapIcon = cap.icon
                return (
                  <div key={i} className="feature-card">
                    <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${feature.heroColor} flex items-center justify-center mb-4 shadow-sm`}>
                      <CapIcon size={18} className="text-white" />
                    </div>
                    <h3 className="font-bold text-gray-900 text-sm mb-2">{cap.title}</h3>
                    <p className="text-xs text-gray-500 leading-relaxed">{cap.desc}</p>
                  </div>
                )
              })}
            </div>
            <button onClick={() => setActiveTab(4)} className="btn-primary text-sm">Get API Access <ArrowRight size={15} /></button>
          </div>
        )}
        
        {/* ─ Tab 2: Why ZKCO ────────────────────────────────────────────────── */}
        {activeTab === 2 && (
          <div>
            <div className="mb-10">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Why ZKCO {feature.name}?</h2>
              <p className="text-gray-500">What sets our architecture apart from every alternative.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
              {feature.why.map((point, i) => {
                const WhyIcon = point.icon
                return (
                  <div key={i} className="p-6 rounded-2xl border border-gray-100 bg-white shadow-sm hover:shadow-md transition-shadow">
                    <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${feature.heroColor} flex items-center justify-center mb-4`}>
                      <WhyIcon size={18} className="text-white" />
                    </div>
                    <h3 className="font-bold text-gray-900 mb-2">{point.title}</h3>
                    <p className="text-sm text-gray-500 leading-relaxed">{point.body}</p>
                  </div>
                )
              })}
            </div>
            <div className={`bg-gradient-to-r ${feature.heroColor} rounded-2xl p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4`}>
              <div>
                <p className="text-white/70 text-sm">Powered by</p>
                <p className="text-white font-bold text-lg">{feature.whyBadge}</p>
              </div>
              <button onClick={() => setActiveTab(4)} className="btn-white text-sm flex-shrink-0">Get API Access <ArrowRight size={14} /></button>
            </div>
          </div>
        )}
        
        {/* ─ Tab 3: How It Works ─────────────────────────────────────────────── */}
        {activeTab === 3 && (
          <div>
            <div className="mb-10">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">How {feature.name} Works</h2>
              <p className="text-gray-500">Step-by-step from input to on-chain attestation.</p>
            </div>
            <div className="relative">
              <div className="absolute left-6 top-6 bottom-6 w-px bg-gray-100 hidden md:block" />
              <div className="space-y-6">
                {feature.steps.map((step, i) => {
                  const isLast = i === feature.steps.length - 1
                  return (
                    <div key={step.n} className="flex items-start gap-5">
                      <div className={`relative z-10 flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center font-bold text-sm border-2 shadow-sm ${isLast ? `bg-gradient-to-br ${feature.heroColor} text-white border-transparent` : 'bg-white border-gray-200 text-gray-600'}`}>
                        {isLast ? <CheckCircle size={20} /> : step.n}
                      </div>
                      <div className="flex-1 pb-2">
                        <h3 className={`font-bold text-base mb-1 ${isLast ? 'text-brand-blue' : 'text-gray-900'}`}>{step.title}</h3>
                        <p className="text-sm text-gray-500 leading-relaxed">{step.desc}</p>
                        {isLast && <button onClick={() => setActiveTab(4)} className="btn-primary text-sm mt-4">Get API Access <ArrowRight size={14} /></button>}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )}
        
        {/* ─ Tab 4: Get Started ──────────────────────────────────────────────── */}
        {activeTab === 4 && <GetStartedTab feature={feature} />}
      </div>
      
      {/* ── Footer ───────────────────────────────────────────────────────────── */}
      <footer className="border-t border-gray-200 bg-gray-50 py-8 px-4 text-center mt-8">
        <p className="text-sm text-gray-400">
          © {new Date().getFullYear()} ZKCO — Zero-Knowledge Compliance Oracle
          {' · '}<Link to="/marketplace" className="text-brand-blue hover:underline">Browse Platform</Link>
          {' · '}<Link to="/" className="text-brand-blue hover:underline">Home</Link>
        </p>
      </footer>
    </div>
  )
}