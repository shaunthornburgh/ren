<script setup lang="ts">
import type {
  CalendarRead,
  EventCreate,
  EventRead,
  EventStatus,
} from '~/types/api'

const props = defineProps<{
  event?: EventRead | null
  calendars?: CalendarRead[]
  submitting?: boolean
  error?: string
  submitLabel?: string
}>()

const emit = defineEmits<{
  (e: 'submit', payload: EventCreate): void
  (e: 'updated', event: EventRead): void
}>()

const { apiFetch } = useApi()

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
  capacity: props.event?.capacity ?? null,
  // Default to the event's calendar, else the organizer's first calendar.
  calendar_id: props.event?.calendar_id ?? props.calendars?.[0]?.id ?? null,
  status: (props.event?.status ?? 'draft') as EventStatus,
})

// Events must belong to a calendar; block the form until one exists.
const hasCalendars = computed(() => (props.calendars ?? []).length > 0)

const localError = ref('')

// --- header image upload (edit mode only — needs an existing event id) ---
const isEdit = computed(() => !!props.event?.id)
const imageUrl = ref<string | null>(props.event?.image_url ?? null)
const previewOverride = ref<string | null>(null)
const imgUploading = ref(false)
const imgError = ref('')
const imageInput = ref<HTMLInputElement | null>(null)
const dragOver = ref(false)

const ACCEPTED_IMAGE = ['image/jpeg', 'image/png', 'image/webp']
const MAX_IMAGE_BYTES = 10 * 1024 * 1024

const displayImage = computed(() => previewOverride.value || imageUrl.value)

function pickImage() {
  if (imgUploading.value) return
  imgError.value = ''
  imageInput.value?.click()
}

async function uploadFile(file: File) {
  if (!props.event) return
  imgError.value = ''
  if (!ACCEPTED_IMAGE.includes(file.type)) {
    imgError.value = 'Please choose a JPG, PNG, or WebP image.'
    return
  }
  if (file.size > MAX_IMAGE_BYTES) {
    imgError.value = 'Image is too large (max 10 MB).'
    return
  }

  previewOverride.value = URL.createObjectURL(file)
  imgUploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const updated = await apiFetch<EventRead>(
      `/events/${props.event.id}/image`,
      { method: 'POST', body: fd },
    )
    imageUrl.value = updated.image_url
    emit('updated', updated)
  } catch (err: any) {
    imgError.value =
      err?.data?.detail?.toString() || 'Could not upload the image. Please try again.'
  } finally {
    if (previewOverride.value) URL.revokeObjectURL(previewOverride.value)
    previewOverride.value = null
    imgUploading.value = false
  }
}

function onImageSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (file) uploadFile(file)
}

function onDrop(e: DragEvent) {
  dragOver.value = false
  if (imgUploading.value) return
  const file = e.dataTransfer?.files?.[0]
  if (file) uploadFile(file)
}

function onDragOver() {
  if (!imgUploading.value) dragOver.value = true
}

function onDragLeave() {
  dragOver.value = false
}

async function removeImage() {
  if (!props.event) return
  imgError.value = ''
  imgUploading.value = true
  try {
    const updated = await apiFetch<EventRead>(
      `/events/${props.event.id}/image`,
      { method: 'DELETE' },
    )
    imageUrl.value = updated.image_url
    emit('updated', updated)
  } catch (err: any) {
    imgError.value =
      err?.data?.detail?.toString() || 'Could not remove the image.'
  } finally {
    imgUploading.value = false
  }
}

const statuses: { value: EventStatus; label: string }[] = [
  { value: 'draft', label: 'Draft' },
  { value: 'published', label: 'Published' },
  { value: 'cancelled', label: 'Cancelled' },
]

const inputClass =
  'w-full h-11 px-3 border rounded-lg border-gray-200 focus:outline-none focus:ring-2 focus:border-purple-600 dark:bg-gray-900 dark:border-gray-700'

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

  if (form.calendar_id === null || form.calendar_id === ('' as any)) {
    localError.value = 'Please select a calendar for this event.'
    return
  }

  emit('submit', {
    title: form.title.trim(),
    description: form.description.trim() || null,
    start_datetime: start.toISOString(),
    end_datetime: end.toISOString(),
    location: form.location.trim() || null,
    capacity: form.capacity === null || form.capacity === ('' as any) ? null : Number(form.capacity),
    calendar_id: Number(form.calendar_id),
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
      <textarea id="description" v-model="form.description" rows="4" placeholder="Tell attendees what to expect…" class="w-full px-3 py-2 border rounded-lg border-gray-200 focus:outline-none focus:ring-2 focus:border-purple-600 dark:bg-gray-900 dark:border-gray-700"></textarea>
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
      <span class="text-sm font-medium">Image</span>

      <!-- edit mode: compact drag-and-drop / click upload -->
      <div v-if="isEdit" class="space-y-2">
        <div
          class="flex items-center max-w-sm gap-4 p-3 transition duration-150 border-2 border-dashed cursor-pointer rounded-xl"
          :class="dragOver
            ? 'border-purple-500 bg-purple-50 dark:bg-gray-800'
            : 'border-gray-200 hover:border-purple-400 dark:border-gray-700 dark:hover:border-purple-500'"
          role="button"
          tabindex="0"
          @click="pickImage"
          @keydown.enter.prevent="pickImage"
          @dragenter.prevent="onDragOver"
          @dragover.prevent="onDragOver"
          @dragleave.prevent="onDragLeave"
          @drop.prevent="onDrop"
        >
          <!-- compact thumbnail -->
          <div class="relative flex items-center justify-center flex-shrink-0 w-20 h-20 overflow-hidden bg-gray-100 rounded-lg dark:bg-gray-900">
            <img
              v-if="displayImage"
              :src="displayImage"
              alt="Event image preview"
              class="object-cover w-full h-full"
              :class="{ 'opacity-60': imgUploading }"
            />
            <i v-else class="text-2xl text-gray-400 bx bx-image"></i>
          </div>

          <div class="min-w-0">
            <p class="text-sm font-medium">
              <span v-if="imgUploading">Uploading…</span>
              <span v-else>
                Drag &amp; drop, or
                <span class="text-purple-600 dark:text-purple-400">click to upload</span>
              </span>
            </p>
            <p class="mt-0.5 text-xs text-gray-400">JPG, PNG, or WebP · up to 10 MB</p>
          </div>
        </div>

        <input
          ref="imageInput"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          class="hidden"
          @change="onImageSelected"
        />

        <button
          v-if="imageUrl && !imgUploading"
          type="button"
          class="text-sm font-medium text-red-600 transition duration-200 hover:text-red-700 dark:text-red-400"
          @click="removeImage"
        >Remove image</button>
        <p v-if="imgError" class="text-sm text-red-500">{{ imgError }}</p>
      </div>

      <!-- create mode: no event id yet, so upload after saving -->
      <p v-else class="text-sm text-gray-400">
        You can upload an image after saving the event.
      </p>
    </div>

    <div class="space-y-1.5">
      <label for="calendar" class="text-sm font-medium">Calendar <span class="text-red-500">*</span></label>
      <select
        id="calendar"
        v-model="form.calendar_id"
        required
        :disabled="!hasCalendars"
        :class="inputClass"
      >
        <option :value="null" disabled>Select a calendar…</option>
        <option v-for="c in calendars ?? []" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
      <p v-if="hasCalendars" class="text-xs text-gray-400">
        Every event belongs to a calendar. Publishing notifies its followers.
      </p>
      <p v-else class="text-xs text-amber-600 dark:text-amber-400">
        You need a calendar before creating an event.
        <NuxtLink to="/dashboard/calendars/new" class="font-medium text-purple-600 hover:text-purple-700">Create one first →</NuxtLink>
      </p>
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
        class="px-6 py-3 font-semibold text-white transition duration-200 bg-purple-600 rounded-full disabled:opacity-50 disabled:cursor-not-allowed hover:bg-purple-700"
        :disabled="submitting || !hasCalendars"
      >{{ submitting ? 'Saving…' : (submitLabel || 'Save event') }}</button>
      <NuxtLink to="/dashboard" class="px-6 py-3 font-semibold text-gray-600 transition duration-200 rounded-full bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700">Cancel</NuxtLink>
    </div>
  </form>
</template>
