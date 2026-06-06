# Auction App

A full-stack vehicle auction platform that aggregates listings from **Copart** and **IAAI**, allowing users to search, watch, and bid on salvage and used vehicles.

## Tech Stack

| Layer    | Technology                              |
|----------|-----------------------------------------|
| Backend  | Node.js · Express · TypeScript          |
| Database | PostgreSQL (Railway) · Prisma ORM       |
| Frontend | Next.js 15 · React 19 · Tailwind CSS    |
| Monorepo | npm workspaces                          |

## Project Structure

```
auction-app/
├── backend/          # Express API + Prisma
│   ├── prisma/       # schema.prisma
│   └── src/
│       └── index.ts  # Entry point — GET /health
└── frontend/         # Next.js App Router
    └── src/app/
```

## Getting Started

### Prerequisites
- Node.js 18+
- A Railway account (or any PostgreSQL instance)

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/auction-app.git
cd auction-app
```

### 2. Install dependencies

```bash
npm install
```

### 3. Set up environment variables

```bash
cp backend/.env.example backend/.env
```

Fill in `backend/.env`:

```env
DATABASE_URL="postgresql://..."   # Railway public URL
JWT_SECRET="your-secret"

PROXY_HOST=""
PROXY_USER=""
PROXY_PASS=""

COPART_EMAIL=""
COPART_PASSWORD=""
IAAI_EMAIL=""
IAAI_PASSWORD=""
```

### 4. Push the database schema

```bash
npm run db:push
```

### 5. Run locally

```bash
# Terminal 1 — backend (http://localhost:4000)
npm run dev:backend

# Terminal 2 — frontend (http://localhost:3000)
npm run dev:frontend
```

### Health check

```bash
curl http://localhost:4000/health
# → { "status": "ok", "message": "API running" }
```

## Database Scripts

| Command              | Description                          |
|----------------------|--------------------------------------|
| `npm run db:push`    | Sync schema to DB (dev)              |
| `npm run db:migrate` | Create a tracked migration           |
| `npm run db:generate`| Regenerate Prisma Client             |
| `npm run db:studio`  | Open Prisma Studio (visual DB UI)    |
