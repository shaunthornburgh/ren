# Event Ticketing System (ren)

## Project Overview
A full-stack platform where users can create/manage **Events** and buy/sell **Tickets**.

## Tech Stack
- **Backend**: FastAPI + SQLAlchemy 2.0 + PostgreSQL
- **Frontend**: Nuxt 3 (Vue 3 + TypeScript)
- **Database**: PostgreSQL
- **Auth**: JWT + Role-based (customer, organizer, admin)
- **Dev**: Docker + docker-compose (everything containerized)

## Current Docker Setup
- Backend runs on http://localhost:8000
- Frontend runs on http://localhost:3000
- DB runs on localhost:5432
- Hot reload is enabled via volume mounts

## Project Structure (Backend)
backend/app/
├── main.py
├── core/
│   ├── config.py
│   ├── database.py
│   └── security.py
├── models/
├── schemas/
├── crud/
├── api/v1/
└── deps.py

## Core Features (MVP)
**Authentication**
- Register / Login (email + password)
- Roles: customer (default), organizer, admin

**Events**
- Organizers can CRUD events
- Fields: title, description, start_datetime, end_datetime, location, image_url, capacity, status

**Tickets**
- Multiple ticket types per event (price, quantity)
- Users can purchase tickets

**Orders / My Tickets**
- Purchase flow
- View purchased tickets

## Instructions for Claude Code
1. Always respect the existing Docker setup.
2. Work **one module at a time**.
3. Use SQLAlchemy 2.0 declarative style (`Mapped`, etc.).
4. Use Pydantic v2.
5. Add proper error handling (`HTTPException`).
6. First priority: Core setup (config, database, security, auth).

Start by exploring the current files, then implement the core backend foundation.