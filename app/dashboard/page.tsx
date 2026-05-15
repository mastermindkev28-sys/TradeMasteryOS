'use client';

import { useEffect, useMemo, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import ChartCard from '@/components/ChartCard';
import AuthGuard from '@/components/AuthGuard';
import { useSupabaseAuth } from '@/components/useSupabaseAuth';
import { supabase } from '@/lib/supabaseClient';
import { Trade } from '@/types/trade';

function formatDollar(value: number) {
  return value >= 0 ? `+$${value.toFixed(0)}` : `-$${Math.abs(value).toFixed(0)}`;
}

export default function DashboardPage() {
  const { session } = useSupabaseAuth();
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadTrades() {
      if (!session?.user?.id) return;
      setLoading(true);
      const { data, error } = await supabase
        .from('trades')
        .select('*')
        .eq('user_id', session.user.id)
        .order('date', { ascending: false })
        .limit(200);

      if (error) {
        console.error(error);
      } else if (data) {
        setTrades(data);
      }
      setLoading(false);
    }

    loadTrades();
  }, [session]);

  const metrics = useMemo(() => {
    const netPnL = trades.reduce((sum, trade) => sum + trade.profit_loss, 0);
    const totalTrades = trades.length;
    const wins = trades.filter((trade) => trade.outcome === 'W').length;
    const winRate = totalTrades ? Math.round((wins / totalTrades) * 1000) / 10 : 0;
    const avgR = totalTrades
      ? trades.reduce((sum, trade) => sum + trade.r_multiple, 0) / totalTrades
      : 0;

    let streak = 0;
    for (const trade of trades) {
      if (trade.outcome === 'W') {
        streak += 1;
      } else {
        break;
      }
    }

    return {
      netPnL,
      totalTrades,
      wins,
      winRate,
      avgR: totalTrades ? Number(avgR.toFixed(2)) : 0,
      streak,
    };
  }, [trades]);

  const chartData = useMemo(() => {
    const monthly = new Map<number, { label: string; pnl: number; wins: number; count: number; rTotal: number }>();

    trades
      .slice()
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
      .forEach((trade) => {
        const date = new Date(trade.date);
        if (Number.isNaN(date.getTime())) return;
        const key = date.getFullYear() * 100 + (date.getMonth() + 1);
        const label = date.toLocaleString('en-US', { month: 'short', year: 'numeric' });
        const current = monthly.get(key) ?? { label, pnl: 0, wins: 0, count: 0, rTotal: 0 };
        current.pnl += trade.profit_loss;
        current.wins += trade.outcome === 'W' ? 1 : 0;
        current.count += 1;
        current.rTotal += trade.r_multiple;
        monthly.set(key, current);
      });

    const entries = Array.from(monthly.entries()).sort(([a], [b]) => a - b);
    const labels = entries.map(([, value]) => value.label);
    const equity = entries.reduce<number[]>((acc, [, value]) => {
      const prev = acc.length ? acc[acc.length - 1] : 0;
      acc.push(prev + value.pnl);
      return acc;
    }, []);
    const monthlyPnL = entries.map(([, value]) => Number(value.pnl.toFixed(0)));
    const winRateTrend = entries.map(([, value]) => (value.count ? Math.round((value.wins / value.count) * 1000) / 10 : 0));
    const avgRTrend = entries.map(([, value]) => (value.count ? Number((value.rTotal / value.count).toFixed(2)) : 0));

    return { labels, equity, monthlyPnL, winRateTrend, avgRTrend };
  }, [trades]);

  const topSetups = useMemo(() => {
    const stats: Record<string, { count: number; wins: number }> = {};

    trades.forEach((trade) => {
      const key = trade.setup || 'Unknown';
      const current = stats[key] ?? { count: 0, wins: 0 };
      current.count += 1;
      current.wins += trade.outcome === 'W' ? 1 : 0;
      stats[key] = current;
    });

    return Object.entries(stats)
      .map(([setup, data]) => ({ setup, count: data.count, winRate: data.count ? Math.round((data.wins / data.count) * 100) : 0 }))
      .sort((a, b) => b.winRate - a.winRate || b.count - a.count)
      .slice(0, 3);
  }, [trades]);

  return (
    <AuthGuard>
      <Sidebar />
      <main className="main">
        <div className="page active">
          <div className="ph">
            <div className="ph-left">
              <div className="ph-title">📊 Performance Dashboard</div>
              <div className="ph-sub">Live trade metrics from Supabase · {trades.length} trades loaded</div>
            </div>
            <div className="ph-actions">
              <a className="btn btn-g" href="/database">
                <i className="fa-solid fa-plus"></i> New Trade
              </a>
              <button className="btn" onClick={() => window.location.reload()}>
                <i className="fa-solid fa-rotate"></i> Refresh
              </button>
            </div>
          </div>

          <div className="callout co-b">
            <i className="fa-solid fa-circle-info"></i>
            <div>
              <div className="co-title">Live trade journal is connected</div>
              <div className="co-body">
                Trades are read from Supabase. Add or edit entries from the Trade Database page and refresh the dashboard for updated metrics.
              </div>
            </div>
          </div>

          <div className="stat-grid">
            <div className="stat-card sc-g">
              <div className="stat-label">Net P&L</div>
              <div className="stat-value sv-g">{formatDollar(metrics.netPnL)}</div>
              <div className="stat-delta sd-up">{metrics.totalTrades} trades logged</div>
            </div>
            <div className="stat-card sc-b">
              <div className="stat-label">Win Rate</div>
              <div className="stat-value sv-b">{metrics.winRate}%</div>
              <div className="stat-delta sd-up">{metrics.winRate >= 60 ? 'Good momentum' : 'Keep refining'}</div>
            </div>
            <div className="stat-card sc-a">
              <div className="stat-label">Total Trades</div>
              <div className="stat-value sv-a">{metrics.totalTrades}</div>
              <div className="stat-delta">{loading ? 'Loading...' : 'Latest trades loaded'}</div>
            </div>
            <div className="stat-card sc-p">
              <div className="stat-label">Avg R-Multiple</div>
              <div className="stat-value sv-p">{metrics.avgR.toFixed(2)}R</div>
              <div className="stat-delta sd-up">Improving risk management</div>
            </div>
            <div className="stat-card sc-g">
              <div className="stat-label">Win Streak</div>
              <div className="stat-value sv-g">🔥 {metrics.streak}W</div>
              <div className="stat-delta">Most recent consecutive wins</div>
            </div>
          </div>

          <div className="g73">
            <div className="card">
              <div className="card-title"><i className="fa-solid fa-chart-line"></i> Equity Curve — YTD</div>
              <div className="cw" style={{ height: '210px' }}>
                {chartData.labels.length ? (
                  <ChartCard
                    type="line"
                    data={{
                      labels: chartData.labels,
                      datasets: [
                        {
                          data: chartData.equity,
                          borderColor: '#22d47a',
                          backgroundColor: 'rgba(34,212,122,0.07)',
                          fill: true,
                          tension: 0.4,
                          pointRadius: 4,
                          pointBackgroundColor: '#22d47a',
                          borderWidth: 2,
                        },
                      ],
                    }}
                    options={{
                      scales: {
                        y: {
                          grid: { color: 'rgba(255,255,255,0.04)' },
                          ticks: {
                            color: '#4e5a75',
                            callback: (value) => `$${Number(value).toFixed(0)}`,
                          },
                        },
                        x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#4e5a75' } },
                      },
                    }}
                  />
                ) : (
                  <div style={{ color: 'var(--t2)', padding: '22px 0' }}>Add trades to populate the equity curve.</div>
                )}
              </div>
            </div>
            <div className="card">
              <div className="card-title"><i className="fa-solid fa-trophy"></i> Top Setups by Win Rate</div>
              {topSetups.length ? (
                topSetups.map((setup, index) => (
                  <div key={setup.setup} className="setup-row" style={{ borderBottom: index === topSetups.length - 1 ? 'none' : undefined, paddingBottom: index === topSetups.length - 1 ? 0 : undefined }}>
                    <div className="setup-rank" style={{ background: index === 0 ? 'var(--abg)' : 'var(--bg4)', color: index === 0 ? 'var(--amber)' : 'var(--t3)' }}>{index + 1}</div>
                    <div className="setup-name">{setup.setup}</div>
                    <div className="sbar-bg"><div className="sbar-fill" style={{ width: `${setup.winRate}%`, background: index === 0 ? 'var(--green)' : index === 1 ? 'var(--blue)' : 'var(--blue)' }}></div></div>
                    <span className={index === 2 ? 'tag tr' : index === 1 ? 'tag tb' : 'tag tg'} style={{ fontSize: '9px' }}>{setup.winRate}%</span>
                  </div>
                ))
              ) : (
                <div style={{ color: 'var(--t2)', padding: '14px 0' }}>Add trades to discover your best setups.</div>
              )}
            </div>
          </div>

          <div className="g3">
            <div className="card">
              <div className="card-title"><i className="fa-solid fa-arrow-trend-up"></i> Win Rate Trend (Monthly)</div>
              <div className="cw" style={{ height: '130px' }}>
                {chartData.labels.length ? (
                  <ChartCard
                    type="line"
                    data={{
                      labels: chartData.labels,
                      datasets: [
                        {
                          data: chartData.winRateTrend,
                          borderColor: '#4f8ef7',
                          backgroundColor: 'rgba(79,142,247,0.07)',
                          fill: true,
                          tension: 0.4,
                          pointRadius: 3,
                          borderWidth: 2,
                        },
                      ],
                    }}
                    options={{
                      scales: {
                        y: { min: 0, max: 100, grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#4e5a75', callback: (value) => `${value}%` } },
                        x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#4e5a75' } },
                      },
                    }}
                  />
                ) : (
                  <div style={{ color: 'var(--t2)', padding: '18px 0' }}>No monthly win rate chart available yet.</div>
                )}
              </div>
            </div>
            <div className="card">
              <div className="card-title"><i className="fa-solid fa-coins"></i> Avg R-Multiple Trend</div>
              <div className="cw" style={{ height: '130px' }}>
                {chartData.labels.length ? (
                  <ChartCard
                    type="line"
                    data={{
                      labels: chartData.labels,
                      datasets: [
                        {
                          data: chartData.avgRTrend,
                          borderColor: '#9b7cf4',
                          backgroundColor: 'rgba(155,124,244,0.07)',
                          fill: true,
                          tension: 0.4,
                          pointRadius: 3,
                          borderWidth: 2,
                        },
                      ],
                    }}
                    options={{
                      scales: {
                        y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#4e5a75', callback: (value) => `${Number(value).toFixed(1)}R` } },
                        x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#4e5a75' } },
                      },
                    }}
                  />
                ) : (
                  <div style={{ color: 'var(--t2)', padding: '18px 0' }}>No R-multiple trend available yet.</div>
                )}
              </div>
            </div>
            <div className="card">
              <div className="card-title"><i className="fa-solid fa-chart-bar"></i> Monthly P&L</div>
              <div className="cw" style={{ height: '130px' }}>
                {chartData.labels.length ? (
                  <ChartCard
                    type="bar"
                    data={{
                      labels: chartData.labels,
                      datasets: [
                        {
                          data: chartData.monthlyPnL,
                          backgroundColor: chartData.monthlyPnL.map((value) => (value >= 0 ? 'rgba(34,212,122,0.7)' : 'rgba(240,82,82,0.7)')),
                          borderRadius: 4,
                        },
                      ],
                    }}
                    options={{
                      scales: {
                        y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#4e5a75', callback: (value) => `$${Number(value).toFixed(0)}` } },
                        x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#4e5a75' } },
                      },
                    }}
                  />
                ) : (
                  <div style={{ color: 'var(--t2)', padding: '18px 0' }}>Monthly P&L will show once trades are logged.</div>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </AuthGuard>
  );
}
