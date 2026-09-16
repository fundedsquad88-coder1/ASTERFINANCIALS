import { PrismaClient } from '@prisma/client';

export const db = new PrismaClient();
export const databaseEnabled = Boolean(process.env.DATABASE_URL);

export async function closeDatabase() {
  await db.$disconnect();
}
