<script setup lang="ts">
import jsQR from 'jsqr'
import type {
  CheckInConflict,
  CheckInResult,
  CheckInStats,
  EventRead,
} from '~/types/api'

// `auth` rather than `organizer`: accepted hosts may be plain customers. The
// API decides who has check-in access (see the stats probe below).
definePageMeta({ middleware: 'auth' })

const route = useRoute()
const { apiFetch } = useApi()
const { formatTicketCode, formatTime } = useFormat()

const eventId = Number(route.params.id)

const { data: event } = await useAsyncData(
  `check-in-event-${eventId}`,
  () => apiFetch<EventRead>(`/events/${eventId}`),
  { server: false },
)

// Doubles as the access check: 403 for anyone who isn't owner/manager/host.
const {
  data: stats,
  error: statsError,
  pending,
  refresh: refreshStats,
} = await useAsyncData(
  `check-in-stats-${eventId}`,
  () => apiFetch<CheckInStats>(`/events/${eventId}/check-in/stats`),
  { server: false },
)

const noAccess = computed(() => {
  const code = (statsError.value as any)?.statusCode
  return code === 403 || code === 404
})

// --- result of the latest attempt ---
type Outcome =
  | { kind: 'success'; ticket: CheckInResult }
  | { kind: 'used' | 'cancelled'; message: string; ticket: CheckInResult }
  | { kind: 'error'; message: string }

const outcome = ref<Outcome | null>(null)
const submitting = ref(false)
const history = ref<{ at: Date; code: string; outcome: Outcome }[]>([])

// A QR may contain the bare code or a URL carrying it as ?code=.
function extractCode(raw: string): string {
  const text = raw.trim()
  try {
    const fromUrl = new URL(text).searchParams.get('code')
    if (fromUrl) return fromUrl
  } catch {
    // not a URL — use as-is
  }
  return text
}

async function checkIn(raw: string) {
  const code = extractCode(raw)
  if (!code || submitting.value) return
  submitting.value = true
  let result: Outcome
  try {
    const ticket = await apiFetch<CheckInResult>('/check-in', {
      method: 'POST',
      body: { code, event_id: eventId },
    })
    result = { kind: 'success', ticket }
    refreshStats()
  } catch (e: any) {
    const detail = e?.data?.detail
    if (e?.statusCode === 409 && detail?.ticket) {
      const conflict = detail as CheckInConflict
      result = {
        kind: conflict.reason === 'already_used' ? 'used' : 'cancelled',
        message: conflict.message,
        ticket: conflict.ticket,
      }
    } else {
      result = {
        kind: 'error',
        message: typeof detail === 'string' ? detail : 'Check-in failed. Please try again.',
      }
    }
  } finally {
    submitting.value = false
  }
  outcome.value = result
  history.value = [{ at: new Date(), code, outcome: result }, ...history.value].slice(0, 20)
  if (import.meta.client && 'vibrate' in navigator) {
    navigator.vibrate(result.kind === 'success' ? 80 : [80, 60, 80])
  }
}

// --- manual entry ---
const manualCode = ref('')

async function submitManual() {
  await checkIn(manualCode.value)
  if (outcome.value?.kind === 'success') manualCode.value = ''
}

// --- camera scanner ---
const video = ref<HTMLVideoElement | null>(null)
const scanning = ref(false)
const cameraError = ref('')
let stream: MediaStream | null = null
let frameHandle = 0
let canvas: HTMLCanvasElement | null = null
// The same QR stays in view for a while after it's read; ignore repeats so a
// success isn't immediately followed by "already checked in".
let lastScan = { code: '', at: 0 }
const REPEAT_COOLDOWN_MS = 4000

async function startCamera() {
  cameraError.value = ''
  if (!navigator.mediaDevices?.getUserMedia) {
    cameraError.value =
      'Camera access needs a secure (https) connection. Use manual entry instead.'
    return
  }
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment' },
      audio: false,
    })
  } catch (e: any) {
    cameraError.value =
      e?.name === 'NotAllowedError'
        ? 'Camera permission was denied. Allow it in your browser settings, or use manual entry.'
        : 'Could not start the camera. Use manual entry instead.'
    return
  }
  scanning.value = true
  await nextTick()
  if (!video.value) return
  video.value.srcObject = stream
  await video.value.play().catch(() => {})
  frameHandle = requestAnimationFrame(scanFrame)
}

function stopCamera() {
  scanning.value = false
  cancelAnimationFrame(frameHandle)
  stream?.getTracks().forEach((t) => t.stop())
  stream = null
  if (video.value) video.value.srcObject = null
}

function scanFrame() {
  if (!scanning.value) return
  const el = video.value
  if (el && el.readyState === el.HAVE_ENOUGH_DATA && !submitting.value) {
    // Downscale before decoding — full-res frames make jsQR sluggish.
    const scale = Math.min(1, 640 / el.videoWidth)
    const w = Math.round(el.videoWidth * scale)
    const h = Math.round(el.videoHeight * scale)
    canvas ??= document.createElement('canvas')
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d', { willReadFrequently: true })
    if (ctx) {
      ctx.drawImage(el, 0, 0, w, h)
      const found = jsQR(ctx.getImageData(0, 0, w, h).data, w, h, {
        inversionAttempts: 'dontInvert',
      })
      const now = Date.now()
      if (
        found?.data &&
        !(found.data === lastScan.code && now - lastScan.at < REPEAT_COOLDOWN_MS)
      ) {
        lastScan = { code: found.data, at: now }
        checkIn(found.data)
      } else if (found?.data) {
        lastScan.at = now // still in view: extend the cooldown
      }
    }
  }
  frameHandle = requestAnimationFrame(scanFrame)
}

onBeforeUnmount(stopCamera)

const outcomeStyles: Record<Outcome['kind'], string> = {
  success: 'bg-green-50 border-green-200 text-green-800 dark:bg-green-900/30 dark:border-green-800 dark:text-green-200',
  used: 'bg-yellow-50 border-yellow-200 text-yellow-800 dark:bg-yellow-900/30 dark:border-yellow-800 dark:text-yellow-200',
  cancelled: 'bg-red-50 border-red-200 text-red-800 dark:bg-red-900/30 dark:border-red-800 dark:text-red-200',
  error: 'bg-red-50 border-red-200 text-red-800 dark:bg-red-900/30 dark:border-red-800 dark:text-red-200',
}

const outcomeTitle: Record<Outcome['kind'], string> = {
  success: 'Checked in',
  used: 'Already checked in',
  cancelled: 'Ticket cancelled',
  error: 'Not admitted',
}
</script>

<template>
  <section>
    <div class="container max-w-screen-md px-4 py-6 mx-auto md:py-10">
      <NuxtLink :to="`/dashboard/events/${eventId}`" class="text-sm text-purple-600 hover:text-purple-700">← Back to event</NuxtLink>

      <div v-if="pending" class="mt-6 text-gray-500">Loading…</div>

      <div v-else-if="noAccess" class="py-16 mt-6 text-center border rounded-2xl dark:border-gray-800">
        <p class="text-xl font-semibold">No check-in access</p>
        <p class="mt-2 text-gray-500">Only the event's organizer, managers and hosts can check guests in.</p>
      </div>

      <div v-else-if="statsError" class="py-16 mt-6 text-center border rounded-2xl dark:border-gray-800">
        <p class="text-xl font-semibold">Couldn't load check-in</p>
        <p class="mt-2 text-gray-500">Please refresh and try again.</p>
      </div>

      <div v-else>
        <!-- header -->
        <div class="flex flex-wrap items-end justify-between gap-4 mt-3">
          <div class="min-w-0">
            <p class="text-sm font-semibold tracking-wide text-purple-600 uppercase dark:text-purple-400">Check-in</p>
            <h1 class="text-3xl font-bold truncate">{{ event?.title ?? 'Event' }}</h1>
          </div>
          <div v-if="stats" class="text-right">
            <div class="text-2xl font-bold">
              {{ stats.checked_in }}<span class="text-gray-400"> / {{ stats.total }}</span>
            </div>
            <div class="text-sm text-gray-500">checked in</div>
          </div>
        </div>

        <!-- scanner -->
        <div class="mt-6 overflow-hidden border rounded-2xl bg-gray-50 dark:bg-gray-800/40 dark:border-gray-800">
          <div v-show="scanning" class="relative bg-black aspect-square sm:aspect-video">
            <video ref="video" class="object-cover w-full h-full" playsinline muted />
            <!-- viewfinder -->
            <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div class="w-3/5 border-4 border-purple-400 aspect-square rounded-3xl shadow-[0_0_0_9999px_rgba(0,0,0,0.35)] sm:w-2/5" />
            </div>
            <div
              v-if="submitting"
              class="absolute px-3 py-1 text-sm font-semibold text-white -translate-x-1/2 bg-purple-600 rounded-full bottom-4 left-1/2"
            >Checking…</div>
          </div>

          <div class="flex flex-col items-center gap-3 p-4 sm:flex-row sm:justify-between">
            <p class="text-sm text-gray-500">
              {{ scanning ? 'Point the camera at a ticket QR code.' : 'Scan ticket QR codes with your camera.' }}
            </p>
            <button
              type="button"
              class="px-5 py-2.5 font-semibold transition duration-200 rounded-full shrink-0"
              :class="scanning
                ? 'text-gray-700 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600'
                : 'text-white bg-purple-600 hover:bg-purple-700'"
              @click="scanning ? stopCamera() : startCamera()"
            >{{ scanning ? 'Stop camera' : 'Start camera' }}</button>
          </div>
          <p v-if="cameraError" class="px-4 pb-4 text-sm text-red-500">{{ cameraError }}</p>
        </div>

        <!-- manual entry -->
        <form class="flex gap-2 mt-4" @submit.prevent="submitManual">
          <input
            v-model="manualCode"
            type="text"
            inputmode="text"
            autocapitalize="characters"
            autocomplete="off"
            spellcheck="false"
            placeholder="Enter ticket code, e.g. 7K3Q-X9MZ-2B4H"
            class="flex-1 min-w-0 px-4 py-2.5 font-mono uppercase border rounded-full bg-white placeholder:normal-case placeholder:font-sans focus:outline-none focus:ring-2 focus:ring-purple-500 dark:bg-gray-900 dark:border-gray-700"
          />
          <button
            type="submit"
            class="px-5 py-2.5 font-semibold text-white transition duration-200 bg-purple-600 rounded-full disabled:opacity-50 hover:bg-purple-700"
            :disabled="submitting || !manualCode.trim()"
          >Check in</button>
        </form>

        <!-- latest result -->
        <div
          v-if="outcome"
          class="p-5 mt-6 border rounded-2xl"
          :class="outcomeStyles[outcome.kind]"
          aria-live="polite"
        >
          <div class="flex items-start gap-3">
            <svg v-if="outcome.kind === 'success'" xmlns="http://www.w3.org/2000/svg" class="w-7 h-7 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" class="w-7 h-7 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <div class="flex-1 min-w-0">
              <p class="text-lg font-bold">{{ outcomeTitle[outcome.kind] }}</p>
              <p v-if="outcome.kind !== 'success'" class="text-sm">{{ outcome.message }}</p>

              <dl v-if="'ticket' in outcome" class="grid grid-cols-[auto,1fr] gap-x-4 gap-y-1 mt-3 text-sm">
                <dt class="opacity-70">Guest</dt>
                <dd class="font-semibold truncate">{{ outcome.ticket.guest.full_name || outcome.ticket.guest.email }}</dd>
                <template v-if="outcome.ticket.guest.full_name">
                  <dt class="opacity-70">Email</dt>
                  <dd class="truncate">{{ outcome.ticket.guest.email }}</dd>
                </template>
                <dt class="opacity-70">Ticket</dt>
                <dd>{{ outcome.ticket.ticket_type_name }} · <span class="font-mono">{{ formatTicketCode(outcome.ticket.code) }}</span></dd>
                <template v-if="outcome.ticket.checked_in_at">
                  <dt class="opacity-70">Checked in</dt>
                  <dd>{{ formatTime(outcome.ticket.checked_in_at) }}</dd>
                </template>
              </dl>
            </div>
          </div>
        </div>

        <!-- this session's scans -->
        <div v-if="history.length" class="mt-8">
          <h2 class="mb-2 text-sm font-medium text-gray-500">Recent scans</h2>
          <ul class="border divide-y rounded-2xl dark:border-gray-800 dark:divide-gray-800">
            <li v-for="(h, i) in history" :key="i" class="flex items-center justify-between gap-3 px-4 py-2.5 text-sm">
              <div class="min-w-0">
                <span class="font-medium truncate">
                  {{ 'ticket' in h.outcome ? (h.outcome.ticket.guest.full_name || h.outcome.ticket.guest.email) : formatTicketCode(h.code) }}
                </span>
                <span class="ml-2 text-gray-400">{{ formatTime(h.at.toISOString()) }}</span>
              </div>
              <span
                class="px-2.5 py-0.5 text-xs font-semibold uppercase rounded-full shrink-0"
                :class="h.outcome.kind === 'success'
                  ? 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300'
                  : 'bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-300'"
              >{{ outcomeTitle[h.outcome.kind] }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </section>
</template>
