<script setup lang="ts">
import QRCode from 'qrcode'

const props = defineProps<{ value: string }>()

// Rendered as inline SVG so it stays crisp at any size. Always dark-on-white,
// even in dark mode — scanners need the contrast.
const svg = ref('')

watchEffect(async () => {
  svg.value = await QRCode.toString(props.value, {
    type: 'svg',
    errorCorrectionLevel: 'M',
    margin: 1,
    color: { dark: '#111827', light: '#ffffff' },
  })
})
</script>

<template>
  <div class="p-2 bg-white rounded-xl [&>svg]:block [&>svg]:w-full [&>svg]:h-auto" v-html="svg" />
</template>
