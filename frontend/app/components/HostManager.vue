<script setup lang="ts">
import type {
  EventHostCreate,
  EventHostRead,
  HostRole,
} from '~/types/api'

const props = defineProps<{ eventId: number }>()

const { apiFetch } = useApi()

const { data: hosts, pending, refresh } = await useAsyncData(
  `event-${props.eventId}-hosts`,
  () => apiFetch<EventHostRead[]>(`/events/${props.eventId}/hosts`),
  { server: false, default: () => [] as EventHostRead[] },
)

const roles: { value: HostRole; label: string }[] = [
  { value: 'host', label: 'Host (display only)' },
  { value: 'manager', label: 'Manager (can manage event)' },
]

const editingId = ref<number | null>(null)
const showForm = ref(false)
const saving = ref(false)
const deletingId = ref<number | null>(null)
const formError = ref('')

const blank = () => ({
  email: '',
  name: '',
  role: 'host' as HostRole,
  show_on_page: true,
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

function startEdit(host: EventHostRead) {
  Object.assign(form, {
    email: host.email,
    name: host.name ?? '',
    role: host.role,
    show_on_page: host.show_on_page,
  })
  editingId.value = host.id
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
  if (editingId.value === null && !form.email.trim()) {
    formError.value = 'Email is required.'
    return
  }

  saving.value = true
  try {
    if (editingId.value !== null) {
      await apiFetch(`/events/${props.eventId}/hosts/${editingId.value}`, {
        method: 'PUT',
        body: {
          name: form.name.trim() || null,
          role: form.role,
          show_on_page: form.show_on_page,
        },
      })
    } else {
      const payload: EventHostCreate = {
        email: form.email.trim(),
        name: form.name.trim() || null,
        role: form.role,
        show_on_page: form.show_on_page,
      }
      await apiFetch(`/events/${props.eventId}/hosts`, {
        method: 'POST',
        body: payload,
      })
    }
    await refresh()
    cancel()
  } catch (e: any) {
    formError.value =
      e?.data?.detail?.toString() || 'Could not save the host. Please try again.'
  } finally {
    saving.value = false
  }
}

async function remove(host: EventHostRead) {
  if (!confirm(`Remove ${host.name || host.email} as a host?`)) return
  deletingId.value = host.id
  try {
    await apiFetch(`/events/${props.eventId}/hosts/${host.id}`, {
      method: 'DELETE',
    })
    await refresh()
    if (editingId.value === host.id) cancel()
  } catch {
    // Non-fatal.
  } finally {
    deletingId.value = null
  }
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold">Hosts</h2>
        <p class="mt-1 text-sm text-gray-400">Invite co-hosts and managers by email.</p>
      </div>
      <button
        v-if="!showForm"
        type="button"
        class="px-5 py-2 font-semibold text-purple-600 transition duration-200 rounded-full bg-purple-50 hover:bg-purple-700 hover:text-white dark:bg-gray-800 dark:text-purple-400 dark:hover:bg-gray-700 dark:hover:text-gray-50"
        @click="startCreate"
      >+ Add host</button>
    </div>

    <p v-if="pending" class="text-gray-500">Loading hosts…</p>

    <div v-if="hosts.length" class="space-y-3">
      <div
        v-for="host in hosts"
        :key="host.id"
        class="flex items-start justify-between gap-4 p-4 border rounded-xl dark:border-gray-800"
      >
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <span class="font-semibold">{{ host.name || host.email }}</span>
            <span
              class="px-2 py-0.5 text-xs font-semibold uppercase rounded-full"
              :class="host.role === 'manager'
                ? 'bg-purple-100 text-purple-700 dark:bg-gray-700 dark:text-purple-300'
                : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'"
            >{{ host.role }}</span>
            <span
              v-if="host.is_creator"
              class="px-2 py-0.5 text-xs font-semibold uppercase rounded-full bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
            >Creator</span>
          </div>
          <div v-if="host.name" class="text-sm text-gray-400">{{ host.email }}</div>
          <div class="flex items-center gap-3 mt-1 text-xs text-gray-400">
            <span v-if="!host.is_creator">{{ host.status }}</span>
            <span v-if="host.show_on_page" class="inline-flex items-center gap-1 text-purple-500 dark:text-purple-400">
              <i class="bx bx-show"></i> On page
            </span>
          </div>
        </div>
        <div v-if="!host.is_creator" class="flex flex-shrink-0 gap-2">
          <button
            type="button"
            class="px-4 py-2 text-sm font-semibold transition duration-200 border rounded-full hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-gray-800"
            @click="startEdit(host)"
          >Edit</button>
          <button
            type="button"
            class="px-4 py-2 text-sm font-semibold text-red-600 transition duration-200 border border-red-200 rounded-full disabled:opacity-50 hover:bg-red-50 dark:border-red-900 dark:hover:bg-red-950"
            :disabled="deletingId === host.id"
            @click="remove(host)"
          >{{ deletingId === host.id ? '…' : 'Remove' }}</button>
        </div>
      </div>
    </div>

    <!-- add / edit form -->
    <div v-if="showForm" class="p-5 space-y-4 border rounded-2xl bg-gray-50 dark:bg-gray-800/40 dark:border-gray-800">
      <h3 class="font-semibold">{{ editingId ? 'Edit host' : 'Invite host' }}</h3>
      <div class="space-y-4">
        <div class="space-y-1.5">
          <label class="text-sm font-medium">Email</label>
          <input
            v-model="form.email"
            type="email"
            :disabled="editingId !== null"
            placeholder="host@example.com"
            :class="[inputClass, editingId !== null ? 'opacity-60 cursor-not-allowed' : '']"
          />
          <p v-if="editingId !== null" class="text-xs text-gray-400">Email can't be changed after inviting.</p>
        </div>
        <div class="space-y-1.5">
          <label class="text-sm font-medium">Display name <span class="text-gray-400">(optional)</span></label>
          <input v-model="form.name" type="text" placeholder="e.g. Jane Doe" :class="inputClass" />
        </div>
        <div class="space-y-1.5">
          <label class="text-sm font-medium">Role</label>
          <select v-model="form.role" :class="inputClass">
            <option v-for="r in roles" :key="r.value" :value="r.value">{{ r.label }}</option>
          </select>
        </div>
        <label class="flex items-center gap-3 cursor-pointer">
          <input v-model="form.show_on_page" type="checkbox" class="w-5 h-5 text-purple-600 rounded focus:ring-purple-600" />
          <span class="text-sm font-medium">Show this host on the public event page</span>
        </label>
      </div>

      <p v-if="formError" class="text-sm text-red-500">{{ formError }}</p>

      <div class="flex items-center gap-3">
        <button
          type="button"
          class="px-5 py-2.5 font-semibold text-white transition duration-200 bg-purple-600 rounded-full disabled:opacity-50 hover:bg-purple-700"
          :disabled="saving"
          @click="save"
        >{{ saving ? 'Saving…' : (editingId ? 'Save host' : 'Send invite') }}</button>
        <button
          type="button"
          class="px-5 py-2.5 font-semibold text-gray-600 transition duration-200 rounded-full bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
          @click="cancel"
        >Cancel</button>
      </div>
    </div>
  </div>
</template>
