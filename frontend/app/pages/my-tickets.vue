<script setup lang="ts">
import type { CheckoutSessionRead, OrderRead } from '~/types/api'

definePageMeta({ middleware: 'auth' })

const { apiFetch } = useApi()
const { user } = useAuth()
const { formatDateTime, formatPrice, formatTicketCode } = useFormat()
const route = useRoute()
const router = useRouter()

const { data: orders, pending, refresh } = await useAsyncData(
  'my-orders',
  () => apiFetch<OrderRead[]>('/my-orders'),
  { server: false, default: () => [] as OrderRead[] },
)

// Stripe redirects back here with ?status=success|cancelled after checkout.
const checkoutStatus = computed(() => {
  const status = route.query.status
  return status === 'success' || status === 'cancelled' ? status : null
})
const checkoutOrderId = computed(() => route.query.order_id ?? null)

// The order status only flips to "paid" once Stripe's webhook lands, which may
// arrive a moment after the redirect — refresh so the paid order shows up.
onMounted(() => {
  if (checkoutStatus.value === 'success') refresh()
})

// Drop the query params so the banner doesn't linger on refresh/back.
function dismissCheckoutStatus() {
  router.replace({ query: {} })
}

const statusStyles: Record<string, string> = {
  paid: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  pending: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
  cancelled: 'bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
}

const busyOrderId = ref<number | null>(null)
const actionError = ref('')

async function completePayment(order: OrderRead) {
  actionError.value = ''
  busyOrderId.value = order.id
  try {
    const session = await apiFetch<CheckoutSessionRead>(
      `/payments/orders/${order.id}/checkout-session`,
      { method: 'POST' },
    )
    window.location.href = session.checkout_url
  } catch (e: any) {
    actionError.value =
      e?.data?.detail || 'Could not start checkout. Please try again later.'
  } finally {
    busyOrderId.value = null
  }
}
</script>

<template>
  <section>
    <!-- cover -->
    <img
      src="https://images.unsplash.com/photo-1492684223066-81342ee5ff30?auto=format&fit=crop&w=1650&q=80"
      alt=""
      class="object-cover w-full h-48 md:h-60"
    />

    <div class="container max-w-screen-xl px-4 pb-6 mx-auto md:pb-12">
      <div class="mt-8 space-y-2">
        <h1 class="text-3xl font-bold">My Tickets</h1>
        <p class="text-gray-500 dark:text-gray-400">
          Orders for {{ user?.full_name || user?.email }}
        </p>
      </div>

      <!-- checkout result banner (from Stripe redirect) -->
      <div
        v-if="checkoutStatus === 'success'"
        class="flex items-start gap-3 p-4 mt-6 text-green-800 border border-green-200 rounded-xl bg-green-50 dark:bg-green-900/30 dark:text-green-200 dark:border-green-800"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
        <div class="flex-1">
          <p class="font-semibold">Payment successful</p>
          <p class="text-sm">
            Thanks! {{ checkoutOrderId ? `Order #${checkoutOrderId} is confirmed` : 'Your order is confirmed' }}.
            Your tickets appear below once payment is processed.
          </p>
        </div>
        <button type="button" class="text-sm underline shrink-0" @click="dismissCheckoutStatus">Dismiss</button>
      </div>

      <div
        v-else-if="checkoutStatus === 'cancelled'"
        class="flex items-start gap-3 p-4 mt-6 text-yellow-800 border border-yellow-200 rounded-xl bg-yellow-50 dark:bg-yellow-900/30 dark:text-yellow-200 dark:border-yellow-800"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
        <div class="flex-1">
          <p class="font-semibold">Payment cancelled</p>
          <p class="text-sm">
            {{ checkoutOrderId ? `Order #${checkoutOrderId} wasn't` : 'Your order wasn\'t' }} paid.
            You can complete payment any time from the order below.
          </p>
        </div>
        <button type="button" class="text-sm underline shrink-0" @click="dismissCheckoutStatus">Dismiss</button>
      </div>

      <p v-if="actionError" class="mt-4 text-sm text-red-500">{{ actionError }}</p>

      <div v-if="pending" class="mt-8 text-gray-500">Loading your orders…</div>

      <div v-else-if="!orders.length" class="py-16 mt-8 text-center border rounded-2xl dark:border-gray-800">
        <p class="text-xl font-semibold">No tickets yet</p>
        <p class="mt-2 text-gray-500">Once you book an event, your tickets will appear here.</p>
        <NuxtLink
          to="/events"
          class="inline-block px-5 py-2 mt-6 font-semibold text-white transition duration-200 bg-purple-600 rounded-full hover:bg-purple-700"
        >Browse events</NuxtLink>
      </div>

      <div v-else class="mt-8 space-y-5">
        <div
          v-for="order in orders"
          :key="order.id"
          class="p-6 border rounded-2xl dark:border-gray-800"
        >
          <!-- header -->
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div class="space-y-1">
              <div class="flex items-center space-x-3">
                <span class="text-lg font-semibold">Order #{{ order.id }}</span>
                <span
                  class="px-3 py-1 text-xs font-semibold uppercase rounded-full"
                  :class="statusStyles[order.status]"
                >{{ order.status }}</span>
              </div>
              <div class="text-sm text-gray-400">{{ formatDateTime(order.created_at) }}</div>
            </div>
            <div class="text-right">
              <div class="text-sm text-gray-400">Total</div>
              <div class="text-xl font-bold">{{ formatPrice(order.total_amount) }}</div>
            </div>
          </div>

          <div class="my-5 border-b border-gray-200 dark:border-gray-800"></div>

          <!-- line items -->
          <div class="space-y-2">
            <div
              v-for="item in order.items"
              :key="item.id"
              class="flex items-center justify-between text-sm"
            >
              <span class="text-gray-600 dark:text-gray-400">
                {{ item.quantity }} × ticket ({{ formatPrice(item.unit_price) }} each)
              </span>
              <span class="font-medium">{{ formatPrice(Number(item.unit_price) * item.quantity) }}</span>
            </div>
          </div>

          <!-- issued tickets (paid orders): QR for check-in at the door -->
          <div v-if="order.tickets.length" class="mt-5">
            <div class="mb-3 text-sm font-medium text-gray-500">Your tickets</div>
            <div class="grid gap-4 grid-cols-2 sm:grid-cols-3 lg:grid-cols-5">
              <div
                v-for="ticket in order.tickets"
                :key="ticket.id"
                class="flex flex-col items-center p-3 text-center border rounded-2xl bg-purple-50 border-purple-100 dark:bg-gray-800/60 dark:border-gray-800"
              >
                <div class="relative w-full max-w-[10rem]">
                  <TicketQrCode
                    :value="ticket.code"
                    :class="{ 'opacity-20': ticket.status !== 'valid' }"
                  />
                  <span
                    v-if="ticket.status !== 'valid'"
                    class="absolute px-3 py-1 text-xs font-semibold uppercase -translate-x-1/2 -translate-y-1/2 rounded-full top-1/2 left-1/2"
                    :class="ticket.status === 'used'
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-600 text-white'"
                  >{{ ticket.status === 'used' ? 'Checked in' : 'Cancelled' }}</span>
                </div>
                <div class="mt-2 font-mono text-sm font-semibold tracking-wider text-purple-700 dark:text-purple-300">
                  {{ formatTicketCode(ticket.code) }}
                </div>
                <div class="text-xs text-gray-500">
                  <template v-if="ticket.status === 'used' && ticket.checked_in_at">
                    {{ formatDateTime(ticket.checked_in_at) }}
                  </template>
                  <template v-else>Ticket #{{ ticket.id }}</template>
                </div>
              </div>
            </div>
            <p class="mt-3 text-xs text-gray-400">Show a QR code at the door to check in — one per guest.</p>
          </div>

          <!-- pending: prompt to pay -->
          <div v-if="order.status === 'pending'" class="flex flex-col gap-3 mt-5 sm:flex-row sm:items-center">
            <p class="flex-1 text-sm text-gray-500">
              This order is awaiting payment. Complete checkout to receive your tickets.
            </p>
            <button
              type="button"
              class="px-5 py-2.5 font-semibold text-white transition duration-200 bg-purple-600 rounded-full disabled:opacity-50 hover:bg-purple-700"
              :disabled="busyOrderId === order.id"
              @click="completePayment(order)"
            >
              {{ busyOrderId === order.id ? 'Redirecting…' : 'Complete payment' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
