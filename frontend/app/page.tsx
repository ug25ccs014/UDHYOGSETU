'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowDown,
  ArrowRight,
  Building2,
  Check,
  ClipboardCheck,
  FileCheck2,
  Landmark,
  ShieldCheck,
  Sparkles,
  Timer,
} from 'lucide-react'
import { Button } from '@/components/ui/button'

const features = [
  { icon: ClipboardCheck, number: '01', title: 'Know your approvals', description: 'Start with your project details and get a clear approval roadmap instead of searching across departments.' },
  { icon: FileCheck2, number: '02', title: 'Prepare with confidence', description: 'Organise documents, resolve queries and see what is still missing before you submit.' },
  { icon: Timer, number: '03', title: 'Track every milestone', description: 'Keep applications, inspections, deadlines and compliance actions visible in one workspace.' },
  { icon: ShieldCheck, number: '04', title: 'Stay compliant', description: 'Review post-approval obligations and regulatory changes that may affect your project.' },
  { icon: Landmark, number: '05', title: 'Discover support', description: 'Explore relevant schemes and incentives alongside the approvals you already need.' },
  { icon: Sparkles, number: '06', title: 'Use the intelligent layer', description: 'Get guided answers and project signals while keeping prototype and government boundaries transparent.' },
]

const journey = [
  ['01', 'Tell us about the project', 'Sector, location, investment and a few essentials.'],
  ['02', 'See your approval roadmap', 'Understand what applies, what comes next and why.'],
  ['03', 'Prepare and submit', 'Build documents, handle queries and track progress.'],
  ['04', 'Operate with visibility', 'Monitor compliance, inspections and regulatory changes.'],
]

export default function Home() {
  const router = useRouter()

  useEffect(() => {
    const nodes = Array.from(document.querySelectorAll<HTMLElement>('.ud-reveal'))
    if (!('IntersectionObserver' in window)) {
      nodes.forEach((node) => node.classList.add('ud-visible'))
      return
    }
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('ud-visible')
          observer.unobserve(entry.target)
        }
      })
    }, { rootMargin: '-80px 0px -10% 0px' })
    nodes.forEach((node) => observer.observe(node))
    return () => observer.disconnect()
  }, [])

  return (
    <main className="min-h-screen overflow-x-hidden bg-[#FFFFE3] text-[#18324A]">
      <div className="pointer-events-none fixed inset-0 z-50 opacity-[.045] ud-noise" aria-hidden="true" />

      <nav className="absolute left-0 right-0 top-0 z-40 px-5 py-5 sm:px-8 lg:px-16">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <Link href="/" className="flex items-center gap-3 text-[#18324A] no-underline">
            <span className="grid h-10 w-10 place-items-center rounded-full border-2 border-[#18324A] bg-white text-[10px] font-black tracking-wider">US</span>
            <span>
              <strong className="block text-sm tracking-[.08em]">UDYOGSETU</strong>
              <small className="block text-[9px] font-semibold uppercase tracking-[.2em] text-[#607386]">Idea to Industry</small>
            </span>
          </Link>
          <div className="flex items-center gap-2 sm:gap-3">
            <Link href="/login" className="hidden rounded-full px-4 py-2 text-sm font-semibold text-[#18324A] transition hover:bg-white/70 sm:inline-flex">Sign in</Link>
            <Button onClick={() => router.push('/register')} className="rounded-full bg-[#173A59] px-5 shadow-lg shadow-[#173A59]/15 hover:bg-[#102f4b]">
              Start a project <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </div>
      </nav>

      <section className="relative min-h-[760px] overflow-hidden border-b border-[#D9D7B7] sm:min-h-[820px]">
        <div className="absolute inset-0 ud-grid opacity-70" />
        <div className="absolute -right-24 top-20 h-[520px] w-[520px] rounded-full bg-[#22B8CF]/10 blur-3xl" />
        <div className="absolute -bottom-48 left-[-8%] h-[500px] w-[500px] rounded-full bg-[#2F9C84]/10 blur-3xl" />

        <div className="relative mx-auto grid min-h-[760px] max-w-7xl items-center gap-12 px-5 pb-20 pt-32 sm:px-8 lg:grid-cols-[1.02fr_.98fr] lg:px-16 lg:pt-28">
          <div className="max-w-3xl">
            <div className="ud-reveal inline-flex items-center gap-2 rounded-full border border-[#C9C7A8] bg-white/65 px-4 py-2 text-[10px] font-black uppercase tracking-[.18em] text-[#547086] backdrop-blur">
              <span className="h-2 w-2 rounded-full bg-[#2F9C84] shadow-[0_0_0_7px_rgba(47,156,132,.10)]" /> Industrial approvals, made clearer
            </div>
            <h1 className="ud-reveal mt-6 text-[clamp(3.2rem,7vw,6.7rem)] font-black leading-[.92] tracking-[-.065em]" style={{ transitionDelay: '80ms' }}>
              From idea to industry.
              <span className="mt-2 block bg-gradient-to-r from-[#173A59] via-[#167A9A] to-[#2F9C84] bg-[length:200%_auto] bg-clip-text text-transparent" style={{ animation: 'ud-shimmer 8s linear infinite' }}>
                One clear journey.
              </span>
            </h1>
            <p className="ud-reveal mt-7 max-w-2xl text-base leading-7 text-[#607386] sm:text-lg" style={{ transitionDelay: '160ms' }}>
              UDYOGSETU brings approvals, documents, applications, inspections, compliance and support schemes into one guided workspace—so you always know what to do next.
            </p>
            <div className="ud-reveal mt-8 flex flex-col gap-3 sm:flex-row" style={{ transitionDelay: '240ms' }}>
              <Button size="lg" onClick={() => router.push('/register')} className="h-12 rounded-full bg-[#173A59] px-7 text-base hover:bg-[#102f4b]">
                Start your project <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
              <a href="#journey" className="inline-flex h-12 items-center justify-center gap-2 rounded-full border border-[#BFC0A5] bg-white/60 px-6 text-sm font-bold text-[#18324A] backdrop-blur transition hover:-translate-y-0.5 hover:bg-white">
                See how it works <ArrowDown className="h-4 w-4" />
              </a>
            </div>
            <div className="ud-reveal mt-8 flex flex-wrap gap-x-6 gap-y-2 text-xs font-semibold text-[#607386]" style={{ transitionDelay: '320ms' }}>
              <span className="inline-flex items-center gap-2"><Check className="h-4 w-4 text-[#2F9C84]" /> Guided approval roadmap</span>
              <span className="inline-flex items-center gap-2"><Check className="h-4 w-4 text-[#2F9C84]" /> Document readiness</span>
              <span className="inline-flex items-center gap-2"><Check className="h-4 w-4 text-[#2F9C84]" /> Compliance visibility</span>
            </div>
          </div>

          <div className="relative mx-auto w-full max-w-[610px] [perspective:1200px]">
            <div className="absolute -inset-8 rounded-[3rem] bg-gradient-to-br from-[#22B8CF]/10 to-[#2F9C84]/10 blur-2xl" />
            <div className="ud-reveal relative rotate-[2deg] rounded-[30px] border border-[#18324A]/15 bg-[#173A59] p-3 shadow-[0_35px_90px_rgba(23,58,89,.22)] [transform-style:preserve-3d]" style={{ transitionDelay: '180ms' }}>
              <div className="overflow-hidden rounded-[23px] border border-white/10 bg-[#0e2941]">
                <div className="flex items-center justify-between border-b border-white/10 px-5 py-4 text-white">
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-[.2em] text-cyan-200/60">Project command view</p>
                    <p className="mt-1 font-semibold">Approval journey</p>
                  </div>
                  <span className="rounded-full bg-[#2F9C84]/15 px-3 py-1 text-[10px] font-bold text-emerald-200">LIVE</span>
                </div>
                <div className="relative min-h-[370px] overflow-hidden px-5 py-6 sm:min-h-[410px]">
                  <div className="absolute inset-0 opacity-20 ud-grid" />
                  <div className="relative z-10 space-y-3">
                    {['Project profile', 'Approval roadmap', 'Document readiness', 'Application tracking', 'Compliance'].map((item, i) => (
                      <div key={item} className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[.045] p-3 backdrop-blur" style={{ animation: `ud-float ${4 + i * .4}s ease-in-out infinite`, animationDelay: `${i * -.45}s` }}>
                        <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl ${i < 2 ? 'bg-[#2F9C84] text-white' : 'bg-white/10 text-cyan-100'}`}>
                          {i < 2 ? <Check className="h-4 w-4" /> : <span className="text-xs font-black">0{i + 1}</span>}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-semibold text-white">{item}</p>
                          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-gradient-to-r from-cyan-300 to-emerald-300" style={{ width: `${[100, 76, 58, 36, 22][i]}%` }} /></div>
                        </div>
                        <span className="text-[10px] text-white/45">{i < 2 ? 'Ready' : 'Next'}</span>
                      </div>
                    ))}
                  </div>
                  <svg className="pointer-events-none absolute bottom-7 left-10 h-20 w-[80%] opacity-50" viewBox="0 0 400 80" fill="none" aria-hidden="true">
                    <path d="M5 65 C90 10 135 75 220 35 S315 20 395 5" stroke="#22D3EE" strokeWidth="2" strokeDasharray="8 10" style={{ animation: 'ud-route 4s linear infinite' }} />
                    {[5, 120, 220, 395].map((cx) => <circle key={cx} cx={cx} cy={cx === 5 ? 65 : cx === 120 ? 48 : cx === 220 ? 35 : 5} r="4" fill="#E0FBFF" />)}
                  </svg>
                </div>
              </div>
            </div>
            <div className="absolute -bottom-5 -left-2 hidden rounded-2xl border border-[#18324A]/10 bg-white/85 px-4 py-3 text-xs font-bold shadow-xl backdrop-blur sm:block" style={{ animation: 'ud-float 4s ease-in-out infinite' }}>
              <span className="mr-2 inline-block h-2 w-2 rounded-full bg-[#2F9C84]" /> Next action: complete project profile
            </div>
          </div>
        </div>
        <div className="absolute bottom-6 left-1/2 hidden -translate-x-1/2 items-center gap-2 text-[10px] font-black uppercase tracking-[.2em] text-[#607386] sm:flex">Scroll to explore <ArrowDown className="h-3 w-3" /></div>
      </section>

      <section id="journey" className="border-b border-[#D9D7B7] bg-white/45 py-24 sm:py-28">
        <div className="mx-auto max-w-7xl px-5 sm:px-8 lg:px-16">
          <div className="ud-reveal max-w-2xl">
            <p className="text-[10px] font-black uppercase tracking-[.22em] text-[#547086]">A guided journey</p>
            <h2 className="mt-3 text-4xl font-black tracking-[-.04em] sm:text-5xl">Know what happens next.</h2>
            <p className="mt-4 text-base leading-7 text-[#607386]">The interface is organised around the work you actually need to complete—not a wall of disconnected tools.</p>
          </div>
          <div className="mt-12 grid gap-4 md:grid-cols-4">
            {journey.map(([step, title, desc], i) => (
              <article key={step} className="ud-reveal group relative rounded-[24px] border border-[#18324A]/10 bg-white/75 p-6 shadow-[0_12px_40px_rgba(24,50,74,.06)] transition duration-300 hover:-translate-y-1 hover:shadow-[0_22px_55px_rgba(24,50,74,.11)]" style={{ transitionDelay: `${i * 70}ms` }}>
                <span className="text-[10px] font-black tracking-[.18em] text-[#2F9C84]">{step}</span>
                <div className="mt-10 h-px w-full bg-[#D9D7B7] transition group-hover:bg-[#2F9C84]" />
                <h3 className="mt-5 text-lg font-black">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-[#607386]">{desc}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="features" className="py-24 sm:py-28">
        <div className="mx-auto max-w-7xl px-5 sm:px-8 lg:px-16">
          <div className="ud-reveal flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
            <div className="max-w-2xl">
              <p className="text-[10px] font-black uppercase tracking-[.22em] text-[#547086]">One workspace</p>
              <h2 className="mt-3 text-4xl font-black tracking-[-.04em] sm:text-5xl">Everything has a place.</h2>
            </div>
            <p className="max-w-md text-sm leading-6 text-[#607386]">Each screen will follow the same visual language: clear hierarchy, predictable actions, generous spacing and purposeful motion.</p>
          </div>

          <div className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {features.map(({ icon: Icon, number, title, description }, i) => (
              <article key={number} className="ud-reveal group relative min-h-[230px] overflow-hidden rounded-[26px] border border-[#18324A]/10 bg-white/65 p-7 backdrop-blur transition duration-300 hover:-translate-y-1 hover:border-[#2F9C84]/35 hover:bg-white" style={{ transitionDelay: `${(i % 3) * 70}ms` }}>
                <div className="absolute -right-10 -top-10 h-32 w-32 rounded-full bg-[#22B8CF]/10 blur-2xl transition duration-500 group-hover:bg-[#22B8CF]/20" />
                <div className="relative flex items-start justify-between">
                  <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#173A59] text-white shadow-lg shadow-[#173A59]/15"><Icon className="h-5 w-5" /></div>
                  <span className="text-[10px] font-black tracking-[.18em] text-[#9AA4A9]">{number}</span>
                </div>
                <h3 className="relative mt-9 text-xl font-black">{title}</h3>
                <p className="relative mt-2 max-w-sm text-sm leading-6 text-[#607386]">{description}</p>
                <ArrowRight className="absolute bottom-7 right-7 h-4 w-4 text-[#A5AFB4] transition duration-300 group-hover:translate-x-1 group-hover:text-[#2F9C84]" />
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="px-5 pb-20 sm:px-8 lg:px-16">
        <div className="mx-auto max-w-7xl overflow-hidden rounded-[32px] bg-[#173A59] px-7 py-14 text-white shadow-[0_30px_80px_rgba(23,58,89,.18)] sm:px-12 sm:py-16 lg:px-16">
          <div className="grid gap-10 lg:grid-cols-[1fr_auto] lg:items-center">
            <div>
              <p className="text-[10px] font-black uppercase tracking-[.22em] text-cyan-200/70">Start with the next step</p>
              <h2 className="mt-3 max-w-3xl text-4xl font-black tracking-[-.04em] sm:text-5xl">Your project should not feel like a paperwork maze.</h2>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-blue-100/75 sm:text-base">Create a project and let the workspace guide you through the journey.</p>
            </div>
            <Button size="lg" onClick={() => router.push('/register')} className="h-12 rounded-full bg-white px-7 font-bold text-[#173A59] hover:bg-[#FFFFE3]">
              Create account <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </div>
      </section>

      <footer className="border-t border-[#D9D7B7] px-5 py-8 sm:px-8 lg:px-16">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 text-xs text-[#607386] sm:flex-row sm:items-center sm:justify-between">
          <span className="font-black tracking-[.12em] text-[#18324A]">UDYOGSETU</span>
          <span>Industrial approval & compliance prototype · Smart India Hackathon</span>
          <Link href="/login" className="font-bold text-[#173A59] hover:underline">Sign in</Link>
        </div>
      </footer>
    </main>
  )
}
