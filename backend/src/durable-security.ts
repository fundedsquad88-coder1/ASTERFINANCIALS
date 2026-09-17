import crypto from 'node:crypto';
import type { PrismaClient } from '@prisma/client';

export type DurableAuditInput = {
  action: string;
  requestId?: string;
  subjectId?: string;
  ip?: string;
  metadata?: Record<string, unknown>;
};

/**
 * Database-backed security primitives. These are intentionally isolated from
 * route code so authentication and mutation handlers can use the same
 * persistence semantics without storing security state in process memory.
 */
export function hashSecurityToken(token: string) {
  return crypto.createHash('sha256').update(token).digest('hex');
}

export async function writeAuditEvent(db: PrismaClient, event: DurableAuditInput) {
  return db.securityAuditEvent.create({
    data: {
      action: event.action,
      requestId: event.requestId,
      subjectId: event.subjectId,
      ip: event.ip,
      metadata: event.metadata as any,
    },
  });
}

export async function createUserSession(db: PrismaClient, userId: string, ttlMs = 24 * 60 * 60 * 1000) {
  const token = crypto.randomBytes(32).toString('base64url');
  const tokenHash = hashSecurityToken(token);
  await db.session.create({
    data: { userId, tokenHash, expiresAt: new Date(Date.now() + ttlMs) },
  });
  return token;
}

export async function consumeUserSession(db: PrismaClient, token: string) {
  const tokenHash = hashSecurityToken(token);
  const session = await db.session.findUnique({ where: { tokenHash }, include: { user: true } });
  if (!session || session.expiresAt <= new Date()) {
    if (session) await db.session.delete({ where: { id: session.id } }).catch(() => undefined);
    return null;
  }
  await db.session.update({ where: { id: session.id }, data: { lastSeenAt: new Date() } });
  return session.user;
}

export async function revokeUserSession(db: PrismaClient, token: string) {
  await db.session.deleteMany({ where: { tokenHash: hashSecurityToken(token) } });
}

export async function purgeExpiredSecurityState(db: PrismaClient) {
  const now = new Date();
  const [sessions, adminSessions, idempotency] = await Promise.all([
    db.session.deleteMany({ where: { expiresAt: { lte: now } } }),
    db.adminSession.deleteMany({ where: { expiresAt: { lte: now } } }),
    db.idempotencyKey.deleteMany({ where: { expiresAt: { lte: now } } }),
  ]);
  return { sessions: sessions.count, adminSessions: adminSessions.count, idempotency: idempotency.count };
}

export function requestIdempotencyScope(route: string, subjectId?: string) {
  return `${subjectId ?? 'anonymous'}:${route}`;
}

export function requestBodyHash(body: unknown) {
  return crypto.createHash('sha256').update(JSON.stringify(body ?? null)).digest('hex');
}
