import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient({
  datasources: { db: { url: process.env.DATABASE_URL } },
});

async function main() {
  // Kill any connection holding the Prisma migrate advisory lock
  const killed = await prisma.$executeRaw`
    SELECT pg_terminate_backend(pid)
    FROM pg_locks
    WHERE locktype = 'advisory' AND objid = 72707369
  `;
  console.log(`Terminated ${killed} connection(s) holding the advisory lock.`);

  // Mark the init migration as already applied (tables exist from db push)
  await prisma.$executeRaw`
    CREATE TABLE IF NOT EXISTS "_prisma_migrations" (
      id VARCHAR(36) PRIMARY KEY,
      checksum VARCHAR(64) NOT NULL,
      finished_at TIMESTAMPTZ,
      migration_name VARCHAR(255) NOT NULL,
      logs TEXT,
      rolled_back_at TIMESTAMPTZ,
      started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      applied_steps_count INTEGER NOT NULL DEFAULT 0
    )
  `;

  await prisma.$executeRaw`
    INSERT INTO "_prisma_migrations" (id, checksum, finished_at, migration_name, logs, applied_steps_count)
    VALUES (
      gen_random_uuid()::text,
      'd41d8cd98f00b204e9800998ecf8427e',
      NOW(),
      '20260606000000_init',
      NULL,
      1
    )
    ON CONFLICT DO NOTHING
  `;

  console.log('Migration 20260606000000_init marked as applied.');
  await prisma.$disconnect();
}

main().catch(e => { console.error(e); process.exit(1); });
