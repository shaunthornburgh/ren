<script setup lang="ts">
import type { CalendarWithEvents, FollowState } from '~/types/api'

const route = useRoute()
const router = useRouter()
const { apiFetch } = useApi()
const { isAuthenticated } = useAuth()

const slug = computed(() => route.params.slug as string)

const CALENDAR_PLACEHOLDER =
  'https://images.unsplash.com/photo-1492684223066-81342ee5ff30?auto=format&fit=crop&w=1200&q=80'

const { data: calendar, pending, error } = await useAsyncData(
  () => `calendar-${slug.value}`,
  () => apiFetch<CalendarWithEvents>(`/calendars/${slug.value}`),
  { server: false, watch: [slug] },
)

const image = computed(
  () => calendar.value?.image_url || CALENDAR_PLACEHOLDER,
)

const busy = ref(false)
const followError = ref('')

async function toggleFollow() {
  if (!calendar.value) return
  if (!isAuthenticated.value) {
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return
  }

  followError.value = ''
  busy.value = true
  const wasFollowing = calendar.value.is_following
  try {
    const res = await apiFetch<FollowState>(
      `/calendars/${calendar.value.id}/follow`,
      { method: wasFollowing ? 'DELETE' : 'POST' },
    )
    calendar.value.is_following = res.following
    calendar.value.follower_count = res.follower_count
  } catch (e: any) {
    followError.value =
      e?.data?.detail?.toString() || 'Could not update follow. Try again.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section>
    <div class="container max-w-screen-xl px-4 py-6 mx-auto md:py-12">
      <div v-if="pending" class="text-gray-500">Loading calendar…</div>

      <div v-else-if="error || !calendar" class="py-20 text-center">
        <p class="text-xl font-semibold">Calendar not found</p>
        <NuxtLink to="/events" class="inline-block mt-4 text-purple-600 hover:text-purple-700">
          ← Browse events
        </NuxtLink>
      </div>

      <div v-else>
        <!-- hero -->
        <div class="overflow-hidden rounded-2xl">
          <img :src="image" :alt="calendar.name" class="object-cover w-full h-48 sm:h-64 md:h-80" />
        </div>

        <div class="flex flex-col gap-5 mt-8 sm:flex-row sm:items-start sm:justify-between">
          <div class="space-y-3">
            <div class="flex items-center gap-3">
              <h1 class="text-3xl font-bold sm:text-4xl">{{ calendar.name }}</h1>
              <span
                v-if="!calendar.is_public"
                class="px-3 py-1 text-xs font-semibold uppercase rounded-full bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-300"
              >Private</span>
            </div>
            <p v-if="calendar.description" class="max-w-2xl text-gray-600 dark:text-gray-400">
              {{ calendar.description }}
            </p>
            <p class="text-sm text-gray-400">
              {{ calendar.follower_count }}
              {{ calendar.follower_count === 1 ? 'follower' : 'followers' }}
            </p>
          </div>

          <!-- follow button -->
          <div class="shrink-0">
            <button
              type="button"
              class="px-6 py-3 font-semibold transition duration-200 rounded-full disabled:opacity-50"
              :class="calendar.is_following
                ? 'border text-gray-700 hover:bg-gray-100 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800'
                : 'text-white bg-purple-600 hover:bg-purple-700'"
              :disabled="busy"
              @click="toggleFollow"
            >
              <span v-if="busy">…</span>
              <span v-else-if="!isAuthenticated">Follow</span>
              <span v-else-if="calendar.is_following">Following ✓</span>
              <span v-else>Follow</span>
            </button>
          </div>
        </div>

        <p v-if="followError" class="mt-3 text-sm text-red-500">{{ followError }}</p>

        <!-- upcoming events -->
        <h2 class="mt-12 text-2xl font-bold">Upcoming events</h2>

        <div v-if="!calendar.upcoming_events.length" class="py-16 mt-6 text-center border rounded-2xl dark:border-gray-800">
          <p class="text-lg font-semibold">No upcoming events</p>
          <p class="mt-2 text-gray-500">Follow to be notified when new events are published.</p>
        </div>

        <div v-else class="grid gap-5 mt-6 sm:grid-cols-2 lg:grid-cols-4">
          <EventCard v-for="event in calendar.upcoming_events" :key="event.id" :event="event" />
        </div>
      </div>
    </div>
  </section>
</template>
