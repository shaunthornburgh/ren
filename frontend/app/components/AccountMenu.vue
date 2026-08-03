<script setup lang="ts">
const { user, logout } = useAuth()
const router = useRouter()

const open = ref(false)
const root = ref<HTMLElement | null>(null)

const displayName = computed(
  () => user.value?.display_name || user.value?.full_name || user.value?.email || '',
)
const initial = computed(() => (displayName.value || '?').charAt(0).toUpperCase())

function toggle() {
  open.value = !open.value
}
function close() {
  open.value = false
}

function onLogout() {
  close()
  logout()
  router.push('/')
}

function onDocClick(e: MouseEvent) {
  if (open.value && root.value && !root.value.contains(e.target as Node)) {
    close()
  }
}

onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>

<template>
  <div ref="root" class="relative">
    <!-- avatar button -->
    <button
      type="button"
      class="flex items-center justify-center w-10 h-10 overflow-hidden text-sm font-bold text-white transition duration-200 bg-purple-600 rounded-full ring-2 ring-transparent hover:ring-purple-300 dark:hover:ring-gray-600"
      :aria-expanded="open"
      aria-label="Account menu"
      @click="toggle"
    >
      <img
        v-if="user?.avatar_url"
        :src="user.avatar_url"
        :alt="displayName"
        class="object-cover w-full h-full"
      />
      <span v-else>{{ initial }}</span>
    </button>

    <!-- dropdown -->
    <div
      v-if="open"
      class="absolute right-0 z-30 mt-2 overflow-hidden bg-white shadow-xl w-56 rounded-2xl dark:bg-gray-800 ring-1 ring-black/5 dark:ring-white/10"
    >
      <div class="px-4 py-3 border-b dark:border-gray-700">
        <div class="text-sm font-semibold truncate">{{ displayName }}</div>
        <div v-if="user?.email" class="text-xs text-gray-400 truncate">{{ user.email }}</div>
      </div>

      <nav class="py-1">
        <NuxtLink
          v-if="user"
          :to="`/users/${user.id}`"
          class="flex items-center gap-3 px-4 py-2.5 text-sm font-medium transition duration-150 hover:bg-purple-50 dark:hover:bg-gray-700/50"
          @click="close"
        >
          <i class="text-lg bx bx-user"></i> View profile
        </NuxtLink>
        <NuxtLink
          to="/account"
          class="flex items-center gap-3 px-4 py-2.5 text-sm font-medium transition duration-150 hover:bg-purple-50 dark:hover:bg-gray-700/50"
          @click="close"
        >
          <i class="text-lg bx bx-cog"></i> Settings
        </NuxtLink>
        <button
          type="button"
          class="flex items-center w-full gap-3 px-4 py-2.5 text-sm font-medium text-left text-red-600 transition duration-150 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/40"
          @click="onLogout"
        >
          <i class="text-lg bx bx-log-out"></i> Logout
        </button>
      </nav>
    </div>
  </div>
</template>
