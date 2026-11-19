# Build Plan

Seeded by `/adopt`. Items 1-15 are already shipped (from git history and the
code); items 16 onward are the roadmap.

Run `/feature` to spec the next unchecked item, or `/feature 16` to pick one.
Keep completed items checked and append new features as the project grows.
Do not renumber completed features; their archived specs refer to those IDs.

## Your features

- [x] 1. **Auth and users** - email/password register and login, JWT, customer/organizer/admin roles
- [x] 2. **Events** - organizer CRUD with draft/published/cancelled status, public listing and detail
- [x] 3. **Ticket types** - multiple priced tiers per event with quantity and max per order
- [x] 4. **Orders** - order creation with inventory reservation, My Orders
- [x] 5. **Stripe payments** - Checkout Session and webhook fulfilment that issues tickets
- [x] 6. **Guest event views** - public event pages and booking UI
- [x] 7. **Organizer dashboard** - manage events, ticket types, guests, hosts, questions, messages
- [x] 8. **Calendars** - organizer calendars with slug pages, followers, new-event notifications
- [x] 9. **Event agendas and FAQ** - agenda items and reorderable FAQ per event
- [x] 10. **Notifications** - in-app notification bell and list, follower emails
- [x] 11. **User profiles** - profile editing, avatars, public profile pages
- [x] 12. **Event images** - upload and remove event cover images
- [x] 13. **Geocoded locations** - Places Autocomplete on the form, map embed on the event page
- [x] 14. **Event search** - search input on the events listing
- [x] 15. **QR tickets and check-in** - per-ticket codes, QR display in My Tickets, door scan check-in with stats
- [ ] 16. **Admin area** - UI for the admin role to manage users, roles, and events
- [ ] 17. **Organizer analytics** - sales, revenue, and attendance reporting on the dashboard
- [ ] 18. **Ticket emails** - email order confirmation with QR tickets after payment
- [ ] 19. **Refunds and cancellations** - refund paid orders via Stripe and handle event cancellation for ticket holders
- [ ] 20. **Forgot password** - password reset flow via email
- [ ] 21. **Discount codes** - organizer-created promo codes that reduce ticket price at checkout
- [ ] 22. **Waitlist** - allow attendees to join a waitlist when an event or ticket type is sold out
- [ ] 23. **Payouts** - organizer payout tracking and status (or Stripe Connect onboarding if you go that route)
- [ ] 24. **Invoices** - downloadable invoices/receipts for completed orders
- [ ] 25. **Event privacy** - private/unlisted events (link-only or invite-only) vs public
- [ ] 26. **Categories and tags** - tag events so search and discovery can filter by category
- [ ] 27. **Profile social links** - add website and social links to user profiles
- [ ] 28. **Add-ons** - optional purchasable extras (e.g. paddle board, merch) attached to an event or order
- [ ] 29. **Invitations** - invite specific people to an event (email or link)
- [ ] 30. **Message templates** - reusable message templates for organizer-to-guest emails
> TODO (confirm): roadmap order is a guess; reorder 16-19 to the order you want
> to build them.
