import crypto from 'node:crypto';
import { z } from 'zod';
import { db, databaseEnabled } from './db';

export const ADMIN_ROLES = ['SUPER_ADMIN', 'OPERATIONS', 'COMPLIANCE', 'FINANCE', 'SUPPORT'] as const;
export type AdminRole = typeof ADMIN_ROLES[number];

export type AdminAuditEvent = {
  id: string;
  actorId: string;
  role: AdminRole;
  action: string;
  targetType: string;
  targetId?: string;
  metadata?: Record<string, unknown>;
  createdAt: string;
};

const auditLog: AdminAuditEvent[] = [];

export const adminActionSchema = z.object({
  actorId: z.string().min(1),
  role: z.enum(ADMIN_ROLES),
  action: z.string().min(2).max(100),
  targetType: z.string().min(2).max(50),
  targetId: z.string().max(100).optional(),
  metadata: z.record(z.unknown()).optional()
});

export function recordAdminAudit(input: z.infer<typeof adminActionSchema>) {
  const event: AdminAuditEvent = {
    id: crypto.randomUUID(),
    ...input,
    createdAt: new Date().toISOString()
  };
  auditLog.unshift(event);
  if (auditLog.length > 1000) auditLog.pop();
  return event;
}

export function getRecentAdminAudit(limit = 100) {
  return auditLog.slice(0, Math.min(Math.max(limit, 1), 1000));
}

export async function adminOverview() {
  if (!databaseEnabled) {
    return {
      persistence: 'memory',
      users: 0,
      pendingDeposits: 0,
      pendingWithdrawals: 0,
      openTrades: 0,
      activeStakes: 0,
      auditEvents: auditLog.length,
      sandbox: true
    };
  }

  const [users, pendingDeposits, pendingWithdrawals, openTrades, activeStakes] = await Promise.all([
    db.user.count(),
    db.deposit.count({ where: { status: 'PENDING' } }),
    db.withdrawal.count({ where: { status: 'PENDING' } }),
    db.trade.count({ where: { status: 'OPEN' } }),
    db.stake.count({ where: { endsAt: { gt: new Date() } } })
  ]);

  return {
    persistence: 'database',
    users,
    pendingDeposits,
    pendingWithdrawals,
    openTrades,
    activeStakes,
    auditEvents: auditLog.length,
    sandbox: true
  };
}

export const ADMIN_FOUNDATION_STATUS = {
  roles: ADMIN_ROLES,
  capabilities: {
    userReview: true,
    depositReview: true,
    withdrawalReview: true,
    tradeMonitoring: true,
    stakingMonitoring: true,
    auditTrail: true,
    realMoneyExecution: false
  },
  note: 'Administrative controls are a foundation only. Production authorization, MFA, approval workflows and immutable audit storage must be implemented before real-money operations.'
} as const;
