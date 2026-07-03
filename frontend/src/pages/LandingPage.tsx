// src/pages/LandingPage.tsx
import React, { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import {
  Network, Shield, Lock, Brain, FileCheck, Zap,
  ArrowRight, CheckCircle, Menu, X, Building2, BookOpen,
  ChevronDown, Layers, GitBranch, Eye, Key,
  TrendingUp, Globe, Award, ArrowUpRight, Sparkles,
} from 'lucide-react'

// ─── NAVBAR ─────────────────────────────────────────────────────────────────
function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false)
  return (
    <nav className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-gradient-to-br from-brand-blue to-blue-700 rounded-lg flex items-center justify-center">
              <Lock size={14} className="text-white" />
            </div>
            <span className="font-bold text-gray-900 text-base">ZKCO</span>
          </Link>
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm font-medium text-gray-700 hover:text-brand-blue transition-colors">Features</a>
            <a href="#architecture" className="text-sm font-medium text-gray-700 hover:text-brand-blue transition-colors">Architecture</a>
            <Link to="/marketplace" className="text-sm font-medium text-gray-700 hover:text-brand-blue transition-colors">Marketplace</Link>
            <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="text-sm font-medium text-gray-700 hover:text-brand-blue transition-colors">GitHub</a>
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
        <div className="md:hidden bg-white border-t border-gray-100 px-4 py-4 space-y-2">
          <a href="#features" className="block px-2 py-2 text-sm text-gray-700 font-medium">Features</a>
          <a href="#architecture" className="block px-2 py-2 text-sm text-gray-700 font-medium">Architecture</a>
          <Link to="/marketplace" className="block px-2 py-2 text-sm text-gray-700 font-medium">Marketplace</Link>
          <Link to="/app" className="btn-primary w-full justify-center mt-3">Launch App</Link>
        </div>
      )}
    </nav>
  )
}

// ─── HERO ───────────────────────────────────────────────────────────────────
function Hero() {
  return (
    <section className="relative bg-gradient-to-br from-brand-navy via-brand-navy-mid to-brand-blue pt-20 pb-28 px-4 overflow-hidden">
      {/* Decorative grid */}
      <div className="absolute inset-0 opacity-10" style={{
        backgroundImage: 'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)',
        backgroundSize: '40px 40px'
      }} />
      <div className="relative max-w-5xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/10 text-white/90 text-xs font-medium mb-8 backdrop-blur-sm border border-white/20">
          <Sparkles size={12} />
          Built for Stellar Hacks 2026 · Casper Buildathon 2026
        </div>
        <h1 className="text-5xl md:text-7xl font-bold text-white mb-6 leading-[1.05] tracking-tight">
          Compliance Infrastructure<br />
          <span className="bg-gradient-to-r from-cyan-300 to-blue-200 bg-clip-text text-transparent">
            for Regulated DeFi
          </span>
        </h1>
        <p className="text-lg md:text-xl text-blue-100 mb-10 max-w-3xl mx-auto leading-relaxed">
          The world's first AI-native Zero-Knowledge Compliance Oracle. Prove regulatory
          compliance without revealing PII. One proof. Many protocols. Stellar is the trust anchor.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link to="/app" className="btn-primary text-sm px-6 py-3">
            Launch App <ArrowRight size={16} />
          </Link>
          <Link to="/marketplace" className="btn-white text-sm px-6 py-3">
            Explore Features
          </Link>
        </div>
        {/* Stats strip */}
        <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-6 max-w-3xl mx-auto">
          {[
            { value: '6', label: 'Risk Factors' },
            { value: '3', label: 'ZK Assertions' },
            { value: '5', label: 'AI Agents' },
            { value: '2', label: 'Chains' },
          ].map((s, i) => (
            <div key={i} className="text-center">
              <p className="text-3xl md:text-4xl font-bold text-white">{s.value}</p>
              <p className="text-xs text-blue-200 mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ─── FEATURE SECTION ────────────────────────────────────────────────────────
type FeatureSectionProps = {
  icon: React.ElementType
  eyebrow: string
  title: string
  description: string
  bullets: { title: string; desc: string }[]
  marketplaceSlug: string
  reverse?: boolean
  accent: string
}

function FeatureSection({ icon: Icon, eyebrow, title, description, bullets, marketplaceSlug, reverse, accent }: FeatureSectionProps) {
  return (
    <div className={`grid md:grid-cols-2 gap-12 items-center ${reverse ? 'md:[&>*:first-child]:order-2' : ''}`}>
      <div>
        <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold mb-4 ${accent}`}>
          <Icon size={12} />
          {eyebrow}
        </span>
        <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4 leading-tight">{title}</h2>
        <p className="text-gray-600 leading-relaxed mb-8">{description}</p>
        <div className="space-y-3 mb-8">
          {bullets.map((b, i) => (
            <div key={i} className="flex gap-3">
              <CheckCircle size={18} className="text-brand-blue flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-gray-900">{b.title}</p>
                <p className="text-sm text-gray-500 leading-relaxed">{b.desc}</p>
              </div>
            </div>
          ))}
        </div>
        <Link to={`/marketplace/${marketplaceSlug}`} className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-blue hover:gap-2.5 transition-all">
          Explore in Marketplace <ArrowRight size={14} />
        </Link>
      </div>
      <div className={`relative rounded-3xl p-8 bg-gradient-to-br ${accent.replace('bg-', 'bg-gradient-to-br from-').replace('/10', '-50 to-blue-50')} border border-gray-100 shadow-sm`}>
        <div className="absolute -top-4 -right-4 w-24 h-24 bg-brand-blue/10 rounded-full blur-2xl" />
        <div className="relative space-y-3">
          {bullets.map((b, i) => (
            <div key={i} className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
              <p className="text-xs font-semibold text-brand-blue uppercase tracking-wider mb-1">{b.title}</p>
              <p className="text-sm text-gray-600">{b.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── MAIN LANDING ───────────────────────────────────────────────────────────
export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      <Hero />

      {/* ── Section 1: Graph Intelligence (EP-01) ─────────────────────────── */}
      <section id="features" className="py-24 px-4">
        <div className="max-w-6xl mx-auto">
          <FeatureSection
            icon={Network}
            eyebrow="EP-01 · Graph Intelligence"
            title="Six-Factor Compliance Index"
            description="Replace single-score heuristics with an investment-grade multi-factor risk model derived from a Neo4j transaction graph. Six independent financial risk dimensions feed a weighted Compliance Index — the private witness proven correct by zero-knowledge cryptography."
            accent="bg-blue-50 text-blue-700"
            marketplaceSlug="graph-risk-engine"
            bullets={[
              { title: 'Liquidity Risk (L)', desc: 'Transaction volume volatility over 30-day trailing window' },
              { title: 'Counterparty Risk (C)', desc: 'PageRank-weighted average risk of 1-hop counterparties' },
              { title: 'Jurisdiction Risk (J)', desc: 'FATF grey-list counterparty fraction, live-refreshable' },
              { title: 'Sanctions Exposure (S)', desc: 'Betweenness path overlap with OFAC sanctioned entities' },
              { title: 'AML Topology (A)', desc: 'Louvain community risk + structural anomaly penalty' },
              { title: 'Behavioural Risk (B)', desc: 'Node2Vec manifold deviation from historical baseline' },
            ]}
          />
        </div>
      </section>

      {/* ── Section 2: ZK Proofs (EP-02) ──────────────────────────────────── */}
      <section className="py-24 px-4 bg-gray-50">
        <div className="max-w-6xl mx-auto">
          <FeatureSection
            icon={Lock}
            eyebrow="EP-02 · Zero-Knowledge Proofs"
            title="Three-Condition Noir Circuit"
            description="A single Noir proof simultaneously asserts: (1) Compliance Index below policy threshold, (2) wallet in low-risk behavioural manifold, (3) jurisdiction in permitted FATF set. The CI value, factor weights, graph topology, and entity identity remain private — never on-chain."
            accent="bg-purple-50 text-purple-700"
            marketplaceSlug="zk-proof-generator"
            reverse
            bullets={[
              { title: 'CI < ci_threshold', desc: 'Private Compliance Index satisfies policy ceiling' },
              { title: 'Manifold ≥ threshold', desc: 'Wallet belongs to low-risk behavioural cluster' },
              { title: 'Jurisdiction permitted', desc: 'Entity domicile is in FATF permitted set' },
              { title: 'Policy-bound proofs', desc: 'policy_id binds proof to specific regulatory version' },
            ]}
          />
        </div>
      </section>

      {/* ── Section 3: Compliance Passport (EP-03) ────────────────────────── */}
      <section className="py-24 px-4">
        <div className="max-w-6xl mx-auto">
          <FeatureSection
            icon={FileCheck}
            eyebrow="EP-03 · Compliance Passport"
            title="One Proof. Many Protocols."
            description="A non-transferable, policy-bound Compliance Passport minted on Stellar after ZK verification. Any DeFi protocol — DEX, lending, RWA, payroll, remittance — verifies compliance with a single Soroban call. No KYC re-run. No PII access. One passport, reusable across the ecosystem."
            accent="bg-emerald-50 text-emerald-700"
            marketplaceSlug="compliance-passport"
            bullets={[
              { title: 'Non-transferable', desc: 'Soul-bound to the wallet it was minted for' },
              { title: 'Policy-bound', desc: 'One active passport per (wallet, policy_id) pair' },
              { title: 'Auto-expiry', desc: 'Enforced at ledger level via ledger().timestamp()' },
              { title: 'Revocable', desc: 'Oracle authority revokes on AML incident detection' },
              { title: 'Selective disclosure', desc: 'Boolean labels only — never factor values or weights' },
            ]}
          />
        </div>
      </section>

      {/* ── Section 4: Multi-Chain (EP-04) ────────────────────────────────── */}
      <section className="py-24 px-4 bg-gray-50">
        <div className="max-w-6xl mx-auto">
          <FeatureSection
            icon={Layers}
            eyebrow="EP-04 · Multi-Chain"
            title="Stellar + Casper, Unified"
            description="Deploy compliance infrastructure where your protocols live. Stellar Soroban for Compliance Passports and verifiable credentials. Casper Odra for ComplianceOracle verdicts, IdentityRegistry, and x402 micropayment gating. Same pipeline, autonomous chain selection via the Settlement Agent."
            accent="bg-amber-50 text-amber-700"
            marketplaceSlug="casper-oracle"
            reverse
            bullets={[
              { title: 'Stellar Soroban', desc: 'ComplianceVerifier + CompliancePassport contracts' },
              { title: 'Casper Odra', desc: 'ComplianceOracle + IdentityRegistry contracts' },
              { title: 'x402 Micropayments', desc: 'Pay-per-request API for AI agents on Casper' },
              { title: 'Autonomous routing', desc: 'Settlement Agent selects chain from policy context' },
            ]}
          />
        </div>
      </section>

      {/* ── Section 5: AI Agents (EP-06) ──────────────────────────────────── */}
      <section className="py-24 px-4">
        <div className="max-w-6xl mx-auto">
          <FeatureSection
            icon={Brain}
            eyebrow="EP-06 · Specialist Agents"
            title="Five-Agent LangGraph Pipeline"
            description="Not a simple three-step workflow — five autonomous specialist agents collaborate through shared state. Each is a domain expert: Intelligence (graph + risk), Compliance (regulatory rules + Groq reasoning), ZK (circuit selection), Settlement (chain dispatch), Auditor (explanation + selective disclosure)."
            accent="bg-rose-50 text-rose-700"
            marketplaceSlug="langgraph-agents"
            bullets={[
              { title: 'Intelligence Agent', desc: 'Six-factor CI + manifold scoring in <20s' },
              { title: 'Compliance Agent', desc: 'FATF, MiCA, Travel Rule rules + Groq reasoning' },
              { title: 'ZK Agent', desc: 'Policy-aware circuit selection + witness construction' },
              { title: 'Settlement Agent', desc: 'Autonomous chain dispatch with retry logic' },
              { title: 'Auditor Agent', desc: 'Human-readable reports + disclosure labels' },
            ]}
          />
        </div>
      </section>

      {/* ── Section 6: Enterprise Security (EP-07) ────────────────────────── */}
      <section className="py-24 px-4 bg-gray-50">
        <div className="max-w-6xl mx-auto">
          <FeatureSection
            icon={Shield}
            eyebrow="EP-07 · Enterprise Security"
            title="Regulatory-Grade Data Governance"
            description="Built for regulated markets. AES-256-GCM encryption at rest for RESTRICTED fields. SHA-256 entity hashing ensures PII never appears on-chain or in logs. Structured security event logging for SOC/SIEM ingestion. Immutable audit trails with 12-month retention."
            accent="bg-slate-100 text-slate-700"
            marketplaceSlug="audit-trail"
            reverse
            bullets={[
              { title: 'Data classification', desc: 'PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED' },
              { title: 'PII minimisation', desc: 'SHA-256 entity hashing everywhere on-chain' },
              { title: 'Encryption at rest', desc: 'AES-256-GCM for entity_id and sensitive fields' },
              { title: 'SOC-ready logging', desc: 'Structured security_events table, async, CRITICAL webhooks' },
            ]}
          />
        </div>
      </section>

      {/* ── Architecture Diagram ──────────────────────────────────────────── */}
      <section id="architecture" className="py-24 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">End-to-End Architecture</h2>
            <p className="text-gray-600 max-w-2xl mx-auto">From entity input to on-chain attestation — every layer is designed for privacy, verifiability, and regulatory compliance.</p>
          </div>
          <div className="bg-gradient-to-br from-brand-navy to-brand-blue rounded-3xl p-8 md:p-12 text-white">
            <div className="grid md:grid-cols-5 gap-4">
              {[
                { icon: Network, label: 'Graph Intelligence', sub: 'Neo4j + NetworkX' },
                { icon: TrendingUp, label: 'Six-Factor CI', sub: 'L·C·J·S·A·B' },
                { icon: Lock, label: 'Noir ZK Circuit', sub: '3 assertions' },
                { icon: Layers, label: 'Multi-Chain', sub: 'Stellar + Casper' },
                { icon: Brain, label: '5 AI Agents', sub: 'LangGraph' },
              ].map((step, i) => {
                const Icon = step.icon
                return (
                  <React.Fragment key={i}>
                    <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-5 border border-white/20 text-center">
                      <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center mx-auto mb-3">
                        <Icon size={18} className="text-white" />
                      </div>
                      <p className="font-bold text-sm mb-1">{step.label}</p>
                      <p className="text-xs text-blue-200">{step.sub}</p>
                    </div>
                  </React.Fragment>
                )
              })}
            </div>
          </div>
        </div>
      </section>

      {/* ── Final CTA ─────────────────────────────────────────────────────── */}
      <section className="py-20 px-4 bg-gradient-to-br from-brand-navy to-brand-blue">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            Ready to see it in action?
          </h2>
          <p className="text-blue-100 mb-8 text-lg">
            Launch the app to explore the full platform — graph intelligence, ZK proofs, compliance passports, and the five-agent pipeline.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link to="/app" className="btn-primary text-sm px-6 py-3">
              Launch App <ArrowRight size={16} />
            </Link>
            <Link to="/marketplace" className="btn-white text-sm px-6 py-3">
              Browse Marketplace
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <footer className="border-t border-gray-200 bg-white py-8 px-4 text-center">
        <p className="text-sm text-gray-400">
          © 2026 ZKCO · Zero-Knowledge Compliance Oracle · Built by Ed Godwin for Stellar Hacks & Casper Buildathon 2026
        </p>
      </footer>
    </div>
  )
}