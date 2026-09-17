import crypto from 'node:crypto';
import { getPersistentAudit, persistAuditEvent } from './security-persistence';

export type SecurityAuditEvent = {
  id: string;
  action: string;
  requestId?: string;
  subjectId?: string;
  ip?: string;
  createdAt: string;
  metadata?: Record<string, string>;
};

const auditEvents: SecurityAuditEvent[] = [];
const IDEMPOTENCY_TTL_MS = 10 * 60 * 1000;
const idempotency = new Map<string, { expiresAt: number; response: unknown }>();

export function audit(action: string, data: Omit<SecurityAuditEvent, 'id' | 'action' | 'createdAt'> = {}) {
  const event = { id: crypto.randomUUID(), action, createdAt: new Date().toISOString(), ...data };
  auditEvents.push(event);
  if (auditEvents.length > 5000) auditEvents.splice(0, auditEvents.length - 5000);
  void persistAuditEvent({ action, requestId: data.requestId, subjectId: data.subjectId, ip: data.ip, metadata: data.metadata }).catch(() => undefined);
  return event;
}

export async function getSecurityAudit(limit = 100) {
  const persistent = await getPersistentAudit(limit).catch(() => []);
  if (persistent.length) return persistent;
  return auditEvents.slice(-Math.min(Math.max(limit, 1), 500)).reverse();
}

export function replayProtection(key: string | undefined, response?: unknown) {
  if (!key) return { replay: false, response: undefined };
  const now = Date.now();
  const existing = idempotency.get(key);
  if (existing && existing.expiresAt > now) return { replay: true, response: existing.response };
  if (response !== undefined) idempotency.set(key, { expiresAt: now + IDEMPOTENCY_TTL_MS, response });
  return { replay: false, response: undefined };
}

setInterval(() => {
  const now = Date.now();
  for (const [key, value] of idempotency) if (value.expiresAt <= now) idempotency.delete(key);
}, 60_000).unref();
