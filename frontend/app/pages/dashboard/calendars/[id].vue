<script setup lang="ts">
import type {
  CalendarFollower,
  CalendarRead,
  CalendarUpdate,
} from '~/types/api'

definePageMeta({ middleware: 'organizer' })

const route = useRoute()
const { apiFetch } = useApi()
const { formatDate } = useFormat()

const calendarId = Number(route.params.id)

const { data, pending, error } = await useAsyncData(
  `dashboard-calendar-${calendarId}`,
  async () => {
    const [calendar, followers] = await Promise.all([
      apiFetch<CalendarRead[]>('/calendars/me').then(
        (list) => list.find((c) => c.id === calendarId) ?? null,
      ),
      apiFetch<CalendarFollower[]>(`/calendars/${calendarId}/followers`),
    ])
    return { calendar, followers }
  },
  { server: false },
)

const submitting = ref(false)
const errorMsg = ref('')
const saved = ref(false)

async function updateCalendar(payload: CalendarUpdate) {
  errorMsg.value = ''
  saved.value = false
  submitting.value = true
  try {
    const updated = await apiFetch<CalendarRead>(`/calendars/${calendarId}`, {
      method: 'PUT',
      body: payload,
    })
    if (data.value) data.value.calendar = updated
    saved.value = true
  } catch (e: any) {
    errorMsg.value =
      e?.data?.detail?.toString() || 'Could not save changes. Please try again.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section>
    <div class="container max-w-3xl px-4 py-6 mx-auto md:py-10 lg:py-12">
      <NuxtLink to="/dashboard/calendars" class="text-sm text-purple-600 hover:text-purple-700">← Back to calendars</NuxtLink>

      <div v-if="pending" class="mt-6 text-gray-500">Loading calendar…</div>

      <div v-else-if="error || !data?.calendar" class="py-16 mt-6 text-center border rounded-2xl dark:border-gray-800">
        <p class="text-xl font-semibold">Calendar not found</p>
        <p class="mt-2 text-gray-500">It may have been removed, or you may not have access.</p>
      </div>

      <div v-else class="space-y-12">
        <!-- edit -->
        <div>
          <div class="flex items-center justify-between mt-3">
            <h1 class="text-3xl font-bold">Edit calendar</h1>
            <NuxtLink :to="`/calendar/${data.calendar.slug}`" class="text-sm text-purple-600 hover:text-purple-700">View public page →</NuxtLink>
          </div>

          <p v-if="saved" class="p-3 mt-4 text-sm text-green-700 rounded-lg bg-green-100 dark:bg-green-900 dark:text-green-300">
            Changes saved.
          </p>

          <div class="mt-6">
            <CalendarForm
              :calendar="data.calendar"
              :submitting="submitting"
              :error="errorMsg"
              submit-label="Save changes"
              @submit="updateCalendar"
            />
          </div>
        </div>

        <!-- followers -->
        <div class="pt-10 border-t dark:border-gray-800">
          <h2 class="text-2xl font-bold">
            Followers
            <span class="text-gray-400">({{ data.followers.length }})</span>
          </h2>

          <div v-if="!data.followers.length" class="py-10 mt-6 text-center border rounded-2xl dark:border-gray-800">
            <p class="text-gray-500">No followers yet.</p>
          </div>

          <ul v-else class="mt-6 divide-y dark:divide-gray-800">
            <li
              v-for="f in data.followers"
              :key="f.user_id"
              class="flex items-center justify-between py-3"
            >
              <div>
                <div class="font-medium">{{ f.full_name || f.email }}</div>
                <div v-if="f.full_name" class="text-sm text-gray-400">{{ f.email }}</div>
              </div>
              <div class="text-sm text-gray-400">Since {{ formatDate(f.followed_at) }}</div>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </section>
</template>
