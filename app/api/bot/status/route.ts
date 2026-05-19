import { NextResponse } from "next/server";

export async function GET() {
  const bridgeUrl = process.env.PYTHON_BRIDGE_URL;
  if (!bridgeUrl) {
    return NextResponse.json({
      can_trade:        false,
      reason:           "Python bridge not configured",
      equity:           0,
      today_pnl:        0,
      week_pnl:         0,
      daily_dd_pct:     0,
      total_dd_pct:     0,
      today_trades:     0,
      total_trades:     0,
      win_rate:         0,
      weekly_progress:  0,
      weekly_target_low:  1000,
      weekly_target_high: 1500,
      mt4:              { status: "not connected" },
      ml:               { trained: false, accuracy: 0, needs_retrain: true },
      suspended:        false,
      prop_firm_mode:   true,
    });
  }

  try {
    const res  = await fetch(`${bridgeUrl}/api/status`, { signal: AbortSignal.timeout(5000) });
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ error: "Bridge unavailable" }, { status: 503 });
  }
}
