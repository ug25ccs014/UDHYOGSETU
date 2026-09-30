'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ArrowLeft, ArrowRight, Building2, Check, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { apiClient } from '@/services/api'

const registerSchema = z.object({ name: z.string().min(2, 'Name must be at least 2 characters'), email: z.string().email('Enter a valid email address'), phone: z.string().min(10, 'Enter a valid 10-digit phone number'), role: z.literal('ENTREPRENEUR'), password: z.string().min(8, 'Password must be at least 8 characters'), confirm_password: z.string() }).refine((data) => data.password === data.confirm_password, { message: 'Passwords do not match', path: ['confirm_password'] })
type RegisterForm = z.infer<typeof registerSchema>

export default function RegisterPage() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<RegisterForm>({ resolver: zodResolver(registerSchema), defaultValues: { role: 'ENTREPRENEUR' } })

  const onSubmit = async (data: RegisterForm) => {
    setError(null)
    try {
      const { confirm_password, ...payload } = data
      await apiClient.register(payload.email, payload.name, payload.phone, payload.password, payload.role)
      router.push('/login?registered=1')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed. Please try again.')
    }
  }

  return (
    <main className="min-h-screen bg-[#FFFFE3] px-5 py-6 text-[#18324A] sm:px-8 lg:px-12">
      <div className="mx-auto grid min-h-[calc(100vh-3rem)] max-w-6xl overflow-hidden rounded-[32px] border border-[#18324A]/10 bg-white shadow-[0_30px_90px_rgba(24,50,74,.12)] lg:grid-cols-[.9fr_1.1fr]">
        <section className="relative hidden overflow-hidden bg-[#173A59] p-10 text-white lg:flex lg:flex-col lg:justify-between lg:p-12">
          <div className="absolute inset-0 opacity-20 ud-grid" />
          <div className="absolute -bottom-20 -left-20 h-80 w-80 rounded-full bg-[#2F9C84]/20 blur-3xl" />
          <Link href="/" className="relative z-10 flex items-center gap-3 text-white no-underline"><span className="grid h-10 w-10 place-items-center rounded-full border-2 border-white/70 text-[10px] font-black">US</span><span><strong className="block text-sm tracking-[.08em]">UDYOGSETU</strong><small className="block text-[9px] uppercase tracking-[.2em] text-blue-100/60">Idea to Industry</small></span></Link>
          <div className="relative z-10">
            <p className="text-[10px] font-black uppercase tracking-[.22em] text-cyan-200/70">Start with clarity</p>
            <h1 className="mt-4 text-4xl font-black leading-tight tracking-[-.04em]">Create once. Build your project journey from there.</h1>
            <div className="mt-8 space-y-3">
              {['Create your entrepreneur profile', 'Add your first industrial project', 'Get a guided approval roadmap'].map((item, i) => <div key={item} className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[.05] px-4 py-3 text-sm"><span className="grid h-7 w-7 place-items-center rounded-full bg-[#2F9C84] text-xs font-black">{i + 1}</span>{item}</div>)}
            </div>
          </div>
          <p className="relative z-10 text-xs text-blue-100/45">You can update your business details later from the profile workspace.</p>
        </section>

        <section className="flex items-center p-6 sm:p-10 lg:p-14">
          <div className="mx-auto w-full max-w-xl">
            <Link href="/" className="mb-7 inline-flex items-center gap-2 text-sm font-bold text-[#173A59]"><ArrowLeft className="h-4 w-4" /> Back to home</Link>
            <p className="text-[10px] font-black uppercase tracking-[.22em] text-[#547086]">Step 1 · Account</p>
            <h2 className="mt-2 text-4xl font-black tracking-[-.04em]">Create your account.</h2>
            <p className="mt-3 text-sm leading-6 text-[#607386]">A few details are enough to get started. Your project-specific information comes next.</p>
            {error && <div className="mt-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
            <form onSubmit={handleSubmit(onSubmit)} className="mt-7 grid gap-5 sm:grid-cols-2">
              <div className="sm:col-span-2"><label className="mb-2 block text-sm font-bold">Full name</label><Input className="h-12 rounded-2xl border-[#C9C7A8] bg-[#FFFFE3]/55" placeholder="Your full name" {...register('name')} />{errors.name && <p className="mt-1.5 text-xs text-red-600">{errors.name.message}</p>}</div>
              <div><label className="mb-2 block text-sm font-bold">Email address</label><Input type="email" className="h-12 rounded-2xl border-[#C9C7A8] bg-[#FFFFE3]/55" placeholder="you@company.com" {...register('email')} />{errors.email && <p className="mt-1.5 text-xs text-red-600">{errors.email.message}</p>}</div>
              <div><label className="mb-2 block text-sm font-bold">Phone number</label><Input type="tel" className="h-12 rounded-2xl border-[#C9C7A8] bg-[#FFFFE3]/55" placeholder="+91 XXXXXXXXXX" {...register('phone')} />{errors.phone && <p className="mt-1.5 text-xs text-red-600">{errors.phone.message}</p>}</div>
              <div><label className="mb-2 block text-sm font-bold">I am a</label><Select className="h-12 rounded-2xl border-[#C9C7A8] bg-[#FFFFE3]/55" {...register('role')} disabled><option value="ENTREPRENEUR">Entrepreneur</option></Select></div>
              <div />
              <div><label className="mb-2 block text-sm font-bold">Password</label><Input type="password" className="h-12 rounded-2xl border-[#C9C7A8] bg-[#FFFFE3]/55" placeholder="Min 8 characters" {...register('password')} />{errors.password && <p className="mt-1.5 text-xs text-red-600">{errors.password.message}</p>}</div>
              <div><label className="mb-2 block text-sm font-bold">Confirm password</label><Input type="password" className="h-12 rounded-2xl border-[#C9C7A8] bg-[#FFFFE3]/55" placeholder="Re-enter password" {...register('confirm_password')} />{errors.confirm_password && <p className="mt-1.5 text-xs text-red-600">{errors.confirm_password.message}</p>}</div>
              <div className="sm:col-span-2"><Button type="submit" className="h-12 w-full rounded-2xl bg-[#173A59] text-base hover:bg-[#102f4b]" disabled={isSubmitting}>{isSubmitting ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Creating account...</> : <>Create account <ArrowRight className="ml-2 h-4 w-4" /></>}</Button></div>
            </form>
            <div className="mt-6 flex items-start gap-2 text-xs leading-5 text-[#607386]"><Check className="mt-0.5 h-4 w-4 shrink-0 text-[#2F9C84]" /> Your account is only the starting point. The dashboard will guide you through your project step by step.</div>
            <p className="mt-6 text-center text-sm text-[#607386]">Already have an account? <Link href="/login" className="font-bold text-[#173A59] hover:underline">Sign in</Link></p>
          </div>
        </section>
      </div>
    </main>
  )
}
