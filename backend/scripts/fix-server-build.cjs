const fs = require('node:fs');
const path = require('node:path');

const file = path.join(__dirname, '..', 'src', 'server.ts');
let text = fs.readFileSync(file, 'utf8');

// Normalize the compact admin list-return statements produced in server.ts.
for (const name of ['deposits', 'withdrawals', 'stakes', 'ledger']) {
  const pattern = new RegExp(`return \\{ ${name}: await ([^\\n]+?) \\}\\); \\}\\);`, 'g');
  text = text.replace(pattern, `return { ${name}: await $1 }; });`);
}

const marker = '// ASTER_PERSISTED_TRADE_ROUTES';
if (!text.includes(marker)) {
  const routes = `
  ${marker}
  app.get('/api/v1/trades', async (request: any, reply: any) => {
    const u: any = await authenticatedUser(request);
    if (!u) return reply.code(401).send({ error: 'Authentication required' });
    if (!databaseEnabled) return { trades: [], sandbox: true, persistence: 'memory', message: 'Database is not configured; trade history is not persisted.' };
    const p = z.object({ status: z.enum(['OPEN','HISTORY','ALL']).default('ALL') }).safeParse(request.query);
    if (!p.success) return reply.code(400).send({ error: 'Invalid trade status' });
    const now = new Date();
    const where: any = { userId: u.id };
    if (p.data.status === 'OPEN') where.status = 'OPEN';
    if (p.data.status === 'HISTORY') where.NOT = { status: 'OPEN' };
    const rows = await db.trade.findMany({ where, orderBy: { openedAt: 'desc' }, take: 100 });
    const trades = rows.map((t: any) => ({ id: t.id, market: t.market, direction: t.direction, amount: t.amount.toString(), status: t.status === 'OPEN' && t.expiresAt <= now ? 'EXPIRED' : t.status, openedAt: t.openedAt.toISOString(), expiresAt: t.expiresAt.toISOString(), settledAt: t.settledAt?.toISOString() ?? null }));
    return { trades, sandbox: true, persistence: 'database' };
  });

  app.post('/api/v1/trades/record', async (request: any, reply: any) => {
    const u: any = await authenticatedUser(request);
    if (!u) return reply.code(401).send({ error: 'Authentication required' });
    const p = z.object({ market: z.string().min(3).max(32), direction: z.enum(['HIGHER','LOWER']), amount: z.coerce.number().positive().max(100000000), expiry: z.coerce.number().int().min(30).max(86400) }).safeParse(request.body);
    if (!p.success) return reply.code(400).send({ error: 'Valid market, direction, amount and expiry are required' });
    if (!databaseEnabled) return { id: crypto.randomUUID(), status: 'OPEN', sandbox: true, persisted: false, message: 'Database is not configured; preview was not persisted.' };
    const openedAt = new Date();
    const expiresAt = new Date(openedAt.getTime() + p.data.expiry * 1000);
    const trade = await db.trade.create({ data: { userId: u.id, market: p.data.market, direction: p.data.direction, amount: decimal(p.data.amount), status: 'OPEN', openedAt, expiresAt } });
    return reply.code(201).send({ id: trade.id, market: trade.market, direction: trade.direction, amount: trade.amount.toString(), status: trade.status, openedAt: trade.openedAt.toISOString(), expiresAt: trade.expiresAt.toISOString(), sandbox: true, persisted: true, message: 'Sandbox trade preview persisted.' });
  });
`;
  const needle = "  app.post('/api/v1/auth/register'";
  if (!text.includes(needle)) throw new Error('Trade route insertion point not found');
  text = text.replace(needle, routes + needle);
}

fs.writeFileSync(file, text);
console.log('Applied server syntax normalization and persisted sandbox trade routes.');
