<script setup lang="ts">
import type { EventRead } from '~/types/api'

const { apiFetch } = useApi()
const router = useRouter()

const search = ref('')

const { data: events, pending } = await useAsyncData(
  'home-events',
  () => apiFetch<EventRead[]>('/events', { params: { limit: 8 } }),
  { server: false, default: () => [] as EventRead[] },
)

function onSearch() {
  router.push({ path: '/events', query: search.value ? { q: search.value } : {} })
}

const features = [
  {
    title: 'Find an event',
    text: 'Browse concerts, festivals, conferences and more happening near you.',
    icon: '<svg xmlns="http://www.w3.org/2000/svg" class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>',
  },
  {
    title: 'Pick your tickets',
    text: 'Choose from multiple ticket types and grab exactly the number you need.',
    icon: '<svg xmlns="http://www.w3.org/2000/svg" class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z" /></svg>',
  },
  {
    title: 'Secure checkout',
    text: 'Pay safely with card through our Stripe-powered checkout.',
    icon: '<svg xmlns="http://www.w3.org/2000/svg" class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>',
  },
  {
    title: 'Get your tickets',
    text: 'Your tickets appear instantly under My Tickets once payment succeeds.',
    icon: '<svg xmlns="http://www.w3.org/2000/svg" class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 13l4 4L19 7" /></svg>',
  },
]
</script>

<template>
  <div>
    <!-- hero -->
    <section class="bg-purple-50 dark:bg-gray-900 dark:border-b dark:border-gray-800">
      <div class="container max-w-screen-xl px-4 py-12 pt-6 mx-auto md:pt-0 md:py-20 lg:py-24">
        <div class="space-y-5">
          <h1 class="text-4xl font-bold bg-gradient-to-br from-purple-500 to-red-600 bg-clip-text text-transparent max-w-[820px] sm:text-7xl">
            Discover events and book tickets you'll love
          </h1>
          <p class="max-w-[440px] text-xl text-gray-600 dark:text-gray-300">
            From sold-out concerts to local meetups — find your next experience and
            book in seconds.
          </p>
        </div>
        <div class="mt-8 md:mt-16">
          <form class="relative" @submit.prevent="onSearch">
            <input
              v-model="search"
              type="text"
              placeholder="Search events..."
              class="w-full px-12 pr-16 h-[60px] border border-white rounded-full placeholder-gray-400 shadow focus:outline-none focus:ring-2 focus:border-purple-600 md:h-[80px] md:text-xl dark:bg-gray-800 dark:border-gray-800"
            />
            <span class="flex justify-center items-center w-7 h-[50px] absolute left-4 top-[5px] text-gray-400 md:h-[60px] md:top-[10px]">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </span>
            <button type="submit" aria-label="Search" class="flex justify-center items-center w-[50px] h-[50px] bg-purple-50 text-purple-600 rounded-full absolute top-[5px] right-[5px] md:w-[60px] md:h-[60px] md:top-[10px] md:right-[10px] dark:bg-gray-700 dark:text-gray-300">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </form>
        </div>
      </div>
    </section>

    <!-- upcoming events -->
    <section>
      <div class="container max-w-screen-xl px-4 py-6 mx-auto md:py-10 lg:py-12">
        <div class="flex items-center justify-between space-x-5">
          <div class="flex items-center space-x-5">
            <div class="flex w-2.5 h-2.5 relative">
              <span class="absolute inline-flex w-full h-full bg-purple-600 rounded-full animate-ping"></span>
              <span class="relative inline-flex w-full h-full bg-purple-600 rounded-full"></span>
            </div>
            <h2 class="text-2xl font-bold">Upcoming events</h2>
          </div>
          <NuxtLink to="/events" class="flex items-center space-x-2 text-purple-600 transition duration-200 hover:text-purple-700 dark:text-purple-400 dark:hover:text-gray-50">
            <span class="font-medium">View all events</span>
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </NuxtLink>
        </div>

        <div v-if="pending" class="mt-8 text-gray-500">Loading events…</div>
        <div v-else-if="!events.length" class="mt-8 text-gray-500">No events yet. Check back soon!</div>
        <div v-else class="grid gap-5 mt-8 sm:grid-cols-2 lg:grid-cols-4">
          <EventCard v-for="event in events" :key="event.id" :event="event" />
        </div>
      </div>
    </section>

    <!-- how it works -->
    <section>
      <div class="container max-w-screen-xl px-4 py-6 mx-auto md:py-10 lg:py-12">
        <h2 class="text-2xl font-bold">How it works</h2>
        <div class="grid gap-5 mt-8 sm:grid-cols-2 lg:grid-cols-4">
          <div
            v-for="feature in features"
            :key="feature.title"
            class="p-6 space-y-5 transition duration-200 transform bg-purple-50 rounded-2xl hover:scale-105 dark:bg-gray-800"
          >
            <div class="flex items-center justify-center text-purple-600 bg-white rounded-full shadow w-14 h-14 dark:bg-gray-700 dark:text-gray-300">
              <span v-html="feature.icon"></span>
            </div>
            <div class="space-y-2.5">
              <h4 class="text-lg font-semibold">{{ feature.title }}</h4>
              <p class="text-gray-600 dark:text-gray-400">{{ feature.text }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
