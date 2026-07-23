<script setup lang="ts">
const { register } = useAuth()
const route = useRoute()
const router = useRouter()

const fullName = ref('')
const email = ref('')
const password = ref('')
const errorMsg = ref('')
const loading = ref(false)

async function onSubmit() {
  errorMsg.value = ''
  if (password.value.length < 8) {
    errorMsg.value = 'Password must be at least 8 characters.'
    return
  }
  loading.value = true
  try {
    await register({
      email: email.value,
      password: password.value,
      full_name: fullName.value || undefined,
    })
    const redirect = (route.query.redirect as string) || '/my-tickets'
    router.push(redirect)
  } catch (e: any) {
    errorMsg.value =
      e?.data?.detail || 'Could not create your account. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="flex items-center justify-center px-4 py-12 md:py-20">
    <div class="w-full max-w-md p-8 space-y-6 border rounded-2xl dark:border-gray-800">
      <div class="space-y-2 text-center">
        <h1 class="text-3xl font-bold">Create your account</h1>
        <p class="text-gray-500 dark:text-gray-400">Join Ren to discover events and book tickets.</p>
      </div>

      <form class="space-y-4" @submit.prevent="onSubmit">
        <div class="space-y-1.5">
          <label for="fullName" class="text-sm font-medium">Full name <span class="text-gray-400">(optional)</span></label>
          <input
            id="fullName"
            v-model="fullName"
            type="text"
            autocomplete="name"
            placeholder="Jane Doe"
            class="w-full h-12 px-4 border rounded-xl border-gray-200 focus:outline-none focus:ring-2 focus:border-purple-600 dark:bg-gray-800 dark:border-gray-800"
          />
        </div>
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
            autocomplete="new-password"
            placeholder="At least 8 characters"
            class="w-full h-12 px-4 border rounded-xl border-gray-200 focus:outline-none focus:ring-2 focus:border-purple-600 dark:bg-gray-800 dark:border-gray-800"
          />
        </div>

        <p v-if="errorMsg" class="text-sm text-red-500">{{ errorMsg }}</p>

        <button
          type="submit"
          class="w-full py-3 font-semibold text-white transition duration-200 bg-purple-600 rounded-full disabled:opacity-50 hover:bg-purple-700"
          :disabled="loading"
        >{{ loading ? 'Creating account…' : 'Create account' }}</button>
      </form>

      <p class="text-sm text-center text-gray-500 dark:text-gray-400">
        Already have an account?
        <NuxtLink to="/login" class="font-medium text-purple-600 hover:text-purple-700">Sign in</NuxtLink>
      </p>
    </div>
  </section>
</template>
