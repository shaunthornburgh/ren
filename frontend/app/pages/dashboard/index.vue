<script setup lang="ts">
import type { OrganizerEventRead } from '~/types/api'

definePageMeta({ middleware: 'organizer' })

const { apiFetch } = useApi()
const { formatDateTime, formatPrice } = useFormat()

const { data: events, pending } = await useAsyncData(
  'organizer-events',
  () => apiFetch<OrganizerEventRead[]>('/events/me'),
  { server: false, default: () => [] as OrganizerEventRead[] },
)

const EVENT_PLACEHOLDER =
  'https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?auto=format&fit=crop&w=400&q=80'

const statusStyles: Record<string, string> = {
  published: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  draft: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
  cancelled: 'bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
}

const totals = computed(() => {
  const list = events.value
  return {
    events: list.length,
    sold: list.reduce((a, e) => a + e.tickets_sold, 0),
    revenue: list.reduce((a, e) => a + parseFloat(e.revenue), 0),
  }
})
</script>

<template>
  <section>
    <div class="container max-w-screen-xl px-4 py-6 mx-auto md:py-10 lg:py-12">
      <!-- header -->
      <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div class="space-y-1">
          <h1 class="text-3xl font-bold bg-gradient-to-br from-purple-500 to-red-600 bg-clip-text text-transparent sm:text-4xl">
            Organizer Dashboard
          </h1>
          <p class="text-gray-500 dark:text-gray-400">Manage your events and ticket sales.</p>
        </div>
        <NuxtLink
          to="/dashboard/events/new"
          class="inline-flex items-center px-5 py-2.5 font-semibold text-center text-white transition duration-200 bg-purple-600 rounded-full hover:bg-purple-700"
        >+ Create event</NuxtLink>
      </div>

      <!-- summary tiles -->
      <div class="grid gap-5 mt-8 sm:grid-cols-3">
        <div class="p-6 bg-purple-50 rounded-2xl dark:bg-gray-800">
          <div class="font-medium text-gray-500">Events</div>
          <div class="mt-1 text-3xl font-bold">{{ totals.events }}</div>
        </div>
        <div class="p-6 bg-purple-50 rounded-2xl dark:bg-gray-800">
          <div class="font-medium text-gray-500">Tickets sold</div>
          <div class="mt-1 text-3xl font-bold">{{ totals.sold }}</div>
        </div>
        <div class="p-6 bg-purple-50 rounded-2xl dark:bg-gray-800">
          <div class="font-medium text-gray-500">Total revenue</div>
          <div class="mt-1 text-3xl font-bold">{{ formatPrice(totals.revenue) }}</div>
        </div>
      </div>

      <!-- events list -->
      <h2 class="mt-12 text-2xl font-bold">Your events</h2>

      <div v-if="pending" class="mt-6 text-gray-500">Loading your events…</div>

      <div v-else-if="!events.length" class="py-16 mt-6 text-center border rounded-2xl dark:border-gray-800">
        <p class="text-xl font-semibold">No events yet</p>
        <p class="mt-2 text-gray-500">Create your first event to start selling tickets.</p>
        <NuxtLink
          to="/dashboard/events/new"
          class="inline-block px-5 py-2 mt-6 font-semibold text-white transition duration-200 bg-purple-600 rounded-full hover:bg-purple-700"
        >Create event</NuxtLink>
      </div>

      <div v-else class="mt-6 space-y-5">
        <div
          v-for="event in events"
          :key="event.id"
          class="p-4 transition duration-200 border rounded-2xl hover:shadow-lg dark:border-gray-800 sm:p-5"
        >
          <div class="flex flex-col gap-5 lg:flex-row lg:items-center">
            <!-- thumbnail -->
            <img
              :src="event.image_url || EVENT_PLACEHOLDER"
              :alt="event.title"
              class="object-cover w-full h-40 rounded-xl lg:w-48 lg:h-28"
            />

            <!-- info + stats -->
            <div class="flex-1 min-w-0 space-y-3">
              <div class="flex items-center gap-3">
                <h3 class="text-xl font-semibold truncate">{{ event.title }}</h3>
                <span
                  class="px-3 py-1 text-xs font-semibold uppercase rounded-full shrink-0"
                  :class="statusStyles[event.status]"
                >{{ event.status }}</span>
              </div>
              <div class="text-sm text-gray-400">{{ formatDateTime(event.start_datetime) }} · {{ event.location || 'Venue TBA' }}</div>

              <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div>
                  <div class="text-xs font-medium text-gray-500">Ticket types</div>
                  <div class="font-bold">{{ event.ticket_types_count }}</div>
                </div>
                <div>
                  <div class="text-xs font-medium text-gray-500">Sold</div>
                  <div class="font-bold">{{ event.tickets_sold }}</div>
                </div>
                <div>
                  <div class="text-xs font-medium text-gray-500">Remaining</div>
                  <div class="font-bold">{{ event.tickets_remaining }}</div>
                </div>
                <div>
                  <div class="text-xs font-medium text-gray-500">Revenue</div>
                  <div class="font-bold">{{ formatPrice(event.revenue) }}</div>
                </div>
              </div>
            </div>

            <!-- actions -->
            <div class="flex flex-row gap-2 lg:flex-col lg:w-40">
              <NuxtLink
                :to="`/dashboard/events/${event.id}`"
                class="flex-1 px-4 py-2 text-sm font-semibold text-center text-white transition duration-200 bg-purple-600 rounded-full hover:bg-purple-700"
              >Manage</NuxtLink>
              <NuxtLink
                :to="`/events/${event.id}`"
                class="flex-1 px-4 py-2 text-sm font-semibold text-center transition duration-200 border rounded-full hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-gray-800"
              >View</NuxtLink>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
