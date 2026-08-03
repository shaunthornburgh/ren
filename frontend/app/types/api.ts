// Types mirroring the FastAPI backend schemas (backend/app/schemas).

export type UserRole = 'customer' | 'organizer' | 'admin'
export type EventStatus = 'draft' | 'published' | 'cancelled'
export type OrderStatus = 'pending' | 'paid' | 'cancelled'
export type TicketStatus = 'valid' | 'used' | 'cancelled'

export interface UserRead {
  id: number
  email: string
  full_name: string | null
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface Token {
  access_token: string
  token_type: string
}

export interface EventRead {
  id: number
  title: string
  description: string | null
  start_datetime: string
  end_datetime: string
  location: string | null
  image_url: string | null
  capacity: number | null
  calendar_id: number | null
  status: EventStatus
  organizer_id: number
  created_at: string
  updated_at: string
}

export interface TicketTypeRead {
  id: number
  name: string
  description: string | null
  price: string // Decimal serialised as a string by the API
  quantity_available: number
  max_per_order: number
  event_id: number
  created_at: string
  updated_at: string
}

export interface TicketRead {
  id: number
  status: TicketStatus
  ticket_type_id: number
  owner_id: number
  order_id: number
  created_at: string
  updated_at: string
}

export interface OrderItemRead {
  id: number
  ticket_type_id: number
  quantity: number
  unit_price: string
}

export interface OrderRead {
  id: number
  status: OrderStatus
  total_amount: string
  user_id: number
  items: OrderItemRead[]
  tickets: TicketRead[]
  created_at: string
  updated_at: string
}

export interface CheckoutSessionRead {
  checkout_url: string
  session_id: string
}

// Event + aggregate stats, returned by GET /events/me for the dashboard.
export interface OrganizerEventRead extends EventRead {
  ticket_types_count: number
  tickets_sold: number
  tickets_remaining: number
  revenue: string
}

// Payloads for creating/updating events (organizer dashboard).
export interface EventCreate {
  title: string
  description?: string | null
  start_datetime: string
  end_datetime: string
  location?: string | null
  image_url?: string | null
  capacity?: number | null
  calendar_id?: number | null
  status?: EventStatus
}
export type EventUpdate = Partial<EventCreate>

// Payloads for creating/updating ticket types.
export interface TicketTypeCreate {
  name: string
  description?: string | null
  price: string
  quantity_available: number
  max_per_order?: number
}
export type TicketTypeUpdate = Partial<TicketTypeCreate>

// A single line in a purchase request.
export interface OrderItemCreate {
  ticket_type_id: number
  quantity: number
}

// ---- Agenda / Schedule ----

export interface AgendaItemRead {
  id: number
  event_id: number
  start_time: string
  end_time: string | null
  title: string
  description: string | null
  speaker_name: string | null
  location: string | null
  sort_order: number
  created_at: string
  updated_at: string
}

export interface AgendaItemCreate {
  start_time: string
  end_time?: string | null
  title: string
  description?: string | null
  speaker_name?: string | null
  location?: string | null
  sort_order?: number
}
export type AgendaItemUpdate = Partial<AgendaItemCreate>

// ---- Calendars ----

export interface CalendarRead {
  id: number
  name: string
  slug: string
  description: string | null
  image_url: string | null
  is_public: boolean
  owner_id: number
  follower_count: number
  created_at: string
  updated_at: string
}

// Public calendar page payload: calendar + upcoming events + caller's state.
export interface CalendarWithEvents extends CalendarRead {
  upcoming_events: EventRead[]
  is_following: boolean
}

export interface CalendarCreate {
  name: string
  slug?: string | null
  description?: string | null
  image_url?: string | null
  is_public?: boolean
}
export type CalendarUpdate = Partial<Omit<CalendarCreate, 'slug'>>

export interface CalendarFollower {
  user_id: number
  email: string
  full_name: string | null
  followed_at: string
}

// Returned by the follow / unfollow endpoints.
export interface FollowState {
  following: boolean
  follower_count: number
}

// ---- Notifications ----

export type NotificationType = 'event_published'

export interface NotificationRead {
  id: number
  type: NotificationType
  title: string
  message: string | null
  event_id: number | null
  calendar_id: number | null
  is_read: boolean
  created_at: string
}
