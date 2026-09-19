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


CREATE TABLE IF NOT EXISTS investments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  category TEXT NOT NULL CHECK (category IN ('crypto','forex')),
  principal NUMERIC(30,8) NOT NULL CHECK (principal > 0),
  current_value NUMERIC(30,8) NOT NULL CHECK (current_value >= 0),
  projection_rate NUMERIC(12,8),
  compounding BOOLEAN NOT NULL DEFAULT TRUE,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','completed','withdrawal_pending','closed')),
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  next_update_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS investments_user_status_idx ON investments(user_id,status,updated_at DESC);


CREATE TABLE IF NOT EXISTS investment_updates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  investment_id UUID NOT NULL REFERENCES investments(id) ON DELETE CASCADE,
  period_ending TIMESTAMPTZ NOT NULL,
  opening_value NUMERIC(30,8) NOT NULL,
  realized_rate NUMERIC(12,8) NOT NULL,
  gain_amount NUMERIC(30,8) NOT NULL,
  closing_value NUMERIC(30,8) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(investment_id, period_ending)
);
CREATE INDEX IF NOT EXISTS investment_updates_investment_period_idx
  ON investment_updates(investment_id, period_ending DESC);

ALTER TABLE investments
  ADD COLUMN IF NOT EXISTS realized_rate NUMERIC(12,8);


CREATE TABLE IF NOT EXISTS investment_weekly_rates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  category TEXT NOT NULL CHECK (category IN ('crypto','forex')),
  period_ending TIMESTAMPTZ NOT NULL,
  realized_rate NUMERIC(12,8) NOT NULL CHECK (realized_rate >= -1 AND realized_rate <= 1),
  published_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(category, period_ending)
);


ALTER TABLE withdrawals
  ADD COLUMN IF NOT EXISTS investment_id UUID REFERENCES investments(id);


ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_code TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by UUID REFERENCES users(id);
CREATE UNIQUE INDEX IF NOT EXISTS users_referral_code_idx ON users(referral_code) WHERE referral_code IS NOT NULL;
CREATE INDEX IF NOT EXISTS users_referred_by_idx ON users(referred_by);

CREATE TABLE IF NOT EXISTS referral_rewards (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  referrer_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  referred_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL CHECK (source_type IN ('deposit','investment')),
  source_reference_id UUID,
  rate NUMERIC(12,8) NOT NULL CHECK (rate >= 0 AND rate <= 1),
  reward_amount NUMERIC(30,8) NOT NULL CHECK (reward_amount >= 0),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','posted','rejected')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  posted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS referral_rewards_referrer_idx ON referral_rewards(referrer_user_id,created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS referral_rewards_source_idx ON referral_rewards(referrer_user_id,source_type,source_reference_id);



-- Blockchain verification and operational controls
CREATE TABLE IF NOT EXISTS blockchain_cursors (
  network TEXT PRIMARY KEY CHECK (network IN ('TRC-20','BEP-20')),
  cursor TEXT NOT NULL DEFAULT '0',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS blockchain_transfers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  network TEXT NOT NULL CHECK (network IN ('TRC-20','BEP-20')),
  tx_hash TEXT NOT NULL,
  transfer_index TEXT NOT NULL DEFAULT '0',
  block_reference TEXT,
  token_contract TEXT NOT NULL,
  from_address TEXT NOT NULL,
  to_address TEXT NOT NULL,
  amount NUMERIC(30,8) NOT NULL CHECK (amount > 0),
  confirmations INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'detected' CHECK (status IN ('detected','confirming','verified','rejected')),
  deposit_id UUID REFERENCES deposits(id),
  detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  verified_at TIMESTAMPTZ,
  UNIQUE(network, tx_hash, transfer_index)
);
CREATE INDEX IF NOT EXISTS blockchain_transfers_status_idx ON blockchain_transfers(network,status,detected_at);
CREATE INDEX IF NOT EXISTS blockchain_transfers_to_idx ON blockchain_transfers(network,to_address,detected_at DESC);

ALTER TABLE deposits ADD COLUMN IF NOT EXISTS transfer_id UUID REFERENCES blockchain_transfers(id);
ALTER TABLE deposits ADD COLUMN IF NOT EXISTS confirmations INTEGER NOT NULL DEFAULT 0;
ALTER TABLE deposits ADD COLUMN IF NOT EXISTS rejection_reason TEXT;

ALTER TABLE withdrawals ADD COLUMN IF NOT EXISTS fee_amount NUMERIC(30,8) NOT NULL DEFAULT 0;
ALTER TABLE withdrawals ADD COLUMN IF NOT EXISTS net_amount NUMERIC(30,8);
ALTER TABLE withdrawals ADD COLUMN IF NOT EXISTS admin_note TEXT;
ALTER TABLE withdrawals ADD COLUMN IF NOT EXISTS outgoing_tx_hash TEXT;
ALTER TABLE withdrawals ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;
ALTER TABLE withdrawals ADD COLUMN IF NOT EXISTS approved_by UUID REFERENCES users(id);
ALTER TABLE withdrawals ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
CREATE UNIQUE INDEX IF NOT EXISTS withdrawals_outgoing_tx_hash_idx ON withdrawals(outgoing_tx_hash) WHERE outgoing_tx_hash IS NOT NULL;

CREATE TABLE IF NOT EXISTS admin_audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  admin_user_id UUID REFERENCES users(id),
  action TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id UUID,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS admin_audit_log_created_idx ON admin_audit_log(created_at DESC);
