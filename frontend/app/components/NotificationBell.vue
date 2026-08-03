<script setup lang="ts">
import type { NotificationRead } from '~/types/api'

const { apiFetch } = useApi()
const { timeAgo } = useFormat()
const router = useRouter()

const open = ref(false)
const unread = ref(0)
const items = ref<NotificationRead[]>([])
const loading = ref(false)
const root = ref<HTMLElement | null>(null)

let pollTimer: ReturnType<typeof setInterval> | null = null

const badge = computed(() => (unread.value > 9 ? '9+' : String(unread.value)))

async function fetchUnread() {
  try {
    const res = await apiFetch<{ unread: number }>(
      '/notifications/unread-count',
    )
    unread.value = res.unread
  } catch {
    // Silently ignore — the bell just won't show a badge.
  }
}

async function fetchList() {
  loading.value = true
  try {
    // Just the recent few for the dropdown; the full list lives at /notifications.
    items.value = await apiFetch<NotificationRead[]>('/notifications', {
      params: { limit: 8 },
    })
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

function toggle() {
  open.value = !open.value
  if (open.value) fetchList()
}

function close() {
  open.value = false
}

async function openNotification(n: NotificationRead) {
  if (!n.is_read) {
    // Optimistic: mark read locally, then persist.
    n.is_read = true
    unread.value = Math.max(0, unread.value - 1)
    try {
      await apiFetch(`/notifications/${n.id}/read`, { method: 'POST' })
    } catch {
      // Non-fatal; the count re-syncs on the next poll.
    }
  }
  close()
  if (n.event_id) router.push(`/events/${n.event_id}`)
}

async function markAllRead() {
  if (!unread.value) return
  items.value = items.value.map((n) => ({ ...n, is_read: true }))
  unread.value = 0
  try {
    await apiFetch('/notifications/read-all', { method: 'POST' })
  } catch {
    // Non-fatal; re-syncs on next poll.
  }
}

function onDocClick(e: MouseEvent) {
  if (open.value && root.value && !root.value.contains(e.target as Node)) {
    close()
  }
}

onMounted(() => {
  fetchUnread()
  document.addEventListener('click', onDocClick)
  // Light polling so the badge stays roughly current.
  pollTimer = setInterval(fetchUnread, 60_000)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick)
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div ref="root" class="relative">
    <!-- bell button -->
    <button
      type="button"
      class="relative flex items-center justify-center w-10 h-10 transition duration-200 rounded-full hover:bg-purple-100 dark:hover:bg-gray-700"
      aria-label="Notifications"
      @click="toggle"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
      </svg>
      <span
        v-if="unread > 0"
        class="absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[11px] font-bold text-white bg-red-500 rounded-full"
      >{{ badge }}</span>
    </button>

    <!-- dropdown -->
    <div
      v-if="open"
      class="absolute right-0 z-30 mt-2 overflow-hidden bg-white shadow-xl w-80 rounded-2xl dark:bg-gray-800 ring-1 ring-black/5 dark:ring-white/10"
    >
      <!-- header -->
      <div class="flex items-center justify-between px-4 py-3 border-b dark:border-gray-700">
        <span class="font-semibold">Notifications</span>
        <button
          v-if="unread > 0"
          type="button"
          class="text-sm font-medium text-purple-600 transition duration-200 hover:text-purple-700 dark:text-purple-400"
          @click="markAllRead"
        >Mark all as read</button>
      </div>

      <!-- list -->
      <div class="max-h-96 overflow-y-auto">
        <p v-if="loading" class="px-4 py-6 text-sm text-center text-gray-500">Loading…</p>

        <p v-else-if="!items.length" class="px-4 py-8 text-sm text-center text-gray-500">
          You're all caught up 🎉
        </p>

        <ul v-else class="divide-y dark:divide-gray-700">
          <li v-for="n in items" :key="n.id">
            <button
              type="button"
              class="flex w-full gap-3 px-4 py-3 text-left transition duration-150 hover:bg-purple-50 dark:hover:bg-gray-700/50"
              :class="{ 'bg-purple-50/60 dark:bg-gray-700/30': !n.is_read }"
              @click="openNotification(n)"
            >
              <!-- unread dot -->
              <span
                class="flex-shrink-0 w-2 h-2 mt-2 rounded-full"
                :class="n.is_read ? 'bg-transparent' : 'bg-purple-600 dark:bg-purple-400'"
              ></span>

              <span class="flex-1 min-w-0">
                <span class="block text-sm font-semibold truncate" :class="{ 'text-gray-500': n.is_read }">
                  {{ n.title }}
                </span>
                <span v-if="n.message" class="block text-sm text-gray-500 line-clamp-2">{{ n.message }}</span>
                <span class="block mt-1 text-xs text-gray-400">{{ timeAgo(n.created_at) }}</span>
              </span>
            </button>
          </li>
        </ul>
      </div>

      <!-- footer -->
      <div class="border-t dark:border-gray-700">
        <NuxtLink
          to="/notifications"
          class="block px-4 py-3 text-sm font-medium text-center text-purple-600 transition duration-200 hover:bg-purple-50 dark:text-purple-400 dark:hover:bg-gray-700/50"
          @click="close"
        >View all</NuxtLink>
      </div>
    </div>
  </div>
</template>
