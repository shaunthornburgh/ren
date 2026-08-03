<script setup lang="ts">
import type { GuestRead } from '~/types/api'

const props = defineProps<{ eventId: number }>()

const { apiFetch } = useApi()
const { formatDate } = useFormat()

const { data: guests, pending } = await useAsyncData(
  `event-${props.eventId}-guests`,
  () => apiFetch<GuestRead[]>(`/events/${props.eventId}/guests`),
  { server: false, default: () => [] as GuestRead[] },
)

const statusStyles: Record<string, string> = {
  paid: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  pending: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
  cancelled: 'bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
}

const totalGuests = computed(() => guests.value.length)
const totalTickets = computed(() =>
  guests.value.reduce((sum, g) => sum + g.total_quantity, 0),
)

// Which guest rows have their answers expanded (keyed by order id).
const open = reactive<Record<number, boolean>>({})
function toggle(orderId: number) {
  open[orderId] = !open[orderId]
}
</script>

<template>
  <div class="space-y-4">
    <div>
      <h2 class="text-2xl font-bold">Guests</h2>
      <p v-if="guests.length" class="mt-1 text-sm text-gray-400">
        {{ totalGuests }} {{ totalGuests === 1 ? 'order' : 'orders' }} · {{ totalTickets }} ticket{{ totalTickets === 1 ? '' : 's' }}
      </p>
    </div>

    <p v-if="pending" class="text-gray-500">Loading guests…</p>

    <div v-else-if="!guests.length" class="py-16 text-center border rounded-2xl dark:border-gray-800">
      <p class="text-xl font-semibold">No guests yet</p>
      <p class="mt-2 text-gray-500">Orders for this event will appear here.</p>
    </div>

    <div v-else class="overflow-hidden border rounded-2xl dark:border-gray-800">
      <table class="w-full text-sm">
        <thead class="text-left text-gray-500 bg-gray-50 dark:bg-gray-800/60">
          <tr>
            <th class="px-4 py-3 font-medium">Guest</th>
            <th class="px-4 py-3 font-medium">Tickets</th>
            <th class="px-4 py-3 font-medium text-center">Qty</th>
            <th class="px-4 py-3 font-medium">Status</th>
            <th class="px-4 py-3 font-medium">Ordered</th>
          </tr>
        </thead>
        <tbody class="divide-y dark:divide-gray-800">
          <template v-for="g in guests" :key="g.order_id">
            <tr class="align-top">
              <td class="px-4 py-3">
                <div class="font-medium">{{ g.full_name || g.email }}</div>
                <div v-if="g.full_name" class="text-gray-400">{{ g.email }}</div>
                <div class="flex items-center gap-2 text-xs text-gray-400">
                  <span>Order #{{ g.order_id }}</span>
                  <button
                    v-if="g.answers.length"
                    type="button"
                    class="font-medium text-purple-600 hover:text-purple-700 dark:text-purple-400"
                    @click="toggle(g.order_id)"
                  >{{ open[g.order_id] ? 'Hide answers' : `${g.answers.length} answer${g.answers.length === 1 ? '' : 's'}` }}</button>
                </div>
              </td>
              <td class="px-4 py-3">
                <div v-for="(line, i) in g.items" :key="i" class="text-gray-600 dark:text-gray-400">
                  {{ line.quantity }} × {{ line.ticket_type_name }}
                </div>
              </td>
              <td class="px-4 py-3 font-semibold text-center">{{ g.total_quantity }}</td>
              <td class="px-4 py-3">
                <span
                  class="px-3 py-1 text-xs font-semibold uppercase rounded-full"
                  :class="statusStyles[g.status]"
                >{{ g.status }}</span>
              </td>
              <td class="px-4 py-3 text-gray-500 whitespace-nowrap">{{ formatDate(g.created_at) }}</td>
            </tr>
            <tr v-if="open[g.order_id] && g.answers.length" class="bg-gray-50 dark:bg-gray-800/40">
              <td colspan="5" class="px-4 py-3">
                <dl class="grid gap-3 sm:grid-cols-2">
                  <div v-for="a in g.answers" :key="a.question_id">
                    <dt class="text-xs font-medium text-gray-400">{{ a.label }}</dt>
                    <dd class="text-sm break-words whitespace-pre-line">{{ a.value }}</dd>
                  </div>
                </dl>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </div>
</template>
