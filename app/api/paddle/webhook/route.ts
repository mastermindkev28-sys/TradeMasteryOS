import { createHmac } from 'crypto';
import { NextRequest, NextResponse } from 'next/server';
import { getSupabaseAdmin } from '@/lib/supabaseServer';

function verifySignature(rawBody: string, signatureHeader: string, secret: string): boolean {
  // Header format: ts=1234567890;h1=abc...
  const parts = signatureHeader.split(';');
  let ts = '';
  let h1 = '';
  for (const part of parts) {
    if (part.startsWith('ts=')) ts = part.slice(3);
    if (part.startsWith('h1=')) h1 = part.slice(3);
  }
  if (!ts || !h1) return false;

  const payload = `${ts}:${rawBody}`;
  const expected = createHmac('sha256', secret).update(payload).digest('hex');
  return expected === h1;
}

const ACTIVE_EVENTS = new Set([
  'subscription.created',
  'subscription.activated',
  'subscription.updated',
  'subscription.resumed',
]);

export async function POST(req: NextRequest) {
  const rawBody = await req.text();
  const signatureHeader = req.headers.get('paddle-signature') ?? '';
  const secret = process.env.PADDLE_WEBHOOK_SECRET ?? '';

  if (!verifySignature(rawBody, signatureHeader, secret)) {
    return NextResponse.json({ error: 'Invalid signature' }, { status: 401 });
  }

  let event: any;
  try {
    event = JSON.parse(rawBody);
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const eventType: string = event.event_type ?? '';
  const data = event.data ?? {};

  const userId: string | undefined = data.custom_data?.user_id;
  if (!userId) {
    // Missing user_id — acknowledge without crashing
    return NextResponse.json({ received: true });
  }

  let status: string;
  if (ACTIVE_EVENTS.has(eventType)) {
    status = 'active';
  } else if (eventType === 'subscription.cancelled') {
    status = 'cancelled';
  } else if (eventType === 'subscription.paused') {
    status = 'paused';
  } else {
    // Unhandled event type — acknowledge
    return NextResponse.json({ received: true });
  }

  const paddleSubscriptionId: string = data.id ?? '';
  const paddleCustomerId: string = data.customer_id ?? '';
  const planId: string = data.items?.[0]?.price?.id ?? '';
  const currentPeriodEnd: string | null = data.current_billing_period?.ends_at ?? null;
  const cancelAtPeriodEnd: boolean = data.scheduled_change?.action === 'cancel';

  const { error } = await getSupabaseAdmin().from('subscriptions').upsert(
    {
      user_id: userId,
      paddle_subscription_id: paddleSubscriptionId,
      paddle_customer_id: paddleCustomerId,
      plan_id: planId,
      status,
      current_period_end: currentPeriodEnd,
      cancel_at_period_end: cancelAtPeriodEnd,
      updated_at: new Date().toISOString(),
    },
    { onConflict: 'paddle_subscription_id' }
  );

  if (error) {
    console.error('Supabase upsert error:', error);
    return NextResponse.json({ error: 'Database error' }, { status: 500 });
  }

  return NextResponse.json({ received: true });
}
