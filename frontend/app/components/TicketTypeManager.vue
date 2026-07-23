<script setup lang="ts">
import type {
  TicketTypeCreate,
  TicketTypeRead,
} from '~/types/api'

const props = defineProps<{ eventId: number }>()

const { apiFetch } = useApi()
const { formatPrice } = useFormat()

const { data: ticketTypes, pending, refresh } = await useAsyncData(
  `event-${props.eventId}-ticket-types`,
  () => apiFetch<TicketTypeRead[]>(`/events/${props.eventId}/ticket-types`),
  { server: false, default: () => [] as TicketTypeRead[] },
)

// Form state doubles for create and edit; `editingId` decides which.
const editingId = ref<number | null>(null)
const showForm = ref(false)
const saving = ref(false)
const formError = ref('')

const blank = (): {
  name: string
  description: string
  price: string
  quantity_available: number | null
  max_per_order: number | null
} => ({
  name: '',
  description: '',
  price: '',
  quantity_available: null,
  max_per_order: 10,
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

function startEdit(tt: TicketTypeRead) {
  Object.assign(form, {
    name: tt.name,
    description: tt.description ?? '',
    price: tt.price,
    quantity_available: tt.quantity_available,
    max_per_order: tt.max_per_order,
  })
  editingId.value = tt.id
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
  if (!form.name.trim()) {
    formError.value = 'Name is required.'
    return
  }
  if (form.price === '' || Number(form.price) < 0) {
    formError.value = 'Enter a valid price.'
    return
  }
  if (form.quantity_available === null || form.quantity_available < 0) {
    formError.value = 'Enter the quantity available.'
    return
  }

  const payload: TicketTypeCreate = {
    name: form.name.trim(),
    description: form.description.trim() || null,
    price: Number(form.price).toFixed(2),
    quantity_available: Number(form.quantity_available),
    max_per_order: Number(form.max_per_order ?? 10),
  }

  saving.value = true
  try {
    if (editingId.value !== null) {
      await apiFetch(
        `/events/${props.eventId}/ticket-types/${editingId.value}`,
        { method: 'PUT', body: payload },
      )
    } else {
      await apiFetch(`/events/${props.eventId}/ticket-types`, {
        method: 'POST',
        body: payload,
      })
    }
    await refresh()
    cancel()
  } catch (e: any) {
    formError.value =
      e?.data?.detail || 'Could not save the ticket type. Please try again.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold">Ticket types</h2>
      <button
        v-if="!showForm"
        type="button"
        class="px-5 py-2 font-semibold text-purple-600 transition duration-200 rounded-full bg-purple-50 hover:bg-purple-700 hover:text-white dark:bg-gray-800 dark:text-purple-400 dark:hover:bg-gray-700 dark:hover:text-gray-50"
        @click="startCreate"
      >+ Add ticket type</button>
    </div>

    <p v-if="pending" class="text-gray-500">Loading ticket types…</p>
    <p v-else-if="!ticketTypes.length && !showForm" class="text-gray-500">
      No ticket types yet. Add one so people can buy tickets.
    </p>

    <!-- existing ticket types -->
    <div v-if="ticketTypes.length" class="space-y-3">
      <div
        v-for="tt in ticketTypes"
        :key="tt.id"
        class="flex items-center justify-between p-4 border rounded-xl dark:border-gray-800"
      >
        <div class="min-w-0">
          <div class="font-semibold truncate">{{ tt.name }}</div>
          <div v-if="tt.description" class="text-sm text-gray-500 truncate">{{ tt.description }}</div>
          <div class="mt-1 text-sm text-gray-400">
            <span class="font-bold text-purple-600 dark:text-purple-400">{{ formatPrice(tt.price) }}</span>
            · {{ tt.quantity_available }} available · max {{ tt.max_per_order }}/order
          </div>
        </div>
        <button
          type="button"
          class="px-4 py-2 text-sm font-semibold transition duration-200 border rounded-full hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-gray-800"
          @click="startEdit(tt)"
        >Edit</button>
      </div>
    </div>

    <!-- add / edit form -->
    <div v-if="showForm" class="p-5 space-y-4 border rounded-2xl bg-gray-50 dark:bg-gray-800/40 dark:border-gray-800">
      <h3 class="font-semibold">{{ editingId ? 'Edit ticket type' : 'New ticket type' }}</h3>
      <div class="grid gap-4 sm:grid-cols-2">
        <div class="space-y-1.5 sm:col-span-2">
          <label class="text-sm font-medium">Name</label>
          <input v-model="form.name" type="text" placeholder="e.g. General Admission" :class="inputClass" />
        </div>
        <div class="space-y-1.5 sm:col-span-2">
          <label class="text-sm font-medium">Description <span class="text-gray-400">(optional)</span></label>
          <input v-model="form.description" type="text" placeholder="e.g. Standing, main arena" :class="inputClass" />
        </div>
        <div class="space-y-1.5">
          <label class="text-sm font-medium">Price (£)</label>
          <input v-model="form.price" type="number" min="0" step="0.01" placeholder="45.00" :class="inputClass" />
        </div>
        <div class="space-y-1.5">
          <label class="text-sm font-medium">Quantity available</label>
          <input v-model="form.quantity_available" type="number" min="0" placeholder="300" :class="inputClass" />
        </div>
        <div class="space-y-1.5">
          <label class="text-sm font-medium">Max per order</label>
          <input v-model="form.max_per_order" type="number" min="1" placeholder="10" :class="inputClass" />
        </div>
      </div>

      <p v-if="formError" class="text-sm text-red-500">{{ formError }}</p>

      <div class="flex items-center gap-3">
        <button
          type="button"
          class="px-5 py-2.5 font-semibold text-white transition duration-200 bg-purple-600 rounded-full disabled:opacity-50 hover:bg-purple-700"
          :disabled="saving"
          @click="save"
        >{{ saving ? 'Saving…' : 'Save ticket type' }}</button>
        <button
          type="button"
          class="px-5 py-2.5 font-semibold text-gray-600 transition duration-200 rounded-full bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
          @click="cancel"
        >Cancel</button>
      </div>
    </div>
  </div>
</template>
