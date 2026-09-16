import crypto from 'node:crypto';

export type Session = { userId: string; tokenHash: string; expiresAt: Date };

export function hashPassword(password: string): string {
  const salt = crypto.randomBytes(16).toString('hex');
  const derived = crypto.scryptSync(password, salt, 64).toString('hex');
  return `${salt}:${derived}`;
}

export function verifyPassword(password: string, stored: string): boolean {
  const [salt, expected] = stored.split(':');
  if (!salt || !expected) return false;
  const actual = crypto.scryptSync(password, salt, 64).toString('hex');
  return crypto.timingSafeEqual(Buffer.from(actual), Buffer.from(expected));
}

export function createSession(userId: string, ttlHours = 24): Session {
  const token = crypto.randomBytes(32).toString('base64url');
  return { userId, tokenHash: crypto.createHash('sha256').update(token).digest('hex'), expiresAt: new Date(Date.now() + ttlHours * 3600000) };
}
