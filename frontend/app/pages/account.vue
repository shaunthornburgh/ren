<script setup lang="ts">
import type { UserRead } from '~/types/api'

definePageMeta({ middleware: 'auth' })

const { apiFetch } = useApi()
const { user } = useAuth()

const form = reactive({
  display_name: user.value?.display_name ?? '',
  bio: user.value?.bio ?? '',
})

const saving = ref(false)
const error = ref('')
const saved = ref(false)

// Avatar upload state
const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const avatarError = ref('')
const previewUrl = ref<string | null>(null)

const ACCEPTED = ['image/jpeg', 'image/png', 'image/webp']
const MAX_BYTES = 5 * 1024 * 1024

const avatarSrc = computed(() => previewUrl.value || user.value?.avatar_url || null)
const initial = computed(() =>
  (user.value?.display_name || user.value?.full_name || user.value?.email || '?')
    .charAt(0)
    .toUpperCase(),
)

const inputClass =
  'w-full h-11 px-3 border rounded-lg border-gray-200 focus:outline-none focus:ring-2 focus:border-purple-600 dark:bg-gray-900 dark:border-gray-700'

function pickFile() {
  avatarError.value = ''
  fileInput.value?.click()
}

async function onFileSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = '' // allow re-selecting the same file later
  if (!file) return

  avatarError.value = ''
  if (!ACCEPTED.includes(file.type)) {
    avatarError.value = 'Please choose a JPG, PNG, or WebP image.'
    return
  }
  if (file.size > MAX_BYTES) {
    avatarError.value = 'Image is too large (max 5 MB).'
    return
  }

  previewUrl.value = URL.createObjectURL(file)
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const updated = await apiFetch<UserRead>('/users/me/avatar', {
      method: 'POST',
      body: fd,
    })
    user.value = updated
  } catch (err: any) {
    avatarError.value =
      err?.data?.detail?.toString() || 'Could not upload the image. Please try again.'
  } finally {
    if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = null
    uploading.value = false
  }
}

async function removeAvatar() {
  avatarError.value = ''
  uploading.value = true
  try {
    const updated = await apiFetch<UserRead>('/users/me/avatar', {
      method: 'DELETE',
    })
    user.value = updated
  } catch (err: any) {
    avatarError.value =
      err?.data?.detail?.toString() || 'Could not remove the image.'
  } finally {
    uploading.value = false
  }
}

async function save() {
  error.value = ''
  saved.value = false
  saving.value = true
  try {
    const updated = await apiFetch<UserRead>('/users/me', {
      method: 'PATCH',
      body: {
        display_name: form.display_name.trim() || null,
        bio: form.bio.trim() || null,
      },
    })
    user.value = updated
    saved.value = true
  } catch (e: any) {
    error.value =
      e?.data?.detail?.toString() || 'Could not save your profile. Please try again.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section>
    <div class="container max-w-screen-xl px-4 py-6 mx-auto md:py-10 lg:py-12">
      <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 class="text-3xl font-bold">Your profile</h1>
          <p class="mt-1 text-gray-500 dark:text-gray-400">
            This is what people see when they open your host profile.
          </p>
        </div>
        <NuxtLink
          v-if="user"
          :to="`/users/${user.id}`"
          class="self-start text-sm text-purple-600 hover:text-purple-700"
        >View public profile →</NuxtLink>
      </div>

      <div class="grid gap-6 mt-8 lg:grid-cols-3">
        <!-- avatar -->
        <div class="p-5 space-y-4 border rounded-2xl bg-gray-50 dark:bg-gray-800/40 dark:border-gray-800">
          <h2 class="font-semibold">Profile photo</h2>
          <div class="flex flex-col items-center gap-4">
            <img
              v-if="avatarSrc"
              :src="avatarSrc"
              alt="Avatar preview"
              class="object-cover w-32 h-32 rounded-full"
              :class="{ 'opacity-60': uploading }"
            />
            <span
              v-else
              class="flex items-center justify-center w-32 h-32 text-4xl font-bold text-white bg-purple-600 rounded-full"
            >{{ initial }}</span>

            <input
              ref="fileInput"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              class="hidden"
              @change="onFileSelected"
            />

            <div class="flex flex-wrap justify-center gap-2">
              <button
                type="button"
                class="px-5 py-2 text-sm font-semibold text-white transition duration-200 bg-purple-600 rounded-full disabled:opacity-50 hover:bg-purple-700"
                :disabled="uploading"
                @click="pickFile"
              >{{ uploading ? 'Uploading…' : (user?.avatar_url ? 'Change photo' : 'Upload photo') }}</button>
              <button
                v-if="user?.avatar_url && !uploading"
                type="button"
                class="px-5 py-2 text-sm font-semibold text-red-600 transition duration-200 border border-red-200 rounded-full hover:bg-red-50 dark:border-red-900 dark:hover:bg-red-950"
                @click="removeAvatar"
              >Remove</button>
            </div>
            <p class="text-xs text-center text-gray-400">JPG, PNG, or WebP · up to 5 MB</p>
            <p v-if="avatarError" class="text-sm text-center text-red-500">{{ avatarError }}</p>
          </div>
        </div>

        <!-- details -->
        <div class="p-5 space-y-4 border rounded-2xl bg-gray-50 lg:col-span-2 dark:bg-gray-800/40 dark:border-gray-800">
          <h2 class="font-semibold">Details</h2>
          <div class="space-y-1.5">
            <label for="display_name" class="text-sm font-medium">Display name</label>
            <input id="display_name" v-model="form.display_name" type="text" placeholder="How your name appears publicly" :class="inputClass" />
          </div>
          <div class="space-y-1.5">
            <label for="bio" class="text-sm font-medium">Bio</label>
            <textarea id="bio" v-model="form.bio" rows="6" placeholder="Tell people a little about yourself…" class="w-full px-3 py-2 border rounded-lg border-gray-200 focus:outline-none focus:ring-2 focus:border-purple-600 dark:bg-gray-900 dark:border-gray-700"></textarea>
          </div>

          <p v-if="error" class="text-sm text-red-500">{{ error }}</p>
          <p v-if="saved" class="text-sm text-green-600 dark:text-green-400">Profile saved.</p>

          <button
            type="button"
            class="px-6 py-2.5 font-semibold text-white transition duration-200 bg-purple-600 rounded-full disabled:opacity-50 hover:bg-purple-700"
            :disabled="saving"
            @click="save"
          >{{ saving ? 'Saving…' : 'Save profile' }}</button>
        </div>
      </div>
    </div>
  </section>
</template>
