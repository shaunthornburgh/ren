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
let observer: MutationObserver | null = null

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
    styleInnerControl()
    watchForRerenders()
  } catch (err: any) {
    loadError.value = err?.message || 'Could not load location search.'
  }
})

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
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

/**
 * Force the widget's own input to the form's field metrics.
 *
 * CSS can't reach the control when the Maps version renders it inside a shadow
 * root, but inline styles can, so set them on the element directly (as
 * `!important`, since the widget's internal sheet is otherwise more specific).
 * Without this the field is taller than a plain `h-10` input and the section
 * reflows when the In person / Online toggle switches which one is shown.
 */
function styleInnerControl() {
  const input = innerInput()
  if (!input) return

  const force = (el: HTMLElement, styles: Record<string, string>) => {
    for (const [prop, value] of Object.entries(styles)) {
      el.style.setProperty(prop, value, 'important')
    }
  }

  force(input, {
    'box-sizing': 'border-box',
    width: '100%',
    height: '100%',
    'min-height': '0',
    margin: '0',
    padding: '0 0.75rem', // px-3
    border: '0',
    'border-radius': '0.5rem', // rounded-lg
    background: 'transparent',
    'box-shadow': 'none',
    outline: 'none',
    color: 'inherit',
    font: 'inherit',
  })

  // The containers between the input and the host carry their own height and
  // vertical padding, so the field stays oversized unless they collapse too.
  // The chain stops on its own at the shadow root (whose child has no
  // parentElement) or at the host element.
  let node = input.parentElement
  while (node && node !== element) {
    force(node, {
      'box-sizing': 'border-box',
      height: '100%',
      'min-height': '0',
      margin: '0',
      'padding-top': '0',
      'padding-bottom': '0',
      border: '0',
      background: 'transparent',
      'box-shadow': 'none',
    })
    node = node.parentElement
  }

  force(element as HTMLElement, { display: 'block', width: '100%', height: '100%' })
}

/**
 * The widget re-renders its internals (e.g. when the suggestion list opens), so
 * re-apply the styling on structural changes. Only `childList` is observed —
 * watching attributes would loop on our own style writes.
 */
function watchForRerenders() {
  const root = element?.shadowRoot ?? element
  if (!root) return
  observer = new MutationObserver(() => styleInnerControl())
  observer.observe(root, { childList: true, subtree: true })
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
  <div class="space-y-1.5">
    <!-- Places widget. The widget renders its own input (partly inside a shadow
         root), so the wrapper draws the border, radius and focus ring instead
         and the widget's own chrome is neutralised in <style> below. -->
    <div
      v-if="isConfigured && !loadError"
      class="place-autocomplete flex items-stretch w-full h-10 bg-white border rounded-lg border-gray-200 focus-within:ring-2 focus-within:border-purple-600 dark:bg-gray-900 dark:border-gray-700"
    >
      <div ref="host" class="place-autocomplete__host"></div>
    </div>

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
    <!-- Empty and idle: still render a hint line, so the section keeps the same
         height as the online field's hint and the toggle doesn't shift things. -->
    <p v-else class="text-xs text-gray-400">
      Search for the venue or address, then pick a suggestion to pin it.
    </p>
  </div>
</template>

<style scoped>
/* The widget is a web component whose internals live in a shadow root, so its
   appearance can only be reached through the Material custom properties Google
   exposes (they inherit past the shadow boundary) — point them at the form's
   palette, and hide its own outline so only the wrapper's border shows.
   The surface colour still has to be opaque: the suggestion dropdown uses it. */
.place-autocomplete {
  --gmp-mat-color-surface: #ffffff;
  --gmp-mat-color-on-surface: #111827; /* gray-900 — matches body text */
  --gmp-mat-color-on-surface-variant: #9ca3af; /* gray-400 — placeholder */
  --gmp-mat-color-outline-decorative: transparent;
  --gmp-mat-color-surface-container-highest: #f3f4f6; /* gray-100 — hovered row */
  --gmp-mat-color-primary: #9333ea; /* purple-600 */
  --gmp-mat-color-on-primary: #ffffff;
  --gmp-mat-font-family: inherit;
}

/* Dark mode is class-based (`darkMode: 'class'`), so key off the html element. */
html.dark .place-autocomplete {
  --gmp-mat-color-surface: #111827; /* gray-900 — same as dark inputs */
  --gmp-mat-color-on-surface: #f9fafb; /* gray-50 */
  --gmp-mat-color-on-surface-variant: #9ca3af; /* gray-400 */
  --gmp-mat-color-surface-container-highest: #1f2937; /* gray-800 */
  --gmp-mat-color-primary: #a855f7; /* purple-500 */
}

/* The wrapper is a fixed h-10 (as the URL input is), so the widget fills it
   exactly and switching modes leaves the layout untouched. */
.place-autocomplete__host {
  display: flex;
  flex: 1 1 auto;
  min-width: 0;
  height: 100%;
}

.place-autocomplete :deep(gmp-place-autocomplete) {
  display: block;
  width: 100%;
  height: 100%;
  background: transparent;
}

/* Applies when the Maps version renders the input in the light DOM; the same
   metrics are set inline by styleInnerControl() for the shadow-root case, and
   having them here too avoids a flash before that runs. */
.place-autocomplete :deep(input) {
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  min-height: 0;
  margin: 0;
  padding: 0 0.75rem; /* px-3 */
  border: 0;
  border-radius: 0.5rem; /* rounded-lg */
  background: transparent;
  color: inherit;
  font: inherit;
  outline: none;
  box-shadow: none;
}
</style>
