'use client'

import { FileSearch, ShieldCheck, Landmark, Building2, Bot, Gift, History, Check, AlertTriangle } from 'lucide-react'
import ScrollReveal from '@/components/fx/ScrollReveal'
import SpotlightCard from '@/components/fx/SpotlightCard'

const Pill = ({ label, tone }: { label: string; tone: string }) => (
  <span className={`rounded-full px-3 py-1 text-xs font-bold ${tone}`}>{label}</span>
)
const Row = ({ label, right, tone }: { label: string; right: React.ReactNode; tone: string }) => (
  <div className="flex items-center justify-between gap-3 rounded-xl border border-gray-200 bg-white px-3.5 py-2.5 text-sm font-semibold text-gray-800">
    <span className="truncate">{label}</span><span className={`flex flex-none items-center gap-1 text-xs font-bold ${tone}`}>{right}</span>
  </div>
)

const features = [
  {
    span: 'sm:col-span-2 lg:row-span-2', icon: FileSearch, tone: 'bg-blue-100 text-blue-600', big: true,
    title: 'Intelligent Approvals', desc: 'Get a personalised approval checklist based on your project — only what applies to you, in the right order.',
    visual: (
      <div className="space-y-2.5">
        <Row label="Factory licence" right="● Approved" tone="text-teal-700" />
        <Row label="Fire NOC" right="● In review" tone="text-amber-600" />
        <Row label="Pollution control consent" right="● To start" tone="text-gray-400" />
        <Row label="Labour registration" right="● To start" tone="text-gray-400" />
        <div className="pt-1">
          <div className="mb-1 flex justify-between text-xs font-bold text-gray-500"><span>Overall progress</span><span>1 of 4 done</span></div>
          <div className="h-2 overflow-hidden rounded-full bg-gray-200"><div className="h-full w-1/4 rounded-full bg-gradient-to-r from-blue-500 to-teal" /></div>
        </div>
      </div>
    ),
  },
  {
    span: '', icon: ShieldCheck, tone: 'bg-teal-100 text-teal-700',
    title: 'Document Intelligence', desc: 'AI-powered document validation and cross-checking.',
    visual: (
      <div className="space-y-2">
        <Row label="Land deed" right={<><Check className="h-3 w-3" /> OK</>} tone="text-teal-700" />
        <Row label="Address" right={<><AlertTriangle className="h-3 w-3" /> Fix</>} tone="text-amber-600" />
      </div>
    ),
  },
  {
    span: '', icon: Landmark, tone: 'bg-sun/30 text-navy-ink',
    title: 'Compliance Tracking', desc: 'Stay on top of post-approval compliance requirements.',
    visual: (
      <div>
        <div className="mb-1 flex justify-between text-xs font-bold text-gray-500"><span>Fire NOC renewal</span><span>12 days</span></div>
        <div className="h-2 overflow-hidden rounded-full bg-gray-200"><div className="h-full w-4/5 rounded-full bg-coral" /></div>
      </div>
    ),
  },
  {
    span: 'sm:col-span-2', icon: Bot, tone: 'bg-coral/20 text-coral',
    title: 'Regulatory Copilot', desc: 'Ask questions about regulations and get grounded answers.',
    visual: (
      <div className="space-y-2 text-sm font-semibold">
        <div className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-md bg-navy px-3.5 py-2 text-cream">Which approvals does my food unit need?</div>
        <div className="w-fit max-w-[90%] rounded-2xl rounded-bl-md border border-gray-200 bg-white px-3.5 py-2 text-gray-800">4 approvals apply. Start with the factory licence.</div>
      </div>
    ),
  },
  {
    span: '', icon: Building2, tone: 'bg-blue-100 text-blue-600',
    title: 'Integration Readiness', desc: 'Transparent prototype with guided, future-authorised integration paths.',
    visual: (
      <div className="flex flex-wrap gap-1.5">
        <Pill label="Simulated" tone="bg-blue-100 text-blue-700" /><Pill label="Guided" tone="bg-teal-100 text-teal-700" /><Pill label="Future" tone="bg-sun/40 text-navy-ink" />
      </div>
    ),
  },
  {
    span: '', icon: Gift, tone: 'bg-teal-100 text-teal-700',
    title: 'Incentive Discovery', desc: 'Find and apply for government schemes you qualify for.',
    visual: (
      <div className="space-y-2">
        <Row label="Capital subsidy" right="Eligible" tone="text-teal-700" />
        <Row label="Stamp duty" right="Check" tone="text-amber-600" />
      </div>
    ),
  },
  {
    span: 'sm:col-span-2', icon: History, tone: 'bg-sun/30 text-navy-ink',
    title: 'Regulatory Change Center', desc: 'Compare regulation versions and review the potential impact on your project.',
    visual: (
      <div className="flex flex-wrap items-center gap-2.5 text-sm font-semibold">
        <Pill label="v1.2" tone="bg-gray-100 text-gray-600" /><span className="text-gray-400">→</span><Pill label="v1.3" tone="bg-blue-100 text-blue-700" />
        <span className="flex items-center gap-1.5 text-gray-700"><span className="h-2 w-2 rounded-full bg-coral" /> 2 changes may affect your project</span>
      </div>
    ),
  },
]

export default function FeatureBento() {
  return (
    <section id="features" className="scroll-mt-16 border-y border-gray-200 bg-white/60 py-20 sm:py-28">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <ScrollReveal className="mx-auto mb-14 max-w-2xl text-center">
          <div className="eyebrow">Features</div>
          <h2 className="mt-3 text-3xl font-extrabold tracking-tight text-navy sm:text-4xl">Everything to set up and run an industrial unit</h2>
          <p className="mt-3 text-gray-600">Built for entrepreneurs setting up in Maharashtra.</p>
        </ScrollReveal>
        <div className="grid gap-5 sm:grid-cols-2 lg:auto-rows-[minmax(230px,auto)] lg:grid-cols-4">
          {features.map((f, i) => {
            const Icon = f.icon
            return (
              <ScrollReveal key={f.title} delay={(i % 4) * 0.07} className={`h-full ${f.span}`}>
                <SpotlightCard className="h-full">
                  <div className={`flex h-full flex-col ${f.big ? 'p-7 sm:p-9' : 'p-6'}`}>
                    <div className={`mb-4 grid place-items-center rounded-xl ${f.tone} ${f.big ? 'h-14 w-14' : 'h-11 w-11'}`}><Icon className={f.big ? 'h-7 w-7' : 'h-5 w-5'} /></div>
                    <h3 className={`font-extrabold text-navy ${f.big ? 'text-2xl' : 'text-lg'}`}>{f.title}</h3>
                    <p className={`mt-1.5 leading-relaxed text-gray-600 ${f.big ? 'max-w-md text-base' : 'text-sm'}`}>{f.desc}</p>
                    <div className="mt-auto pt-5">{f.visual}</div>
                  </div>
                </SpotlightCard>
              </ScrollReveal>
            )
          })}
        </div>
      </div>
    </section>
  )
}
