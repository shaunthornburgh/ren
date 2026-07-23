<script setup lang="ts">
const { login } = useAuth()
const route = useRoute()
const router = useRouter()

const email = ref('')
const password = ref('')
const errorMsg = ref('')
const loading = ref(false)

async function onSubmit() {
  errorMsg.value = ''
  loading.value = true
  try {
    await login(email.value, password.value)
    const redirect = (route.query.redirect as string) || '/my-tickets'
    router.push(redirect)
  } catch (e: any) {
    errorMsg.value =
      e?.data?.detail || 'Incorrect email or password. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="flex items-center justify-center px-4 py-12 md:py-20">
    <div class="w-full max-w-md p-8 space-y-6 border rounded-2xl dark:border-gray-800">
      <div class="space-y-2 text-center">
        <h1 class="text-3xl font-bold">Welcome back</h1>
        <p class="text-gray-500 dark:text-gray-400">Sign in to book and view your tickets.</p>
      </div>

      <form class="space-y-4" @submit.prevent="onSubmit">
        <div class="space-y-1.5">
          <label for="email" class="text-sm font-medium">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            required
            autocomplete="email"
            placeholder="you@example.com"
            class="w-full h-12 px-4 border rounded-xl border-gray-200 focus:outline-none focus:ring-2 focus:border-purple-600 dark:bg-gray-800 dark:border-gray-800"
          />
        </div>
        <div class="space-y-1.5">
          <label for="password" class="text-sm font-medium">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            required
            autocomplete="current-password"
            placeholder="••••••••"
            class="w-full h-12 px-4 border rounded-xl border-gray-200 focus:outline-none focus:ring-2 focus:border-purple-600 dark:bg-gray-800 dark:border-gray-800"
          />
        </div>

        <p v-if="errorMsg" class="text-sm text-red-500">{{ errorMsg }}</p>

        <button
          type="submit"
          class="w-full py-3 font-semibold text-white transition duration-200 bg-purple-600 rounded-full disabled:opacity-50 hover:bg-purple-700"
          :disabled="loading"
        >{{ loading ? 'Signing in…' : 'Sign in' }}</button>
      </form>

      <p class="text-sm text-center text-gray-500 dark:text-gray-400">
        Don't have an account?
        <NuxtLink to="/register" class="font-medium text-purple-600 hover:text-purple-700">Create one</NuxtLink>
      </p>
    </div>
  </section>
</template>
