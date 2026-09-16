import Fastify from 'fastify';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';
import crypto from 'node:crypto';
import { z } from 'zod';

const app = Fastify({ logger: true });
const demoMarkets = [
  { symbol: 'BTCUSDT', display: 'BTC/USDT', source: 'binance', live: true },
  { symbol: 'ETHUSDT', display: 'ETH/USDT', source: 'binance', live: true },
  { symbol: 'XAUUSDT', display: 'XAU/USDT', source: 'provider-required', live: false }
] as const;

type Credential = { id: string; email: string; passwordHash: string };
type Session = { userId: string; tokenHash: string; expiresAt: number };
const credentials = new Map<string, Credential>();
const sessions = new Map<string, Session>();

function hashPassword(password: string) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(password, salt, 64).toString('hex');
  return `${salt}:${hash}`;
}
function verifyPassword(password: string, stored: string) {
  const [salt, expected] = stored.split(':');
  if (!salt || !expected) return false;
  const actual = crypto.scryptSync(password, salt, 64).toString('hex');
  return crypto.timingSafeEqual(Buffer.from(actual), Buffer.from(expected));
}
function issueSession(userId: string) {
  const token = crypto.randomBytes(32).toString('base64url');
  const tokenHash = crypto.createHash('sha256').update(token).digest('hex');
  sessions.set(tokenHash, { userId, tokenHash, expiresAt: Date.now() + 24 * 60 * 60 * 1000 });
  return token;
}
function authenticatedUser(request: { headers: Record<string, string | string[] | undefined> }) {
  const header = request.headers.authorization;
  if (!header || !header.startsWith('Bearer ')) return null;
  const token = header.slice(7);
  const hash = crypto.createHash('sha256').update(token).digest('hex');
  const session = sessions.get(hash);
  if (!session || session.expiresAt <= Date.now()) {
    sessions.delete(hash);
    return null;
  }
  return credentials.get(session.userId) ?? null;
}

async function main() {
  await app.register(helmet);
  // Development-only CORS for the WebView client. Restrict this to the app/web origin before production.
  await app.register(cors, { origin: true });

  app.get('/health', async () => ({ ok: true, service: 'aster-financials-api', environment: process.env.NODE_ENV ?? 'development', timestamp: new Date().toISOString() }));
  app.get('/api/v1/system/status', async () => ({ api: 'online', trading: 'sandbox', blockchain: 'sandbox', message: 'Production integrations are intentionally disabled in this foundation.' }));
  app.get('/api/v1/markets', async () => ({ markets: demoMarkets }));

  app.post('/api/v1/auth/register', async (request, reply) => {
    const parsed = z.object({ email: z.string().email(), password: z.string().min(8) }).safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: 'Valid email and password of at least 8 characters are required' });
    const email = parsed.data.email.toLowerCase();
    if ([...credentials.values()].some(x => x.email === email)) return reply.code(409).send({ error: 'Account already exists' });
    const id = crypto.randomUUID();
    credentials.set(id, { id, email, passwordHash: hashPassword(parsed.data.password) });
    const token = issueSession(id);
    return reply.code(201).send({ user: { id, email, status: 'ACTIVE' }, token, sandbox: true });
  });

  app.post('/api/v1/auth/login', async (request, reply) => {
    const parsed = z.object({ email: z.string().email(), password: z.string() }).safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: 'Invalid credentials format' });
    const user = [...credentials.values()].find(x => x.email === parsed.data.email.toLowerCase());
    if (!user || !verifyPassword(parsed.data.password, user.passwordHash)) return reply.code(401).send({ error: 'Invalid email or password' });
    return { user: { id: user.id, email: user.email, status: 'ACTIVE' }, token: issueSession(user.id), sandbox: true };
  });

  app.post('/api/v1/auth/logout', async (request) => {
    const header = request.headers.authorization;
    if (header?.startsWith('Bearer ')) {
      const hash = crypto.createHash('sha256').update(header.slice(7)).digest('hex');
      sessions.delete(hash);
    }
    return { ok: true };
  });

  app.get('/api/v1/me', async (request, reply) => {
    const user = authenticatedUser(request);
    if (!user) return reply.code(401).send({ error: 'Authentication required' });
    return { user: { id: user.id, email: user.email, status: 'ACTIVE' }, wallets: [{ asset: 'USDT', available: '0.00', locked: '0.00' }], sandbox: true };
  });

  app.get('/api/v1/account/:id', async (request, reply) => {
    const parsed = z.object({ id: z.string().min(1) }).safeParse(request.params);
    if (!parsed.success) return reply.code(400).send({ error: 'Invalid account id' });
    const requester = authenticatedUser(request);
    if (!requester || requester.id !== parsed.data.id) return reply.code(401).send({ error: 'Authentication required' });
    return { id: requester.id, email: requester.email, status: 'ACTIVE', wallets: [{ asset: 'USDT', available: '0.00', locked: '0.00' }], sandbox: true };
  });

  app.post('/api/v1/trades/preview', async (request, reply) => {
    const user = authenticatedUser(request);
    if (!user) return reply.code(401).send({ error: 'Authentication required' });
    const parsed = z.object({ symbol: z.enum(['BTCUSDT', 'ETHUSDT', 'XAUUSDT']), side: z.enum(['HIGHER', 'LOWER']), amount: z.number().positive(), expirySeconds: z.number().int().min(30).max(86400) }).safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: 'Invalid trade preview request' });
    return { sandbox: true, accepted: false, reason: 'Preview only; no real-money order is submitted', userId: user.id, ...parsed.data };
  });

  await app.listen({ host: '0.0.0.0', port: Number(process.env.PORT ?? 3000) });
}
main().catch((error) => { app.log.error(error); process.exit(1); });
