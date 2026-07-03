import React, { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Search, ArrowRight, ChevronRight, ChevronDown, Menu, X,
  Network, Lock, FileCheck, Brain, Shield, Layers, Eye, Key, TrendingUp,
  Building2, BookOpen, ArrowUpRight, GitBranch,
} from 'lucide-react'
import { FEATURES } from '../data/features'

// ─── CONSTANTS ────────────────────────────────────────────────────────────────
const CATEGORIES = ['All', 'Compliance', 'Privacy', 'Identity', 'Blockchain', 'AI', 'Integration', 'Security']
const EXPLORE_NAV_ITEMS = [
  { icon: Network,    label: 'Graph Risk Engine',    slug: 'graph-risk-engine' },
  { icon: Lock,       label: 'ZK Proof Generator',   slug: 'zk-proof-generator' },
  { icon: FileCheck,  label: 'Compliance Passport',  slug: 'compliance-passport' },
  { icon: Layers,     label: 'Casper Oracle',        slug: 'casper-oracle' },
  { icon: Brain,      label: 'LangGraph Agents',     slug: 'langgraph-agents' },
  { icon: GitBranch,  label: 'Audit Trail',          slug: 'audit-trail' },
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
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1 text-sm font-medium text-gray-700 hover:text-brand-blue transition-colors"
      >
        Explore
        <ChevronDown size={15} className={`transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="absolute left-0 top-full mt-2 w-72 bg-white rounded-2xl shadow-xl border border-gray-100 p-2 z-50">
          {EXPLORE_NAV_ITEMS.map(item => {
            const Icon = item.icon
            return (
              <Link
                key={item.slug}
                to={`/marketplace/${item.slug}`}
                onClick={() => setOpen(false)}
                className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-gray-50 group transition-colors"
              >
                <span className="flex-shrink-0 w-7 h-7 rounded-lg bg-blue-50 flex items-center justify-center">
                  <Icon size={14} className="text-brand-blue" />
                </span>
                <span className="text-sm text-gray-700 font-medium group-hover:text-brand-blue transition-colors">
                  {item.label}
                </span>
                <ArrowUpRight size={12} className="ml-auto opacity-0 group-hover:opacity-100 text-brand-blue transition-opacity" />
              </Link>
            )
          })}
          <div className="border-t border-gray-100 mt-1 pt-2 px-3 pb-1">
            <Link to="/marketplace" onClick={() => setOpen(false)} className="text-xs text-brand-blue font-medium hover:underline">
              View full platform →
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── SHARED NAVBAR ────────────────────────────────────────────────────────────
function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false)
  return (
    <nav className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-gradient-to-br from-brand-blue to-blue-700 rounded-lg flex items-center justify-center">
              <Lock size={14} className="text-white" />
            </div>
            <span className="font-bold text-gray-900 text-base">ZKCO</span>
          </Link>
          
          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-8">
            <ExploreDropdown />
            <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-sm font-medium text-gray-700 hover:text-brand-blue transition-colors">
              <Building2 size={14} /> GitHub
            </a>
            <a href="#docs" className="flex items-center gap-1.5 text-sm font-medium text-gray-700 hover:text-brand-blue transition-colors">
              <BookOpen size={14} /> Docs
            </a>
          </div>
          
          {/* CTA buttons */}
          <div className="hidden md:flex items-center gap-3">
            <Link to="/login" className="text-sm font-medium text-gray-700 hover:text-brand-blue transition-colors">Sign in</Link>
            <Link to="/app" className="btn-primary text-xs px-4 py-2">Launch App</Link>
          </div>
          
          {/* Mobile hamburger */}
          <button className="md:hidden p-2 rounded-lg text-gray-600 hover:bg-gray-100 transition-colors" onClick={() => setMobileOpen(o => !o)}>
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>
      {/* Mobile menu */}
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
            <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 px-2 py-2.5 text-sm text-gray-700 font-medium rounded-xl hover:bg-gray-50">
              <Building2 size={16} /> GitHub
            </a>
            <a href="#docs" className="flex items-center gap-2 px-2 py-2.5 text-sm text-gray-700 font-medium rounded-xl hover:bg-gray-50">
              <BookOpen size={16} /> Docs
            </a>
            <Link to="/app" className="btn-primary w-full justify-center mt-3">Launch App</Link>
          </div>
        </div>
      )}
    </nav>
  )
}

// ─── MARKETPLACE PAGE ─────────────────────────────────────────────────────────
export default function MarketplacePage() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('All')
  const filtered = FEATURES.filter(f => {
    const q = search.toLowerCase()
    const matchesSearch = !q || f.name.toLowerCase().includes(q) || f.tagline.toLowerCase().includes(q) || f.category.toLowerCase().includes(q)
    const matchesCategory = category === 'All' || f.category === category
    return matchesSearch && matchesCategory
  })

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      
      {/* ── Hero ─────────────────────────────────────────────────────────────── */}
      <section className="bg-gradient-to-br from-brand-navy via-brand-navy-mid to-brand-blue pt-16 pb-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/10 text-white/80 text-xs font-medium mb-6 backdrop-blur-sm border border-white/20">
            S01 · Platform Marketplace
          </span>
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-4 leading-tight">
            Explore the ZKCO Architecture
          </h1>
          <p className="text-lg text-blue-200 mb-10 max-w-2xl mx-auto leading-relaxed">
            Discover every compliance infrastructure component — from multi-factor graph intelligence to zero-knowledge proof generation, on-chain passports, and specialist AI agents.
          </p>
          {/* Search bar */}
          <div className="relative max-w-lg mx-auto mb-8">
            <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            <input
              type="text"
              placeholder="Search capabilities..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-11 pr-4 py-3.5 rounded-xl bg-white shadow-lg text-gray-900 placeholder-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-brand-blue/40"
            />
          </div>
          {/* Category filter chips */}
          <div className="flex flex-wrap justify-center gap-2">
            {CATEGORIES.map(cat => (
              <button
                key={cat}
                onClick={() => setCategory(cat)}
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200 ${
                  category === cat
                    ? 'bg-white text-brand-blue shadow-md'
                    : 'bg-white/10 text-white/80 hover:bg-white/20 border border-white/20'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>
      </section>
      
      {/* ── Feature Grid ─────────────────────────────────────────────────────── */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {filtered.length === 0 ? (
          <div className="text-center py-24">
            <p className="text-gray-400 text-lg mb-4">No capabilities match your search.</p>
            <button onClick={() => { setSearch(''); setCategory('All') }} className="text-brand-blue text-sm font-medium hover:underline">
              Clear filters
            </button>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {filtered.map(feature => {
                const Icon = feature.icon
                return (
                  <Link key={feature.slug} to={`/marketplace/${feature.slug}`} className="feature-card group flex flex-col">
                    {/* Icon */}
                    <div className={`inline-flex w-12 h-12 rounded-xl bg-gradient-to-br ${feature.heroColor} items-center justify-center mb-4 shadow-sm`}>
                      <Icon size={22} className="text-white" />
                    </div>
                    {/* Name + category */}
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <h3 className="font-bold text-gray-900 text-base leading-tight">{feature.name}</h3>
                    </div>
                    <span className={`self-start text-xs font-medium px-2.5 py-0.5 rounded-full mb-3 ${feature.categoryColor}`}>
                      {feature.category}
                    </span>
                    {/* Tagline */}
                    <p className="text-sm text-gray-500 leading-relaxed flex-1 mb-5">{feature.tagline}</p>
                    {/* Stats mini-row */}
                    <div className="flex items-center gap-5 pb-5 mb-5 border-b border-gray-100">
                      {feature.stats.slice(0, 2).map((stat, i) => (
                        <div key={i}>
                          <p className="text-sm font-bold text-gray-900">{stat.value}</p>
                          <p className="text-xs text-gray-400">{stat.label}</p>
                        </div>
                      ))}
                    </div>
                    {/* Explore CTA */}
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold text-brand-blue flex items-center gap-1.5 group-hover:gap-2 transition-all">
                        Explore capability
                        <ArrowRight size={14} className="group-hover:translate-x-0.5 transition-transform" />
                      </span>
                      <ChevronRight size={16} className="text-gray-200 group-hover:text-brand-blue transition-colors" />
                    </div>
                  </Link>
                )
              })}
            </div>
            <p className="text-center text-sm text-gray-400 mt-10">
              Showing {filtered.length} of {FEATURES.length} capabilities
            </p>
          </>
        )}
      </section>
      
      {/* ── Footer ───────────────────────────────────────────────────────────── */}
      <footer className="border-t border-gray-200 bg-white py-8 px-4 text-center">
        <p className="text-sm text-gray-400">
          © {new Date().getFullYear()} ZKCO — Zero-Knowledge Compliance Oracle · Built by Ed Godwin
        </p>
      </footer>
    </div>
  )
}