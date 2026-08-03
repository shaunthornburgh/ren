<script setup lang="ts">
import type { CalendarRead } from '~/types/api'

definePageMeta({ middleware: 'organizer' })

const { apiFetch } = useApi()

const { data: calendars, pending } = await useAsyncData(
  'organizer-calendars',
  () => apiFetch<CalendarRead[]>('/calendars/me'),
  { server: false, default: () => [] as CalendarRead[] },
)

const CAL_PLACEHOLDER =
  'https://images.unsplash.com/photo-1492684223066-81342ee5ff30?auto=format&fit=crop&w=400&q=80'
</script>

<template>
  <section>
    <div class="container max-w-screen-xl px-4 py-6 mx-auto md:py-10 lg:py-12">
      <!-- header -->
      <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div class="space-y-1">
          <NuxtLink to="/dashboard" class="text-sm text-purple-600 hover:text-purple-700">← Back to dashboard</NuxtLink>
          <h1 class="text-3xl font-bold bg-gradient-to-br from-purple-500 to-red-600 bg-clip-text text-transparent sm:text-4xl">
            Your calendars
          </h1>
          <p class="text-gray-500 dark:text-gray-400">Group events and let people follow for updates.</p>
        </div>
        <NuxtLink
          to="/dashboard/calendars/new"
          class="inline-flex items-center px-5 py-2.5 font-semibold text-center text-white transition duration-200 bg-purple-600 rounded-full hover:bg-purple-700"
        >+ Create calendar</NuxtLink>
      </div>

      <div v-if="pending" class="mt-8 text-gray-500">Loading your calendars…</div>

      <div v-else-if="!calendars.length" class="py-16 mt-8 text-center border rounded-2xl dark:border-gray-800">
        <p class="text-xl font-semibold">No calendars yet</p>
        <p class="mt-2 text-gray-500">Create a calendar to start building an audience.</p>
        <NuxtLink
          to="/dashboard/calendars/new"
          class="inline-block px-5 py-2 mt-6 font-semibold text-white transition duration-200 bg-purple-600 rounded-full hover:bg-purple-700"
        >Create calendar</NuxtLink>
      </div>

      <div v-else class="grid gap-5 mt-8 sm:grid-cols-2 lg:grid-cols-3">
        <div
          v-for="cal in calendars"
          :key="cal.id"
          class="overflow-hidden transition duration-200 border rounded-2xl hover:shadow-lg dark:border-gray-800"
        >
          <img :src="cal.image_url || CAL_PLACEHOLDER" :alt="cal.name" class="object-cover w-full h-32" />
          <div class="p-5 space-y-3">
            <div class="flex items-center gap-2">
              <h3 class="text-lg font-semibold truncate">{{ cal.name }}</h3>
              <span
                v-if="!cal.is_public"
                class="px-2 py-0.5 text-xs font-semibold uppercase rounded-full bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-300"
              >Private</span>
            </div>
            <p class="text-sm text-gray-400">/calendar/{{ cal.slug }}</p>
            <p class="text-sm font-medium text-gray-500">
              {{ cal.follower_count }} {{ cal.follower_count === 1 ? 'follower' : 'followers' }}
            </p>
            <div class="flex gap-2 pt-1">
              <NuxtLink
                :to="`/dashboard/calendars/${cal.id}`"
                class="flex-1 px-4 py-2 text-sm font-semibold text-center text-white transition duration-200 bg-purple-600 rounded-full hover:bg-purple-700"
              >Manage</NuxtLink>
              <NuxtLink
                :to="`/calendar/${cal.slug}`"
                class="flex-1 px-4 py-2 text-sm font-semibold text-center transition duration-200 border rounded-full hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-gray-800"
              >View</NuxtLink>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
