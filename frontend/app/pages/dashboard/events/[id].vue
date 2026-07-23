<script setup lang="ts">
import type { EventCreate, EventRead } from '~/types/api'

definePageMeta({ middleware: 'organizer' })

const route = useRoute()
const { apiFetch } = useApi()

const eventId = Number(route.params.id)

const { data: event, pending, error } = await useAsyncData(
  `dashboard-event-${eventId}`,
  () => apiFetch<EventRead>(`/events/${eventId}`),
  { server: false },
)

const submitting = ref(false)
const errorMsg = ref('')
const savedAt = ref(false)

async function updateEvent(payload: EventCreate) {
  errorMsg.value = ''
  savedAt.value = false
  submitting.value = true
  try {
    event.value = await apiFetch<EventRead>(`/events/${eventId}`, {
      method: 'PUT',
      body: payload,
    })
    savedAt.value = true
  } catch (e: any) {
    errorMsg.value =
      e?.data?.detail?.toString() ||
      'Could not save changes. Please try again.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section>
    <div class="container max-w-3xl px-4 py-6 mx-auto md:py-10 lg:py-12">
      <NuxtLink to="/dashboard" class="text-sm text-purple-600 hover:text-purple-700">← Back to dashboard</NuxtLink>

      <div v-if="pending" class="mt-6 text-gray-500">Loading event…</div>

      <div v-else-if="error || !event" class="py-16 mt-6 text-center border rounded-2xl dark:border-gray-800">
        <p class="text-xl font-semibold">Event not found</p>
        <p class="mt-2 text-gray-500">It may have been removed, or you may not have access.</p>
      </div>

      <div v-else class="space-y-12">
        <!-- edit event -->
        <div>
          <div class="flex items-center justify-between mt-3">
            <h1 class="text-3xl font-bold">Edit event</h1>
            <NuxtLink :to="`/events/${event.id}`" class="text-sm text-purple-600 hover:text-purple-700">View public page →</NuxtLink>
          </div>

          <p v-if="savedAt" class="p-3 mt-4 text-sm text-green-700 rounded-lg bg-green-100 dark:bg-green-900 dark:text-green-300">
            Changes saved.
          </p>

          <div class="mt-6">
            <OrganizerEventForm
              :event="event"
              :submitting="submitting"
              :error="errorMsg"
              submit-label="Save changes"
              @submit="updateEvent"
            />
          </div>
        </div>

        <!-- manage ticket types -->
        <div class="pt-10 border-t dark:border-gray-800">
          <TicketTypeManager :event-id="eventId" />
        </div>
      </div>
    </div>
  </section>
</template>
