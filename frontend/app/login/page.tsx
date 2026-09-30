'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ArrowRight, Building2, Check, Loader2, Lock, Mail } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { apiClient } from '@/services/api'
import { getRoleFromToken, setSession } from '@/lib/auth'

const loginSchema = z.object({ email: z.string().email('Enter a valid email address'), password: z.string().min(8, 'Password must be at least 8 characters') })
type LoginForm = z.infer<typeof loginSchema>

export default function LoginPage() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) })

  const onSubmit = async (data: LoginForm) => {
    setError(null)
    try {
      const result = await apiClient.login(data.email, data.password)
      const token = result.access_token
      const role = getRoleFromToken(token)
      setSession(token, { email: data.email, role })
      router.push(role === 'OFFICER' || role === 'ADMIN' ? '/dashboard/officer' : '/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid email or password')
    }
  }

  return (
    <main className="min-h-screen bg-[#FFFFE3] px-5 py-6 text-[#18324A] sm:px-8 lg:px-12">
      <div className="mx-auto grid min-h-[calc(100vh-3rem)] max-w-6xl overflow-hidden rounded-[32px] border border-[#18324A]/10 bg-white shadow-[0_30px_90px_rgba(24,50,74,.12)] lg:grid-cols-[.95fr_1.05fr]">
        <section className="relative hidden overflow-hidden bg-[#173A59] p-10 text-white lg:flex lg:flex-col lg:justify-between lg:p-12">
          <div className="absolute inset-0 opacity-20 ud-grid" />
          <div className="absolute -right-24 top-12 h-72 w-72 rounded-full bg-cyan-300/15 blur-3xl" />
          <Link href="/" className="relative z-10 flex items-center gap-3 text-white no-underline">
            <span className="grid h-10 w-10 place-items-center rounded-full border-2 border-white/70 text-[10px] font-black">US</span>
            <span><strong className="block text-sm tracking-[.08em]">UDYOGSETU</strong><small className="block text-[9px] uppercase tracking-[.2em] text-blue-100/60">Idea to Industry</small></span>
          </Link>
          <div className="relative z-10">
            <p className="text-[10px] font-black uppercase tracking-[.22em] text-cyan-200/70">Your workspace</p>
            <h1 className="mt-4 text-4xl font-black leading-tight tracking-[-.04em]">Pick up exactly where you left off.</h1>
            <p className="mt-4 max-w-md text-sm leading-6 text-blue-100/70">Applications, documents, inspections and compliance stay connected to your project.</p>
            <div className="mt-8 space-y-3">
              {['Approval roadmap in one view', 'Documents and queries stay together', 'Clear next actions on every screen'].map((item) => (
                <div key={item} className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[.05] px-4 py-3 text-sm">
                  <span className="grid h-7 w-7 place-items-center rounded-full bg-[#2F9C84]"><Check className="h-3.5 w-3.5" /></span>{item}
                </div>
              ))}
            </div>
          </div>
          <p className="relative z-10 text-xs text-blue-100/45">Prototype experience · Government integrations are clearly identified in the workspace.</p>
        </section>

        <section className="flex items-center p-6 sm:p-10 lg:p-14">
          <div className="mx-auto w-full max-w-md">
            <Link href="/" className="mb-8 inline-flex items-center gap-2 text-sm font-bold text-[#173A59] lg:hidden"><Building2 className="h-5 w-5" /> UDYOGSETU</Link>
            <div>
              <p className="text-[10px] font-black uppercase tracking-[.22em] text-[#547086]">Welcome back</p>
              <h2 className="mt-2 text-4xl font-black tracking-[-.04em]">Sign in to continue.</h2>
              <p className="mt-3 text-sm leading-6 text-[#607386]">Open your project workspace and continue from your next action.</p>
            </div>
            {error && <div className="mt-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
            <form onSubmit={handleSubmit(onSubmit)} className="mt-8 space-y-5">
              <div>
                <label className="mb-2 block text-sm font-bold">Email address</label>
                <div className="relative"><Mail className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#7B8A94]" /><Input type="email" placeholder="you@company.com" autoComplete="email" className="h-12 rounded-2xl border-[#C9C7A8] bg-[#FFFFE3]/55 pl-11" {...register('email')} /></div>
                {errors.email && <p className="mt-1.5 text-xs text-red-600">{errors.email.message}</p>}
              </div>
              <div>
                <label className="mb-2 block text-sm font-bold">Password</label>
                <div className="relative"><Lock className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#7B8A94]" /><Input type="password" placeholder="••••••••" autoComplete="current-password" className="h-12 rounded-2xl border-[#C9C7A8] bg-[#FFFFE3]/55 pl-11" {...register('password')} /></div>
                {errors.password && <p className="mt-1.5 text-xs text-red-600">{errors.password.message}</p>}
              </div>
              <Button type="submit" className="h-12 w-full rounded-2xl bg-[#173A59] text-base hover:bg-[#102f4b]" disabled={isSubmitting}>
                {isSubmitting ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Signing in...</> : <>Sign in <ArrowRight className="ml-2 h-4 w-4" /></>}
              </Button>
            </form>
            <p className="mt-7 text-center text-sm text-[#607386]">New to UDYOGSETU? <Link href="/register" className="font-bold text-[#173A59] hover:underline">Create your account</Link></p>
          </div>
        </section>
      </div>
    </main>
  )
}
