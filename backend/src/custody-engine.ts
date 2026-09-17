import type { FastifyInstance } from 'fastify';
import { Prisma } from '@prisma/client';
import { z } from 'zod';
import { db, databaseEnabled } from './db';
import { audit } from './security';
import { bearerFromRequest, requireAdminRole, resolveUserSession, idempotentMutation, completeIdempotency } from './route-security';

type Network = 'TRC20' | 'BEP20';

const TRON_USDT = process.env.TRON_USDT_CONTRACT ?? 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t';
const BSC_USDT = (process.env.BSC_USDT_CONTRACT ?? '0x55d398326f99059ff775485246999027b3197955').toLowerCase();
const TRONGRID_URL = (process.env.TRONGRID_API_URL ?? 'https://api.trongrid.io').replace(/\/$/, '');
const BSC_RPC_URL = process.env.BSC_RPC_URL ?? '';
const TRONGRID_API_KEY = process.env.TRONGRID_API_KEY ?? '';
const TRON_CONFIRMATIONS = Number(process.env.TRON_CONFIRMATIONS ?? 1);
const BSC_CONFIRMATIONS = Number(process.env.BSC_CONFIRMATIONS ?? 15);
const BSC_SCAN_BLOCKS = Number(process.env.BSC_SCAN_BLOCKS ?? 500);
const TRANSFER_TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a0df523b3ef';

function decimal(value: string | number) { return new Prisma.Decimal(value); }
function normalizeEvmAddress(value: string) { return value.trim().toLowerCase(); }
function topicAddress(value: string) { return `0x${value.replace(/^0x/, '').slice(-40).toLowerCase()}`; }
function userFromRequest(request: any) {
  const token = bearerFromRequest(request);
  return token && databaseEnabled ? resolveUserSession(token) : null;
}

async function creditConfirmedDeposit(input: { network: Network; txHash: string; asset: string; amount: Prisma.Decimal; fromAddress?: string; toAddress: string; blockNumber?: bigint; confirmations: number; raw?: unknown }) {
  if (!databaseEnabled || input.amount.lte(0)) return null;
  const existing = await db.custodyTransaction.findUnique({ where: { network_txHash: { network: input.network, txHash: input.txHash } } });
  if (existing?.status === 'CONFIRMED') return existing;
  const destination = input.network === 'BEP20' ? normalizeEvmAddress(input.toAddress) : input.toAddress;
  const address = await db.depositAddress.findFirst({ where: { network: input.network, address: input.network === 'BEP20' ? { equals: destination, mode: 'insensitive' } : destination, active: true } });
  if (!address) return null;
  if (input.confirmations < (input.network === 'TRC20' ? TRON_CONFIRMATIONS : BSC_CONFIRMATIONS)) return null;

  return db.$transaction(async tx => {
    const current = await tx.custodyTransaction.findUnique({ where: { network_txHash: { network: input.network, txHash: input.txHash } } });
    if (current?.status === 'CONFIRMED') return current;
    const deposit = await tx.deposit.create({ data: { userId: address.userId, asset: input.asset, network: input.network, amount: input.amount, txHash: input.txHash, depositAddressId: address.id, confirmations: input.confirmations, status: 'CONFIRMED', confirmedAt: new Date() } });
    const wallet = await tx.wallet.findFirst({ where: { userId: address.userId, asset: { symbol: input.asset } } });
    if (!wallet) throw new Error('WALLET_NOT_FOUND_FOR_DEPOSIT');
    await tx.wallet.update({ where: { id: wallet.id }, data: { available: { increment: input.amount } } });
    await tx.ledgerEntry.createMany({ data: [
      { reference: `deposit:${deposit.id}`, account: address.userId, assetSymbol: input.asset, direction: 'CREDIT', amount: input.amount },
      { reference: `deposit:${deposit.id}`, account: `ASTER_TREASURY_${input.network}`, assetSymbol: input.asset, direction: 'DEBIT', amount: input.amount }
    ] });
    return tx.custodyTransaction.upsert({ where: { network_txHash: { network: input.network, txHash: input.txHash } }, update: { status: 'CONFIRMED', confirmations: input.confirmations, confirmedAt: new Date(), userId: address.userId, depositId: deposit.id, amount: input.amount, toAddress: input.toAddress, fromAddress: input.fromAddress, blockNumber: input.blockNumber, raw: input.raw as any }, create: { network: input.network, txHash: input.txHash, asset: input.asset, amount: input.amount, fromAddress: input.fromAddress, toAddress: input.toAddress, blockNumber: input.blockNumber, confirmations: input.confirmations, status: 'CONFIRMED', userId: address.userId, depositId: deposit.id, confirmedAt: new Date(), raw: input.raw as any } });
  });
}

async function scanTronAddress(address: { id: string; userId: string; address: string }) {
  const headers: Record<string,string> = { accept: 'application/json' };
  if (TRONGRID_API_KEY) headers['TRON-PRO-API-KEY'] = TRONGRID_API_KEY;
  const url = new URL(`${TRONGRID_URL}/v1/accounts/${encodeURIComponent(address.address)}/transactions/trc20`);
  url.searchParams.set('limit', '200');
  url.searchParams.set('only_confirmed', 'true');
  url.searchParams.set('only_to', 'true');
  url.searchParams.set('contract_address', TRON_USDT);
  const response = await fetch(url, { headers });
  if (!response.ok) throw new Error(`TRONGRID_${response.status}`);
  const body: any = await response.json();
  let credited = 0;
  for (const item of Array.isArray(body?.data) ? body.data : []) {
    const value = String(item.value ?? '0');
    const amount = decimal(value).div(decimal(10).pow(6));
    const txHash = String(item.transaction_id ?? '');
    if (!txHash || amount.lte(0)) continue;
    const result = await creditConfirmedDeposit({ network: 'TRC20', txHash, asset: 'USDT', amount, fromAddress: item.from, toAddress: item.to ?? address.address, confirmations: TRON_CONFIRMATIONS, raw: item });
    if (result) credited++;
  }
  return credited;
}

async function bscRpc(method: string, params: unknown[]) {
  if (!BSC_RPC_URL) throw new Error('BSC_RPC_URL_NOT_CONFIGURED');
  const response = await fetch(BSC_RPC_URL, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ jsonrpc: '2.0', id: Date.now(), method, params }) });
  if (!response.ok) throw new Error(`BSC_RPC_${response.status}`);
  const body: any = await response.json();
  if (body?.error) throw new Error(`BSC_RPC_ERROR_${body.error.code}`);
  return body.result;
}

async function scanBep20Address(address: { id: string; userId: string; address: string }) {
  const latestHex = await bscRpc('eth_blockNumber', []);
  const latest = BigInt(latestHex);
  const from = latest > BigInt(BSC_SCAN_BLOCKS) ? latest - BigInt(BSC_SCAN_BLOCKS) : 0n;
  const padded = address.address.toLowerCase().replace(/^0x/, '').padStart(64, '0');
  const logs: any[] = await bscRpc('eth_getLogs', [{ address: BSC_USDT, fromBlock: `0x${from.toString(16)}`, toBlock: `0x${latest.toString(16)}`, topics: [TRANSFER_TOPIC, null, `0x${padded}`] }]);
  let credited = 0;
  for (const log of logs) {
    const amount = decimal(BigInt(log.data).toString()).div(decimal(10).pow(18));
    const blockNumber = BigInt(log.blockNumber);
    const confirmations = Number(latest - blockNumber + 1n);
    const txHash = String(log.transactionHash ?? '');
    if (!txHash || amount.lte(0)) continue;
    const result = await creditConfirmedDeposit({ network: 'BEP20', txHash, asset: 'USDT', amount, fromAddress: topicAddress(log.topics?.[1] ?? ''), toAddress: address.address, blockNumber, confirmations, raw: log });
    if (result) credited++;
  }
  return credited;
}

export async function scanCustodyDeposits() {
  if (!databaseEnabled) return { scanned: 0, credited: 0, configured: false };
  const addresses = await db.depositAddress.findMany({ where: { active: true }, select: { id: true, userId: true, address: true, network: true } });
  let credited = 0;
  for (const address of addresses) {
    try {
      credited += address.network === 'TRC20' ? await scanTronAddress(address) : await scanBep20Address(address);
    } catch (error) {
      console.error('custody deposit scan failed', { network: address.network, addressId: address.id, error });
    }
  }
  return { scanned: addresses.length, credited, configured: true };
}

export function startCustodyScanner(intervalMs = Number(process.env.CUSTODY_SCAN_INTERVAL_MS ?? 30000)) {
  if (!databaseEnabled) return () => undefined;
  let running = false;
  const run = async () => { if (running) return; running = true; try { await scanCustodyDeposits(); } finally { running = false; } };
  void run();
  const timer = setInterval(() => void run(), intervalMs);
  timer.unref();
  return () => clearInterval(timer);
}

export async function registerCustodyRoutes(app: FastifyInstance) {
  app.get('/api/v1/custody/deposit-addresses', async (request: any, reply: any) => {
    const user: any = await userFromRequest(request);
    if (!user) return reply.code(401).send({ error: 'Authentication required' });
    const addresses = await db.depositAddress.findMany({ where: { userId: user.id, active: true }, orderBy: { createdAt: 'asc' }, select: { id: true, network: true, address: true, label: true } });
    return { addresses, instructions: 'Use the address matching the network you selected. Deposits sent on another network may not be recoverable.' };
  });

  app.get('/api/v1/custody/deposits', async (request: any, reply: any) => {
    const user: any = await userFromRequest(request);
    if (!user) return reply.code(401).send({ error: 'Authentication required' });
    const deposits = await db.deposit.findMany({ where: { userId: user.id }, orderBy: { createdAt: 'desc' }, take: 100, include: { depositAddress: { select: { network: true, address: true } }, custodyTransaction: { select: { confirmations: true, status: true, blockNumber: true } } } });
    return { deposits };
  });

  app.post('/api/v1/admin/custody/deposit-addresses', async (request: any, reply: any) => {
    const admin = await requireAdminRole(request, reply, ['SUPER_ADMIN', 'OPERATIONS', 'FINANCE']);
    if (!admin) return;
    const parsed = z.object({ userId: z.string().min(1), network: z.enum(['TRC20','BEP20']), address: z.string().min(20).max(128), label: z.string().max(100).optional() }).safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: 'userId, network and a valid deposit address are required' });
    const normalized = parsed.data.network === 'BEP20' ? normalizeEvmAddress(parsed.data.address) : parsed.data.address.trim();
    try {
      const created = await db.depositAddress.create({ data: { userId: parsed.data.userId, network: parsed.data.network, address: normalized, label: parsed.data.label } });
      audit('custody_deposit_address_assigned', { requestId: request.id, subjectId: parsed.data.userId, metadata: { network: parsed.data.network, addressId: created.id, adminId: admin.id } });
      return reply.code(201).send({ address: created });
    } catch (error) { return reply.code(409).send({ error: 'Deposit address already assigned or user does not exist' }); }
  });

  app.get('/api/v1/admin/custody/deposit-addresses', async (request: any, reply: any) => {
    const admin = await requireAdminRole(request, reply, ['SUPER_ADMIN', 'OPERATIONS', 'COMPLIANCE', 'FINANCE']);
    if (!admin) return;
    const addresses = await db.depositAddress.findMany({ orderBy: { createdAt: 'desc' }, take: 1000, include: { user: { select: { id: true, email: true } } } });
    return { addresses };
  });

  app.post('/api/v1/admin/custody/scan', async (request: any, reply: any) => {
    const admin = await requireAdminRole(request, reply, ['SUPER_ADMIN', 'OPERATIONS', 'FINANCE']);
    if (!admin) return;
    const result = await scanCustodyDeposits();
    audit('custody_scan', { requestId: request.id, subjectId: admin.id, metadata: result });
    return result;
  });

  app.get('/api/v1/admin/custody/transactions', async (request: any, reply: any) => {
    const admin = await requireAdminRole(request, reply, ['SUPER_ADMIN', 'OPERATIONS', 'COMPLIANCE', 'FINANCE']);
    if (!admin) return;
    const txs = await db.custodyTransaction.findMany({ orderBy: { observedAt: 'desc' }, take: 1000, include: { user: { select: { id: true, email: true } }, deposit: true } });
    return { transactions: txs };
  });

  app.post('/api/v1/admin/withdrawals/:id/sent', async (request: any, reply: any) => {
    const admin = await requireAdminRole(request, reply, ['SUPER_ADMIN', 'FINANCE']);
    if (!admin) return;
    const id = String(request.params.id);
    const parsed = z.object({ txHash: z.string().min(20).max(200) }).safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: 'A blockchain transaction hash is required' });
    const idem = await idempotentMutation(request, reply, `admin/withdrawals/${id}/sent`);
    if (idem) return idem;
    const withdrawal = await db.withdrawal.findUnique({ where: { id } });
    if (!withdrawal) return reply.code(404).send({ error: 'Withdrawal not found' });
    if (withdrawal.status !== 'APPROVED') return reply.code(400).send({ error: 'Withdrawal must be approved before settlement' });
    const updated = await db.$transaction(async tx => {
      const result = await tx.withdrawal.update({ where: { id }, data: { status: 'SENT', txHash: parsed.data.txHash, sentAt: new Date() } });
      const wallet = await tx.wallet.findFirst({ where: { userId: withdrawal.userId, asset: { symbol: withdrawal.asset } } });
      if (wallet) await tx.wallet.update({ where: { id: wallet.id }, data: { locked: { decrement: withdrawal.amount } } });
      await tx.ledgerEntry.createMany({ data: [{ reference: `withdrawal:${id}:settled`, account: `ASTER_TREASURY_${withdrawal.network ?? 'UNKNOWN'}`, assetSymbol: withdrawal.asset, direction: 'DEBIT', amount: withdrawal.amount }, { reference: `withdrawal:${id}:settled`, account: withdrawal.userId, assetSymbol: withdrawal.asset, direction: 'CREDIT', amount: withdrawal.amount }] });
      return result;
    });
    audit('withdrawal_sent', { requestId: request.id, subjectId: admin.id, metadata: { withdrawalId: id, txHash: parsed.data.txHash } });
    const body = { withdrawal: updated, message: 'Settlement recorded with blockchain transaction hash.' };
    const key = request.headers?.['idempotency-key']; if (typeof key === 'string') await completeIdempotency(`admin/withdrawals/${id}/sent`, key, 200, body);
    return body;
  });
}
