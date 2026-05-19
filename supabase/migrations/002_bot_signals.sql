-- GoldMaster Pro — Bot Signals Table
-- Stores all trading signals from TradingView, ML engine, or manual input

create table if not exists public.bot_signals (
  id          uuid    primary key default gen_random_uuid(),
  created_at  timestamptz not null default now(),
  action      text    not null check (action in ('BUY', 'SELL')),
  symbol      text    not null default 'XAUUSD',
  price       numeric(12,4),
  sl          numeric(12,4),
  tp1         numeric(12,4),
  tp2         numeric(12,4),
  lot_size    numeric(8,2),
  confidence  numeric(5,4),
  score       numeric(5,1),
  atr         numeric(8,4),
  source      text    default 'tradingview',
  status      text    not null default 'pending'
                check (status in ('pending','executed','rejected','cancelled')),
  raw         jsonb,
  updated_at  timestamptz not null default now()
);

-- Indexes
create index if not exists bot_signals_created_at_idx on public.bot_signals (created_at desc);
create index if not exists bot_signals_status_idx     on public.bot_signals (status);
create index if not exists bot_signals_action_idx     on public.bot_signals (action);

-- RLS: service role only (bot writes, no user-level access)
alter table public.bot_signals enable row level security;

-- Allow service role full access
create policy "service_role_all" on public.bot_signals
  for all using (true) with check (true);

-- Trigger: update updated_at
create or replace function update_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists bot_signals_updated_at on public.bot_signals;
create trigger bot_signals_updated_at
  before update on public.bot_signals
  for each row execute function update_updated_at();
