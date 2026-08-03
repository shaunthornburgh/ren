<script setup lang="ts">
import type { FaqItemCreate, FaqItemRead } from '~/types/api'

const props = defineProps<{ eventId: number }>()

const { apiFetch } = useApi()

const { data: items, pending, refresh } = await useAsyncData(
  `event-${props.eventId}-faq`,
  () => apiFetch<FaqItemRead[]>(`/events/${props.eventId}/faq`),
  { server: false, default: () => [] as FaqItemRead[] },
)

const editingId = ref<number | null>(null)
const showForm = ref(false)
const saving = ref(false)
const deletingId = ref<number | null>(null)
const formError = ref('')

const blank = () => ({ question: '', answer: '' })
const form = reactive(blank())

const inputClass =
  'w-full h-11 px-3 border rounded-lg border-gray-200 focus:outline-none focus:ring-2 focus:border-purple-600 dark:bg-gray-900 dark:border-gray-700'

function startCreate() {
  Object.assign(form, blank())
  editingId.value = null
  formError.value = ''
  showForm.value = true
}

function startEdit(item: FaqItemRead) {
  Object.assign(form, { question: item.question, answer: item.answer })
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
  if (!form.question.trim()) {
    formError.value = 'Question is required.'
    return
  }
  if (!form.answer.trim()) {
    formError.value = 'Answer is required.'
    return
  }

  const payload: FaqItemCreate = {
    question: form.question.trim(),
    answer: form.answer.trim(),
  }

  saving.value = true
  try {
    if (editingId.value !== null) {
      await apiFetch(`/events/${props.eventId}/faq/${editingId.value}`, {
        method: 'PUT',
        body: payload,
      })
    } else {
      await apiFetch(`/events/${props.eventId}/faq`, {
        method: 'POST',
        body: payload,
      })
    }
    await refresh()
    cancel()
  } catch (e: any) {
    formError.value =
      e?.data?.detail?.toString() ||
      'Could not save the FAQ item. Please try again.'
  } finally {
    saving.value = false
  }
}

async function remove(item: FaqItemRead) {
  if (!confirm(`Delete “${item.question}”?`)) return
  deletingId.value = item.id
  try {
    await apiFetch(`/events/${props.eventId}/faq/${item.id}`, {
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
    await apiFetch(`/events/${props.eventId}/faq/reorder`, {
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
        <h2 class="text-2xl font-bold">Event FAQ</h2>
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
      >+ Add FAQ item</button>
    </div>

    <p v-if="pending" class="text-gray-500">Loading FAQ…</p>
    <p v-else-if="!items.length && !showForm" class="text-gray-500">
      No FAQ items yet. Add common questions to help attendees.
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
          <div class="font-semibold">{{ item.question }}</div>
          <div class="mt-1 text-sm text-gray-500 whitespace-pre-line">{{ item.answer }}</div>
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
      <h3 class="font-semibold">{{ editingId ? 'Edit FAQ item' : 'New FAQ item' }}</h3>
      <div class="space-y-4">
        <div class="space-y-1.5">
          <label class="text-sm font-medium">Question</label>
          <input v-model="form.question" type="text" placeholder="e.g. Are refunds available?" :class="inputClass" />
        </div>
        <div class="space-y-1.5">
          <label class="text-sm font-medium">Answer</label>
          <textarea v-model="form.answer" rows="3" placeholder="Write a clear answer…" class="w-full px-3 py-2 border rounded-lg border-gray-200 focus:outline-none focus:ring-2 focus:border-purple-600 dark:bg-gray-900 dark:border-gray-700"></textarea>
        </div>
      </div>

      <p v-if="formError" class="text-sm text-red-500">{{ formError }}</p>

      <div class="flex items-center gap-3">
        <button
          type="button"
          class="px-5 py-2.5 font-semibold text-white transition duration-200 bg-purple-600 rounded-full disabled:opacity-50 hover:bg-purple-700"
          :disabled="saving"
          @click="save"
        >{{ saving ? 'Saving…' : 'Save FAQ item' }}</button>
        <button
          type="button"
          class="px-5 py-2.5 font-semibold text-gray-600 transition duration-200 rounded-full bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
          @click="cancel"
        >Cancel</button>
      </div>
    </div>
  </div>
</template>
