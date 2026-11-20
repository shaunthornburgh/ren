<script setup lang="ts">
import type { AdminUserUpdate, UserRead, UserRole } from '~/types/api'

definePageMeta({ middleware: 'admin' })

const PAGE_SIZE = 50
const ROLES: UserRole[] = ['customer', 'organizer', 'admin']

const { apiFetch } = useApi()
const { user: me } = useAuth()
const { formatDate } = useFormat()

// Filters: `search` is the input; `appliedQ` changes only on submit.
const search = ref('')
const appliedQ = ref('')
const roleFilter = ref<UserRole | ''>('')

function fetchPage(skip: number) {
  return apiFetch<UserRead[]>('/admin/users', {
    query: {
      q: appliedQ.value || undefined,
      role: roleFilter.value || undefined,
      skip,
      limit: PAGE_SIZE,
    },
  })
}

// True while the last page fetched was full, so another may exist.
const hasMore = ref(false)

const { data: users, pending, error, refresh } = await useAsyncData(
  'admin-users',
  async () => {
    const rows = await fetchPage(0)
    hasMore.value = rows.length === PAGE_SIZE
    return rows
  },
  { server: false, default: () => [] as UserRead[], watch: [appliedQ, roleFilter] },
)

const loadingMore = ref(false)
const loadMoreError = ref('')
async function loadMore() {
  loadingMore.value = true
  loadMoreError.value = ''
  try {
    const next = await fetchPage(users.value.length)
    users.value = [...users.value, ...next]
    hasMore.value = next.length === PAGE_SIZE
  } catch {
    loadMoreError.value = 'Could not load more users. Please try again.'
  } finally {
    loadingMore.value = false
  }
}

function applySearch() {
  appliedQ.value = search.value.trim()
}

// Per-row save state.
const saving = reactive<Record<number, boolean>>({})
const rowErrors = reactive<Record<number, string>>({})
const announcement = ref('')

function nameOf(u: UserRead) {
  return u.display_name || u.full_name || u.email
}

async function save(u: UserRead, patch: AdminUserUpdate, success: string) {
  saving[u.id] = true
  delete rowErrors[u.id]
  announcement.value = ''
  try {
    const updated = await apiFetch<UserRead>(`/admin/users/${u.id}`, {
      method: 'PATCH',
      body: patch,
    })
    Object.assign(u, updated)
    announcement.value = success
  } catch (e: any) {
    rowErrors[u.id] = e?.data?.detail?.toString() || 'Could not save this change. Please try again.'
  } finally {
    saving[u.id] = false
  }
}

function onRoleChange(u: UserRead, event: Event) {
  const select = event.target as HTMLSelectElement
  const role = select.value as UserRole
  const previous = u.role
  // Keep the select showing the saved value until the API confirms.
  select.value = previous
  save(u, { role }, `${nameOf(u)} is now ${role}.`).then(() => {
    select.value = u.role
  })
}

function toggleActive(u: UserRead) {
  if (u.is_active && !confirm(`Deactivate ${nameOf(u)}? They will be signed out and unable to log in.`)) {
    return
  }
  const next = !u.is_active
  save(u, { is_active: next }, `${nameOf(u)} ${next ? 'activated' : 'deactivated'}.`)
}

const roleStyles: Record<UserRole, string> = {
  admin: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
  organizer: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  customer: 'bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
}
</script>

<template>
  <section>
    <div class="container max-w-screen-xl px-4 py-6 mx-auto md:py-10 lg:py-12">
      <div class="space-y-1">
        <h1 class="text-3xl font-bold bg-gradient-to-br from-purple-500 to-red-600 bg-clip-text text-transparent sm:text-4xl">
          Admin
        </h1>
        <p class="text-gray-500 dark:text-gray-400">Manage users, roles, and events across the platform.</p>
      </div>

      <AdminTabs />

      <!-- filters -->
      <form class="flex flex-col gap-3 mt-8 sm:flex-row sm:items-end" role="search" @submit.prevent="applySearch">
        <div class="flex-1">
          <label for="user-search" class="block mb-1 text-sm font-medium text-gray-600 dark:text-gray-300">Search users</label>
          <input
            id="user-search"
            v-model="search"
            type="search"
            maxlength="100"
            placeholder="Name or email"
            class="w-full px-4 py-2.5 border rounded-full dark:bg-gray-800 dark:border-gray-700 focus:outline-none focus:ring-2 focus:ring-purple-600"
          />
        </div>
        <div>
          <label for="role-filter" class="block mb-1 text-sm font-medium text-gray-600 dark:text-gray-300">Role</label>
          <select
            id="role-filter"
            v-model="roleFilter"
            class="w-full px-4 py-2.5 border rounded-full sm:w-44 dark:bg-gray-800 dark:border-gray-700 focus:outline-none focus:ring-2 focus:ring-purple-600"
          >
            <option value="">All roles</option>
            <option v-for="r in ROLES" :key="r" :value="r" class="capitalize">{{ r }}</option>
          </select>
        </div>
        <button
          type="submit"
          class="inline-flex items-center justify-center gap-2 px-5 py-2.5 font-semibold text-white transition duration-200 bg-purple-600 rounded-full hover:bg-purple-700"
        ><i class="bx bx-search" aria-hidden="true"></i> Search</button>
      </form>

      <p class="sr-only" aria-live="polite">{{ announcement }}</p>

      <div v-if="pending" class="mt-8 text-gray-500">Loading users…</div>

      <div v-else-if="error" class="py-12 mt-8 text-center border rounded-2xl dark:border-gray-800" role="alert">
        <p class="text-xl font-semibold">Could not load users</p>
        <p class="mt-2 text-gray-500">{{ (error as any)?.data?.detail || 'Something went wrong. Please try again.' }}</p>
        <button
          type="button"
          class="px-5 py-2 mt-6 font-semibold text-white transition duration-200 bg-purple-600 rounded-full hover:bg-purple-700"
          @click="refresh()"
        >Retry</button>
      </div>

      <div v-else-if="!users.length" class="py-16 mt-8 text-center border rounded-2xl dark:border-gray-800">
        <p class="text-xl font-semibold">No users match</p>
        <p class="mt-2 text-gray-500">Try a different search or role filter.</p>
      </div>

      <ul v-else class="mt-8 space-y-4">
        <li
          v-for="u in users"
          :key="u.id"
          class="p-4 border rounded-2xl dark:border-gray-800 sm:p-5"
        >
          <div class="flex flex-col gap-4 lg:flex-row lg:items-center">
            <div class="flex-1 min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <NuxtLink :to="`/users/${u.id}`" class="font-semibold truncate hover:text-purple-600">{{ nameOf(u) }}</NuxtLink>
                <span class="px-3 py-0.5 text-xs font-semibold uppercase rounded-full" :class="roleStyles[u.role]">{{ u.role }}</span>
                <span
                  v-if="!u.is_active"
                  class="px-3 py-0.5 text-xs font-semibold uppercase rounded-full bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300"
                >Inactive</span>
                <span v-if="u.id === me?.id" class="text-xs font-medium text-gray-500">This is you — you can't change your own role or status.</span>
              </div>
              <div class="mt-1 text-sm text-gray-400 truncate">{{ u.email }} · Joined {{ formatDate(u.created_at) }}</div>
              <p v-if="rowErrors[u.id]" class="mt-2 text-sm text-red-600 dark:text-red-400" role="alert">{{ rowErrors[u.id] }}</p>
            </div>

            <div class="flex flex-row gap-2 lg:w-80">
              <select
                :value="u.role"
                :aria-label="`Role for ${u.email}`"
                :disabled="u.id === me?.id || saving[u.id]"
                class="flex-1 px-4 py-2 text-sm border rounded-full dark:bg-gray-800 dark:border-gray-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-purple-600"
                @change="onRoleChange(u, $event)"
              >
                <option v-for="r in ROLES" :key="r" :value="r">{{ r }}</option>
              </select>
              <button
                type="button"
                :aria-label="`${u.is_active ? 'Deactivate' : 'Activate'} ${u.email}`"
                :disabled="u.id === me?.id || saving[u.id]"
                class="flex-1 px-4 py-2 text-sm font-semibold transition duration-200 border rounded-full disabled:opacity-50 dark:border-gray-700"
                :class="u.is_active
                  ? 'text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/40'
                  : 'text-green-700 hover:bg-green-50 dark:text-green-400 dark:hover:bg-green-950/40'"
                @click="toggleActive(u)"
              >{{ u.is_active ? 'Deactivate' : 'Activate' }}</button>
            </div>
          </div>
        </li>
      </ul>

      <div v-if="!pending && !error && hasMore" class="mt-6 text-center">
        <button
          type="button"
          :disabled="loadingMore"
          class="px-5 py-2 font-semibold transition duration-200 border rounded-full hover:bg-gray-100 disabled:opacity-50 dark:border-gray-700 dark:hover:bg-gray-800"
          @click="loadMore"
        >{{ loadingMore ? 'Loading…' : 'Load more' }}</button>
        <p v-if="loadMoreError" class="mt-2 text-sm text-red-600 dark:text-red-400" role="alert">{{ loadMoreError }}</p>
      </div>
    </div>
  </section>
</template>
