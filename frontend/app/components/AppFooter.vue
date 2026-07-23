<script setup lang="ts">
const year = 2026

const columns = [
  {
    title: 'Browse',
    links: [
      { label: 'All events', to: '/events' },
      { label: 'My tickets', to: '/my-tickets' },
    ],
  },
  {
    title: 'Resources',
    links: [
      { label: 'Help center', to: '#' },
      { label: 'FAQ', to: '#' },
      { label: 'Contact support', to: '#' },
    ],
  },
  {
    title: 'Company',
    links: [
      { label: 'About', to: '#' },
      { label: 'Careers', to: '#' },
      { label: 'Terms of Service', to: '#' },
      { label: 'Privacy', to: '#' },
    ],
  },
]
</script>

<template>
  <footer>
    <div class="container max-w-screen-xl px-4 pt-6 mx-auto mb-8 md:pt-10 lg:pt-12">
      <div class="p-6 space-y-8 border rounded-2xl sm:p-12 dark:border-gray-800">
        <div class="grid gap-6 sm:gap-10 md:grid-cols-3">
          <div class="space-y-5">
            <NuxtLink to="/" class="flex items-center space-x-3 text-xl font-bold">
              <span class="flex items-center justify-center w-8 h-8 text-white bg-purple-600 rounded-lg">
                <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z" /></svg>
              </span>
              <span>ren</span>
            </NuxtLink>
            <p class="max-w-sm text-gray-400 dark:text-gray-600">
              Discover events and book tickets in seconds — concerts, festivals,
              conferences and more. Your next great night out starts here.
            </p>
          </div>
          <div class="grid gap-6 sm:gap-10 sm:grid-cols-3 md:col-span-2">
            <div v-for="col in columns" :key="col.title" class="space-y-4">
              <div class="space-y-2.5">
                <h5 class="font-semibold">{{ col.title }}</h5>
                <div class="border-b border-gray-200 dark:border-gray-800"></div>
              </div>
              <ul class="space-y-3 text-gray-600 dark:text-gray-400">
                <li v-for="link in col.links" :key="link.label">
                  <NuxtLink :to="link.to" class="hover:text-gray-900 dark:hover:text-gray-50">{{ link.label }}</NuxtLink>
                </li>
              </ul>
            </div>
          </div>
        </div>
        <div class="border-b border-gray-200 dark:border-gray-800"></div>
        <div class="flex flex-col items-start justify-between sm:flex-row">
          <p class="order-last text-sm text-gray-400 sm:order-first">© {{ year }} Ren, Inc</p>
          <div class="flex items-center mb-5 space-x-3 sm:mb-0">
            <a href="#" aria-label="Facebook" class="flex items-center justify-center w-8 h-8 transition duration-200 bg-gray-100 rounded-lg hover:bg-purple-100 dark:bg-gray-800 dark:hover:bg-gray-700">
              <i class="text-2xl text-gray-600 transition duration-200 bx bxl-facebook-square hover:text-purple-600 dark:text-gray-400 dark:hover:text-gray-50"></i>
            </a>
            <a href="#" aria-label="Twitter" class="flex items-center justify-center w-8 h-8 transition duration-200 bg-gray-100 rounded-lg hover:bg-purple-100 dark:bg-gray-800 dark:hover:bg-gray-700">
              <i class="text-2xl text-gray-600 transition duration-200 bx bxl-twitter hover:text-purple-600 dark:text-gray-400 dark:hover:text-gray-50"></i>
            </a>
            <a href="#" aria-label="Instagram" class="flex items-center justify-center w-8 h-8 transition duration-200 bg-gray-100 rounded-lg hover:bg-purple-100 dark:bg-gray-800 dark:hover:bg-gray-700">
              <i class="text-2xl text-gray-600 transition duration-200 bx bxl-instagram-alt hover:text-purple-600 dark:text-gray-400 dark:hover:text-gray-50"></i>
            </a>
          </div>
        </div>
      </div>
    </div>
  </footer>
</template>
