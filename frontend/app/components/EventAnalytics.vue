<script setup lang="ts">
import type { EventAnalytics } from '~/types/api'

const props = defineProps<{ eventId: number }>()

const { apiFetch } = useApi()
const { formatPrice } = useFormat()

const { data, pending, error, refresh } = await useAsyncData(
  `event-analytics-${props.eventId}`,
  () => apiFetch<EventAnalytics>(`/events/${props.eventId}/analytics`),
  { server: false },
)

function percent(rate: number | null) {
  return rate === null ? '—' : `${Math.round(rate * 100)}%`
}

const errorDetail = computed(
  () => (error.value as any)?.data?.detail?.toString() || 'Something went wrong. Please try again.',
)
</script>

<template>
  <div class="space-y-8">
    <div class="flex items-center justify-between gap-4">
      <h2 class="text-xl font-bold">Analytics</h2>
      <button
        type="button"
        :disabled="pending"
        class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold transition duration-200 border rounded-full hover:bg-gray-100 disabled:opacity-50 dark:border-gray-700 dark:hover:bg-gray-800"
        @click="refresh()"
      ><i class="bx bx-refresh" aria-hidden="true"></i> {{ pending ? 'Refreshing…' : 'Refresh' }}</button>
    </div>

    <div v-if="pending && !data" class="text-gray-500">Loading analytics…</div>

    <div v-else-if="error" class="py-12 text-center border rounded-2xl dark:border-gray-800" role="alert">
      <p class="text-xl font-semibold">Could not load analytics</p>
      <p class="mt-2 text-gray-500">{{ errorDetail }}</p>
      <button
        type="button"
        class="px-5 py-2 mt-6 font-semibold text-white transition duration-200 bg-purple-600 rounded-full hover:bg-purple-700"
        @click="refresh()"
      >Retry</button>
    </div>

    <div v-else-if="data && !data.ticket_types.length" class="py-16 text-center border rounded-2xl dark:border-gray-800">
      <p class="text-xl font-semibold">No ticket types yet</p>
      <p class="mt-2 text-gray-500">Add one in the Registration tab to start selling.</p>
    </div>

    <template v-else-if="data">
      <!-- summary tiles -->
      <div class="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div class="p-6 bg-purple-50 rounded-2xl dark:bg-gray-800">
          <div class="font-medium text-gray-500">Tickets sold</div>
          <div class="mt-1 text-3xl font-bold">{{ data.totals.sold }}</div>
        </div>
        <div class="p-6 bg-purple-50 rounded-2xl dark:bg-gray-800">
          <div class="font-medium text-gray-500">Revenue</div>
          <div class="mt-1 text-3xl font-bold">{{ formatPrice(data.totals.revenue) }}</div>
        </div>
        <div class="p-6 bg-purple-50 rounded-2xl dark:bg-gray-800">
          <div class="font-medium text-gray-500">Checked in</div>
          <div class="mt-1 text-3xl font-bold">{{ data.totals.checked_in }}</div>
        </div>
        <div class="p-6 bg-purple-50 rounded-2xl dark:bg-gray-800">
          <div class="font-medium text-gray-500">Attendance</div>
          <div class="mt-1 text-3xl font-bold">{{ percent(data.attendance_rate) }}</div>
          <div class="h-2 mt-3 overflow-hidden bg-purple-100 rounded-full dark:bg-gray-700" aria-hidden="true">
            <div class="h-full bg-purple-600 rounded-full" :style="{ width: `${Math.round((data.attendance_rate ?? 0) * 100)}%` }"></div>
          </div>
        </div>
      </div>

      <!-- per ticket type -->
      <div class="overflow-x-auto border rounded-2xl dark:border-gray-800">
        <table class="w-full text-sm text-left">
          <caption class="sr-only">Sales and attendance by ticket type</caption>
          <thead class="text-xs font-semibold text-gray-500 uppercase bg-gray-50 dark:bg-gray-800/40">
            <tr>
              <th scope="col" class="px-4 py-3">Ticket type</th>
              <th scope="col" class="px-4 py-3 text-right">Price</th>
              <th scope="col" class="px-4 py-3 text-right">Sold</th>
              <th scope="col" class="px-4 py-3 text-right">Remaining</th>
              <th scope="col" class="px-4 py-3 text-right">Checked in</th>
              <th scope="col" class="px-4 py-3 text-right">Revenue</th>
            </tr>
          </thead>
          <tbody class="divide-y dark:divide-gray-800">
            <tr v-for="row in data.ticket_types" :key="row.ticket_type_id">
              <th scope="row" class="px-4 py-3 font-medium">{{ row.name }}</th>
              <td class="px-4 py-3 text-right">{{ formatPrice(row.price) }}</td>
              <td class="px-4 py-3 text-right">{{ row.sold }}</td>
              <td class="px-4 py-3 text-right">{{ row.remaining }}</td>
              <td class="px-4 py-3 text-right">{{ row.checked_in }}</td>
              <td class="px-4 py-3 text-right">{{ formatPrice(row.revenue) }}</td>
            </tr>
          </tbody>
          <tfoot class="font-bold border-t dark:border-gray-800">
            <tr>
              <th scope="row" class="px-4 py-3">Total</th>
              <td class="px-4 py-3"></td>
              <td class="px-4 py-3 text-right">{{ data.totals.sold }}</td>
              <td class="px-4 py-3 text-right">{{ data.totals.remaining }}</td>
              <td class="px-4 py-3 text-right">{{ data.totals.checked_in }}</td>
              <td class="px-4 py-3 text-right">{{ formatPrice(data.totals.revenue) }}</td>
            </tr>
          </tfoot>
        </table>
      </div>

      <!-- orders -->
      <div>
        <h3 class="font-semibold">Orders</h3>
        <dl class="grid grid-cols-3 gap-3 mt-3 sm:w-96">
          <div>
            <dt class="text-xs font-medium text-gray-500">Paid</dt>
            <dd class="font-bold">{{ data.orders.paid }}</dd>
          </div>
          <div>
            <dt class="text-xs font-medium text-gray-500">Pending</dt>
            <dd class="font-bold">{{ data.orders.pending }}</dd>
          </div>
          <div>
            <dt class="text-xs font-medium text-gray-500">Cancelled</dt>
            <dd class="font-bold">{{ data.orders.cancelled }}</dd>
          </div>
        </dl>
      </div>
    </template>
  </div>
</template>
