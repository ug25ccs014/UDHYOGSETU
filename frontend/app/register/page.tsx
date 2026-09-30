'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import AuthShell from '@/components/AuthShell'
import { apiClient } from '@/services/api'
import { useLanguage, TKey } from '@/lib/language'

// Messages are translation keys, resolved at render time in the selected language.
const registerSchema = z
  .object({
    name: z.string().min(2, 'auth.vName'),
    email: z.string().email('auth.vEmail'),
    phone: z.string().min(10, 'auth.vPhone'),
    role: z.literal('ENTREPRENEUR'),
    password: z.string().min(8, 'auth.vPassword'),
    confirm_password: z.string(),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: 'auth.vMatch',
    path: ['confirm_password'],
  })

type RegisterForm = z.infer<typeof registerSchema>

const Label = ({ htmlFor, children }: { htmlFor: string; children: React.ReactNode }) => (
  <label htmlFor={htmlFor} className="mb-1 block text-sm font-semibold text-gray-700">{children}</label>
)
const Err = ({ msg }: { msg?: string }) => {
  const { t } = useLanguage()
  return msg ? <p className="mt-1 text-xs text-red-600">{t(msg as TKey)}</p> : null
}

export default function RegisterPage() {
  const { t } = useLanguage()
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: { role: 'ENTREPRENEUR' },
  })

  const onSubmit = async (data: RegisterForm) => {
    setError(null)
    try {
      const { confirm_password, ...payload } = data
      await apiClient.register(payload.email, payload.name, payload.phone, payload.password, payload.role)
      router.push('/login?registered=1')
    } catch (err: any) {
      setError(err.response?.data?.detail || t('auth.regFailed'))
    }
  }

  return (
    <AuthShell
      step={t('auth.regStep')}
      title={t('auth.regTitle')}
      subtitle={t('auth.regSub')}
      points={[t('auth.regP1'), t('auth.regP2'), t('auth.regP3')]}
      footer={
        <>
          {t('auth.haveAccount')}{' '}
          <Link href="/login" className="font-bold text-blue-600 hover:text-blue-500">{t('auth.signIn')}</Link>
        </>
      }
    >
      {error && (
        <div role="alert" className="mb-5 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <div>
          <Label htmlFor="name">{t('auth.fullName')}</Label>
          <Input id="name" type="text" placeholder={t('auth.fullNamePh')} autoComplete="name" {...register('name')} />
          <Err msg={errors.name?.message} />
        </div>
        <div>
          <Label htmlFor="email">{t('auth.email')}</Label>
          <Input id="email" type="email" placeholder="you@company.com" autoComplete="email" {...register('email')} />
          <Err msg={errors.email?.message} />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="phone">{t('auth.phone')}</Label>
            <Input id="phone" type="tel" placeholder="+91 XXXXXXXXXX" autoComplete="tel" {...register('phone')} />
            <Err msg={errors.phone?.message} />
          </div>
          <div>
            <Label htmlFor="role">{t('auth.iAmA')}</Label>
            <Select id="role" {...register('role')} disabled>
              <option value="ENTREPRENEUR">{t('auth.entrepreneur')}</option>
            </Select>
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="password">{t('auth.password')}</Label>
            <Input id="password" type="password" placeholder={t('auth.passwordPh')} autoComplete="new-password" {...register('password')} />
            <Err msg={errors.password?.message} />
          </div>
          <div>
            <Label htmlFor="confirm_password">{t('auth.confirm')}</Label>
            <Input id="confirm_password" type="password" placeholder={t('auth.confirmPh')} autoComplete="new-password" {...register('confirm_password')} />
            <Err msg={errors.confirm_password?.message} />
          </div>
        </div>

        <Button type="submit" size="lg" className="mt-2 w-full" disabled={isSubmitting}>
          {isSubmitting ? (<><Loader2 className="h-4 w-4 animate-spin" /> {t('auth.creating')}</>) : t('auth.createAccount')}
        </Button>
      </form>
    </AuthShell>
  )
}
