/**
 * Route guard for authenticated pages. Runs on the client only — the token
 * lives in localStorage, so a server-side check would always fail and cause a
 * redirect flash on hydration.
 */
export default defineNuxtRouteMiddleware((to) => {
  if (import.meta.server) return

  const { isAuthenticated } = useAuth()
  if (!isAuthenticated.value) {
    return navigateTo({ path: '/login', query: { redirect: to.fullPath } })
  }
})
