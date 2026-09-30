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

const registerSchema = z
  .object({
    name: z.string().min(2, 'Name must be at least 2 characters'),
    email: z.string().email('Enter a valid email address'),
    phone: z.string().min(10, 'Enter a valid 10-digit phone number'),
    role: z.literal('ENTREPRENEUR'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirm_password: z.string(),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: 'Passwords do not match',
    path: ['confirm_password'],
  })

type RegisterForm = z.infer<typeof registerSchema>

const Label = ({ htmlFor, children }: { htmlFor: string; children: React.ReactNode }) => (
  <label htmlFor={htmlFor} className="mb-1 block text-sm font-semibold text-gray-700">{children}</label>
)
const Err = ({ msg }: { msg?: string }) => (msg ? <p className="mt-1 text-xs text-red-600">{msg}</p> : null)

export default function RegisterPage() {
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
      setError(err.response?.data?.detail || 'Registration failed. Please try again.')
    }
  }

  return (
    <AuthShell
      step="Step 1 of 2 · Create account"
      title="Create your account"
      subtitle="It takes about a minute. Next, you'll set up your first project."
      points={[
        'A personalised approval checklist for your unit',
        'Automatic document checks before you submit',
        'One place to track applications and compliance',
      ]}
      footer={
        <>
          Already have an account?{' '}
          <Link href="/login" className="font-bold text-blue-600 hover:text-blue-500">Sign in</Link>
        </>
      }
    >
      {error && (
        <div role="alert" className="mb-5 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <div>
          <Label htmlFor="name">Full name</Label>
          <Input id="name" type="text" placeholder="Your full name" autoComplete="name" {...register('name')} />
          <Err msg={errors.name?.message} />
        </div>
        <div>
          <Label htmlFor="email">Email address</Label>
          <Input id="email" type="email" placeholder="you@company.com" autoComplete="email" {...register('email')} />
          <Err msg={errors.email?.message} />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="phone">Phone number</Label>
            <Input id="phone" type="tel" placeholder="+91 XXXXXXXXXX" autoComplete="tel" {...register('phone')} />
            <Err msg={errors.phone?.message} />
          </div>
          <div>
            <Label htmlFor="role">I am a</Label>
            <Select id="role" {...register('role')} disabled>
              <option value="ENTREPRENEUR">Entrepreneur</option>
            </Select>
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="password">Password</Label>
            <Input id="password" type="password" placeholder="Min 8 characters" autoComplete="new-password" {...register('password')} />
            <Err msg={errors.password?.message} />
          </div>
          <div>
            <Label htmlFor="confirm_password">Confirm password</Label>
            <Input id="confirm_password" type="password" placeholder="Re-enter password" autoComplete="new-password" {...register('confirm_password')} />
            <Err msg={errors.confirm_password?.message} />
          </div>
        </div>

        <Button type="submit" size="lg" className="mt-2 w-full" disabled={isSubmitting}>
          {isSubmitting ? (<><Loader2 className="h-4 w-4 animate-spin" /> Creating account...</>) : 'Create account'}
        </Button>
      </form>
    </AuthShell>
  )
}
