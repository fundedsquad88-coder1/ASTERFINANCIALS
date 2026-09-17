import crypto from 'node:crypto';
import { db, databaseEnabled } from './db';
import { hashToken, createUserSession, resolveUserSession, revokeUserSession, persistAuditEvent, getPersistentAudit, claimIdempotency, completeIdempotency } from './security-persistence';

export { hashToken, createUserSession, resolveUserSession, revokeUserSession, persistAuditEvent, getPersistentAudit, claimIdempotency, completeIdempotency };

export function bearerFromRequest(request: any) {
  const value = request.headers?.authorization;
  return typeof value === 'string' && value.startsWith('Bearer ') ? value.slice(7) : null;
}

export async function resolveAdminSession(token: string) {
  if (!databaseEnabled) return null;
  const session = await db.adminSession.findUnique({ where: { tokenHash: hashToken(token) }, include: { adminUser: true } });
  if (!session || !session.adminUser.enabled || session.expiresAt.getTime() <= Date.now()) {
    if (session) await db.adminSession.delete({ where: { id: session.id } }).catch(() => undefined);
    return null;
  }
  await db.adminSession.update({ where: { id: session.id }, data: { lastSeenAt: new Date() } });
  return session.adminUser;
}

export async function createAdminSession(adminUserId: string, ttlMs = 8 * 60 * 60 * 1000) {
  const token = crypto.randomBytes(32).toString('base64url');
  if (databaseEnabled) await db.adminSession.create({ data: { adminUserId, tokenHash: hashToken(token), expiresAt: new Date(Date.now() + ttlMs) } });
  return token;
}

export async function revokeAdminSession(token: string) {
  if (databaseEnabled) await db.adminSession.deleteMany({ where: { tokenHash: hashToken(token) } });
}

export async function requireAdminRole(request: any, reply: any, allowedRoles: string[] = []) {
  const token = bearerFromRequest(request);
  if (!token) { reply.code(401).send({ error: 'Administrator authentication required' }); return null; }
  const admin = await resolveAdminSession(token);
  if (!admin) { reply.code(401).send({ error: 'Administrator session is invalid or expired' }); return null; }
  if (allowedRoles.length && !allowedRoles.includes(admin.role)) { reply.code(403).send({ error: 'Administrator role is not permitted for this action' }); return null; }
  return admin;
}

export function requestBodyHash(body: unknown) {
  return crypto.createHash('sha256').update(JSON.stringify(body ?? null)).digest('hex');
}

export async function idempotentMutation(request: any, reply: any, scope: string) {
  const key = request.headers?.['idempotency-key'];
  if (typeof key !== 'string' || key.length < 16 || key.length > 200) return null;
  try {
    const state = await claimIdempotency(scope, key, requestBodyHash(request.body));
    if (state.replay) { reply.code(state.responseStatus ?? 200); return state.responseBody; }
    return { key, scope };
  } catch (error) {
    if (error instanceof Error && error.message === 'IDEMPOTENCY_KEY_REUSED') { reply.code(409); return { error: 'Idempotency key was already used with a different request body' }; }
    throw error;
  }
}
