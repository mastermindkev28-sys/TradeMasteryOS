-- Create subscriptions table
create table if not exists public.subscriptions (
  id                      uuid primary key default gen_random_uuid(),
  user_id                 uuid references auth.users(id) on delete cascade not null unique,
  paddle_subscription_id  text unique,
  paddle_customer_id      text,
  plan_id                 text,
  status                  text not null default 'inactive',
  current_period_end      timestamptz,
  cancel_at_period_end    boolean default false,
  created_at              timestamptz default now(),
  updated_at              timestamptz default now()
);

-- Enable Row Level Security
alter table public.subscriptions enable row level security;

-- Policy: users can select their own subscription row
create policy "Users can view own subscription"
  on public.subscriptions
  for select
  using (auth.uid() = user_id);
