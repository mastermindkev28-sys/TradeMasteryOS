'use client';

import { useEffect, useState, useCallback } from 'react';
import Sidebar from '@/components/Sidebar';
import AuthGuard from '@/components/AuthGuard';

// ─────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────
interface BotStatus {
  can_trade:          boolean;
  reason:             string;
  equity:             number;
  today_pnl:          number;
  week_pnl:           number;
  daily_dd_pct:       number;
  total_dd_pct:       number;
  today_trades:       number;
  total_trades:       number;
  win_rate:           number;
  weekly_progress:    number;
  weekly_target_low:  number;
  weekly_target_high: number;
  suspended:          boolean;
  prop_firm_mode:     boolean;
  mt4:                { status: string; equity?: number; spread?: number };
  ml:                 { trained: boolean; accuracy: number; needs_retrain: boolean };
}

interface Signal {
  id:          string;
  created_at:  string;
  action:      string;
  symbol:      string;
  price:       number;
  sl:          number;
  tp1:         number;
  tp2:         number;
  lot_size:    number;
  confidence:  number;
  score:       number;
  status:      string;
  source:      string;
}

// ─────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────
const fmtUSD = (n: number | null | undefined) =>
  n == null ? '—' : (n >= 0 ? '+' : '') + new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD', maximumFractionDigits: 2
  }).format(n);

const fmtPct = (n: number | null | undefined) =>
  n == null ? '—' : `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;

const clr = (n: number) => n >= 0 ? 'var(--green)' : 'var(--red)';

// ─────────────────────────────────────────────
// PAGE
// ─────────────────────────────────────────────
export default function BotPage() {
  const [status,    setStatus]    = useState<BotStatus | null>(null);
  const [signals,   setSignals]   = useState<Signal[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [lastUpdate,setLastUpdate]= useState<string>('');

  const fetchData = useCallback(async () => {
    try {
      const [statusRes, signalsRes] = await Promise.all([
        fetch('/api/bot/status'),
        fetch('/api/bot/signals'),
      ]);
      if (statusRes.ok)  setStatus(await statusRes.json());
      if (signalsRes.ok) {
        const d = await signalsRes.json();
        setSignals(d.signals ?? []);
      }
      setLastUpdate(new Date().toLocaleTimeString());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000); // refresh every 15s
    return () => clearInterval(interval);
  }, [fetchData]);

  const weeklyProgress = status
    ? Math.min(100, ((status.week_pnl / status.weekly_target_high) * 100))
    : 0;

  const dailyDDPct  = Math.abs(status?.daily_dd_pct  ?? 0);
  const totalDDPct  = Math.abs(status?.total_dd_pct  ?? 0);
  const dailyBar    = Math.min(100, (dailyDDPct / 3) * 100);
  const totalBar    = Math.min(100, (totalDDPct / 6) * 100);

  return (
    <AuthGuard>
      <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg)' }}>
        <Sidebar />
        <main style={{ marginLeft: 220, flex: 1, padding: '32px 40px' }}>

          {/* Header */}
          <div className="page-header" style={{ marginBottom: 32 }}>
            <div>
              <h1 style={{ fontSize: 26, fontWeight: 700, color: 'var(--t1)', marginBottom: 4 }}>
                <i className="fa-solid fa-robot" style={{ color: 'var(--amber)', marginRight: 10 }}></i>
                GoldMaster Pro — Bot Control
              </h1>
              <p style={{ color: 'var(--t2)', fontSize: 13 }}>
                XAUUSD Automated Trading System · Prop Firm Edition · Target $1,000–$1,500/week
                {lastUpdate && <span style={{ marginLeft: 16, color: 'var(--t3)' }}>Updated {lastUpdate}</span>}
              </p>
            </div>
            <button onClick={fetchData} style={{
              background: 'var(--bg4)', border: '1px solid var(--border2)',
              borderRadius: 8, padding: '8px 16px', color: 'var(--t1)',
              cursor: 'pointer', fontSize: 13
            }}>
              <i className="fa-solid fa-rotate-right" style={{ marginRight: 6 }}></i>Refresh
            </button>
          </div>

          {loading ? (
            <div style={{ color: 'var(--t2)', padding: 40, textAlign: 'center' }}>
              Loading bot status...
            </div>
          ) : (
            <>
              {/* Status banner */}
              <div style={{
                background: status?.can_trade
                  ? 'rgba(34,212,122,0.08)' : 'rgba(240,82,82,0.08)',
                border: `1px solid ${status?.can_trade ? 'var(--green)' : 'var(--red)'}`,
                borderRadius: 10, padding: '12px 20px', marginBottom: 24,
                display: 'flex', alignItems: 'center', gap: 12
              }}>
                <div style={{
                  width: 10, height: 10, borderRadius: '50%',
                  background: status?.can_trade ? 'var(--green)' : 'var(--red)',
                  boxShadow: `0 0 8px ${status?.can_trade ? 'var(--green)' : 'var(--red)'}`,
                }} />
                <strong style={{ color: status?.can_trade ? 'var(--green)' : 'var(--red)', fontSize: 14 }}>
                  {status?.can_trade ? 'BOT ACTIVE — TRADING ENABLED' : 'TRADING PAUSED'}
                </strong>
                {status?.reason && (
                  <span style={{ color: 'var(--t2)', fontSize: 13, marginLeft: 4 }}>
                    · {status.reason}
                  </span>
                )}
                <span style={{ marginLeft: 'auto', color: 'var(--t3)', fontSize: 12 }}>
                  {status?.prop_firm_mode ? '🛡 Prop Firm Mode ON' : 'Prop Mode OFF'}
                </span>
              </div>

              {/* KPI Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
                {[
                  { label: 'Today P&L',    value: fmtUSD(status?.today_pnl),   color: clr(status?.today_pnl ?? 0) },
                  { label: 'Week P&L',     value: fmtUSD(status?.week_pnl),    color: clr(status?.week_pnl ?? 0) },
                  { label: 'Account Equity',value: status ? new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(status.equity) : '—', color: 'var(--t1)' },
                  { label: 'Win Rate',     value: `${(status?.win_rate ?? 0).toFixed(1)}%`, color: 'var(--t1)' },
                ].map((kpi) => (
                  <div key={kpi.label} style={{
                    background: 'var(--bg2)', border: '1px solid var(--border)',
                    borderRadius: 10, padding: '18px 20px'
                  }}>
                    <div style={{ color: 'var(--t3)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
                      {kpi.label}
                    </div>
                    <div style={{ fontSize: 22, fontWeight: 700, color: kpi.color, fontFamily: 'JetBrains Mono, monospace' }}>
                      {kpi.value}
                    </div>
                  </div>
                ))}
              </div>

              {/* Weekly Progress + Risk Meters */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>

                {/* Weekly target */}
                <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 10, padding: 20 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                    <span style={{ color: 'var(--t2)', fontSize: 13 }}>Weekly Target Progress</span>
                    <span style={{ color: 'var(--amber)', fontSize: 13, fontWeight: 600 }}>
                      {fmtUSD(status?.week_pnl)} / {fmtUSD(status?.weekly_target_high)}
                    </span>
                  </div>
                  <div style={{ height: 8, background: 'var(--bg4)', borderRadius: 4, overflow: 'hidden' }}>
                    <div style={{
                      width: `${Math.max(0, weeklyProgress)}%`,
                      height: '100%', borderRadius: 4,
                      background: weeklyProgress >= 100 ? 'var(--green)'
                                : weeklyProgress >= 50  ? 'var(--amber)' : 'var(--blue)',
                      transition: 'width 0.5s ease'
                    }} />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
                    <span style={{ color: 'var(--t3)', fontSize: 11 }}>$0</span>
                    <span style={{ color: 'var(--t3)', fontSize: 11 }}>
                      Min ${status?.weekly_target_low?.toLocaleString()} · Target ${status?.weekly_target_high?.toLocaleString()}
                    </span>
                  </div>
                  <div style={{ marginTop: 12, color: 'var(--t2)', fontSize: 12 }}>
                    Trades today: <strong style={{ color: 'var(--t1)' }}>{status?.today_trades} / 3</strong>
                    &emsp;Total: <strong style={{ color: 'var(--t1)' }}>{status?.total_trades}</strong>
                  </div>
                </div>

                {/* Drawdown meters */}
                <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 10, padding: 20 }}>
                  <div style={{ color: 'var(--t2)', fontSize: 13, marginBottom: 16 }}>Risk Meters — Prop Firm Limits</div>

                  {[
                    { label: 'Daily Drawdown',  used: dailyDDPct, limit: 3.0,  bar: dailyBar  },
                    { label: 'Total Drawdown',  used: totalDDPct, limit: 6.0,  bar: totalBar  },
                  ].map((m) => (
                    <div key={m.label} style={{ marginBottom: 14 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                        <span style={{ color: 'var(--t2)', fontSize: 12 }}>{m.label}</span>
                        <span style={{ fontSize: 12, color: m.used > m.limit * 0.8 ? 'var(--red)' : 'var(--t2)' }}>
                          {m.used.toFixed(2)}% / {m.limit}%
                        </span>
                      </div>
                      <div style={{ height: 6, background: 'var(--bg4)', borderRadius: 4, overflow: 'hidden' }}>
                        <div style={{
                          width: `${m.bar}%`, height: '100%', borderRadius: 4,
                          background: m.bar > 80 ? 'var(--red)' : m.bar > 50 ? 'var(--amber)' : 'var(--green)',
                          transition: 'width 0.5s ease'
                        }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* System Status Row */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 24 }}>

                {/* MT4 */}
                <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 10, padding: 18 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                    <div style={{
                      width: 8, height: 8, borderRadius: '50%',
                      background: status?.mt4?.status === 'connected' ? 'var(--green)' : 'var(--red)'
                    }} />
                    <span style={{ color: 'var(--t1)', fontWeight: 600 }}>MT4 Connection</span>
                  </div>
                  <div style={{ color: 'var(--t2)', fontSize: 13 }}>
                    Status: <strong style={{ color: 'var(--t1)' }}>{status?.mt4?.status ?? 'Unknown'}</strong>
                  </div>
                  {status?.mt4?.spread && (
                    <div style={{ color: 'var(--t2)', fontSize: 13, marginTop: 4 }}>
                      Spread: <strong style={{ color: 'var(--t1)' }}>{status.mt4.spread} pips</strong>
                    </div>
                  )}
                  <div style={{ color: 'var(--t3)', fontSize: 11, marginTop: 8 }}>
                    GoldMaster_Bridge.mq4 running in MT4
                  </div>
                </div>

                {/* ML Model */}
                <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 10, padding: 18 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                    <div style={{
                      width: 8, height: 8, borderRadius: '50%',
                      background: status?.ml?.trained ? 'var(--green)' : 'var(--amber)'
                    }} />
                    <span style={{ color: 'var(--t1)', fontWeight: 600 }}>ML Model</span>
                  </div>
                  <div style={{ color: 'var(--t2)', fontSize: 13 }}>
                    Status: <strong style={{ color: 'var(--t1)' }}>
                      {status?.ml?.trained ? 'Loaded' : 'Not trained'}
                    </strong>
                  </div>
                  {status?.ml?.accuracy != null && (
                    <div style={{ color: 'var(--t2)', fontSize: 13, marginTop: 4 }}>
                      Accuracy: <strong style={{ color: 'var(--green)' }}>
                        {(status.ml.accuracy * 100).toFixed(1)}%
                      </strong>
                    </div>
                  )}
                  <div style={{ color: 'var(--t3)', fontSize: 11, marginTop: 8 }}>
                    XGBoost + Random Forest ensemble
                  </div>
                </div>

                {/* TradingView */}
                <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 10, padding: 18 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--blue)' }} />
                    <span style={{ color: 'var(--t1)', fontWeight: 600 }}>TradingView</span>
                  </div>
                  <div style={{ color: 'var(--t2)', fontSize: 13 }}>
                    Webhook:
                  </div>
                  <code style={{
                    display: 'block', marginTop: 4, fontSize: 10,
                    background: 'var(--bg4)', padding: '4px 8px', borderRadius: 4,
                    color: 'var(--amber)', wordBreak: 'break-all'
                  }}>
                    /api/tradingview/webhook
                  </code>
                  <div style={{ color: 'var(--t3)', fontSize: 11, marginTop: 8 }}>
                    GoldMaster_Strategy.pine loaded on XAUUSD M15
                  </div>
                </div>
              </div>

              {/* Strategy Overview */}
              <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 10, padding: 20, marginBottom: 24 }}>
                <div style={{ color: 'var(--t1)', fontWeight: 600, marginBottom: 16, fontSize: 14 }}>
                  Active Strategies
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
                  {[
                    { name: 'London Breakout', desc: 'Pre-London range breakout at open', active: true },
                    { name: 'Trend Pullback',  desc: 'H4 trend + EMA21/50 bounce',       active: true },
                    { name: 'NY Momentum',     desc: 'NY open momentum with VWAP',        active: true },
                    { name: 'VWAP Reversion',  desc: '2-ATR VWAP deviation reversal',     active: false },
                  ].map((s) => (
                    <div key={s.name} style={{
                      background: 'var(--bg3)', borderRadius: 8, padding: 14,
                      border: `1px solid ${s.active ? 'var(--border2)' : 'var(--border)'}`,
                      opacity: s.active ? 1 : 0.5
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                        <div style={{
                          width: 7, height: 7, borderRadius: '50%',
                          background: s.active ? 'var(--green)' : 'var(--t3)'
                        }} />
                        <span style={{ color: 'var(--t1)', fontWeight: 600, fontSize: 12 }}>{s.name}</span>
                      </div>
                      <div style={{ color: 'var(--t3)', fontSize: 11 }}>{s.desc}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Risk Parameters */}
              <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 10, padding: 20, marginBottom: 24 }}>
                <div style={{ color: 'var(--t1)', fontWeight: 600, marginBottom: 16, fontSize: 14 }}>
                  Risk Parameters — Prop Firm Configuration
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
                  {[
                    { label: 'Risk / Trade', value: '0.75%' },
                    { label: 'Max Daily Loss', value: '3.0%' },
                    { label: 'Max Total DD', value: '6.0%' },
                    { label: 'Min R:R', value: '2:1' },
                    { label: 'Max Trades/Day', value: '3' },
                  ].map((p) => (
                    <div key={p.label} style={{ textAlign: 'center', padding: '12px 0' }}>
                      <div style={{ color: 'var(--amber)', fontSize: 18, fontWeight: 700, fontFamily: 'JetBrains Mono, monospace' }}>
                        {p.value}
                      </div>
                      <div style={{ color: 'var(--t3)', fontSize: 11, marginTop: 4 }}>{p.label}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Signal Log */}
              <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 10, padding: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <span style={{ color: 'var(--t1)', fontWeight: 600, fontSize: 14 }}>Recent Signals</span>
                  <span style={{ color: 'var(--t3)', fontSize: 12 }}>{signals.length} signals</span>
                </div>

                {signals.length === 0 ? (
                  <div style={{ color: 'var(--t3)', textAlign: 'center', padding: '32px 0', fontSize: 13 }}>
                    No signals yet. Configure TradingView webhook or start the Python bridge.
                  </div>
                ) : (
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid var(--border)' }}>
                          {['Time', 'Action', 'Price', 'SL', 'TP1', 'Lots', 'Score', 'Conf.', 'Source', 'Status'].map((h) => (
                            <th key={h} style={{ textAlign: 'left', padding: '6px 12px', color: 'var(--t3)', fontWeight: 500 }}>
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {signals.slice(0, 20).map((sig) => (
                          <tr key={sig.id} style={{ borderBottom: '1px solid var(--border)' }}>
                            <td style={{ padding: '8px 12px', color: 'var(--t3)' }}>
                              {new Date(sig.created_at).toLocaleTimeString()}
                            </td>
                            <td style={{ padding: '8px 12px' }}>
                              <span style={{
                                color: sig.action === 'BUY' ? 'var(--green)' : 'var(--red)',
                                fontWeight: 700, fontSize: 11
                              }}>{sig.action}</span>
                            </td>
                            <td style={{ padding: '8px 12px', color: 'var(--t1)', fontFamily: 'monospace' }}>
                              {sig.price?.toFixed(2) ?? '—'}
                            </td>
                            <td style={{ padding: '8px 12px', color: 'var(--red)', fontFamily: 'monospace' }}>
                              {sig.sl?.toFixed(2) ?? '—'}
                            </td>
                            <td style={{ padding: '8px 12px', color: 'var(--green)', fontFamily: 'monospace' }}>
                              {sig.tp1?.toFixed(2) ?? '—'}
                            </td>
                            <td style={{ padding: '8px 12px', color: 'var(--t2)' }}>{sig.lot_size ?? '—'}</td>
                            <td style={{ padding: '8px 12px', color: 'var(--amber)' }}>{sig.score ?? '—'}/100</td>
                            <td style={{ padding: '8px 12px', color: 'var(--t2)' }}>
                              {sig.confidence ? `${(sig.confidence * 100).toFixed(0)}%` : '—'}
                            </td>
                            <td style={{ padding: '8px 12px', color: 'var(--t3)', fontSize: 11 }}>{sig.source}</td>
                            <td style={{ padding: '8px 12px' }}>
                              <span style={{
                                fontSize: 10, padding: '2px 8px', borderRadius: 4, fontWeight: 600,
                                background: sig.status === 'executed' ? 'rgba(34,212,122,0.15)'
                                           : sig.status === 'rejected' ? 'rgba(240,82,82,0.15)'
                                           : 'rgba(79,142,247,0.15)',
                                color: sig.status === 'executed' ? 'var(--green)'
                                     : sig.status === 'rejected' ? 'var(--red)' : 'var(--blue)',
                              }}>
                                {sig.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Setup Instructions */}
              <div style={{ background: 'var(--bg2)', border: '1px solid var(--border2)', borderRadius: 10, padding: 24, marginTop: 24 }}>
                <div style={{ color: 'var(--t1)', fontWeight: 600, fontSize: 14, marginBottom: 16 }}>
                  <i className="fa-solid fa-circle-info" style={{ color: 'var(--blue)', marginRight: 8 }}></i>
                  Quick Setup Guide
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                  <div>
                    <div style={{ color: 'var(--amber)', fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
                      Step 1 — TradingView
                    </div>
                    <ol style={{ color: 'var(--t2)', fontSize: 12, paddingLeft: 16, lineHeight: '1.8' }}>
                      <li>Load <code style={{ color: 'var(--amber)' }}>GoldMaster_Strategy.pine</code> on XAUUSD M15</li>
                      <li>Create alert → condition: &quot;GoldMaster LONG/SHORT&quot;</li>
                      <li>Webhook URL: <code style={{ color: 'var(--amber)' }}>https://yourserver.com/api/tradingview/webhook</code></li>
                      <li>Message: leave as Pine Script template (JSON)</li>
                    </ol>
                  </div>
                  <div>
                    <div style={{ color: 'var(--amber)', fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
                      Step 2 — Python Bridge
                    </div>
                    <code style={{
                      display: 'block', background: 'var(--bg4)', padding: '10px 14px',
                      borderRadius: 6, fontSize: 11, color: 'var(--t1)', lineHeight: '1.8'
                    }}>
                      cd trading-bot/python<br/>
                      pip install -r requirements.txt<br/>
                      python ml_signal_generator.py --train<br/>
                      python webhook_bridge.py
                    </code>
                  </div>
                  <div>
                    <div style={{ color: 'var(--amber)', fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
                      Step 3 — MT4
                    </div>
                    <ol style={{ color: 'var(--t2)', fontSize: 12, paddingLeft: 16, lineHeight: '1.8' }}>
                      <li>Copy <code style={{ color: 'var(--amber)' }}>GoldMasterEA.mq4</code> to MT4 Experts folder</li>
                      <li>Compile in MetaEditor (F7)</li>
                      <li>Attach to XAUUSD M15 chart</li>
                      <li>Set <code>SignalsDir</code> to your signals folder path</li>
                      <li>Enable AutoTrading in MT4</li>
                    </ol>
                  </div>
                  <div>
                    <div style={{ color: 'var(--amber)', fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
                      Step 4 — Environment
                    </div>
                    <code style={{
                      display: 'block', background: 'var(--bg4)', padding: '10px 14px',
                      borderRadius: 6, fontSize: 11, color: 'var(--t1)', lineHeight: '1.8'
                    }}>
                      PYTHON_BRIDGE_URL=http://localhost:5000<br/>
                      WEBHOOK_SECRET=your-secret-key<br/>
                      ACCOUNT_SIZE=100000<br/>
                      PROP_FIRM_MODE=true
                    </code>
                  </div>
                </div>
              </div>

            </>
          )}
        </main>
      </div>
    </AuthGuard>
  );
}
