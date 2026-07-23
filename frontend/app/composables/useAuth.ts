import type { Token, UserRead } from '~/types/api'

const TOKEN_KEY = 'ren_token'

/**
 * Auth state + actions, backed by a JWT in localStorage.
 *
 * State is shared across the app via `useState`. The token is loaded from
 * localStorage by the client-only `auth` plugin on startup.
 */
export function useAuth() {
  const config = useRuntimeConfig()
  const token = useState<string | null>('auth:token', () => null)
  const user = useState<UserRead | null>('auth:user', () => null)

  const isAuthenticated = computed(() => !!token.value)

  function setToken(value: string | null) {
    token.value = value
    if (import.meta.client) {
      if (value) localStorage.setItem(TOKEN_KEY, value)
      else localStorage.removeItem(TOKEN_KEY)
    }
  }

  async function fetchUser(): Promise<UserRead | null> {
    if (!token.value) {
      user.value = null
      return null
    }
    try {
      user.value = await $fetch<UserRead>('/auth/me', {
        baseURL: config.public.apiBase,
        headers: { Authorization: `Bearer ${token.value}` },
      })
    } catch {
      // Token invalid/expired — clear it.
      setToken(null)
      user.value = null
    }
    return user.value
  }

  async function login(email: string, password: string): Promise<void> {
    const res = await $fetch<Token>('/auth/login', {
      baseURL: config.public.apiBase,
      method: 'POST',
      body: { email, password },
    })
    setToken(res.access_token)
    await fetchUser()
  }

  async function register(payload: {
    email: string
    password: string
    full_name?: string
  }): Promise<void> {
    await $fetch<UserRead>('/auth/register', {
      baseURL: config.public.apiBase,
      method: 'POST',
      body: payload,
    })
    // Registration doesn't return a token, so log in immediately after.
    await login(payload.email, payload.password)
  }

  function logout() {
    setToken(null)
    user.value = null
  }

  return {
    token,
    user,
    isAuthenticated,
    setToken,
    fetchUser,
    login,
    register,
    logout,
  }
}
