import crypto from 'node:crypto';
import { z } from 'zod';

export const TRADE_DIRECTIONS = ['HIGHER', 'LOWER'] as const;
export type TradeDirection = typeof TRADE_DIRECTIONS[number];

export const tradeCommandSchema = z.object({
  userId: z.string().min(1),
  symbol: z.enum(['BTCUSDT', 'ETHUSDT', 'XAUUSDT']),
  direction: z.enum(TRADE_DIRECTIONS),
  amount: z.number().positive(),
  expirySeconds: z.number().int().min(30).max(86400),
  referencePrice: z.number().positive().optional()
});

export type TradeCommand = z.infer<typeof tradeCommandSchema>;
export type EngineTrade = TradeCommand & {
  id: string;
  status: 'PREVIEW';
  createdAt: string;
  expiresAt: string;
};

/**
 * Deterministic boundary for the future execution service.
 * This module deliberately does not debit balances, create real orders,
 * choose settlement prices, or connect to a broker/exchange.
 */
export function previewTrade(command: TradeCommand): EngineTrade {
  const parsed = tradeCommandSchema.parse(command);
  const created = Date.now();
  return {
    ...parsed,
    id: `preview_${crypto.randomUUID()}`,
    status: 'PREVIEW',
    createdAt: new Date(created).toISOString(),
    expiresAt: new Date(created + parsed.expirySeconds * 1000).toISOString()
  };
}

export const EXECUTION_ARCHITECTURE = {
  marketData: 'provider adapter',
  orderRouter: 'disabled',
  riskEngine: 'required before production',
  settlementEngine: 'disabled',
  ledger: 'authoritative account balance',
  audit: 'required for every state transition',
  realMoneyExecution: false
} as const;
