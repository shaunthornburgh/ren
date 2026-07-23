/**
 * Route guard for organizer-only pages. Requires an authenticated user whose
 * role is `organizer` or `admin`. Runs on the client only (the token lives in
 * localStorage), consistent with the `auth` middleware.
 */
export default defineNuxtRouteMiddleware((to) => {
  if (import.meta.server) return

  const { isAuthenticated, user } = useAuth()
  if (!isAuthenticated.value) {
    return navigateTo({ path: '/login', query: { redirect: to.fullPath } })
  }

  const role = user.value?.role
  if (role !== 'organizer' && role !== 'admin') {
    // Signed in but not permitted — send home rather than to login.
    return navigateTo('/')
  }
})
