<script setup lang="ts">
import type { EventRead } from '~/types/api'

const { apiFetch } = useApi()
const route = useRoute()

const search = ref((route.query.q as string) || '')
const tab = ref<'all' | 'upcoming' | 'past'>('all')

const { data: events, pending } = await useAsyncData(
  'events-list',
  () => apiFetch<EventRead[]>('/events', { params: { limit: 100 } }),
  { server: false, default: () => [] as EventRead[] },
)

const now = () => new Date()

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  return events.value.filter((e) => {
    const matchesText =
      !q ||
      e.title.toLowerCase().includes(q) ||
      (e.location ?? '').toLowerCase().includes(q)
    const start = new Date(e.start_datetime)
    const matchesTab =
      tab.value === 'all' ||
      (tab.value === 'upcoming' && start >= now()) ||
      (tab.value === 'past' && start < now())
    return matchesText && matchesTab
  })
})

const tabs = [
  { key: 'all', label: 'All events' },
  { key: 'upcoming', label: 'Upcoming' },
  { key: 'past', label: 'Past' },
] as const
</script>

<template>
  <div>
    <!-- search hero -->
    <section class="bg-purple-50 dark:bg-gray-900 dark:border-b dark:border-gray-800">
      <div class="container max-w-screen-xl px-4 pt-6 py-12 mx-auto">
        <form class="relative" @submit.prevent>
          <input
            v-model="search"
            type="text"
            placeholder="Search events by name or venue..."
            class="w-full px-12 pr-16 h-[60px] border border-white rounded-full placeholder-gray-400 shadow focus:outline-none focus:ring-2 focus:border-purple-600 md:h-[80px] md:text-xl dark:bg-gray-800 dark:border-gray-800"
          />
          <span class="flex justify-center items-center w-7 h-[50px] absolute left-4 top-[5px] text-gray-400 md:h-[60px] md:top-[10px]">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </span>
        </form>
      </div>
    </section>

    <!-- listing -->
    <section>
      <div class="container max-w-screen-xl px-4 pt-12 py-6 mx-auto md:py-10 lg:py-12">
        <h1 class="text-3xl font-bold bg-gradient-to-br from-purple-500 to-red-600 bg-clip-text text-transparent sm:text-5xl">
          Explore events
        </h1>

        <div class="flex flex-nowrap mt-12 space-x-2.5 overflow-x-scroll no-scrollbar">
          <button
            v-for="t in tabs"
            :key="t.key"
            type="button"
            class="flex flex-none items-center px-5 py-2.5 rounded-full bg-purple-50 space-x-3 font-semibold transition duration-200 hover:bg-purple-100 dark:bg-gray-800 dark:hover:bg-gray-700"
            :class="{ 'text-purple-600 bg-purple-100 dark:text-purple-400': tab === t.key }"
            @click="tab = t.key"
          >
            <span
              v-if="t.key === 'upcoming'"
              class="flex w-2.5 h-2.5 relative"
            >
              <span class="absolute inline-flex w-full h-full bg-purple-600 rounded-full animate-ping"></span>
              <span class="relative inline-flex w-full h-full bg-purple-600 rounded-full"></span>
            </span>
            <span>{{ t.label }}</span>
          </button>
        </div>

        <div v-if="pending" class="mt-8 text-gray-500">Loading events…</div>
        <div v-else-if="!filtered.length" class="mt-8 text-gray-500">
          No events match your search.
        </div>
        <div v-else class="grid gap-5 mt-8 sm:grid-cols-2 lg:grid-cols-4">
          <EventCard v-for="event in filtered" :key="event.id" :event="event" />
        </div>
      </div>
    </section>
  </div>
</template>
