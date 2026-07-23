<script setup lang="ts">
import type { EventCreate, EventRead } from '~/types/api'

definePageMeta({ middleware: 'organizer' })

const { apiFetch } = useApi()
const router = useRouter()

const submitting = ref(false)
const errorMsg = ref('')

async function createEvent(payload: EventCreate) {
  errorMsg.value = ''
  submitting.value = true
  try {
    const event = await apiFetch<EventRead>('/events', {
      method: 'POST',
      body: payload,
    })
    // Go to the manage page so the organizer can add ticket types next.
    router.push(`/dashboard/events/${event.id}`)
  } catch (e: any) {
    errorMsg.value =
      e?.data?.detail?.toString() ||
      'Could not create the event. Please check the details and try again.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section>
    <div class="container max-w-3xl px-4 py-6 mx-auto md:py-10 lg:py-12">
      <NuxtLink to="/dashboard" class="text-sm text-purple-600 hover:text-purple-700">← Back to dashboard</NuxtLink>
      <h1 class="mt-3 text-3xl font-bold">Create event</h1>
      <p class="mt-1 text-gray-500 dark:text-gray-400">
        Set up the details. You can add ticket types after saving.
      </p>

      <div class="mt-8">
        <OrganizerEventForm
          :submitting="submitting"
          :error="errorMsg"
          submit-label="Create event"
          @submit="createEvent"
        />
      </div>
    </div>
  </section>
</template>
