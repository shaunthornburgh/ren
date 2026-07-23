/**
 * A thin `$fetch` wrapper that targets the backend API and attaches the bearer
 * token (when present) to every request.
 */
export function useApi() {
  const config = useRuntimeConfig()
  const { token } = useAuth()

  function apiFetch<T>(url: string, opts: Record<string, any> = {}): Promise<T> {
    return $fetch<T>(url, {
      baseURL: config.public.apiBase,
      ...opts,
      headers: {
        ...(opts.headers ?? {}),
        ...(token.value ? { Authorization: `Bearer ${token.value}` } : {}),
      },
    })
  }

  return { apiFetch }
}
