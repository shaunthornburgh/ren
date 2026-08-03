<script setup lang="ts">
import type { CalendarCreate, CalendarRead } from '~/types/api'

definePageMeta({ middleware: 'organizer' })

const { apiFetch } = useApi()
const router = useRouter()

const submitting = ref(false)
const errorMsg = ref('')

async function createCalendar(payload: CalendarCreate) {
  errorMsg.value = ''
  submitting.value = true
  try {
    const calendar = await apiFetch<CalendarRead>('/calendars', {
      method: 'POST',
      body: payload,
    })
    router.push(`/dashboard/calendars/${calendar.id}`)
  } catch (e: any) {
    errorMsg.value =
      e?.data?.detail?.toString() ||
      'Could not create the calendar. Please try again.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section>
    <div class="container max-w-3xl px-4 py-6 mx-auto md:py-10 lg:py-12">
      <NuxtLink to="/dashboard/calendars" class="text-sm text-purple-600 hover:text-purple-700">← Back to calendars</NuxtLink>
      <h1 class="mt-3 text-3xl font-bold">Create calendar</h1>
      <p class="mt-1 text-gray-500 dark:text-gray-400">
        Followers get notified whenever you publish a new event here.
      </p>

      <div class="mt-8">
        <CalendarForm
          :submitting="submitting"
          :error="errorMsg"
          submit-label="Create calendar"
          @submit="createCalendar"
        />
      </div>
    </div>
  </section>
</template>
