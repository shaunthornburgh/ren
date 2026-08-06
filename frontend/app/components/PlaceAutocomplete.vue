<script setup lang="ts">
/**
 * Google Places Autocomplete for a single in-person location field.
 *
 * Wraps `PlaceAutocompleteElement` (the current Places API — the legacy
 * `Autocomplete` widget is closed to new keys). Picking a suggestion emits the
 * formatted address together with its coordinates; typing without picking one
 * emits a `clear` so the caller can drop stale coordinates, because the
 * backend only accepts an in-person location that came from a real place.
 */
const props = defineProps<{
  /** Current formatted address. */
  modelValue: string
  /** Shown as a confirmation line when coordinates are present. */
  hasCoords?: boolean
  placeholder?: string
  inputClass?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'select', place: { address: string; lat: number; lng: number }): void
  (e: 'clear'): void
}>()

const { isConfigured, loadLibrary } = useGoogleMaps()

const host = ref<HTMLElement | null>(null)
const loadError = ref('')
const ready = ref(false)

let element: any = null

onMounted(async () => {
  if (!isConfigured.value || !host.value) return
  try {
    const { PlaceAutocompleteElement } = await loadLibrary('places')
    element = new PlaceAutocompleteElement()
    if (props.placeholder) element.placeholder = props.placeholder

    element.addEventListener('gmp-select', onSelect)
    // The inner input is the only place a free-text edit shows up; watching it
    // lets us invalidate coordinates the moment the address stops matching.
    element.addEventListener('input', onFreeText)

    host.value.appendChild(element)
    ready.value = true
    await nextTick()
    syncInputValue(props.modelValue)
  } catch (err: any) {
    loadError.value = err?.message || 'Could not load location search.'
  }
})

onBeforeUnmount(() => {
  element?.removeEventListener('gmp-select', onSelect)
  element?.removeEventListener('input', onFreeText)
  element?.remove()
  element = null
})

/** The widget has no `value` API, so reach for the input it renders — which
 *  may live in its shadow root depending on the Maps version. */
function innerInput(): HTMLInputElement | null {
  return (
    element?.querySelector('input') ??
    element?.shadowRoot?.querySelector('input') ??
    null
  )
}

function syncInputValue(value: string) {
  const input = innerInput()
  if (input && input.value !== value) input.value = value
}

// Reflect changes made by the parent (mode switch, cancelled edit).
watch(
  () => props.modelValue,
  (value) => {
    if (ready.value) syncInputValue(value)
  },
)

async function onSelect(event: any) {
  const prediction = event?.placePrediction
  if (!prediction) return
  try {
    const place = prediction.toPlace()
    await place.fetchFields({
      fields: ['formattedAddress', 'location', 'displayName'],
    })
    const address = place.formattedAddress || place.displayName || ''
    const lat = place.location?.lat?.()
    const lng = place.location?.lng?.()
    if (address && typeof lat === 'number' && typeof lng === 'number') {
      emit('update:modelValue', address)
      emit('select', { address, lat, lng })
      await nextTick()
      syncInputValue(address)
    }
  } catch {
    loadError.value = 'Could not read that place. Please try another.'
  }
}

function onFreeText(event: Event) {
  // The event crosses the component's shadow boundary, so `target` is the host
  // element rather than the field the user typed in. composedPath()[0] is the
  // real input; fall back to querying for it.
  const source = (event.composedPath?.()[0] ?? null) as HTMLInputElement | null
  const input = source?.tagName === 'INPUT' ? source : innerInput()
  const value = input?.value ?? ''
  if (value === props.modelValue) return
  emit('update:modelValue', value)
  emit('clear')
}
</script>

<template>
  <div class="space-y-1">
    <!-- Places widget -->
    <div v-if="isConfigured && !loadError" ref="host" class="place-autocomplete"></div>

    <!-- No key configured, or the script failed: fall back to a plain input so
         the rest of the form stays usable and the reason is visible. -->
    <input
      v-else
      :value="modelValue"
      type="text"
      :placeholder="placeholder"
      :class="inputClass"
      @input="
        emit('update:modelValue', ($event.target as HTMLInputElement).value);
        emit('clear')
      "
    />

    <p v-if="loadError" class="text-xs text-red-500">{{ loadError }}</p>
    <p v-else-if="!isConfigured" class="text-xs text-amber-600 dark:text-amber-400">
      Location search is unavailable — set
      <code>NUXT_PUBLIC_GOOGLE_MAPS_API_KEY</code> to pick an address on the map.
    </p>
    <p v-else-if="hasCoords" class="text-xs text-green-600 dark:text-green-400">
      <i class="bx bx-check"></i> Pinned on the map
    </p>
    <p v-else-if="modelValue" class="text-xs text-amber-600 dark:text-amber-400">
      Choose an address from the suggestions to pin it on the map.
    </p>
  </div>
</template>

<style scoped>
/* The widget is a web component; size it like the other form inputs. */
.place-autocomplete :deep(gmp-place-autocomplete) {
  width: 100%;
}
</style>
