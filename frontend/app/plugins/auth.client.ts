/**
 * On client startup, restore the session from localStorage and load the user.
 * Runs before route middleware so guarded routes see the correct auth state.
 */
export default defineNuxtPlugin(async () => {
  const { token, fetchUser } = useAuth()
  const stored = localStorage.getItem('ren_token')
  if (stored) {
    token.value = stored
    await fetchUser()
  }
})
