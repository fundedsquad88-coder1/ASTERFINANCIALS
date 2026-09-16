import { Prisma } from '@prisma/client';
import { db, databaseEnabled } from './db';

export const SANDBOX_STAKING_RATE_BPS = 500;

export function projectedStakingReward(amount: Prisma.Decimal | number, durationDays: number) {
  const principal = new Prisma.Decimal(amount);
  return principal.mul(SANDBOX_STAKING_RATE_BPS).div(10000).mul(durationDays).div(365);
}

export async function getEarnSummary(userId: string) {
  if (!databaseEnabled) return { available: '0', locked: '0', positions: [], rewards: [], sandbox: true };

  const [wallet, positions, rewards] = await Promise.all([
    db.wallet.findFirst({ where: { userId, asset: { symbol: 'USDT' } } }),
    db.stake.findMany({ where: { userId }, orderBy: { startedAt: 'desc' }, take: 50 }),
    db.reward.findMany({ where: { userId }, orderBy: { createdAt: 'desc' }, take: 100 })
  ]);

  return {
    available: wallet?.available.toString() ?? '0',
    locked: wallet?.locked.toString() ?? '0',
    positions,
    rewards,
    sandbox: true
  };
}
