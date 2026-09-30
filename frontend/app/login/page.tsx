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
import { useLanguage, TKey } from '@/lib/language'

// Messages are translation keys, resolved at render time in the selected language.
const loginSchema = z.object({
  email: z.string().email('auth.vEmail'),
  password: z.string().min(8, 'auth.vPassword'),
})

type LoginForm = z.infer<typeof loginSchema>

export default function LoginPage() {
  const { t } = useLanguage()
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
      setError(err.response?.data?.detail || t('auth.invalidLogin'))
    }
  }

  return (
    <AuthShell
      title={t('auth.loginTitle')}
      subtitle={t('auth.loginSub')}
      points={[t('auth.loginP1'), t('auth.loginP2'), t('auth.loginP3')]}
      footer={
        <>
          {t('auth.noAccount')}{' '}
          <Link href="/register" className="font-bold text-blue-600 hover:text-blue-500">{t('auth.createOne')}</Link>
        </>
      }
    >
      {justRegistered && (
        <div role="status" className="mb-5 flex items-start gap-2 rounded-xl border border-teal-100 bg-teal-50 p-3 text-sm text-teal-700">
          <CheckCircle2 className="mt-0.5 h-4 w-4 flex-none" /> {t('auth.registered')}
        </div>
      )}
      {error && (
        <div role="alert" className="mb-5 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
        <div>
          <label htmlFor="email" className="mb-1 block text-sm font-semibold text-gray-700">{t('auth.email')}</label>
          <div className="relative">
            <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input id="email" type="email" placeholder="you@company.com" autoComplete="email" className="pl-10" {...register('email')} />
          </div>
          {errors.email && <p className="mt-1 text-xs text-red-600">{t(errors.email.message as TKey)}</p>}
        </div>

        <div>
          <label htmlFor="password" className="mb-1 block text-sm font-semibold text-gray-700">{t('auth.password')}</label>
          <div className="relative">
            <Lock className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input id="password" type="password" placeholder="••••••••" autoComplete="current-password" className="pl-10" {...register('password')} />
          </div>
          {errors.password && <p className="mt-1 text-xs text-red-600">{t(errors.password.message as TKey)}</p>}
        </div>

        <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? (<><Loader2 className="h-4 w-4 animate-spin" /> {t('auth.signingIn')}</>) : t('auth.signIn')}
        </Button>
      </form>
    </AuthShell>
  )
}
