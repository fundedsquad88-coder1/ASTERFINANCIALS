CREATE TABLE IF NOT EXISTS admin_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('super_admin','operations_admin','finance_admin','support_admin')),
  two_factor_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_user_id UUID REFERENCES users(id),
  event_type TEXT NOT NULL,
  entity_type TEXT,
  entity_id UUID,
  request_id TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS audit_events_created_idx ON audit_events(created_at DESC);
CREATE INDEX IF NOT EXISTS audit_events_entity_idx ON audit_events(entity_type,entity_id,created_at DESC);

CREATE TABLE IF NOT EXISTS blockchain_cursors (
  network TEXT PRIMARY KEY CHECK (network IN ('TRC-20','BEP-20')),
  last_block BIGINT NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS blockchain_transfers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  network TEXT NOT NULL CHECK (network IN ('TRC-20','BEP-20')),
  direction TEXT NOT NULL CHECK (direction IN ('inbound','outbound')),
  tx_hash TEXT NOT NULL,
  transfer_index TEXT NOT NULL DEFAULT '0',
  token_contract TEXT NOT NULL,
  from_address TEXT NOT NULL,
  to_address TEXT NOT NULL,
  amount NUMERIC(30,8) NOT NULL CHECK (amount > 0),
  block_number BIGINT NOT NULL,
  block_hash TEXT,
  confirmations INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'detected' CHECK (status IN ('detected','confirming','confirmed','rejected')),
  deposit_id UUID REFERENCES deposits(id),
  withdrawal_id UUID REFERENCES withdrawals(id),
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  confirmed_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS blockchain_transfers_identity_idx ON blockchain_transfers(network,tx_hash,transfer_index);
CREATE INDEX IF NOT EXISTS blockchain_transfers_scan_idx ON blockchain_transfers(network,block_number);

CREATE TABLE IF NOT EXISTS withdrawal_fee_bands (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  min_amount NUMERIC(30,8) NOT NULL CHECK (min_amount >= 0),
  max_amount NUMERIC(30,8),
  fee_rate NUMERIC(12,8) NOT NULL CHECK (fee_rate >= 0 AND fee_rate <= 1),
  active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS withdrawal_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  withdrawal_id UUID NOT NULL UNIQUE REFERENCES withdrawals(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','submitted','broadcast','failed','completed')),
  idempotency_key TEXT NOT NULL UNIQUE,
  signer_reference TEXT,
  tx_hash TEXT,
  error_code TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE withdrawals ADD COLUMN IF NOT EXISTS fee_amount NUMERIC(30,8) NOT NULL DEFAULT 0;
ALTER TABLE withdrawals ADD COLUMN IF NOT EXISTS net_amount NUMERIC(30,8);
ALTER TABLE withdrawals ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;
ALTER TABLE withdrawals ADD COLUMN IF NOT EXISTS approved_by UUID REFERENCES users(id);
ALTER TABLE withdrawals ADD COLUMN IF NOT EXISTS destination_normalized TEXT;
ALTER TABLE withdrawals ADD COLUMN IF NOT EXISTS failure_reason TEXT;
ALTER TABLE deposits ADD COLUMN IF NOT EXISTS block_number BIGINT;
ALTER TABLE deposits ADD COLUMN IF NOT EXISTS token_contract TEXT;
ALTER TABLE deposits ADD COLUMN IF NOT EXISTS transfer_index TEXT;
ALTER TABLE deposits ADD COLUMN IF NOT EXISTS confirmations INTEGER NOT NULL DEFAULT 0;
CREATE INDEX IF NOT EXISTS deposits_status_network_idx ON deposits(status,network,submitted_at);
CREATE INDEX IF NOT EXISTS withdrawals_status_idx ON withdrawals(status,requested_at);

INSERT INTO withdrawal_fee_bands(min_amount,max_amount,fee_rate)
SELECT 0,1000,0.015 WHERE NOT EXISTS (SELECT 1 FROM withdrawal_fee_bands);
INSERT INTO withdrawal_fee_bands(min_amount,max_amount,fee_rate)
SELECT 1000,10000,0.0175 WHERE NOT EXISTS (SELECT 1 FROM withdrawal_fee_bands WHERE min_amount=1000);
INSERT INTO withdrawal_fee_bands(min_amount,max_amount,fee_rate)
SELECT 10000,NULL,0.02 WHERE NOT EXISTS (SELECT 1 FROM withdrawal_fee_bands WHERE min_amount=10000);
