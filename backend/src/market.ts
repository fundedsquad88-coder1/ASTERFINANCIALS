export type Market = { symbol: string; name: string; source: string; status: 'LIVE' | 'REQUIRES_PROVIDER' };

export const MARKETS: Market[] = [
  { symbol: 'BTC/USDT', name: 'Bitcoin', source: 'Binance public market data', status: 'LIVE' },
  { symbol: 'ETH/USDT', name: 'Ethereum', source: 'Binance public market data', status: 'LIVE' },
  { symbol: 'XAU/USDT', name: 'Gold', source: 'External gold market-data provider required', status: 'REQUIRES_PROVIDER' }
];
