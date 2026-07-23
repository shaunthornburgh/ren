<script setup lang="ts">
import type { EventCreate, EventRead, EventStatus } from '~/types/api'

const props = defineProps<{
  event?: EventRead | null
  submitting?: boolean
  error?: string
  submitLabel?: string
}>()

const emit = defineEmits<{ (e: 'submit', payload: EventCreate): void }>()

// Convert an ISO timestamp to the `YYYY-MM-DDTHH:mm` value a
// datetime-local input expects (in the browser's local timezone).
function toLocalInput(iso?: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const form = reactive({
  title: props.event?.title ?? '',
  description: props.event?.description ?? '',
  start_datetime: toLocalInput(props.event?.start_datetime),
  end_datetime: toLocalInput(props.event?.end_datetime),
  location: props.event?.location ?? '',
  image_url: props.event?.image_url ?? '',
  capacity: props.event?.capacity ?? null,
  status: (props.event?.status ?? 'draft') as EventStatus,
})

const localError = ref('')

const statuses: { value: EventStatus; label: string }[] = [
  { value: 'draft', label: 'Draft' },
  { value: 'published', label: 'Published' },
  { value: 'cancelled', label: 'Cancelled' },
]

const inputClass =
  'w-full h-12 px-4 border rounded-xl border-gray-200 focus:outline-none focus:ring-2 focus:border-purple-600 dark:bg-gray-800 dark:border-gray-800'

function onSubmit() {
  localError.value = ''

  if (!form.start_datetime || !form.end_datetime) {
    localError.value = 'Please provide both a start and end time.'
    return
  }
  const start = new Date(form.start_datetime)
  const end = new Date(form.end_datetime)
  if (end <= start) {
    localError.value = 'End time must be after the start time.'
    return
  }

  emit('submit', {
    title: form.title.trim(),
    description: form.description.trim() || null,
    start_datetime: start.toISOString(),
    end_datetime: end.toISOString(),
    location: form.location.trim() || null,
    image_url: form.image_url.trim() || null,
    capacity: form.capacity === null || form.capacity === ('' as any) ? null : Number(form.capacity),
    status: form.status,
  })
}
</script>

<template>
  <form class="space-y-5" @submit.prevent="onSubmit">
    <div class="space-y-1.5">
      <label for="title" class="text-sm font-medium">Title</label>
      <input id="title" v-model="form.title" type="text" required placeholder="e.g. Aurora Nights Festival" :class="inputClass" />
    </div>

    <div class="space-y-1.5">
      <label for="description" class="text-sm font-medium">Description</label>
      <textarea id="description" v-model="form.description" rows="4" placeholder="Tell attendees what to expect…" class="w-full px-4 py-3 border rounded-xl border-gray-200 focus:outline-none focus:ring-2 focus:border-purple-600 dark:bg-gray-800 dark:border-gray-800"></textarea>
    </div>

    <div class="grid gap-5 sm:grid-cols-2">
      <div class="space-y-1.5">
        <label for="start" class="text-sm font-medium">Starts</label>
        <input id="start" v-model="form.start_datetime" type="datetime-local" required :class="inputClass" />
      </div>
      <div class="space-y-1.5">
        <label for="end" class="text-sm font-medium">Ends</label>
        <input id="end" v-model="form.end_datetime" type="datetime-local" required :class="inputClass" />
      </div>
    </div>

    <div class="space-y-1.5">
      <label for="location" class="text-sm font-medium">Venue / location</label>
      <input id="location" v-model="form.location" type="text" placeholder="e.g. Victoria Park, London" :class="inputClass" />
    </div>

    <div class="space-y-1.5">
      <label for="image" class="text-sm font-medium">Image URL</label>
      <input id="image" v-model="form.image_url" type="url" placeholder="https://…" :class="inputClass" />
    </div>

    <div class="grid gap-5 sm:grid-cols-2">
      <div class="space-y-1.5">
        <label for="capacity" class="text-sm font-medium">Capacity <span class="text-gray-400">(optional)</span></label>
        <input id="capacity" v-model="form.capacity" type="number" min="0" placeholder="e.g. 500" :class="inputClass" />
      </div>
      <div class="space-y-1.5">
        <label for="status" class="text-sm font-medium">Status</label>
        <select id="status" v-model="form.status" :class="inputClass">
          <option v-for="s in statuses" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
      </div>
    </div>

    <p v-if="localError || error" class="text-sm text-red-500">{{ localError || error }}</p>

    <div class="flex items-center gap-3">
      <button
        type="submit"
        class="px-6 py-3 font-semibold text-white transition duration-200 bg-purple-600 rounded-full disabled:opacity-50 hover:bg-purple-700"
        :disabled="submitting"
      >{{ submitting ? 'Saving…' : (submitLabel || 'Save event') }}</button>
      <NuxtLink to="/dashboard" class="px-6 py-3 font-semibold text-gray-600 transition duration-200 rounded-full bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700">Cancel</NuxtLink>
    </div>
  </form>
</template>
