<script setup lang="ts">
/**
 * Map marker for an in-person event.
 *
 * Uses the Maps Embed API rather than the JS SDK: the public event page only
 * needs to show one pin, and an iframe avoids shipping the whole Maps bundle
 * to every visitor. Renders nothing without coordinates or a key, so the page
 * degrades to the address on its own.
 */
const props = defineProps<{
  lat: number | null
  lng: number | null
  /** Used as the marker label / info window title. */
  label?: string | null
}>()

const { apiKey } = useGoogleMaps()

const hasCoords = computed(
  () => typeof props.lat === 'number' && typeof props.lng === 'number',
)

const embedUrl = computed(() => {
  if (!apiKey || !hasCoords.value) return null
  const params = new URLSearchParams({
    key: apiKey,
    q: `${props.lat},${props.lng}`,
    zoom: '15',
  })
  return `https://www.google.com/maps/embed/v1/place?${params}`
})

// Deep link for "open in Maps" — works even when the embed is unavailable.
const directionsUrl = computed(() => {
  if (!hasCoords.value) return null
  const query = encodeURIComponent(`${props.lat},${props.lng}`)
  return `https://www.google.com/maps/search/?api=1&query=${query}`
})
</script>

<template>
  <div v-if="embedUrl" class="space-y-2">
    <div class="overflow-hidden border rounded-2xl dark:border-gray-800">
      <iframe
        :src="embedUrl"
        :title="label ? `Map showing ${label}` : 'Event location map'"
        class="block w-full h-64 border-0"
        loading="lazy"
        referrerpolicy="no-referrer-when-downgrade"
        allowfullscreen
      ></iframe>
    </div>
    <a
      v-if="directionsUrl"
      :href="directionsUrl"
      target="_blank"
      rel="noopener noreferrer"
      class="inline-flex items-center gap-1.5 text-sm font-medium text-purple-600 hover:underline dark:text-purple-400"
    >
      <i class="bx bx-directions"></i> Get directions
    </a>
  </div>
</template>
