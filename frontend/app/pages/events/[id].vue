<script setup lang="ts">
import type {
  AgendaItemRead,
  CheckoutSessionRead,
  EventRead,
  FaqItemRead,
  OrderRead,
  PublicHostRead,
  RegistrationQuestionRead,
  TicketTypeRead,
} from '~/types/api'

const route = useRoute()
const router = useRouter()
const { apiFetch } = useApi()
const { isAuthenticated } = useAuth()
const { formatDate, formatDateTime, formatTime, formatPrice } = useFormat()

const eventId = Number(route.params.id)

const EVENT_PLACEHOLDER =
  'https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?auto=format&fit=crop&w=900&q=80'

const { data, pending, error } = await useAsyncData(
  `event-${eventId}`,
  async () => {
    const [event, ticketTypes, agenda, faq, questions, hosts] =
      await Promise.all([
        apiFetch<EventRead>(`/events/${eventId}`),
        apiFetch<TicketTypeRead[]>(`/events/${eventId}/ticket-types`),
        apiFetch<AgendaItemRead[]>(`/events/${eventId}/agenda`),
        apiFetch<FaqItemRead[]>(`/events/${eventId}/faq`),
        apiFetch<RegistrationQuestionRead[]>(`/events/${eventId}/questions`),
        apiFetch<PublicHostRead[]>(`/events/${eventId}/hosts`),
      ])
    return { event, ticketTypes, agenda, faq, questions, hosts }
  },
  { server: false },
)

// Registration answers keyed by question id.
const answers = reactive<Record<number, string>>({})
watch(
  () => data.value?.questions,
  (questions) => {
    for (const q of questions ?? []) {
      if (!(q.id in answers)) answers[q.id] = ''
    }
  },
  { immediate: true },
)

// Group agenda items by calendar day so multi-day schedules read clearly.
const agendaByDay = computed(() => {
  const groups = new Map<string, AgendaItemRead[]>()
  for (const item of data.value?.agenda ?? []) {
    const day = formatDate(item.start_time)
    if (!groups.has(day)) groups.set(day, [])
    groups.get(day)!.push(item)
  }
  return Array.from(groups, ([day, items]) => ({ day, items }))
})

// Per-ticket-type selected quantity, keyed by id.
const quantities = reactive<Record<number, number>>({})

watch(
  () => data.value?.ticketTypes,
  (types) => {
    for (const t of types ?? []) {
      if (!(t.id in quantities)) quantities[t.id] = 0
    }
  },
  { immediate: true },
)

function maxFor(t: TicketTypeRead): number {
  return Math.max(0, Math.min(t.max_per_order, t.quantity_available))
}

function step(t: TicketTypeRead, delta: number) {
  const next = (quantities[t.id] ?? 0) + delta
  quantities[t.id] = Math.min(maxFor(t), Math.max(0, next))
}

const image = computed(
  () => data.value?.event.image_url || EVENT_PLACEHOLDER,
)

const total = computed(() => {
  const types = data.value?.ticketTypes ?? []
  return types.reduce(
    (sum, t) => sum + (quantities[t.id] ?? 0) * parseFloat(t.price),
    0,
  )
})

const totalCount = computed(() =>
  Object.values(quantities).reduce((a, b) => a + b, 0),
)

const purchasing = ref(false)
const purchaseError = ref('')
const purchaseNotice = ref('')

async function buy() {
  purchaseError.value = ''
  purchaseNotice.value = ''

  if (!isAuthenticated.value) {
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return
  }

  const items = (data.value?.ticketTypes ?? [])
    .filter((t) => (quantities[t.id] ?? 0) > 0)
    .map((t) => ({ ticket_type_id: t.id, quantity: quantities[t.id] }))

  if (!items.length) return

  // Validate required registration questions before reserving inventory.
  const questions = data.value?.questions ?? []
  const missing = questions.find(
    (q) => q.required && !(answers[q.id] ?? '').trim(),
  )
  if (missing) {
    purchaseError.value = `Please answer: ${missing.label}`
    return
  }

  const answersPayload = questions
    .map((q) => ({ question_id: q.id, value: (answers[q.id] ?? '').trim() }))
    .filter((a) => a.value !== '')

  purchasing.value = true
  try {
    // 1) Create a pending order (reserves inventory).
    const order = await apiFetch<OrderRead>('/orders', {
      method: 'POST',
      body: { items, answers: answersPayload },
    })

    // 2) Create a Stripe Checkout Session and redirect to it.
    try {
      const session = await apiFetch<CheckoutSessionRead>(
        `/payments/orders/${order.id}/checkout-session`,
        { method: 'POST' },
      )
      window.location.href = session.checkout_url
    } catch (e: any) {
      // Payments not configured (503) or gateway error — the order still
      // exists as pending, so point the user to My Tickets to complete it.
      if (e?.response?.status === 503) {
        purchaseNotice.value =
          'Your order was reserved, but online payment is not available right now. ' +
          'You can complete it later from My Tickets.'
      } else {
        purchaseError.value =
          e?.data?.detail || 'Could not start checkout. Please try again.'
      }
    }
  } catch (e: any) {
    purchaseError.value =
      e?.data?.detail || 'Could not create your order. Please try again.'
  } finally {
    purchasing.value = false
  }
}
</script>

<template>
  <section>
    <div class="container max-w-screen-xl px-4 py-6 mx-auto md:py-12">
      <div v-if="pending" class="text-gray-500">Loading event…</div>
      <div v-else-if="error || !data" class="py-20 text-center">
        <p class="text-xl font-semibold">Event not found</p>
        <NuxtLink to="/events" class="inline-block mt-4 text-purple-600 hover:text-purple-700">
          ← Back to all events
        </NuxtLink>
      </div>

      <div v-else class="space-y-14">
        <div class="grid gap-10 lg:grid-cols-5">
        <!-- image -->
        <div class="lg:col-span-3">
          <div class="relative flex items-center justify-center p-5 rounded-2xl bg-gray-100 lg:sticky top-10 sm:p-10 dark:bg-gray-800">
            <img :src="image" :alt="data.event.title" class="object-cover w-full shadow-2xl rounded-xl" />
          </div>
        </div>

        <!-- details -->
        <div class="lg:col-span-2">
          <div class="space-y-5">
            <h1 class="text-4xl font-bold">{{ data.event.title }}</h1>
            <p v-if="data.event.description" class="text-gray-600 dark:text-gray-400">
              {{ data.event.description }}
            </p>
          </div>

          <!-- when & where -->
          <div class="mt-8 space-y-4">
            <div class="flex items-center space-x-3">
              <span class="flex items-center justify-center w-10 h-10 text-purple-600 rounded-full bg-purple-50 dark:bg-gray-800 dark:text-purple-400">
                <i class="text-xl bx bx-calendar"></i>
              </span>
              <div>
                <div class="text-sm text-gray-400">Starts</div>
                <div class="font-semibold">{{ formatDateTime(data.event.start_datetime) }}</div>
              </div>
            </div>
            <div class="flex items-center space-x-3">
              <span class="flex items-center justify-center w-10 h-10 text-purple-600 rounded-full bg-purple-50 dark:bg-gray-800 dark:text-purple-400">
                <i class="text-xl bx bx-time"></i>
              </span>
              <div>
                <div class="text-sm text-gray-400">Ends</div>
                <div class="font-semibold">{{ formatDateTime(data.event.end_datetime) }}</div>
              </div>
            </div>
            <div class="flex items-center space-x-3">
              <span class="flex items-center justify-center w-10 h-10 text-purple-600 rounded-full bg-purple-50 dark:bg-gray-800 dark:text-purple-400">
                <i class="text-xl bx bx-map"></i>
              </span>
              <div>
                <div class="text-sm text-gray-400">Venue</div>
                <div class="font-semibold">{{ data.event.location || 'To be announced' }}</div>
              </div>
            </div>
          </div>

          <!-- hosts -->
          <div v-if="data.hosts.length" class="mt-8">
            <div class="mb-3 text-sm text-gray-400">Hosted by</div>
            <div class="flex flex-wrap gap-2">
              <component
                :is="host.user_id ? 'NuxtLink' : 'div'"
                v-for="(host, i) in data.hosts"
                :key="i"
                :to="host.user_id ? `/users/${host.user_id}` : undefined"
                class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-100 dark:bg-gray-800"
                :class="host.user_id ? 'transition duration-200 hover:bg-purple-100 dark:hover:bg-gray-700' : ''"
              >
                <span class="flex items-center justify-center w-6 h-6 text-xs font-bold text-white bg-purple-600 rounded-full">
                  {{ (host.name || host.email).charAt(0).toUpperCase() }}
                </span>
                <span class="text-sm font-medium">{{ host.name || host.email }}</span>
              </component>
            </div>
          </div>

          <!-- tickets -->
          <div class="mt-12 overflow-hidden border rounded-2xl dark:border-gray-800">
            <div class="p-6 space-y-4">
              <h2 class="text-2xl font-bold">Tickets</h2>

              <p v-if="!data.ticketTypes.length" class="text-gray-500">
                Tickets are not on sale yet. Check back soon.
              </p>

              <div
                v-for="t in data.ticketTypes"
                :key="t.id"
                class="flex items-center justify-between p-4 rounded-xl bg-gray-100 dark:bg-gray-800"
              >
                <div class="space-y-1">
                  <div class="font-semibold">{{ t.name }}</div>
                  <div v-if="t.description" class="text-sm text-gray-500">{{ t.description }}</div>
                  <div class="font-bold text-purple-600 dark:text-purple-400">{{ formatPrice(t.price) }}</div>
                  <div class="text-xs text-gray-400">
                    <span v-if="t.quantity_available > 0">{{ t.quantity_available }} available</span>
                    <span v-else class="text-red-500">Sold out</span>
                  </div>
                </div>

                <!-- quantity stepper -->
                <div class="flex items-center space-x-3">
                  <button
                    type="button"
                    class="flex items-center justify-center w-8 h-8 text-lg font-bold transition duration-200 bg-white border rounded-full disabled:opacity-40 hover:bg-purple-50 dark:bg-gray-700 dark:border-gray-600 dark:hover:bg-gray-600"
                    :disabled="(quantities[t.id] ?? 0) <= 0"
                    aria-label="Decrease quantity"
                    @click="step(t, -1)"
                  >−</button>
                  <span class="w-6 font-semibold text-center">{{ quantities[t.id] ?? 0 }}</span>
                  <button
                    type="button"
                    class="flex items-center justify-center w-8 h-8 text-lg font-bold transition duration-200 bg-white border rounded-full disabled:opacity-40 hover:bg-purple-50 dark:bg-gray-700 dark:border-gray-600 dark:hover:bg-gray-600"
                    :disabled="(quantities[t.id] ?? 0) >= maxFor(t)"
                    aria-label="Increase quantity"
                    @click="step(t, 1)"
                  >+</button>
                </div>
              </div>
            </div>

            <div v-if="data.ticketTypes.length" class="p-6 space-y-4 bg-gray-100 dark:bg-gray-800">
              <!-- registration questions -->
              <div v-if="data.questions.length && totalCount > 0" class="pb-4 space-y-4 border-b border-gray-200 dark:border-gray-700">
                <h3 class="font-semibold">Your details</h3>
                <div v-for="q in data.questions" :key="q.id" class="space-y-1.5">
                  <label :for="`q-${q.id}`" class="text-sm font-medium">
                    {{ q.label }}<span v-if="q.required" class="text-red-500"> *</span>
                  </label>
                  <textarea
                    v-if="q.field_type === 'textarea'"
                    :id="`q-${q.id}`"
                    v-model="answers[q.id]"
                    rows="3"
                    class="w-full px-3 py-2 border rounded-lg border-gray-200 focus:outline-none focus:ring-2 focus:border-purple-600 dark:bg-gray-900 dark:border-gray-700"
                  ></textarea>
                  <input
                    v-else
                    :id="`q-${q.id}`"
                    v-model="answers[q.id]"
                    :type="q.field_type === 'url' ? 'url' : 'text'"
                    :placeholder="q.field_type === 'url' ? 'https://…' : ''"
                    class="w-full h-11 px-3 border rounded-lg border-gray-200 focus:outline-none focus:ring-2 focus:border-purple-600 dark:bg-gray-900 dark:border-gray-700"
                  />
                </div>
              </div>

              <div class="flex items-center justify-between">
                <span class="font-medium text-gray-500">Total</span>
                <span class="text-2xl font-bold">{{ formatPrice(total) }}</span>
              </div>

              <p v-if="purchaseError" class="text-sm text-red-500">{{ purchaseError }}</p>
              <p v-if="purchaseNotice" class="text-sm text-purple-600 dark:text-purple-400">
                {{ purchaseNotice }}
                <NuxtLink to="/my-tickets" class="underline">View My Tickets</NuxtLink>
              </p>

              <button
                type="button"
                class="w-full py-4 font-semibold text-white transition duration-200 bg-purple-600 rounded-full disabled:opacity-50 disabled:cursor-not-allowed hover:bg-purple-700"
                :disabled="totalCount === 0 || purchasing"
                @click="buy"
              >
                <span v-if="purchasing">Processing…</span>
                <span v-else-if="!isAuthenticated">Sign in to buy</span>
                <span v-else>Buy {{ totalCount }} ticket{{ totalCount === 1 ? '' : 's' }}</span>
              </button>
            </div>
          </div>
        </div>
        </div>

        <!-- agenda / schedule -->
        <div v-if="agendaByDay.length">
          <h2 class="text-3xl font-bold">Schedule</h2>

          <div v-for="group in agendaByDay" :key="group.day" class="mt-8">
            <h3 v-if="agendaByDay.length > 1" class="mb-4 text-lg font-semibold text-purple-600 dark:text-purple-400">
              {{ group.day }}
            </h3>

            <ol class="space-y-4">
              <li
                v-for="item in group.items"
                :key="item.id"
                class="flex flex-col gap-4 p-5 border rounded-2xl sm:flex-row dark:border-gray-800"
              >
                <!-- time column -->
                <div class="flex-shrink-0 sm:w-32">
                  <div class="font-bold text-purple-600 dark:text-purple-400">{{ formatTime(item.start_time) }}</div>
                  <div v-if="item.end_time" class="text-sm text-gray-400">until {{ formatTime(item.end_time) }}</div>
                </div>

                <!-- content -->
                <div class="flex-1 min-w-0">
                  <h4 class="text-lg font-semibold">{{ item.title }}</h4>
                  <div class="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1 text-sm text-gray-500">
                    <span v-if="item.speaker_name" class="inline-flex items-center gap-1.5">
                      <i class="bx bx-user"></i>{{ item.speaker_name }}
                    </span>
                    <span v-if="item.location" class="inline-flex items-center gap-1.5">
                      <i class="bx bx-map-pin"></i>{{ item.location }}
                    </span>
                  </div>
                  <p v-if="item.description" class="mt-2 text-gray-600 dark:text-gray-400">
                    {{ item.description }}
                  </p>
                </div>
              </li>
            </ol>
          </div>
        </div>

        <!-- FAQ -->
        <div v-if="data.faq.length">
          <h2 class="text-3xl font-bold">Event FAQ</h2>
          <dl class="mt-6 divide-y dark:divide-gray-800">
            <div v-for="item in data.faq" :key="item.id" class="py-5 first:pt-0">
              <dt class="text-lg font-semibold">{{ item.question }}</dt>
              <dd class="mt-2 text-gray-600 dark:text-gray-400 whitespace-pre-line">{{ item.answer }}</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  </section>
</template>
