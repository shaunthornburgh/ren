<script setup lang="ts">
import type { PublicUserProfile } from '~/types/api'

const route = useRoute()
const { apiFetch } = useApi()

const userId = computed(() => route.params.id as string)

const { data: profile, pending, error } = await useAsyncData(
  () => `user-${userId.value}`,
  () => apiFetch<PublicUserProfile>(`/users/${userId.value}`),
  { server: false, watch: [userId] },
)

const initial = computed(() =>
  (profile.value?.display_name || '?').charAt(0).toUpperCase(),
)
</script>

<template>
  <section>
    <div class="container max-w-screen-xl px-4 py-6 mx-auto md:py-12">
      <div v-if="pending" class="text-gray-500">Loading profile…</div>

      <div v-else-if="error || !profile" class="py-20 text-center">
        <p class="text-xl font-semibold">Profile not found</p>
        <NuxtLink to="/events" class="inline-block mt-4 text-purple-600 hover:text-purple-700">
          ← Browse events
        </NuxtLink>
      </div>

      <div v-else>
        <!-- header -->
        <div class="flex flex-col items-center gap-5 text-center sm:flex-row sm:items-center sm:text-left">
          <img
            v-if="profile.avatar_url"
            :src="profile.avatar_url"
            :alt="profile.display_name"
            class="object-cover w-24 h-24 rounded-full shrink-0"
          />
          <span
            v-else
            class="flex items-center justify-center w-24 h-24 text-3xl font-bold text-white bg-purple-600 rounded-full shrink-0"
          >{{ initial }}</span>

          <div class="space-y-2">
            <h1 class="text-3xl font-bold sm:text-4xl">{{ profile.display_name }}</h1>
            <p v-if="profile.bio" class="max-w-2xl text-gray-600 dark:text-gray-400 whitespace-pre-line">
              {{ profile.bio }}
            </p>
          </div>
        </div>

        <!-- hosting -->
        <h2 class="mt-12 text-2xl font-bold">Hosting</h2>

        <div v-if="!profile.hosting_events.length" class="py-16 mt-6 text-center border rounded-2xl dark:border-gray-800">
          <p class="text-lg font-semibold">No upcoming events</p>
          <p class="mt-2 text-gray-500">This host has no upcoming public events right now.</p>
        </div>

        <div v-else class="grid gap-5 mt-6 sm:grid-cols-2 lg:grid-cols-4">
          <EventCard v-for="event in profile.hosting_events" :key="event.id" :event="event" />
        </div>
      </div>
    </div>
  </section>
</template>
