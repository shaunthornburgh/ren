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
  // When true, render a compact read-only view with an Edit button
  // (used on the manage page). When false, always show the full form
  // (used on the create page).
  clickToEdit?: boolean
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
  title: '',
  description: '',
  start_datetime: '',
  end_datetime: '',
  // One location field for both modes: a Google address, or a joining URL.
  location: '',
  is_online: false,
  lat: null as number | null,
  lng: null as number | null,
  capacity: null as number | null,
  calendar_id: null as number | null,
  status: 'draft' as EventStatus,
})

// Populate the form fields from the current event (or sensible defaults).
function resetForm() {
  form.title = props.event?.title ?? ''
  form.description = props.event?.description ?? ''
  form.start_datetime = toLocalInput(props.event?.start_datetime)
  form.end_datetime = toLocalInput(props.event?.end_datetime)
  form.location = props.event?.location ?? ''
  form.is_online = props.event?.is_online ?? false
  form.lat = props.event?.lat ?? null
  form.lng = props.event?.lng ?? null
  form.capacity = props.event?.capacity ?? null
  // Default to the event's calendar, else the organizer's first calendar.
  form.calendar_id = props.event?.calendar_id ?? props.calendars?.[0]?.id ?? null
  form.status = (props.event?.status ?? 'draft') as EventStatus
}
resetForm()

// Events must belong to a calendar; block the form until one exists.
const hasCalendars = computed(() => (props.calendars ?? []).length > 0)

const localError = ref('')

// --- location mode ---
// Switching mode swaps what `location` means, so start the field empty rather
// than carrying an address into a URL box (or the reverse). Returning to the
// event's original mode restores what was saved.
function setOnline(value: boolean) {
  if (form.is_online === value) return
  form.is_online = value
  const original = props.event
  if (original && original.is_online === value) {
    form.location = original.location ?? ''
    form.lat = original.lat ?? null
    form.lng = original.lng ?? null
  } else {
    form.location = ''
    form.lat = null
    form.lng = null
  }
}

function onPlaceSelected(place: { address: string; lat: number; lng: number }) {
  form.location = place.address
  form.lat = place.lat
  form.lng = place.lng
}

// Free text that no longer corresponds to a picked place has no coordinates.
function onPlaceCleared() {
  form.lat = null
  form.lng = null
}

function isHttpUrl(value: string): boolean {
  try {
    const url = new URL(value)
    return url.protocol === 'http:' || url.protocol === 'https:'
  } catch {
    return false
  }
}

// --- view / edit mode ---
// In click-to-edit mode we start read-only; otherwise the form is always open.
const editing = ref(!props.clickToEdit)
// Track a save in flight so we can return to view mode once it succeeds.
const pendingSave = ref(false)

function startEdit() {
  resetForm()
  localError.value = ''
  editing.value = true
}

function cancelEdit() {
  resetForm()
  localError.value = ''
  editing.value = false
}

// When a save completes, drop back to view mode if it succeeded.
watch(
  () => props.submitting,
  (now, prev) => {
    if (prev && !now && pendingSave.value) {
      pendingSave.value = false
      if (!props.error && !localError.value && props.clickToEdit) {
        editing.value = false
      }
    }
  },
)

// Keep local state in sync if the parent swaps the event underneath us
// (e.g. after an image upload or an external refresh).
watch(
  () => props.event,
  (ev) => {
    imageUrl.value = ev?.image_url ?? null
    if (!editing.value) resetForm()
  },
)

// --- read-only display helpers ---
function formatDateTime(iso?: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const calendarName = computed(
  () =>
    (props.calendars ?? []).find((c) => c.id === props.event?.calendar_id)?.name ??
    '—',
)

const statusMeta: Record<EventStatus, { label: string; class: string }> = {
  draft: {
    label: 'Draft',
    class: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
  },
  published: {
    label: 'Published',
    class: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  },
  cancelled: {
    label: 'Cancelled',
    class: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300',
  },
}

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
  'w-full h-10 px-3 border rounded-lg border-gray-200 focus:outline-none focus:ring-2 focus:border-purple-600 dark:bg-gray-900 dark:border-gray-700'

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

  // Mirror the backend's location rules so mistakes surface before the round trip.
  const location = form.location.trim()
  if (form.is_online) {
    if (!location) {
      localError.value = 'Please add the link attendees will join on.'
      return
    }
    if (!isHttpUrl(location)) {
      localError.value =
        'Please enter a valid link, including https:// — e.g. https://meet.google.com/abc-defg-hij'
      return
    }
  } else {
    if (!location) {
      localError.value = 'Please add where the event takes place.'
      return
    }
    if (form.lat === null || form.lng === null) {
      localError.value =
        'Please choose the address from the suggestions so we can show it on a map.'
      return
    }
  }

  pendingSave.value = true
  emit('submit', {
    title: form.title.trim(),
    description: form.description.trim() || null,
    start_datetime: start.toISOString(),
    end_datetime: end.toISOString(),
    location,
    is_online: form.is_online,
    lat: form.is_online ? null : form.lat,
    lng: form.is_online ? null : form.lng,
    capacity: form.capacity === null || form.capacity === ('' as any) ? null : Number(form.capacity),
    calendar_id: Number(form.calendar_id),
    status: form.status,
  })
}
</script>

<template>
  <!-- ===================== VIEW MODE (compact, read-only) ===================== -->
  <div v-if="clickToEdit && !editing && event" class="space-y-3">
    <div class="flex items-start gap-4">
      <!-- small thumbnail -->
      <div class="relative flex items-center justify-center flex-shrink-0 w-24 h-24 overflow-hidden bg-gray-100 rounded-lg dark:bg-gray-900">
        <img v-if="displayImage" :src="displayImage" alt="Event image" class="object-cover w-full h-full" />
        <i v-else class="text-2xl text-gray-400 bx bx-image"></i>
      </div>

      <div class="flex-1 min-w-0">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <h3 class="text-lg font-semibold truncate">{{ event.title }}</h3>
            <span
              class="inline-block mt-1 px-2 py-0.5 text-xs font-medium rounded-full"
              :class="statusMeta[event.status].class"
            >{{ statusMeta[event.status].label }}</span>
          </div>
          <button
            type="button"
            class="flex-shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-semibold text-purple-600 transition duration-200 rounded-lg hover:bg-purple-50 dark:text-purple-400 dark:hover:bg-purple-900/30"
            @click="startEdit"
          >
            <i class="bx bx-edit-alt"></i> Edit
          </button>
        </div>
        <p v-if="event.description" class="mt-1.5 text-sm text-gray-600 line-clamp-2 dark:text-gray-400">
          {{ event.description }}
        </p>
      </div>
    </div>

    <!-- dense detail rows -->
    <dl class="grid grid-cols-1 pt-3 text-sm border-t gap-x-6 gap-y-2 sm:grid-cols-2 dark:border-gray-800">
      <div class="flex gap-2">
        <dt class="flex-shrink-0 w-16 text-gray-400">Starts</dt>
        <dd class="font-medium">{{ formatDateTime(event.start_datetime) }}</dd>
      </div>
      <div class="flex gap-2">
        <dt class="flex-shrink-0 w-16 text-gray-400">Ends</dt>
        <dd class="font-medium">{{ formatDateTime(event.end_datetime) }}</dd>
      </div>
      <div class="flex gap-2">
        <dt class="flex-shrink-0 w-16 text-gray-400">{{ event.is_online ? 'Link' : 'Where' }}</dt>
        <dd class="font-medium truncate">
          <a
            v-if="event.is_online && event.location"
            :href="event.location"
            target="_blank"
            rel="noopener noreferrer"
            class="text-purple-600 hover:underline dark:text-purple-400"
          >{{ event.location }}</a>
          <span v-else>{{ event.location || '—' }}</span>
        </dd>
      </div>
      <div class="flex gap-2">
        <dt class="flex-shrink-0 w-16 text-gray-400">Calendar</dt>
        <dd class="font-medium truncate">{{ calendarName }}</dd>
      </div>
      <div class="flex gap-2">
        <dt class="flex-shrink-0 w-16 text-gray-400">Capacity</dt>
        <dd class="font-medium">{{ event.capacity ?? 'Unlimited' }}</dd>
      </div>
    </dl>
  </div>

  <!-- ===================== EDIT / FULL FORM ===================== -->
  <form v-else class="space-y-4" @submit.prevent="onSubmit">
    <div class="space-y-1">
      <label for="title" class="text-sm font-medium">Title</label>
      <input id="title" v-model="form.title" type="text" required placeholder="e.g. Aurora Nights Festival" :class="inputClass" />
    </div>

    <div class="space-y-1">
      <label for="description" class="text-sm font-medium">Description</label>
      <textarea id="description" v-model="form.description" rows="3" placeholder="Tell attendees what to expect…" class="w-full px-3 py-2 border rounded-lg border-gray-200 focus:outline-none focus:ring-2 focus:border-purple-600 dark:bg-gray-900 dark:border-gray-700"></textarea>
    </div>

    <div class="grid gap-4 sm:grid-cols-2">
      <div class="space-y-1">
        <label for="start" class="text-sm font-medium">Starts</label>
        <input id="start" v-model="form.start_datetime" type="datetime-local" required :class="inputClass" />
      </div>
      <div class="space-y-1">
        <label for="end" class="text-sm font-medium">Ends</label>
        <input id="end" v-model="form.end_datetime" type="datetime-local" required :class="inputClass" />
      </div>
    </div>

    <div class="space-y-2">
      <span class="text-sm font-medium">Location</span>

      <!-- mode toggle: one location, two shapes -->
      <div class="inline-flex p-1 rounded-full bg-gray-100 dark:bg-gray-800">
        <button
          v-for="mode in [
            { online: false, label: 'In person', icon: 'bx-map' },
            { online: true, label: 'Online', icon: 'bx-video' },
          ]"
          :key="String(mode.online)"
          type="button"
          class="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-semibold transition duration-200 rounded-full"
          :class="form.is_online === mode.online
            ? 'bg-white text-purple-600 shadow-sm dark:bg-gray-900 dark:text-purple-400'
            : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'"
          :aria-pressed="form.is_online === mode.online"
          @click="setOnline(mode.online)"
        >
          <i :class="`bx ${mode.icon}`"></i> {{ mode.label }}
        </button>
      </div>

      <!-- online: a single URL field -->
      <div v-if="form.is_online" class="space-y-1">
        <input
          id="location"
          v-model="form.location"
          type="url"
          inputmode="url"
          placeholder="https://meet.google.com/abc-defg-hij"
          :class="inputClass"
        />
        <p class="text-xs text-gray-400">
          The link attendees join on. Shown on the event page.
        </p>
      </div>

      <!-- in person: a single Places-backed field -->
      <PlaceAutocomplete
        v-else
        v-model="form.location"
        :has-coords="form.lat !== null && form.lng !== null"
        placeholder="Search for an address or venue…"
        :input-class="inputClass"
        @select="onPlaceSelected"
        @clear="onPlaceCleared"
      />
    </div>

    <div class="space-y-1">
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
          <div class="relative flex items-center justify-center flex-shrink-0 w-16 h-16 overflow-hidden bg-gray-100 rounded-lg dark:bg-gray-900">
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

    <div class="space-y-1">
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

    <div class="grid gap-4 sm:grid-cols-2">
      <div class="space-y-1">
        <label for="capacity" class="text-sm font-medium">Capacity <span class="text-gray-400">(optional)</span></label>
        <input id="capacity" v-model="form.capacity" type="number" min="0" placeholder="e.g. 500" :class="inputClass" />
      </div>
      <div class="space-y-1">
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
        class="px-6 py-2.5 font-semibold text-white transition duration-200 bg-purple-600 rounded-full disabled:opacity-50 disabled:cursor-not-allowed hover:bg-purple-700"
        :disabled="submitting || !hasCalendars"
      >{{ submitting ? 'Saving…' : (submitLabel || 'Save event') }}</button>

      <!-- click-to-edit: cancel returns to the read-only view -->
      <button
        v-if="clickToEdit"
        type="button"
        class="px-6 py-2.5 font-semibold text-gray-600 transition duration-200 rounded-full bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
        :disabled="submitting"
        @click="cancelEdit"
      >Cancel</button>
      <!-- create flow: cancel leaves the page -->
      <NuxtLink v-else to="/dashboard" class="px-6 py-2.5 font-semibold text-gray-600 transition duration-200 rounded-full bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700">Cancel</NuxtLink>
    </div>
  </form>
</template>
