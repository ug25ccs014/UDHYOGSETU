'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { CheckCircle2, Loader2, Lock, Mail } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import AuthShell from '@/components/AuthShell'
import { apiClient } from '@/services/api'
import { getRoleFromToken, setSession } from '@/lib/auth'

const loginSchema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
})

type LoginForm = z.infer<typeof loginSchema>

export default function LoginPage() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const [justRegistered, setJustRegistered] = useState(false)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) })

  useEffect(() => {
    setJustRegistered(new URLSearchParams(window.location.search).get('registered') === '1')
  }, [])

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
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to continue your projects and applications."
      points={[
        'Pick up exactly where you left off',
        'See which approvals and documents are pending',
        'Get alerts for queries, inspections and deadlines',
      ]}
      footer={
        <>
          Don&apos;t have an account?{' '}
          <Link href="/register" className="font-bold text-blue-600 hover:text-blue-500">Create one</Link>
        </>
      }
    >
      {justRegistered && (
        <div role="status" className="mb-5 flex items-start gap-2 rounded-xl border border-teal-100 bg-teal-50 p-3 text-sm text-teal-700">
          <CheckCircle2 className="mt-0.5 h-4 w-4 flex-none" /> Account created. Please sign in to continue.
        </div>
      )}
      {error && (
        <div role="alert" className="mb-5 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
        <div>
          <label htmlFor="email" className="mb-1 block text-sm font-semibold text-gray-700">Email address</label>
          <div className="relative">
            <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input id="email" type="email" placeholder="you@company.com" autoComplete="email" className="pl-10" {...register('email')} />
          </div>
          {errors.email && <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>}
        </div>

        <div>
          <label htmlFor="password" className="mb-1 block text-sm font-semibold text-gray-700">Password</label>
          <div className="relative">
            <Lock className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input id="password" type="password" placeholder="••••••••" autoComplete="current-password" className="pl-10" {...register('password')} />
          </div>
          {errors.password && <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>}
        </div>

        <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? (<><Loader2 className="h-4 w-4 animate-spin" /> Signing in...</>) : 'Sign in'}
        </Button>
      </form>
    </AuthShell>
  )
}
