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

// A single line in a purchase request.
export interface OrderItemCreate {
  ticket_type_id: number
  quantity: number
}
