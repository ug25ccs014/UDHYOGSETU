type SessionUser = {
  name: string
  email?: string
  role: string
}

const TOKEN_KEY = 'access_token'
const USER_KEY = 'udyogsetu_user'

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(TOKEN_KEY)
}

export function decodeTokenPayload(token: string): Record<string, unknown> | null {
  try {
    return JSON.parse(atob(token.split('.')[1]))
  } catch {
    return null
  }
}

export function getRoleFromToken(token: string): string {
  const payload = decodeTokenPayload(token)
  const role = payload?.role
  return typeof role === 'string' && role ? role : 'ENTREPRENEUR'
}

export function setSession(token: string, user?: any) {
  if (typeof window === 'undefined') return
  localStorage.setItem(TOKEN_KEY, token)
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearSession() {
  if (typeof window === 'undefined') return
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function getSessionUser(): SessionUser | null {
  if (typeof window === 'undefined') return null
  const token = getToken()
  try {
    const raw = localStorage.getItem(USER_KEY)
    if (raw) return JSON.parse(raw)
    if (token) {
      const payload = decodeTokenPayload(token) || {}
      return {
        name: (payload.email as string)?.split('@')[0] || 'User',
        email: payload.email as string | undefined,
        role: getRoleFromToken(token),
      }
    }
  } catch {
    return null
  }
  return null
}

export function isAuthenticated(): boolean {
  return !!getToken()
}

export function isTokenExpired(): boolean {
  const token = getToken()
  if (!token) return true
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    const exp = payload.exp as number | undefined
    if (!exp) return false
    return Date.now() >= exp * 1000
  } catch {
    return true
  }
}

export function logout() {
  clearSession()
  if (typeof window !== 'undefined') {
    window.location.href = '/login'
  }
}

export type { SessionUser }