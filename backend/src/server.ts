import Fastify from 'fastify';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';
import crypto from 'node:crypto';
import { Prisma } from '@prisma/client';
import { z } from 'zod';
import { db, databaseEnabled } from './db';

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
function bearerToken(request: { headers: Record<string, string | string[] | undefined> }) {
  const value = request.headers.authorization;
  if (typeof value !== 'string' || !value.startsWith('Bearer ')) return null;
  return value.slice(7);
}
async function authenticatedUser(request: { headers: Record<string, string | string[] | undefined> }) {
  const token = bearerToken(request);
  if (!token) return null;
  const hash = crypto.createHash('sha256').update(token).digest('hex');
  const session = sessions.get(hash);
  if (!session || session.expiresAt <= Date.now()) {
    sessions.delete(hash);
    return null;
  }
  if (databaseEnabled) return db.user.findUnique({ where: { id: session.userId } });
  return credentials.get(session.userId) ?? null;
}
async function createDatabaseUser(email: string, passwordHash: string) {
  return db.$transaction(async tx => {
    const asset = await tx.asset.upsert({ where: { symbol: 'USDT' }, update: {}, create: { symbol: 'USDT', decimals: 6 } });
    const user = await tx.user.create({ data: { email, passwordHash } });
    await tx.wallet.create({ data: { userId: user.id, assetId: asset.id, available: 0, locked: 0 } });
    return user;
  });
}
function decimal(value: string | number) { return new Prisma.Decimal(value); }

async function main() {
  await app.register(helmet);
  await app.register(cors, { origin: true });

  app.get('/health', async () => ({ ok: true, service: 'aster-financials-api', environment: process.env.NODE_ENV ?? 'development', database: databaseEnabled ? 'configured' : 'memory-fallback', timestamp: new Date().toISOString() }));
  app.get('/api/v1/system/status', async () => ({ api: 'online', trading: 'sandbox', blockchain: 'sandbox', database: databaseEnabled ? 'configured' : 'memory-fallback', message: 'Production integrations are intentionally disabled in this foundation.' }));
  app.get('/api/v1/markets', async () => ({ markets: demoMarkets }));

  app.post('/api/v1/auth/register', async (request, reply) => {
    const parsed = z.object({ email: z.string().email(), password: z.string().min(8) }).safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: 'Valid email and password of at least 8 characters are required' });
    const email = parsed.data.email.toLowerCase();
    const passwordHash = hashPassword(parsed.data.password);
    try {
      if (databaseEnabled) {
        if (await db.user.findUnique({ where: { email } })) return reply.code(409).send({ error: 'Account already exists' });
        const user = await createDatabaseUser(email, passwordHash);
        return reply.code(201).send({ user: { id: user.id, email: user.email, status: 'ACTIVE' }, token: issueSession(user.id), sandbox: true, persistence: 'database' });
      }
      if ([...credentials.values()].some(x => x.email === email)) return reply.code(409).send({ error: 'Account already exists' });
      const id = crypto.randomUUID(); credentials.set(id, { id, email, passwordHash });
      return reply.code(201).send({ user: { id, email, status: 'ACTIVE' }, token: issueSession(id), sandbox: true, persistence: 'memory' });
    } catch (error) { request.log.error(error); return reply.code(500).send({ error: 'Unable to create account' }); }
  });

  app.post('/api/v1/auth/login', async (request, reply) => {
    const parsed = z.object({ email: z.string().email(), password: z.string() }).safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: 'Invalid credentials format' });
    const email = parsed.data.email.toLowerCase();
    try {
      const user = databaseEnabled ? await db.user.findUnique({ where: { email } }) : [...credentials.values()].find(x => x.email === email) ?? null;
      if (!user || !verifyPassword(parsed.data.password, user.passwordHash)) return reply.code(401).send({ error: 'Invalid email or password' });
      return { user: { id: user.id, email: user.email, status: 'ACTIVE' }, token: issueSession(user.id), sandbox: true, persistence: databaseEnabled ? 'database' : 'memory' };
    } catch (error) { request.log.error(error); return reply.code(500).send({ error: 'Unable to sign in' }); }
  });

  app.post('/api/v1/auth/logout', async request => {
    const token = bearerToken(request);
    if (token) sessions.delete(crypto.createHash('sha256').update(token).digest('hex'));
    return { ok: true };
  });

  app.get('/api/v1/me', async (request, reply) => {
    const user = await authenticatedUser(request);
    if (!user) return reply.code(401).send({ error: 'Authentication required' });
    if (!databaseEnabled) return { user: { id: user.id, email: user.email, status: 'ACTIVE' }, wallets: [{ asset: 'USDT', available: '0.00', locked: '0.00' }], sandbox: true, persistence: 'memory' };
    const wallets = await db.wallet.findMany({ where: { userId: user.id }, include: { asset: true } });
    return { user: { id: user.id, email: user.email, status: 'ACTIVE' }, wallets: wallets.map(w => ({ asset: w.asset.symbol, available: w.available.toString(), locked: w.locked.toString() })), sandbox: true, persistence: 'database' };
  });

  app.get('/api/v1/wallets', async (request, reply) => {
    const user = await authenticatedUser(request);
    if (!user) return reply.code(401).send({ error: 'Authentication required' });
    if (!databaseEnabled) return { wallets: [{ asset: 'USDT', available: '0.00', locked: '0.00' }], sandbox: true };
    const wallets = await db.wallet.findMany({ where: { userId: user.id }, include: { asset: true } });
    return { wallets: wallets.map(w => ({ id: w.id, asset: w.asset.symbol, available: w.available.toString(), locked: w.locked.toString() })), sandbox: true };
  });

  app.get('/api/v1/wallets/activity', async (request, reply) => {
    const user = await authenticatedUser(request);
    if (!user) return reply.code(401).send({ error: 'Authentication required' });
    if (!databaseEnabled) return { deposits: [], withdrawals: [], ledger: [], sandbox: true };
    const [deposits, withdrawals, ledger] = await Promise.all([
      db.deposit.findMany({ where: { userId: user.id }, orderBy: { createdAt: 'desc' }, take: 50 }),
      db.withdrawal.findMany({ where: { userId: user.id }, orderBy: { createdAt: 'desc' }, take: 50 }),
      db.ledgerEntry.findMany({ where: { account: user.id }, orderBy: { createdAt: 'desc' }, take: 100 })
    ]);
    return { deposits, withdrawals, ledger, sandbox: true };
  });

  app.post('/api/v1/deposits/request', async (request, reply) => {
    const user = await authenticatedUser(request);
    if (!user) return reply.code(401).send({ error: 'Authentication required' });
    const parsed = z.object({ asset: z.literal('USDT'), amount: z.coerce.number().positive().max(100000000), txHash: z.string().min(8).max(200).optional() }).safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: 'USDT amount must be positive and valid' });
    if (!databaseEnabled) return { id: crypto.randomUUID(), status: 'PENDING', sandbox: true, message: 'Database is not configured; request was not persisted.' };
    const deposit = await db.deposit.create({ data: { userId: user.id, asset: 'USDT', amount: decimal(parsed.data.amount), txHash: parsed.data.txHash } });
    return reply.code(201).send({ id: deposit.id, asset: deposit.asset, amount: deposit.amount.toString(), status: deposit.status, sandbox: true, message: 'Deposit request recorded. Confirmation is intentionally manual in this foundation.' });
  });

  app.post('/api/v1/withdrawals/request', async (request, reply) => {
    const user = await authenticatedUser(request);
    if (!user) return reply.code(401).send({ error: 'Authentication required' });
    const parsed = z.object({ asset: z.literal('USDT'), amount: z.coerce.number().positive().max(100000000), address: z.string().min(10).max(200) }).safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: 'USDT amount and destination address are required' });
    if (!databaseEnabled) return { id: crypto.randomUUID(), status: 'PENDING', sandbox: true, message: 'Database is not configured; request was not persisted.' };
    try {
      const result = await db.$transaction(async tx => {
        const wallet = await tx.wallet.findFirst({ where: { userId: user.id, asset: { symbol: 'USDT' } } });
        if (!wallet) throw new Error('WALLET_NOT_FOUND');
        const amount = decimal(parsed.data.amount);
        if (wallet.available.lt(amount)) throw new Error('INSUFFICIENT_BALANCE');
        const updated = await tx.wallet.update({ where: { id: wallet.id }, data: { available: { decrement: amount }, locked: { increment: amount } } });
        const withdrawal = await tx.withdrawal.create({ data: { userId: user.id, asset: 'USDT', amount, address: parsed.data.address, status: 'PENDING' } });
        const reference = `withdrawal:${withdrawal.id}`;
        await tx.ledgerEntry.createMany({ data: [
          { reference, account: user.id, assetSymbol: 'USDT', direction: 'DEBIT', amount },
          { reference, account: 'ASTER_WITHDRAWAL_CLEARING', assetSymbol: 'USDT', direction: 'CREDIT', amount }
        ] });
        return { withdrawal, updated };
      });
      return reply.code(201).send({ id: result.withdrawal.id, asset: result.withdrawal.asset, amount: result.withdrawal.amount.toString(), status: result.withdrawal.status, sandbox: true, message: 'Withdrawal queued for manual approval. No blockchain transaction was sent.' });
    } catch (error) {
      if (error instanceof Error && error.message === 'INSUFFICIENT_BALANCE') return reply.code(400).send({ error: 'Insufficient available USDT balance' });
      if (error instanceof Error && error.message === 'WALLET_NOT_FOUND') return reply.code(404).send({ error: 'USDT wallet not found' });
      request.log.error(error); return reply.code(500).send({ error: 'Unable to create withdrawal request' });
    }
  });

  app.post('/api/v1/trades/preview', async (request, reply) => {
    const user = await authenticatedUser(request);
    if (!user) return reply.code(401).send({ error: 'Authentication required' });
    const parsed = z.object({ symbol: z.enum(['BTCUSDT', 'ETHUSDT', 'XAUUSDT']), side: z.enum(['HIGHER', 'LOWER']), amount: z.number().positive(), expirySeconds: z.number().int().min(30).max(86400) }).safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: 'Invalid trade preview request' });
    return { sandbox: true, accepted: false, reason: 'Preview only; no real-money order is submitted', userId: user.id, ...parsed.data };
  });

  await app.listen({ host: '0.0.0.0', port: Number(process.env.PORT ?? 3000) });
}
main().catch(async error => { app.log.error(error); await db.$disconnect().catch(() => undefined); process.exit(1); });
