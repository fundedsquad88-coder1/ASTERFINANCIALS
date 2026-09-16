export type Asset = 'USDT';
export type Wallet = { asset: Asset; available: string; locked: string };
export type Account = { id: string; email: string; status: 'ACTIVE' | 'SUSPENDED'; wallets: Wallet[] };

export function emptyAccount(id: string, email: string): Account {
  return { id, email, status: 'ACTIVE', wallets: [{ asset: 'USDT', available: '0.00', locked: '0.00' }] };
}
