import {
  clearSession,
  decodeTokenPayload,
  getRoleFromToken,
  getSessionUser,
  getToken,
  isAuthenticated,
  isTokenExpired,
  setSession,
} from '@/lib/auth'

function makeToken(payload: Record<string, unknown>, expiresInSeconds = 3600): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const body = btoa(
    JSON.stringify({ ...payload, exp: Math.floor(Date.now() / 1000) + expiresInSeconds }),
  )
  return `${header}.${body}.signature`
}

describe('auth helpers', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('stores and retrieves the session token', () => {
    setSession(makeToken({ sub: 'u1' }), { name: 'Ada', role: 'ENTREPRENEUR' })
    expect(getToken()).toBeTruthy()
    expect(getSessionUser()).toEqual({ name: 'Ada', role: 'ENTREPRENEUR' })
  })

  it('marks the session authenticated after storing a token', () => {
    expect(isAuthenticated()).toBe(false)
    setSession(makeToken({ sub: 'u1' }))
    expect(isAuthenticated()).toBe(true)
  })

  it('detects an expired token', () => {
    setSession(makeToken({ sub: 'u1' }, -10))
    expect(isTokenExpired()).toBe(true)
  })

  it('detects a valid token as unexpired', () => {
    setSession(makeToken({ sub: 'u1' }, 3600))
    expect(isTokenExpired()).toBe(false)
  })

  it('clears the session', () => {
    setSession(makeToken({ sub: 'u1' }), { name: 'Ada', role: 'ENTREPRENEUR' })
    clearSession()
    expect(getToken()).toBeNull()
    expect(getSessionUser()).toBeNull()
  })

  it('extracts the actual role from the JWT payload', () => {
    expect(getRoleFromToken(makeToken({ sub: 'u1', role: 'OFFICER' }))).toBe('OFFICER')
    expect(getRoleFromToken(makeToken({ sub: 'u2', role: 'ENTREPRENEUR' }))).toBe('ENTREPRENEUR')
  })

  it('falls back to ENTREPRENEUR when the token has no role', () => {
    expect(getRoleFromToken(makeToken({ sub: 'u1' }))).toBe('ENTREPRENEUR')
  })

  it('returns null when the token cannot be decoded', () => {
    expect(decodeTokenPayload('not-a-jwt')).toBeNull()
    expect(getRoleFromToken('not-a-jwt')).toBe('ENTREPRENEUR')
  })

  it('stores the authenticated user role from the decoded token', () => {
    const token = makeToken({ sub: 'o1', email: 'officer@test.com', role: 'OFFICER' })
    setSession(token, { email: 'officer@test.com', role: getRoleFromToken(token) })
    expect(getSessionUser()).toEqual({
      email: 'officer@test.com',
      role: 'OFFICER',
    })
  })

  it('infers the user name and role from the JWT when no stored user exists', () => {
    const token = makeToken({ sub: 'e1', email: 'entrepreneur@test.com', role: 'ENTREPRENEUR' })
    setSession(token)
    expect(getSessionUser()).toEqual({
      name: 'entrepreneur',
      email: 'entrepreneur@test.com',
      role: 'ENTREPRENEUR',
    })
  })
})