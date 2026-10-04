create table if not exists opportunities(id bigserial primary key,title text not null,source text,estimated_usdt numeric(20,6) default 0,status text not null,created_at timestamptz default now());
create table if not exists revenue_events(id bigserial primary key,amount_usdt numeric(20,6) not null,source text,external_id text unique,status text not null,created_at timestamptz default now());
create table if not exists payout_requests(id bigserial primary key,amount_usdt numeric(20,6) not null,address text not null,status text not null,tx_hash text,created_at timestamptz default now());
create table if not exists agent_runs(id bigserial primary key,ran_at timestamptz default now(),status text not null);
create table if not exists payment_requests(id bigserial primary key,customer_ref text not null,amount_usdt numeric(20,6) not null,network text not null default 'BEP20',asset text not null default 'USDT',pay_address text not null,status text not null default 'pending',tx_hash text,created_at timestamptz default now(),expires_at timestamptz);
create unique index if not exists payment_requests_pending_amount_idx on payment_requests(amount_usdt) where status='pending';
create table if not exists watcher_state(id integer primary key, last_block bigint not null);
