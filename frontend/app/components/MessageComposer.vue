<script setup lang="ts">
import type { EventMessageRead, GuestRead } from '~/types/api'

const props = defineProps<{ eventId: number }>()

const { apiFetch } = useApi()
const { formatDateTime } = useFormat()

const { data: messages, refresh } = await useAsyncData(
  `event-${props.eventId}-messages`,
  () => apiFetch<EventMessageRead[]>(`/events/${props.eventId}/messages`),
  { server: false, default: () => [] as EventMessageRead[] },
)

// Recipients = unique emails of guests with a paid order (matches the backend).
const { data: guests } = await useAsyncData(
  `event-${props.eventId}-guests-for-messages`,
  () => apiFetch<GuestRead[]>(`/events/${props.eventId}/guests`),
  { server: false, default: () => [] as GuestRead[] },
)

const recipientCount = computed(
  () =>
    new Set(
      guests.value.filter((g) => g.status === 'paid').map((g) => g.email),
    ).size,
)

const form = reactive({ subject: '', body: '' })
const sending = ref(false)
const error = ref('')
const notice = ref('')

const inputClass =
  'w-full h-11 px-3 border rounded-lg border-gray-200 focus:outline-none focus:ring-2 focus:border-purple-600 dark:bg-gray-900 dark:border-gray-700'

async function send() {
  error.value = ''
  notice.value = ''
  if (!form.subject.trim()) {
    error.value = 'Subject is required.'
    return
  }
  if (!form.body.trim()) {
    error.value = 'Message body is required.'
    return
  }

  sending.value = true
  try {
    const sent = await apiFetch<EventMessageRead>(
      `/events/${props.eventId}/messages`,
      { method: 'POST', body: { subject: form.subject.trim(), body: form.body.trim() } },
    )
    notice.value =
      sent.recipient_count > 0
        ? `Message sent to ${sent.recipient_count} guest${sent.recipient_count === 1 ? '' : 's'}.`
        : 'Message saved, but there are no paid guests to email yet.'
    form.subject = ''
    form.body = ''
    await refresh()
  } catch (e: any) {
    error.value =
      e?.data?.detail?.toString() || 'Could not send the message. Please try again.'
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <div class="space-y-8">
    <!-- compose -->
    <div class="space-y-4">
      <div>
        <h2 class="text-2xl font-bold">Message guests</h2>
        <p class="mt-1 text-sm text-gray-400">
          Emails all guests with a paid order for this event —
          <span class="font-medium text-gray-500 dark:text-gray-300">{{ recipientCount }} recipient{{ recipientCount === 1 ? '' : 's' }}</span>.
        </p>
      </div>

      <div class="p-5 space-y-4 border rounded-2xl bg-gray-50 dark:bg-gray-800/40 dark:border-gray-800">
        <div class="space-y-1.5">
          <label class="text-sm font-medium">Subject</label>
          <input v-model="form.subject" type="text" placeholder="e.g. Important update about the event" :class="inputClass" />
        </div>
        <div class="space-y-1.5">
          <label class="text-sm font-medium">Message</label>
          <textarea v-model="form.body" rows="6" placeholder="Write your message to guests…" class="w-full px-3 py-2 border rounded-lg border-gray-200 focus:outline-none focus:ring-2 focus:border-purple-600 dark:bg-gray-900 dark:border-gray-700"></textarea>
        </div>

        <p v-if="error" class="text-sm text-red-500">{{ error }}</p>
        <p v-if="notice" class="text-sm text-green-600 dark:text-green-400">{{ notice }}</p>

        <button
          type="button"
          class="px-6 py-2.5 font-semibold text-white transition duration-200 bg-purple-600 rounded-full disabled:opacity-50 hover:bg-purple-700"
          :disabled="sending"
          @click="send"
        >{{ sending ? 'Sending…' : 'Send message' }}</button>
      </div>
    </div>

    <!-- history -->
    <div class="space-y-4">
      <h3 class="text-lg font-bold">Sent messages</h3>
      <p v-if="!messages.length" class="text-gray-500">No messages sent yet.</p>
      <ul v-else class="space-y-3">
        <li v-for="m in messages" :key="m.id" class="p-4 border rounded-xl dark:border-gray-800">
          <div class="flex items-center justify-between gap-3">
            <span class="font-semibold truncate">{{ m.subject }}</span>
            <span class="flex-shrink-0 text-xs text-gray-400">{{ formatDateTime(m.created_at) }}</span>
          </div>
          <p class="mt-1 text-sm text-gray-500 whitespace-pre-line line-clamp-3">{{ m.body }}</p>
          <p class="mt-2 text-xs text-gray-400">Sent to {{ m.recipient_count }} recipient{{ m.recipient_count === 1 ? '' : 's' }}</p>
        </li>
      </ul>
    </div>
  </div>
</template>
