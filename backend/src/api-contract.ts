export const API_VERSION = 'v1';

export const API_CONTRACT = {
  auth: {
    register: 'POST /api/v1/auth/register',
    login: 'POST /api/v1/auth/login',
    logout: 'POST /api/v1/auth/logout'
  },
  account: {
    me: 'GET /api/v1/me'
  },
  markets: {
    list: 'GET /api/v1/markets'
  },
  trading: {
    preview: 'POST /api/v1/trades/preview'
  }
} as const;

// The mobile client must treat all balances, trades and settlement responses as
// server-authoritative. This contract is currently sandbox-only.