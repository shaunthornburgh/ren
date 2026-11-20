<script setup lang="ts">
import type { AdminEventRead, EventRead, EventStatus } from '~/types/api'

definePageMeta({ middleware: 'admin' })

const PAGE_SIZE = 50
const STATUSES: EventStatus[] = ['draft', 'published', 'cancelled']

const { apiFetch } = useApi()
const { formatDateTime } = useFormat()

// Filters: `search` is the input; `appliedQ` changes only on submit.
const search = ref('')
const appliedQ = ref('')
const statusFilter = ref<EventStatus | ''>('')

function fetchPage(skip: number) {
  return apiFetch<AdminEventRead[]>('/admin/events', {
    query: {
      q: appliedQ.value || undefined,
      status: statusFilter.value || undefined,
      skip,
      limit: PAGE_SIZE,
    },
  })
}

// True while the last page fetched was full, so another may exist.
const hasMore = ref(false)

const { data: events, pending, error, refresh } = await useAsyncData(
  'admin-events',
  async () => {
    const rows = await fetchPage(0)
    hasMore.value = rows.length === PAGE_SIZE
    return rows
  },
  { server: false, default: () => [] as AdminEventRead[], watch: [appliedQ, statusFilter] },
)

const loadingMore = ref(false)
const loadMoreError = ref('')
async function loadMore() {
  loadingMore.value = true
  loadMoreError.value = ''
  try {
    const next = await fetchPage(events.value.length)
    events.value = [...events.value, ...next]
    hasMore.value = next.length === PAGE_SIZE
  } catch {
    loadMoreError.value = 'Could not load more events. Please try again.'
  } finally {
    loadingMore.value = false
  }
}

function applySearch() {
  appliedQ.value = search.value.trim()
}

// Per-row save state.
const saving = reactive<Record<number, boolean>>({})
const rowErrors = reactive<Record<number, string>>({})
const announcement = ref('')

async function onStatusChange(ev: AdminEventRead, event: Event) {
  const select = event.target as HTMLSelectElement
  const status = select.value as EventStatus
  // Keep the select showing the saved value until the API confirms.
  select.value = ev.status
  if (status === ev.status) return
  if (status === 'cancelled' && !confirm(`Cancel “${ev.title}”? It will be hidden from public listings.`)) {
    return
  }

  saving[ev.id] = true
  delete rowErrors[ev.id]
  announcement.value = ''
  try {
    const updated = await apiFetch<EventRead>(`/events/${ev.id}`, {
      method: 'PUT',
      body: { status },
    })
    Object.assign(ev, updated)
    announcement.value = `“${ev.title}” is now ${ev.status}.`
  } catch (e: any) {
    rowErrors[ev.id] = e?.data?.detail?.toString() || 'Could not change the status. Please try again.'
  } finally {
    saving[ev.id] = false
    select.value = ev.status
  }
}

const statusStyles: Record<EventStatus, string> = {
  published: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  draft: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
  cancelled: 'bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
}
</script>

<template>
  <section>
    <div class="container max-w-screen-xl px-4 py-6 mx-auto md:py-10 lg:py-12">
      <div class="space-y-1">
        <h1 class="text-3xl font-bold bg-gradient-to-br from-purple-500 to-red-600 bg-clip-text text-transparent sm:text-4xl">
          Admin
        </h1>
        <p class="text-gray-500 dark:text-gray-400">Manage users, roles, and events across the platform.</p>
      </div>

      <AdminTabs />

      <!-- filters -->
      <form class="flex flex-col gap-3 mt-8 sm:flex-row sm:items-end" role="search" @submit.prevent="applySearch">
        <div class="flex-1">
          <label for="event-search" class="block mb-1 text-sm font-medium text-gray-600 dark:text-gray-300">Search events</label>
          <input
            id="event-search"
            v-model="search"
            type="search"
            maxlength="100"
            placeholder="Event title"
            class="w-full px-4 py-2.5 border rounded-full dark:bg-gray-800 dark:border-gray-700 focus:outline-none focus:ring-2 focus:ring-purple-600"
          />
        </div>
        <div>
          <label for="status-filter" class="block mb-1 text-sm font-medium text-gray-600 dark:text-gray-300">Status</label>
          <select
            id="status-filter"
            v-model="statusFilter"
            class="w-full px-4 py-2.5 border rounded-full sm:w-44 dark:bg-gray-800 dark:border-gray-700 focus:outline-none focus:ring-2 focus:ring-purple-600"
          >
            <option value="">All statuses</option>
            <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
          </select>
        </div>
        <button
          type="submit"
          class="inline-flex items-center justify-center gap-2 px-5 py-2.5 font-semibold text-white transition duration-200 bg-purple-600 rounded-full hover:bg-purple-700"
        ><i class="bx bx-search" aria-hidden="true"></i> Search</button>
      </form>

      <p class="sr-only" aria-live="polite">{{ announcement }}</p>

      <div v-if="pending" class="mt-8 text-gray-500">Loading events…</div>

      <div v-else-if="error" class="py-12 mt-8 text-center border rounded-2xl dark:border-gray-800" role="alert">
        <p class="text-xl font-semibold">Could not load events</p>
        <p class="mt-2 text-gray-500">{{ (error as any)?.data?.detail || 'Something went wrong. Please try again.' }}</p>
        <button
          type="button"
          class="px-5 py-2 mt-6 font-semibold text-white transition duration-200 bg-purple-600 rounded-full hover:bg-purple-700"
          @click="refresh()"
        >Retry</button>
      </div>

      <div v-else-if="!events.length" class="py-16 mt-8 text-center border rounded-2xl dark:border-gray-800">
        <p class="text-xl font-semibold">No events match</p>
        <p class="mt-2 text-gray-500">Try a different search or status filter.</p>
      </div>

      <ul v-else class="mt-8 space-y-4">
        <li
          v-for="ev in events"
          :key="ev.id"
          class="p-4 border rounded-2xl dark:border-gray-800 sm:p-5"
        >
          <div class="flex flex-col gap-4 lg:flex-row lg:items-center">
            <div class="flex-1 min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <h2 class="font-semibold truncate">{{ ev.title }}</h2>
                <span class="px-3 py-0.5 text-xs font-semibold uppercase rounded-full" :class="statusStyles[ev.status]">{{ ev.status }}</span>
              </div>
              <div class="mt-1 text-sm text-gray-400 truncate">
                {{ formatDateTime(ev.start_datetime) }} · by
                <NuxtLink :to="`/users/${ev.organizer_id}`" class="hover:text-purple-600">{{ ev.organizer_name }}</NuxtLink>
              </div>
              <p v-if="rowErrors[ev.id]" class="mt-2 text-sm text-red-600 dark:text-red-400" role="alert">{{ rowErrors[ev.id] }}</p>
            </div>

            <div class="flex flex-row flex-wrap gap-2 lg:w-96 lg:flex-nowrap">
              <select
                :value="ev.status"
                :aria-label="`Status for ${ev.title}`"
                :disabled="saving[ev.id]"
                class="flex-1 px-4 py-2 text-sm border rounded-full dark:bg-gray-800 dark:border-gray-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-purple-600"
                @change="onStatusChange(ev, $event)"
              >
                <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
              </select>
              <NuxtLink
                :to="`/dashboard/events/${ev.id}`"
                class="px-4 py-2 text-sm font-semibold text-center text-white transition duration-200 bg-purple-600 rounded-full hover:bg-purple-700"
              >Manage</NuxtLink>
              <NuxtLink
                :to="`/events/${ev.id}`"
                class="px-4 py-2 text-sm font-semibold text-center transition duration-200 border rounded-full hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-gray-800"
              >View</NuxtLink>
            </div>
          </div>
        </li>
      </ul>

      <div v-if="!pending && !error && hasMore" class="mt-6 text-center">
        <button
          type="button"
          :disabled="loadingMore"
          class="px-5 py-2 font-semibold transition duration-200 border rounded-full hover:bg-gray-100 disabled:opacity-50 dark:border-gray-700 dark:hover:bg-gray-800"
          @click="loadMore"
        >{{ loadingMore ? 'Loading…' : 'Load more' }}</button>
        <p v-if="loadMoreError" class="mt-2 text-sm text-red-600 dark:text-red-400" role="alert">{{ loadMoreError }}</p>
      </div>
    </div>
  </section>
</template>
