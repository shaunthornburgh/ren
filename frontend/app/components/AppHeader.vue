<script setup lang="ts">
const { isAuthenticated, user, logout } = useAuth()
const router = useRouter()

const open = ref(false) // mobile menu

const nav = [
  { label: 'Home', to: '/' },
  { label: 'Events', to: '/events' },
  { label: 'My Tickets', to: '/my-tickets' },
]

function signOut() {
  logout()
  open.value = false
  router.push('/')
}
</script>

<template>
  <header class="max-w-full bg-purple-50 dark:bg-gray-900">
    <div class="container max-w-screen-xl px-4 mx-auto">
      <div class="relative flex items-center justify-between py-5 dark:text-gray-50">
        <!-- logo -->
        <div>
          <NuxtLink to="/" class="flex items-center space-x-3 text-xl font-bold">
            <span class="flex items-center justify-center w-8 h-8 text-white bg-purple-600 rounded-lg">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z" /></svg>
            </span>
            <span>ren</span>
          </NuxtLink>
        </div>

        <!-- desktop nav -->
        <div class="hidden md:block">
          <div class="flex space-x-8">
            <NuxtLink
              v-for="link in nav"
              :key="link.to"
              :to="link.to"
              class="block font-semibold transition duration-200 hover:text-purple-600"
              active-class="text-purple-600"
            >{{ link.label }}</NuxtLink>
          </div>
        </div>

        <div class="flex items-center space-x-3">
          <ThemeToggle />

          <!-- auth actions (desktop) -->
          <template v-if="isAuthenticated">
            <span class="hidden md:block text-sm font-medium text-gray-500 dark:text-gray-400">
              {{ user?.full_name || user?.email }}
            </span>
            <button
              class="hidden px-5 py-2 font-semibold text-center text-white transition duration-200 bg-purple-600 rounded-full md:block hover:bg-purple-700"
              @click="signOut"
            >Sign out</button>
          </template>
          <NuxtLink
            v-else
            to="/login"
            class="hidden px-5 py-2 font-semibold text-center text-white transition duration-200 bg-purple-600 rounded-full md:block hover:bg-purple-700"
          >Sign in</NuxtLink>

          <!-- mobile menu -->
          <div class="md:hidden">
            <button
              class="flex items-center justify-center w-10 h-10 transition duration-200 rounded hover:bg-purple-100 dark:hover:bg-gray-700"
              aria-label="Open menu"
              @click="open = true"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <div
              v-show="open"
              class="absolute left-0 z-20 w-full p-4 bg-white shadow-lg top-20 rounded-xl dark:bg-gray-800"
              @click="open = false"
            >
              <NuxtLink
                v-for="link in nav"
                :key="link.to"
                :to="link.to"
                class="block px-3 py-2 font-semibold transition duration-200 rounded-md hover:text-purple-600 hover:bg-purple-50 dark:hover:bg-gray-700 dark:hover:text-purple-400"
              >{{ link.label }}</NuxtLink>
              <button
                v-if="isAuthenticated"
                class="block w-full px-3 py-2 mt-2 font-semibold text-center text-white transition duration-200 bg-purple-600 rounded-md hover:bg-purple-700"
                @click="signOut"
              >Sign out</button>
              <NuxtLink
                v-else
                to="/login"
                class="block px-3 py-2 mt-2 font-semibold text-center text-white transition duration-200 bg-purple-600 rounded-md hover:bg-purple-700"
              >Sign in</NuxtLink>
            </div>
          </div>
          <!-- end mobile menu -->
        </div>
      </div>
    </div>
  </header>
</template>
