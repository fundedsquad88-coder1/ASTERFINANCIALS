import { PrismaClient } from '@prisma/client';
import { startSecurityMaintenance } from './security-maintenance';

export const db = new PrismaClient();
export const databaseEnabled = Boolean(process.env.DATABASE_URL);

const stopSecurityMaintenance = databaseEnabled ? startSecurityMaintenance(db) : undefined;

export async function closeDatabase() {
  if (stopSecurityMaintenance) stopSecurityMaintenance();
  await db.$disconnect();
}
