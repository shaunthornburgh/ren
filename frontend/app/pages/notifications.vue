<script setup lang="ts">
import type { NotificationRead } from '~/types/api'

definePageMeta({ middleware: 'auth' })

const { apiFetch } = useApi()
const { timeAgo } = useFormat()
const router = useRouter()

const PAGE_SIZE = 20

const items = ref<NotificationRead[]>([])
const unread = ref(0)
const loading = ref(true)
const loadingMore = ref(false)
const done = ref(false)

async function fetchUnread() {
  try {
    const res = await apiFetch<{ unread: number }>('/notifications/unread-count')
    unread.value = res.unread
  } catch {
    // ignore
  }
}

async function loadMore() {
  if (loadingMore.value || done.value) return
  loadingMore.value = true
  try {
    const batch = await apiFetch<NotificationRead[]>('/notifications', {
      params: { skip: items.value.length, limit: PAGE_SIZE },
    })
    items.value.push(...batch)
    if (batch.length < PAGE_SIZE) done.value = true
  } catch {
    done.value = true
  } finally {
    loadingMore.value = false
    loading.value = false
  }
}

async function openNotification(n: NotificationRead) {
  if (!n.is_read) {
    n.is_read = true
    unread.value = Math.max(0, unread.value - 1)
    try {
      await apiFetch(`/notifications/${n.id}/read`, { method: 'POST' })
    } catch {
      // Non-fatal.
    }
  }
  if (n.event_id) router.push(`/events/${n.event_id}`)
}

async function markAllRead() {
  if (!unread.value) return
  items.value = items.value.map((n) => ({ ...n, is_read: true }))
  unread.value = 0
  try {
    await apiFetch('/notifications/read-all', { method: 'POST' })
  } catch {
    // Non-fatal.
  }
}

onMounted(loadMore)
onMounted(fetchUnread)
</script>

<template>
  <section>
    <!-- cover -->
    <img
      src="https://images.unsplash.com/photo-1492684223066-81342ee5ff30?auto=format&fit=crop&w=1650&q=80"
      alt=""
      class="object-cover w-full h-48 md:h-60"
    />

    <div class="container max-w-screen-xl px-4 pb-6 mx-auto md:pb-12">
      <!-- header -->
      <div class="flex flex-col gap-4 mt-8 sm:flex-row sm:items-center sm:justify-between">
        <div class="space-y-2">
          <h1 class="text-3xl font-bold">Notifications</h1>
          <p class="text-gray-500 dark:text-gray-400">
            <span v-if="unread">{{ unread }} unread</span>
            <span v-else>You're all caught up.</span>
          </p>
        </div>
        <button
          v-if="unread > 0"
          type="button"
          class="self-start px-5 py-2.5 font-semibold text-purple-600 transition duration-200 rounded-full bg-purple-50 hover:bg-purple-700 hover:text-white dark:bg-gray-800 dark:text-purple-400 dark:hover:bg-gray-700 dark:hover:text-gray-50"
          @click="markAllRead"
        >Mark all as read</button>
      </div>

      <!-- states -->
      <div v-if="loading" class="mt-8 text-gray-500">Loading notifications…</div>

      <div v-else-if="!items.length" class="py-16 mt-8 text-center border rounded-2xl dark:border-gray-800">
        <p class="text-xl font-semibold">No notifications yet</p>
        <p class="mt-2 text-gray-500">
          Follow a calendar to hear when new events are published.
        </p>
        <NuxtLink to="/events" class="inline-block mt-6 font-semibold text-purple-600 hover:text-purple-700">
          Browse events →
        </NuxtLink>
      </div>

      <!-- list -->
      <ul v-else class="mt-8 space-y-3">
        <li v-for="n in items" :key="n.id">
          <button
            type="button"
            class="flex w-full gap-3 p-4 text-left transition duration-150 border rounded-2xl hover:shadow-md dark:border-gray-800"
            :class="{ 'bg-purple-50/60 dark:bg-gray-800/50 border-purple-200 dark:border-gray-700': !n.is_read }"
            @click="openNotification(n)"
          >
            <span
              class="flex-shrink-0 w-2.5 h-2.5 mt-2 rounded-full"
              :class="n.is_read ? 'bg-transparent' : 'bg-purple-600 dark:bg-purple-400'"
            ></span>
            <span class="flex-1 min-w-0">
              <span class="flex items-center justify-between gap-3">
                <span class="font-semibold truncate" :class="{ 'text-gray-500': n.is_read }">{{ n.title }}</span>
                <span class="flex-shrink-0 text-xs text-gray-400">{{ timeAgo(n.created_at) }}</span>
              </span>
              <span v-if="n.message" class="block mt-0.5 text-sm text-gray-500">{{ n.message }}</span>
              <span v-if="n.event_id" class="inline-block mt-2 text-sm font-medium text-purple-600 dark:text-purple-400">
                View event →
              </span>
            </span>
          </button>
        </li>
      </ul>

      <!-- load more -->
      <div v-if="items.length && !done" class="mt-6 text-center">
        <button
          type="button"
          class="px-6 py-2.5 font-semibold transition duration-200 border rounded-full disabled:opacity-50 hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-gray-800"
          :disabled="loadingMore"
          @click="loadMore"
        >{{ loadingMore ? 'Loading…' : 'Load more' }}</button>
      </div>
    </div>
  </section>
</template>
