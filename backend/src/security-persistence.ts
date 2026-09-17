import crypto from 'node:crypto';
import { db, databaseEnabled } from './db';

const SESSION_TTL_MS = 24 * 60 * 60 * 1000;
const ADMIN_SESSION_TTL_MS = 8 * 60 * 60 * 1000;
const IDEMPOTENCY_TTL_MS = 10 * 60 * 1000;

export function hashToken(token: string) {
  return crypto.createHash('sha256').update(token).digest('hex');
}

export async function createUserSession(userId: string) {
  const token = crypto.randomBytes(32).toString('base64url');
  const tokenHash = hashToken(token);
  if (databaseEnabled) {
    await db.session.create({ data: { userId, tokenHash, expiresAt: new Date(Date.now() + SESSION_TTL_MS) } });
  }
  return token;
}

export async function resolveUserSession(token: string) {
  if (!databaseEnabled) return null;
  const tokenHash = hashToken(token);
  const session = await db.session.findUnique({ where: { tokenHash }, include: { user: true } });
  if (!session) return null;
  if (session.expiresAt.getTime() <= Date.now()) {
    await db.session.delete({ where: { id: session.id } }).catch(() => undefined);
    return null;
  }
  await db.session.update({ where: { id: session.id }, data: { lastSeenAt: new Date() } });
  return session.user;
}

export async function revokeUserSession(token: string) {
  if (!databaseEnabled) return;
  await db.session.deleteMany({ where: { tokenHash: hashToken(token) } });
}

export async function persistAuditEvent(event: { action: string; requestId?: string; subjectId?: string; ip?: string; metadata?: Record<string, string> }) {
  if (!databaseEnabled) return;
  await db.securityAuditEvent.create({ data: { ...event, metadata: event.metadata ?? undefined } });
}

export async function getPersistentAudit(limit = 100) {
  if (!databaseEnabled) return [];
  return db.securityAuditEvent.findMany({ orderBy: { createdAt: 'desc' }, take: Math.min(Math.max(limit, 1), 500) });
}

export async function claimIdempotency(scope: string, key: string, requestHash: string) {
  if (!databaseEnabled) return { replay: false as const, responseStatus: undefined, responseBody: undefined };
  const existing = await db.idempotencyKey.findUnique({ where: { scope_key: { scope, key } } });
  if (existing && existing.expiresAt.getTime() > Date.now()) {
    if (existing.requestHash !== requestHash) throw new Error('IDEMPOTENCY_KEY_REUSED');
    return { replay: true as const, responseStatus: existing.responseStatus ?? 200, responseBody: existing.responseBody };
  }
  if (existing) await db.idempotencyKey.delete({ where: { id: existing.id } }).catch(() => undefined);
  await db.idempotencyKey.create({ data: { scope, key, requestHash, expiresAt: new Date(Date.now() + IDEMPOTENCY_TTL_MS) } });
  return { replay: false as const, responseStatus: undefined, responseBody: undefined };
}

export async function completeIdempotency(scope: string, key: string, status: number, body: unknown) {
  if (!databaseEnabled) return;
  await db.idempotencyKey.updateMany({ where: { scope, key }, data: { responseStatus: status, responseBody: body as any } });
}

export async function cleanupSecurityState() {
  if (!databaseEnabled) return;
  const now = new Date();
  await Promise.all([
    db.session.deleteMany({ where: { expiresAt: { lte: now } } }),
    db.adminSession.deleteMany({ where: { expiresAt: { lte: now } } }),
    db.idempotencyKey.deleteMany({ where: { expiresAt: { lte: now } } }),
  ]);
}

export { ADMIN_SESSION_TTL_MS };
