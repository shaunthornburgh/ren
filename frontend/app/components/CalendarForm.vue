<script setup lang="ts">
import type { CalendarCreate, CalendarRead } from '~/types/api'

const props = defineProps<{
  calendar?: CalendarRead | null
  submitting?: boolean
  error?: string
  submitLabel?: string
}>()

const emit = defineEmits<{ (e: 'submit', payload: CalendarCreate): void }>()

const isEdit = computed(() => !!props.calendar)

const form = reactive({
  name: props.calendar?.name ?? '',
  slug: props.calendar?.slug ?? '',
  description: props.calendar?.description ?? '',
  image_url: props.calendar?.image_url ?? '',
  is_public: props.calendar?.is_public ?? true,
})

const localError = ref('')

const inputClass =
  'w-full h-12 px-4 border rounded-xl border-gray-200 focus:outline-none focus:ring-2 focus:border-purple-600 dark:bg-gray-800 dark:border-gray-800'

function onSubmit() {
  localError.value = ''
  if (!form.name.trim()) {
    localError.value = 'Please give your calendar a name.'
    return
  }

  const payload: CalendarCreate = {
    name: form.name.trim(),
    description: form.description.trim() || null,
    image_url: form.image_url.trim() || null,
    is_public: form.is_public,
  }
  // Slug is only settable on create; it's derived from the name when blank.
  if (!isEdit.value && form.slug.trim()) payload.slug = form.slug.trim()

  emit('submit', payload)
}
</script>

<template>
  <form class="space-y-5" @submit.prevent="onSubmit">
    <div class="space-y-1.5">
      <label for="cal-name" class="text-sm font-medium">Name</label>
      <input id="cal-name" v-model="form.name" type="text" required placeholder="e.g. Techno Nights" :class="inputClass" />
    </div>

    <div v-if="!isEdit" class="space-y-1.5">
      <label for="cal-slug" class="text-sm font-medium">
        URL slug <span class="text-gray-400">(optional)</span>
      </label>
      <div class="flex items-center gap-2">
        <span class="text-sm text-gray-400">/calendar/</span>
        <input id="cal-slug" v-model="form.slug" type="text" placeholder="techno-nights" :class="inputClass" />
      </div>
      <p class="text-xs text-gray-400">Leave blank to generate one from the name.</p>
    </div>

    <div class="space-y-1.5">
      <label for="cal-description" class="text-sm font-medium">Description</label>
      <textarea id="cal-description" v-model="form.description" rows="4" placeholder="What is this calendar about?" class="w-full px-4 py-3 border rounded-xl border-gray-200 focus:outline-none focus:ring-2 focus:border-purple-600 dark:bg-gray-800 dark:border-gray-800"></textarea>
    </div>

    <div class="space-y-1.5">
      <label for="cal-image" class="text-sm font-medium">Cover image URL</label>
      <input id="cal-image" v-model="form.image_url" type="url" placeholder="https://…" :class="inputClass" />
    </div>

    <label class="flex items-center gap-3 cursor-pointer">
      <input v-model="form.is_public" type="checkbox" class="w-5 h-5 text-purple-600 rounded focus:ring-purple-600" />
      <span class="text-sm font-medium">Public — anyone can find and follow this calendar</span>
    </label>

    <p v-if="localError || error" class="text-sm text-red-500">{{ localError || error }}</p>

    <div class="flex items-center gap-3">
      <button
        type="submit"
        class="px-6 py-3 font-semibold text-white transition duration-200 bg-purple-600 rounded-full disabled:opacity-50 hover:bg-purple-700"
        :disabled="submitting"
      >{{ submitting ? 'Saving…' : (submitLabel || 'Save calendar') }}</button>
      <NuxtLink to="/dashboard/calendars" class="px-6 py-3 font-semibold text-gray-600 transition duration-200 rounded-full bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700">Cancel</NuxtLink>
    </div>
  </form>
</template>
