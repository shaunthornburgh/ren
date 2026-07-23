<script setup lang="ts">
import type { EventRead } from '~/types/api'

const props = defineProps<{ event: EventRead }>()

const { formatDate } = useFormat()

const EVENT_PLACEHOLDER =
  'https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?auto=format&fit=crop&w=800&q=80'

const image = computed(() => props.event.image_url || EVENT_PLACEHOLDER)
</script>

<template>
  <div class="relative py-4 space-y-4 transition duration-200 transform border rounded-2xl hover:shadow-lg hover:-translate-y-2 dark:border-gray-800">
    <!-- date chip -->
    <div class="flex items-center px-4 space-x-2.5 text-purple-600 dark:text-purple-400">
      <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
      <span class="font-semibold">{{ formatDate(event.start_datetime) }}</span>
    </div>

    <!-- whole-card link -->
    <NuxtLink :to="`/events/${event.id}`" class="absolute z-10 w-full h-full" :aria-label="event.title"></NuxtLink>

    <div class="relative overflow-hidden">
      <img :src="image" :alt="event.title" class="object-cover w-full h-52" />
    </div>

    <div class="px-4">
      <span class="text-xl font-semibold line-clamp-1">{{ event.title }}</span>
    </div>

    <div class="flex items-center justify-between p-4 mx-4 space-x-3 bg-gray-100 rounded-lg dark:bg-gray-800 min-h-[84px]">
      <div class="flex-1 min-w-0">
        <div class="font-medium text-gray-500">Date</div>
        <div class="font-bold truncate">{{ formatDate(event.start_datetime) }}</div>
      </div>
      <div class="self-stretch border-l dark:border-gray-700"></div>
      <div class="flex-1 min-w-0 text-right">
        <div class="font-medium text-gray-500">Venue</div>
        <div class="font-bold truncate">{{ event.location || 'TBA' }}</div>
      </div>
    </div>
  </div>
</template>
