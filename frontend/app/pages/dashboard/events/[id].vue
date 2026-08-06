<script setup lang="ts">
import type { CalendarRead, EventCreate, EventRead } from '~/types/api'

definePageMeta({ middleware: 'organizer' })

const route = useRoute()
const router = useRouter()
const { apiFetch } = useApi()

const eventId = Number(route.params.id)

const { data: event, pending, error } = await useAsyncData(
  `dashboard-event-${eventId}`,
  () => apiFetch<EventRead>(`/events/${eventId}`),
  { server: false },
)

const { data: calendars } = await useAsyncData(
  'organizer-calendars-for-event-edit',
  () => apiFetch<CalendarRead[]>('/calendars/me'),
  { server: false, default: () => [] as CalendarRead[] },
)

// --- tabs (state synced to the ?tab= query param) ---
const tabs = [
  { key: 'overview', label: 'Overview' },
  { key: 'registration', label: 'Registration' },
  { key: 'guests', label: 'Guests' },
  { key: 'messages', label: 'Messages' },
] as const
type TabKey = (typeof tabs)[number]['key']
const tabKeys = tabs.map((t) => t.key) as readonly string[]

function resolveTab(value: unknown): TabKey {
  return (tabKeys.includes(value as string) ? value : 'overview') as TabKey
}

const activeTab = ref<TabKey>(resolveTab(route.query.tab))

function selectTab(key: TabKey) {
  activeTab.value = key
  router.replace({ query: { ...route.query, tab: key } })
}

// Keep the tab in sync with browser back/forward.
watch(
  () => route.query.tab,
  (value) => {
    const next = resolveTab(value)
    if (next !== activeTab.value) activeTab.value = next
  },
)

// --- overview: save/publish ---
const submitting = ref(false)
const errorMsg = ref('')
const savedAt = ref(false)

// The image upload/remove happens inside the form against its own endpoint;
// keep our event copy in sync when it reports a change.
function onEventUpdated(updated: EventRead) {
  event.value = updated
}

async function updateEvent(payload: EventCreate) {
  errorMsg.value = ''
  savedAt.value = false
  submitting.value = true
  try {
    event.value = await apiFetch<EventRead>(`/events/${eventId}`, {
      method: 'PUT',
      body: payload,
    })
    savedAt.value = true
  } catch (e: any) {
    errorMsg.value =
      e?.data?.detail?.toString() || 'Could not save changes. Please try again.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section>
    <div class="container max-w-screen-xl px-4 py-6 mx-auto md:py-10 lg:py-12">
      <NuxtLink to="/dashboard" class="text-sm text-purple-600 hover:text-purple-700">← Back to dashboard</NuxtLink>

      <div v-if="pending" class="mt-6 text-gray-500">Loading event…</div>

      <div v-else-if="error || !event" class="py-16 mt-6 text-center border rounded-2xl dark:border-gray-800">
        <p class="text-xl font-semibold">Event not found</p>
        <p class="mt-2 text-gray-500">It may have been removed, or you may not have access.</p>
      </div>

      <div v-else>
        <!-- header -->
        <div class="flex items-center justify-between mt-3">
          <h1 class="text-3xl font-bold truncate">{{ event.title }}</h1>
          <NuxtLink :to="`/events/${event.id}`" class="flex-shrink-0 text-sm text-purple-600 hover:text-purple-700">View public page →</NuxtLink>
        </div>

        <!-- tab nav -->
        <div class="flex gap-1 mt-6 overflow-x-auto border-b no-scrollbar dark:border-gray-800">
          <button
            v-for="t in tabs"
            :key="t.key"
            type="button"
            class="px-4 py-3 text-sm font-semibold transition duration-200 border-b-2 whitespace-nowrap -mb-px"
            :class="activeTab === t.key
              ? 'border-purple-600 text-purple-600 dark:text-purple-400'
              : 'border-transparent text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'"
            @click="selectTab(t.key)"
          >{{ t.label }}</button>
        </div>

        <!-- panels -->
        <div class="mt-8">
          <!-- Overview -->
          <div v-show="activeTab === 'overview'" class="space-y-12">
            <div class="space-y-3">
              <h2 class="text-xl font-bold">Event details</h2>
              <div class="p-4 space-y-3 border rounded-2xl bg-gray-50 dark:bg-gray-800/40 dark:border-gray-800">
                <p v-if="savedAt" class="p-2.5 text-sm text-green-700 rounded-lg bg-green-100 dark:bg-green-900 dark:text-green-300">
                  Changes saved.
                </p>
                <OrganizerEventForm
                  :event="event"
                  :calendars="calendars"
                  :submitting="submitting"
                  :error="errorMsg"
                  click-to-edit
                  submit-label="Save changes"
                  @submit="updateEvent"
                  @updated="onEventUpdated"
                />
              </div>
            </div>

            <div class="pt-10 border-t dark:border-gray-800">
              <HostManager :event-id="eventId" />
            </div>

            <div class="pt-10 border-t dark:border-gray-800">
              <AgendaManager :event-id="eventId" />
            </div>

            <div class="pt-10 border-t dark:border-gray-800">
              <FaqManager :event-id="eventId" />
            </div>
          </div>

          <!-- Registration -->
          <div v-show="activeTab === 'registration'" class="space-y-12">
            <TicketTypeManager :event-id="eventId" />
            <div class="pt-10 border-t dark:border-gray-800">
              <QuestionManager :event-id="eventId" />
            </div>
          </div>

          <!-- Guests -->
          <div v-show="activeTab === 'guests'">
            <GuestList :event-id="eventId" />
          </div>

          <!-- Messages -->
          <div v-show="activeTab === 'messages'">
            <MessageComposer :event-id="eventId" />
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
