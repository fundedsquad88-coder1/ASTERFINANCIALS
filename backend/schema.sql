CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  full_name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  email_verified_at TIMESTAMPTZ,
  verification_token_hash TEXT,
  verification_expires_at TIMESTAMPTZ,
  reset_token_hash TEXT,
  reset_expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS users_email_idx ON users (LOWER(email));

-- Financial tables are intentionally separated from authentication.
-- Balances must be derived from server-side ledger entries, never from the Android client.
CREATE TABLE IF NOT EXISTS ledger_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type TEXT NOT NULL CHECK (type IN ('deposit','investment_principal','investment_gain','withdrawal','referral_reward','adjustment')),
  amount NUMERIC(30,8) NOT NULL,
  currency TEXT NOT NULL DEFAULT 'USDT',
  reference_id UUID,
  status TEXT NOT NULL DEFAULT 'posted' CHECK (status IN ('pending','posted','rejected')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ledger_user_created_idx ON ledger_entries(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS refresh_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ
);


CREATE TABLE IF NOT EXISTS wallet_addresses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  network TEXT NOT NULL UNIQUE CHECK (network IN ('TRC-20','BEP-20')),
  address TEXT NOT NULL,
  qr_asset_url TEXT,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS deposits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  wallet_address_id UUID NOT NULL REFERENCES wallet_addresses(id),
  network TEXT NOT NULL CHECK (network IN ('TRC-20','BEP-20')),
  amount NUMERIC(30,8) NOT NULL CHECK (amount > 0),
  tx_hash TEXT,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','confirming','completed','rejected')),
  submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  verified_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS deposits_user_created_idx ON deposits(user_id, submitted_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS deposits_network_tx_hash_idx ON deposits(network, tx_hash) WHERE tx_hash IS NOT NULL;

CREATE TABLE IF NOT EXISTS withdrawals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  network TEXT NOT NULL CHECK (network IN ('TRC-20','BEP-20')),
  destination_address TEXT NOT NULL,
  amount NUMERIC(30,8) NOT NULL CHECK (amount > 0),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','completed','rejected')),
  requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS withdrawals_user_created_idx ON withdrawals(user_id, requested_at DESC);


INSERT INTO wallet_addresses (network,address,qr_asset_url)
VALUES
('TRC-20','TMrK4d1r2cGye2TwX3JfjCaUDWvZy6aoXD',NULL),
('BEP-20','0xAf37c145EE58C0C0bD281BF454Ee92beC93F13d5',NULL)
ON CONFLICT (network) DO UPDATE SET address=EXCLUDED.address;
