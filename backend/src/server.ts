import Fastify from 'fastify';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';
import crypto from 'node:crypto';
import { Prisma } from '@prisma/client';
import { z } from 'zod';
import { db, databaseEnabled } from './db';

const app = Fastify({ logger: true });
const commoditySymbols: Record<string, string> = {
  XAUUSDT: 'XAU/USD', XAGUSDT: 'XAG/USD', WTIUSDT: 'WTI/USD', BRENTUSDT: 'BRENT/USD'
};
const commodityConfigured = Boolean(process.env.TWELVEDATA_API_KEY);
const demoMarkets = [
  { symbol: 'BTCUSDT', display: 'BTC/USDT', source: 'binance', live: true },
  { symbol: 'ETHUSDT', display: 'ETH/USDT', source: 'binance', live: true },
  ...Object.entries(commoditySymbols).map(([symbol, provider]) => ({
    symbol, display: symbol.replace('USDT', '/USDT'),
    source: commodityConfigured ? 'twelve-data' : 'provider-required', live: commodityConfigured, provider
  }))
] as const;

type Credential = { id: string; email: string; passwordHash: string; referralCode?: string };
type Session = { userId: string; tokenHash: string; expiresAt: number };
const credentials = new Map<string, Credential>();
const sessions = new Map<string, Session>();
const adminSessions = new Map<string, number>();

function hashPassword(password: string) {
  const salt = crypto.randomBytes(16).toString('hex');
  return `${salt}:${crypto.scryptSync(password, salt, 64).toString('hex')}`;
}
function verifyPassword(password: string, stored: string) {
  const [salt, expected] = stored.split(':');
  if (!salt || !expected) return false;
  const actual = crypto.scryptSync(password, salt, 64).toString('hex');
  return crypto.timingSafeEqual(Buffer.from(actual), Buffer.from(expected));
}
function tokenHash(token: string) { return crypto.createHash('sha256').update(token).digest('hex'); }
function bearer(request: any) {
  const value = request.headers?.authorization;
  return typeof value === 'string' && value.startsWith('Bearer ') ? value.slice(7) : null;
}
function issueSession(userId: string) {
  const token = crypto.randomBytes(32).toString('base64url');
  const hash = tokenHash(token);
  sessions.set(hash, { userId, tokenHash: hash, expiresAt: Date.now() + 86400000 });
  return token;
}
function issueAdminSession() {
  const token = crypto.randomBytes(32).toString('base64url');
  adminSessions.set(tokenHash(token), Date.now() + 28800000);
  return token;
}
function adminAuthenticated(request: any) {
  const token = bearer(request);
  if (!token) return false;
  const hash = tokenHash(token);
  const exp = adminSessions.get(hash);
  if (!exp || exp <= Date.now()) { adminSessions.delete(hash); return false; }
  return true;
}
function requireAdmin(request: any, reply: any) {
  if (!adminAuthenticated(request)) {
    reply.code(401).send({ error: 'Administrator authentication required' });
    return false;
  }
  return true;
}
async function authenticatedUser(request: any) {
  const token = bearer(request);
  if (!token) return null;
  const hash = tokenHash(token);
  const session = sessions.get(hash);
  if (!session || session.expiresAt <= Date.now()) { if (session) sessions.delete(hash); return null; }
  if (databaseEnabled) return db.user.findUnique({ where: { id: session.userId } });
  return credentials.get(session.userId) ?? null;
}
function decimal(value: string | number) { return new Prisma.Decimal(value); }
async function createDatabaseUser(email: string, passwordHash: string, referralCode?: string) {
  return db.$transaction(async tx => {
    const asset = await tx.asset.upsert({ where: { symbol: 'USDT' }, update: {}, create: { symbol: 'USDT', decimals: 6 } });
    const referrer = referralCode ? await tx.user.findUnique({ where: { referralCode } }) : null;
    if (referralCode && !referrer) throw new Error('INVALID_REFERRAL_CODE');
    const user = await tx.user.create({ data: { email, passwordHash, referralCode: `AST-${crypto.randomBytes(5).toString('hex').toUpperCase()}` } });
    await tx.wallet.create({ data: { userId: user.id, assetId: asset.id, available: 0, locked: 0 } });
    if (referrer && referrer.id !== user.id) await tx.referral.create({ data: { referrerId: referrer.id, refereeId: user.id } });
    return user;
  });
}

async function main() {
  await app.register(helmet);
  await app.register(cors, { origin: true });

  app.get('/health', async () => ({ ok: true, service: 'aster-financials-api', environment: process.env.NODE_ENV ?? 'development', database: databaseEnabled ? 'configured' : 'memory-fallback', commodityProvider: commodityConfigured ? 'twelve-data' : 'not-configured', timestamp: new Date().toISOString() }));
  app.get('/api/v1/system/status', async () => ({ api: 'online', trading: 'sandbox', blockchain: 'sandbox', database: databaseEnabled ? 'configured' : 'memory-fallback', commodityProvider: commodityConfigured ? 'twelve-data' : 'not-configured' }));
  app.get('/api/v1/markets', async () => ({ markets: demoMarkets }));

  app.get('/api/v1/commodities/:symbol/time-series', async (request: any, reply: any) => {
    const symbol = String(request.params.symbol).toUpperCase();
    const providerSymbol = commoditySymbols[symbol];
    if (!providerSymbol) return reply.code(404).send({ error: 'Commodity market not supported' });
    const apiKey = process.env.TWELVEDATA_API_KEY;
    if (!apiKey) return reply.code(503).send({ error: 'Commodity market-data provider is not configured' });
    const parsed = z.object({ interval: z.enum(['1min','5min','15min','30min','45min','1h','2h','4h','8h','1day','1week','1month']).default('1min'), outputsize: z.coerce.number().int().min(1).max(500).default(300) }).safeParse(request.query);
    if (!parsed.success) return reply.code(400).send({ error: 'Invalid commodity interval or output size' });
    const url = new URL('https://api.twelvedata.com/time_series');
    url.searchParams.set('symbol', providerSymbol); url.searchParams.set('interval', parsed.data.interval); url.searchParams.set('outputsize', String(parsed.data.outputsize)); url.searchParams.set('timezone', 'UTC'); url.searchParams.set('apikey', apiKey);
    try {
      const upstream = await fetch(url);
      const data: any = await upstream.json();
      if (!upstream.ok || data?.status === 'error') return reply.code(502).send({ error: data?.message ?? 'Commodity provider request failed' });
      const values = Array.isArray(data?.values) ? data.values : [];
      return { symbol, providerSymbol, source: 'Twelve Data', interval: parsed.data.interval, values: values.map((v: any) => ({ datetime: v.datetime, open: Number(v.open), high: Number(v.high), low: Number(v.low), close: Number(v.close) })).filter((v: any) => [v.open,v.high,v.low,v.close].every(Number.isFinite)) };
    } catch (error) { request.log.error(error); return reply.code(503).send({ error: 'Commodity market-data provider is temporarily unavailable' }); }
  });

  app.post('/api/v1/auth/register', async (request: any, reply: any) => {
    const parsed = z.object({ email: z.string().email(), password: z.string().min(8), referralCode: z.string().min(4).max(64).optional() }).safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: 'Valid email and password of at least 8 characters are required' });
    const email = parsed.data.email.toLowerCase(); const passwordHash = hashPassword(parsed.data.password);
    try {
      if (databaseEnabled) {
        if (await db.user.findUnique({ where: { email } })) return reply.code(409).send({ error: 'Account already exists' });
        const user = await createDatabaseUser(email, passwordHash, parsed.data.referralCode);
        return reply.code(201).send({ user: { id: user.id, email: user.email, status: 'ACTIVE', referralCode: user.referralCode }, token: issueSession(user.id), sandbox: true, persistence: 'database' });
      }
      if ([...credentials.values()].some(x => x.email === email)) return reply.code(409).send({ error: 'Account already exists' });
      const id = crypto.randomUUID(); const referralCode = `AST-${crypto.randomBytes(5).toString('hex').toUpperCase()}`;
      credentials.set(id, { id, email, passwordHash, referralCode });
      return reply.code(201).send({ user: { id, email, status: 'ACTIVE', referralCode }, token: issueSession(id), sandbox: true, persistence: 'memory' });
    } catch (error) {
      if (error instanceof Error && error.message === 'INVALID_REFERRAL_CODE') return reply.code(400).send({ error: 'Invalid referral code' });
      request.log.error(error); return reply.code(500).send({ error: 'Unable to create account' });
    }
  });
  app.post('/api/v1/auth/login', async (request: any, reply: any) => {
    const parsed = z.object({ email: z.string().email(), password: z.string() }).safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: 'Invalid credentials format' });
    const email = parsed.data.email.toLowerCase();
    try {
      const user: any = databaseEnabled ? await db.user.findUnique({ where: { email } }) : ([...credentials.values()].find(x => x.email === email) ?? null);
      if (!user || !verifyPassword(parsed.data.password, user.passwordHash)) return reply.code(401).send({ error: 'Invalid email or password' });
      return { user: { id: user.id, email: user.email, status: 'ACTIVE', referralCode: user.referralCode ?? null }, token: issueSession(user.id), sandbox: true, persistence: databaseEnabled ? 'database' : 'memory' };
    } catch (error) { request.log.error(error); return reply.code(500).send({ error: 'Unable to sign in' }); }
  });
  app.post('/api/v1/auth/logout', async (request: any) => { const token = bearer(request); if (token) sessions.delete(tokenHash(token)); return { ok: true }; });

  app.get('/api/v1/me', async (request: any, reply: any) => {
    const user: any = await authenticatedUser(request); if (!user) return reply.code(401).send({ error: 'Authentication required' });
    if (!databaseEnabled) return { user: { id: user.id, email: user.email, status: 'ACTIVE', referralCode: user.referralCode ?? null }, wallets: [{ asset: 'USDT', available: '0.00', locked: '0.00' }], sandbox: true, persistence: 'memory' };
    const wallets = await db.wallet.findMany({ where: { userId: user.id }, include: { asset: true } });
    return { user: { id: user.id, email: user.email, status: 'ACTIVE', referralCode: user.referralCode }, wallets: wallets.map(w => ({ asset: w.asset.symbol, available: w.available.toString(), locked: w.locked.toString() })), sandbox: true, persistence: 'database' };
  });
  app.get('/api/v1/wallets', async (request: any, reply: any) => {
    const user: any = await authenticatedUser(request); if (!user) return reply.code(401).send({ error: 'Authentication required' });
    if (!databaseEnabled) return { wallets: [{ asset: 'USDT', available: '0.00', locked: '0.00' }], sandbox: true };
    const wallets = await db.wallet.findMany({ where: { userId: user.id }, include: { asset: true } });
    return { wallets: wallets.map(w => ({ id: w.id, asset: w.asset.symbol, available: w.available.toString(), locked: w.locked.toString() })), sandbox: true };
  });
  app.get('/api/v1/wallets/activity', async (request: any, reply: any) => {
    const user: any = await authenticatedUser(request); if (!user) return reply.code(401).send({ error: 'Authentication required' });
    if (!databaseEnabled) return { deposits: [], withdrawals: [], ledger: [], sandbox: true };
    const [deposits, withdrawals, ledger] = await Promise.all([
      db.deposit.findMany({ where: { userId: user.id }, orderBy: { createdAt: 'desc' }, take: 50 }),
      db.withdrawal.findMany({ where: { userId: user.id }, orderBy: { createdAt: 'desc' }, take: 50 }),
      db.ledgerEntry.findMany({ where: { account: user.id }, orderBy: { createdAt: 'desc' }, take: 100 })
    ]);
    return { deposits, withdrawals, ledger, sandbox: true };
  });

  app.post('/api/v1/deposits/request', async (request: any, reply: any) => {
    const user: any = await authenticatedUser(request); if (!user) return reply.code(401).send({ error: 'Authentication required' });
    const parsed = z.object({ asset: z.literal('USDT'), amount: z.coerce.number().positive().max(100000000), txHash: z.string().min(8).max(200).optional() }).safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: 'USDT amount must be positive and valid' });
    if (!databaseEnabled) return { id: crypto.randomUUID(), status: 'PENDING', sandbox: true, message: 'Database is not configured; request was not persisted.' };
    const deposit = await db.deposit.create({ data: { userId: user.id, asset: 'USDT', amount: decimal(parsed.data.amount), txHash: parsed.data.txHash } });
    return reply.code(201).send({ id: deposit.id, asset: deposit.asset, amount: deposit.amount.toString(), status: deposit.status, sandbox: true, message: 'Deposit request recorded. Confirmation is manual in this foundation.' });
  });
  app.post('/api/v1/withdrawals/request', async (request: any, reply: any) => {
    const user: any = await authenticatedUser(request); if (!user) return reply.code(401).send({ error: 'Authentication required' });
    const parsed = z.object({ asset: z.literal('USDT'), amount: z.coerce.number().positive().max(100000000), address: z.string().min(10).max(200) }).safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: 'USDT amount and destination address are required' });
    if (!databaseEnabled) return { id: crypto.randomUUID(), status: 'PENDING', sandbox: true, message: 'Database is not configured; request was not persisted.' };
    try {
      const withdrawal = await db.$transaction(async tx => {
        const wallet = await tx.wallet.findFirst({ where: { userId: user.id, asset: { symbol: 'USDT' } } });
        if (!wallet) throw new Error('WALLET_NOT_FOUND');
        const amount = decimal(parsed.data.amount);
        if (wallet.available.lt(amount)) throw new Error('INSUFFICIENT_BALANCE');
        await tx.wallet.update({ where: { id: wallet.id }, data: { available: { decrement: amount }, locked: { increment: amount } } });
        const created = await tx.withdrawal.create({ data: { userId: user.id, asset: 'USDT', amount, address: parsed.data.address, status: 'PENDING' } });
        await tx.ledgerEntry.createMany({ data: [
          { reference: `withdrawal:${created.id}`, account: user.id, assetSymbol: 'USDT', direction: 'DEBIT', amount },
          { reference: `withdrawal:${created.id}`, account: 'ASTER_WITHDRAWAL_CLEARING', assetSymbol: 'USDT', direction: 'CREDIT', amount }
        ] });
        return created;
      });
      return reply.code(201).send({ id: withdrawal.id, asset: withdrawal.asset, amount: withdrawal.amount.toString(), status: withdrawal.status, sandbox: true, message: 'Withdrawal queued for manual approval. No blockchain transaction was sent.' });
    } catch (error) {
      if (error instanceof Error && error.message === 'INSUFFICIENT_BALANCE') return reply.code(400).send({ error: 'Insufficient available USDT balance' });
      if (error instanceof Error && error.message === 'WALLET_NOT_FOUND') return reply.code(404).send({ error: 'USDT wallet not found' });
      request.log.error(error); return reply.code(500).send({ error: 'Unable to create withdrawal request' });
    }
  });

  app.get('/api/v1/earn/staking', async (request: any, reply: any) => {
    const user: any = await authenticatedUser(request); if (!user) return reply.code(401).send({ error: 'Authentication required' });
    if (!databaseEnabled) return { positions: [], available: '0.00', locked: '0.00', sandbox: true, message: 'Staking requires database persistence.' };
    const [positions, wallet] = await Promise.all([
      db.stake.findMany({ where: { userId: user.id }, orderBy: { startedAt: 'desc' }, take: 50 }),
      db.wallet.findFirst({ where: { userId: user.id, asset: { symbol: 'USDT' } } })
    ]);
    return { positions, available: wallet?.available.toString() ?? '0', locked: wallet?.locked.toString() ?? '0', sandbox: true, productStatus: 'SANDBOX' };
  });
  app.post('/api/v1/earn/staking/preview', async (request: any, reply: any) => {
    const user = await authenticatedUser(request); if (!user) return reply.code(401).send({ error: 'Authentication required' });
    const parsed = z.object({ amount: z.coerce.number().positive(), durationDays: z.coerce.number().int().min(1).max(365) }).safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: 'Valid amount and duration are required' });
    const rateBps = 500; const projected = parsed.data.amount * (rateBps / 10000) * (parsed.data.durationDays / 365);
    return { sandbox: true, accepted: false, reason: 'Preview only; no funds are locked', asset: 'USDT', amount: parsed.data.amount.toFixed(6), durationDays: parsed.data.durationDays, rateBps, projectedReward: projected.toFixed(6) };
  });
  app.post('/api/v1/earn/staking/create', async (request: any, reply: any) => {
    const user: any = await authenticatedUser(request); if (!user) return reply.code(401).send({ error: 'Authentication required' });
    const parsed = z.object({ amount: z.coerce.number().positive(), durationDays: z.coerce.number().int().min(1).max(365) }).safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: 'Valid amount and duration are required' });
    if (!databaseEnabled) return reply.code(503).send({ error: 'Database persistence is required for staking' });
    try {
      const stake = await db.$transaction(async tx => {
        const wallet = await tx.wallet.findFirst({ where: { userId: user.id, asset: { symbol: 'USDT' } } });
        if (!wallet) throw new Error('WALLET_NOT_FOUND');
        const amount = decimal(parsed.data.amount); if (wallet.available.lt(amount)) throw new Error('INSUFFICIENT_BALANCE');
        const endsAt = new Date(Date.now() + parsed.data.durationDays * 86400000); const rateBps = 500;
        await tx.wallet.update({ where: { id: wallet.id }, data: { available: { decrement: amount }, locked: { increment: amount } } });
        const created = await tx.stake.create({ data: { userId: user.id, asset: 'USDT', amount, rateBps, endsAt } });
        await tx.ledgerEntry.createMany({ data: [
          { reference: `stake:${created.id}`, account: user.id, assetSymbol: 'USDT', direction: 'DEBIT', amount },
          { reference: `stake:${created.id}`, account: 'ASTER_STAKING_POOL', assetSymbol: 'USDT', direction: 'CREDIT', amount }
        ] });
        return created;
      });
      return reply.code(201).send({ id: stake.id, asset: stake.asset, amount: stake.amount.toString(), rateBps: stake.rateBps, startedAt: stake.startedAt, endsAt: stake.endsAt, sandbox: true, message: 'Sandbox stake created. Reward settlement is not automatic yet.' });
    } catch (error) {
      if (error instanceof Error && error.message === 'INSUFFICIENT_BALANCE') return reply.code(400).send({ error: 'Insufficient available USDT balance' });
      if (error instanceof Error && error.message === 'WALLET_NOT_FOUND') return reply.code(404).send({ error: 'USDT wallet not found' });
      request.log.error(error); return reply.code(500).send({ error: 'Unable to create stake' });
    }
  });
  app.get('/api/v1/earn/referral', async (request: any, reply: any) => {
    const user: any = await authenticatedUser(request); if (!user) return reply.code(401).send({ error: 'Authentication required' });
    if (!databaseEnabled) return { referralCode: user.referralCode ?? null, referralCount: 0, referrals: [], rewards: [], sandbox: true, rewardStatus: 'NOT_AUTOMATIC' };
    const [account, referrals, rewards] = await Promise.all([
      db.user.findUnique({ where: { id: user.id }, select: { referralCode: true } }),
      db.referral.findMany({ where: { referrerId: user.id }, orderBy: { createdAt: 'desc' }, take: 100 }),
      db.reward.findMany({ where: { userId: user.id, type: 'REFERRAL' }, orderBy: { createdAt: 'desc' }, take: 100 })
    ]);
    return { referralCode: account?.referralCode ?? null, referralCount: referrals.length, referrals: referrals.map(r => ({ id: r.refereeId, joinedAt: r.createdAt })), rewards, sandbox: true, rewardStatus: 'NOT_AUTOMATIC' };
  });
  app.get('/api/v1/rewards', async (request: any, reply: any) => {
    const user: any = await authenticatedUser(request); if (!user) return reply.code(401).send({ error: 'Authentication required' });
    if (!databaseEnabled) return { rewards: [], totals: { all: '0', staking: '0', referral: '0', trading: '0', promotion: '0' }, sandbox: true, rewardStatus: 'NOT_AUTOMATIC' };
    const rewards = await db.reward.findMany({ where: { userId: user.id }, orderBy: { createdAt: 'desc' }, take: 100 });
    const totals: Record<string, string> = { all: '0', staking: '0', referral: '0', trading: '0', promotion: '0' };
    for (const reward of rewards) { totals.all = new Prisma.Decimal(totals.all).plus(reward.amount).toString(); const key = reward.type.toLowerCase(); if (key in totals) totals[key] = new Prisma.Decimal(totals[key]).plus(reward.amount).toString(); }
    return { rewards, totals, sandbox: true, rewardStatus: 'NOT_AUTOMATIC' };
  });

  const tradeSchema = z.object({ market: z.enum(['BTCUSDT','ETHUSDT','XAUUSDT','XAGUSDT','WTIUSDT','BRENTUSDT']), direction: z.enum(['HIGHER','LOWER']), amount: z.coerce.number().positive().max(100000000), expiry: z.coerce.number().int().min(10).max(86400) });
  app.post('/api/v1/trades/preview', async (request: any, reply: any) => {
    const user = await authenticatedUser(request); if (!user) return reply.code(401).send({ error: 'Authentication required' });
    const parsed = tradeSchema.safeParse(request.body); if (!parsed.success) return reply.code(400).send({ error: 'Valid market, direction, amount and expiry are required' });
    return { sandbox: true, accepted: false, ...parsed.data, amount: parsed.data.amount.toFixed(6), message: 'Preview only. No binary trade was executed.' };
  });
  app.get('/api/v1/trades', async (request: any, reply: any) => {
    const user: any = await authenticatedUser(request); if (!user) return reply.code(401).send({ error: 'Authentication required' });
    if (!databaseEnabled) return { trades: [], sandbox: true, persistence: 'memory' };
    const trades = await db.trade.findMany({ where: { userId: user.id }, orderBy: { openedAt: 'desc' }, take: 100 });
    return { trades: trades.map(t => ({ ...t, amount: t.amount.toString() })), sandbox: true, persistence: 'database' };
  });
  app.post('/api/v1/trades/record', async (request: any, reply: any) => {
    const user: any = await authenticatedUser(request); if (!user) return reply.code(401).send({ error: 'Authentication required' });
    const parsed = tradeSchema.safeParse(request.body); if (!parsed.success) return reply.code(400).send({ error: 'Valid market, direction, amount and expiry are required' });
    if (!databaseEnabled) return { trade: { id: crypto.randomUUID(), ...parsed.data, amount: parsed.data.amount.toFixed(6), status: 'PENDING', openedAt: new Date().toISOString(), expiresAt: new Date(Date.now() + parsed.data.expiry * 1000).toISOString() }, sandbox: true, persistence: 'memory' };
    const trade = await db.trade.create({ data: { userId: user.id, market: parsed.data.market, direction: parsed.data.direction, amount: decimal(parsed.data.amount), status: 'PENDING', expiresAt: new Date(Date.now() + parsed.data.expiry * 1000) } });
    return reply.code(201).send({ trade: { ...trade, amount: trade.amount.toString() }, sandbox: true, persistence: 'database', message: 'Trade record created for sandbox activity only. No real-money execution occurred.' });
  });

  app.post('/api/v1/admin/login', async (request: any, reply: any) => {
    const parsed = z.object({ email: z.string().email(), password: z.string() }).safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: 'Invalid admin credentials format' });
    if (parsed.data.email.toLowerCase() !== (process.env.ADMIN_EMAIL ?? '').toLowerCase() || parsed.data.password !== (process.env.ADMIN_PASSWORD ?? '')) return reply.code(401).send({ error: 'Invalid administrator credentials' });
    return { token: issueAdminSession(), expiresIn: 28800, sandbox: true };
  });
  app.post('/api/v1/admin/logout', async (request: any) => { const token = bearer(request); if (token) adminSessions.delete(tokenHash(token)); return { ok: true }; });
  app.get('/api/v1/admin/overview', async (request: any, reply: any) => {
    if (!requireAdmin(request, reply)) return;
    if (!databaseEnabled) return { users: credentials.size, pendingDeposits: 0, pendingWithdrawals: 0, openStakes: 0, sandbox: true };
    const [users, pendingDeposits, pendingWithdrawals, openStakes] = await Promise.all([
      db.user.count(), db.deposit.count({ where: { status: 'PENDING' } }), db.withdrawal.count({ where: { status: 'PENDING' } }), db.stake.count({ where: { endsAt: { gt: new Date() } } })
    ]);
    return { users, pendingDeposits, pendingWithdrawals, openStakes, sandbox: true };
  });
  app.get('/api/v1/admin/users', async (request: any, reply: any) => {
    if (!requireAdmin(request, reply)) return;
    if (!databaseEnabled) return { users: [...credentials.values()].map(u => ({ id: u.id, email: u.email, status: 'ACTIVE', referralCode: u.referralCode })), sandbox: true };
    const users = await db.user.findMany({ orderBy: { createdAt: 'desc' }, take: 500, select: { id: true, email: true, referralCode: true, createdAt: true } });
    return { users, sandbox: true };
  });
  app.get('/api/v1/admin/deposits', async (request: any, reply: any) => {
    if (!requireAdmin(request, reply)) return;
    if (!databaseEnabled) return { deposits: [], sandbox: true };
    const deposits = await db.deposit.findMany({ orderBy: { createdAt: 'desc' }, take: 500, include: { user: { select: { email: true } } } });
    return { deposits, sandbox: true };
  });
  app.get('/api/v1/admin/withdrawals', async (request: any, reply: any) => {
    if (!requireAdmin(request, reply)) return;
    if (!databaseEnabled) return { withdrawals: [], sandbox: true };
    const withdrawals = await db.withdrawal.findMany({ orderBy: { createdAt: 'desc' }, take: 500, include: { user: { select: { email: true } } } });
    return { withdrawals, sandbox: true };
  });
  app.get('/api/v1/admin/stakes', async (request: any, reply: any) => {
    if (!requireAdmin(request, reply)) return;
    if (!databaseEnabled) return { stakes: [], sandbox: true };
    const stakes = await db.stake.findMany({ orderBy: { startedAt: 'desc' }, take: 500, include: { user: { select: { email: true } } } });
    return { stakes, sandbox: true };
  });
  app.get('/api/v1/admin/ledger', async (request: any, reply: any) => {
    if (!requireAdmin(request, reply)) return;
    if (!databaseEnabled) return { ledger: [], sandbox: true };
    const ledger = await db.ledgerEntry.findMany({ orderBy: { createdAt: 'desc' }, take: 1000 });
    return { ledger, sandbox: true };
  });
  app.post('/api/v1/admin/withdrawals/:id/approve', async (request: any, reply: any) => {
    if (!requireAdmin(request, reply)) return;
    if (!databaseEnabled) return reply.code(503).send({ error: 'Database persistence is required' });
    const id = String(request.params.id);
    const withdrawal = await db.withdrawal.findUnique({ where: { id } });
    if (!withdrawal) return reply.code(404).send({ error: 'Withdrawal not found' });
    if (withdrawal.status !== 'PENDING') return reply.code(400).send({ error: 'Withdrawal is not pending' });
    const updated = await db.$transaction(async tx => {
      const result = await tx.withdrawal.update({ where: { id }, data: { status: 'APPROVED' } });
      const wallet = await tx.wallet.findFirst({ where: { userId: withdrawal.userId, asset: { symbol: 'USDT' } } });
      if (wallet) await tx.wallet.update({ where: { id: wallet.id }, data: { locked: { decrement: withdrawal.amount } } });
      return result;
    });
    return { withdrawal: updated, sandbox: true, message: 'Approved internally only. No blockchain transaction was sent.' };
  });

  const port = Number(process.env.PORT ?? 3000);
  await app.listen({ port, host: '0.0.0.0' });
}

main().catch(error => { app.log.error(error); process.exit(1); });
