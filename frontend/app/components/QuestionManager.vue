<script setup lang="ts">
import type {
  RegistrationFieldType,
  RegistrationQuestionCreate,
  RegistrationQuestionRead,
} from '~/types/api'

const props = defineProps<{ eventId: number }>()

const { apiFetch } = useApi()

const { data: items, pending, refresh } = await useAsyncData(
  `event-${props.eventId}-questions`,
  () => apiFetch<RegistrationQuestionRead[]>(`/events/${props.eventId}/questions`),
  { server: false, default: () => [] as RegistrationQuestionRead[] },
)

const fieldTypes: { value: RegistrationFieldType; label: string }[] = [
  { value: 'text', label: 'Short text' },
  { value: 'textarea', label: 'Long text' },
  { value: 'url', label: 'URL' },
]
const typeLabels: Record<RegistrationFieldType, string> = {
  text: 'Short text',
  textarea: 'Long text',
  url: 'URL',
}

const editingId = ref<number | null>(null)
const showForm = ref(false)
const saving = ref(false)
const deletingId = ref<number | null>(null)
const formError = ref('')

const blank = () => ({
  label: '',
  field_type: 'text' as RegistrationFieldType,
  required: false,
})
const form = reactive(blank())

const inputClass =
  'w-full h-11 px-3 border rounded-lg border-gray-200 focus:outline-none focus:ring-2 focus:border-purple-600 dark:bg-gray-900 dark:border-gray-700'

function startCreate() {
  Object.assign(form, blank())
  editingId.value = null
  formError.value = ''
  showForm.value = true
}

function startEdit(item: RegistrationQuestionRead) {
  Object.assign(form, {
    label: item.label,
    field_type: item.field_type,
    required: item.required,
  })
  editingId.value = item.id
  formError.value = ''
  showForm.value = true
}

function cancel() {
  showForm.value = false
  editingId.value = null
  formError.value = ''
}

async function save() {
  formError.value = ''
  if (!form.label.trim()) {
    formError.value = 'Question label is required.'
    return
  }

  const payload: RegistrationQuestionCreate = {
    label: form.label.trim(),
    field_type: form.field_type,
    required: form.required,
  }

  saving.value = true
  try {
    if (editingId.value !== null) {
      await apiFetch(`/events/${props.eventId}/questions/${editingId.value}`, {
        method: 'PUT',
        body: payload,
      })
    } else {
      await apiFetch(`/events/${props.eventId}/questions`, {
        method: 'POST',
        body: payload,
      })
    }
    await refresh()
    cancel()
  } catch (e: any) {
    formError.value =
      e?.data?.detail?.toString() ||
      'Could not save the question. Please try again.'
  } finally {
    saving.value = false
  }
}

async function remove(item: RegistrationQuestionRead) {
  if (!confirm(`Delete “${item.label}”? Existing answers will be removed.`)) return
  deletingId.value = item.id
  try {
    await apiFetch(`/events/${props.eventId}/questions/${item.id}`, {
      method: 'DELETE',
    })
    await refresh()
    if (editingId.value === item.id) cancel()
  } catch {
    // Non-fatal.
  } finally {
    deletingId.value = null
  }
}

// --- drag-to-reorder (native HTML5 DnD) ---
const draggedIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)
const reordering = ref(false)

function onDragStart(index: number, e: DragEvent) {
  draggedIndex.value = index
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(index))
  }
}

function onDragOver(index: number, e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
  dragOverIndex.value = index
}

function onDragLeave(index: number) {
  if (dragOverIndex.value === index) dragOverIndex.value = null
}

function onDragEnd() {
  draggedIndex.value = null
  dragOverIndex.value = null
}

async function onDrop(index: number) {
  const from = draggedIndex.value
  onDragEnd()
  if (from === null || from === index) return

  const previous = items.value
  const next = [...items.value]
  const [moved] = next.splice(from, 1)
  next.splice(index, 0, moved)
  items.value = next

  reordering.value = true
  try {
    await apiFetch(`/events/${props.eventId}/questions/reorder`, {
      method: 'PUT',
      body: { item_ids: next.map((i) => i.id) },
    })
  } catch {
    items.value = previous
  } finally {
    reordering.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold">Registration questions</h2>
        <p v-if="items.length > 1 && !showForm" class="mt-1 text-sm text-gray-400">
          <span v-if="reordering" class="text-purple-500">Saving order…</span>
          <span v-else>Drag items to reorder.</span>
        </p>
      </div>
      <button
        v-if="!showForm"
        type="button"
        class="px-5 py-2 font-semibold text-purple-600 transition duration-200 rounded-full bg-purple-50 hover:bg-purple-700 hover:text-white dark:bg-gray-800 dark:text-purple-400 dark:hover:bg-gray-700 dark:hover:text-gray-50"
        @click="startCreate"
      >+ Add question</button>
    </div>

    <p v-if="pending" class="text-gray-500">Loading questions…</p>
    <p v-else-if="!items.length && !showForm" class="text-gray-500">
      No custom questions yet. Ask registrants for extra details at checkout.
    </p>

    <!-- existing items (drag to reorder) -->
    <div v-if="items.length" class="space-y-3">
      <div
        v-for="(item, index) in items"
        :key="item.id"
        :draggable="!showForm"
        class="flex items-start gap-3 p-4 transition duration-150 border rounded-xl dark:border-gray-800"
        :class="{
          'opacity-50': draggedIndex === index,
          'border-purple-500 ring-1 ring-purple-500': dragOverIndex === index && draggedIndex !== index,
        }"
        @dragstart="onDragStart(index, $event)"
        @dragover="onDragOver(index, $event)"
        @dragleave="onDragLeave(index)"
        @drop="onDrop(index)"
        @dragend="onDragEnd"
      >
        <span
          class="pt-0.5 text-lg leading-none text-gray-300 select-none dark:text-gray-600"
          :class="showForm ? 'cursor-not-allowed opacity-40' : 'cursor-grab active:cursor-grabbing'"
          aria-hidden="true"
          title="Drag to reorder"
        >⠿</span>

        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="font-semibold">{{ item.label }}</span>
            <span
              v-if="item.required"
              class="px-2 py-0.5 text-xs font-semibold uppercase rounded-full bg-purple-100 text-purple-700 dark:bg-gray-700 dark:text-purple-300"
            >Required</span>
          </div>
          <div class="mt-0.5 text-sm text-gray-400">{{ typeLabels[item.field_type] }}</div>
        </div>
        <div class="flex flex-shrink-0 gap-2">
          <button
            type="button"
            class="px-4 py-2 text-sm font-semibold transition duration-200 border rounded-full hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-gray-800"
            @click="startEdit(item)"
          >Edit</button>
          <button
            type="button"
            class="px-4 py-2 text-sm font-semibold text-red-600 transition duration-200 border border-red-200 rounded-full disabled:opacity-50 hover:bg-red-50 dark:border-red-900 dark:hover:bg-red-950"
            :disabled="deletingId === item.id"
            @click="remove(item)"
          >{{ deletingId === item.id ? '…' : 'Delete' }}</button>
        </div>
      </div>
    </div>

    <!-- add / edit form -->
    <div v-if="showForm" class="p-5 space-y-4 border rounded-2xl bg-gray-50 dark:bg-gray-800/40 dark:border-gray-800">
      <h3 class="font-semibold">{{ editingId ? 'Edit question' : 'New question' }}</h3>
      <div class="space-y-4">
        <div class="space-y-1.5">
          <label class="text-sm font-medium">Question label</label>
          <input v-model="form.label" type="text" placeholder="e.g. Instagram profile" :class="inputClass" />
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div class="space-y-1.5">
            <label class="text-sm font-medium">Field type</label>
            <select v-model="form.field_type" :class="inputClass">
              <option v-for="t in fieldTypes" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>
          <label class="flex items-center gap-3 mt-2 cursor-pointer sm:mt-7">
            <input v-model="form.required" type="checkbox" class="w-5 h-5 text-purple-600 rounded focus:ring-purple-600" />
            <span class="text-sm font-medium">Required</span>
          </label>
        </div>
      </div>

      <p v-if="formError" class="text-sm text-red-500">{{ formError }}</p>

      <div class="flex items-center gap-3">
        <button
          type="button"
          class="px-5 py-2.5 font-semibold text-white transition duration-200 bg-purple-600 rounded-full disabled:opacity-50 hover:bg-purple-700"
          :disabled="saving"
          @click="save"
        >{{ saving ? 'Saving…' : 'Save question' }}</button>
        <button
          type="button"
          class="px-5 py-2.5 font-semibold text-gray-600 transition duration-200 rounded-full bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
          @click="cancel"
        >Cancel</button>
      </div>
    </div>
  </div>
</template>
