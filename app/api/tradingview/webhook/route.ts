import { createHmac, timingSafeEqual } from "crypto";
import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET ?? "";

function verifySignature(body: string, signature: string): boolean {
  if (!WEBHOOK_SECRET || !signature) return true; // optional in dev
  const expected = createHmac("sha256", WEBHOOK_SECRET)
    .update(body)
    .digest("hex");
  try {
    return timingSafeEqual(Buffer.from(expected), Buffer.from(signature));
  } catch {
    return false;
  }
}

export async function POST(req: NextRequest) {
  const rawBody = await req.text();
  const sig     = req.headers.get("x-signature") ?? "";

  if (WEBHOOK_SECRET && !verifySignature(rawBody, sig)) {
    return NextResponse.json({ error: "Invalid signature" }, { status: 401 });
  }

  let payload: Record<string, unknown>;
  try {
    payload = JSON.parse(rawBody);
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const action = String(payload.action ?? "").toUpperCase();
  if (!["BUY", "SELL"].includes(action)) {
    return NextResponse.json({ error: `Unknown action: ${action}` }, { status: 400 });
  }

  // Persist signal to Supabase
  const { error } = await supabase.from("bot_signals").insert({
    action,
    symbol:     payload.symbol ?? "XAUUSD",
    price:      payload.price  ?? null,
    sl:         payload.sl     ?? null,
    tp1:        payload.tp1    ?? null,
    tp2:        payload.tp2    ?? null,
    lot_size:   payload.lot_size ?? null,
    confidence: payload.confidence ?? null,
    score:      payload.score  ?? null,
    atr:        payload.atr    ?? null,
    source:     payload.source ?? "tradingview",
    status:     "pending",
    raw:        payload,
  });

  if (error) {
    console.error("Supabase insert error:", error);
    return NextResponse.json({ error: "DB error" }, { status: 500 });
  }

  // Forward to Python bridge if configured
  const bridgeUrl = process.env.PYTHON_BRIDGE_URL;
  if (bridgeUrl) {
    try {
      await fetch(`${bridgeUrl}/api/tradingview/webhook`, {
        method:  "POST",
        headers: { "Content-Type": "application/json", "X-Signature": sig },
        body:    rawBody,
        signal:  AbortSignal.timeout(5000),
      });
    } catch (e) {
      console.warn("Bridge forward failed:", e);
    }
  }

  return NextResponse.json({ received: true, action });
}
