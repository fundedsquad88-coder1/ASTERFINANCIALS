import type { PrismaClient } from '@prisma/client';
import { purgeExpiredSecurityState } from './durable-security';

export function startSecurityMaintenance(db: PrismaClient, intervalMs = 15 * 60 * 1000) {
  const run = async () => {
    try {
      await purgeExpiredSecurityState(db);
    } catch (error) {
      console.error('security maintenance failed', error);
    }
  };
  void run();
  const timer = setInterval(run, intervalMs);
  timer.unref();
  return () => clearInterval(timer);
}
