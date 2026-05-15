import Sidebar from '@/components/Sidebar';

export default function AnalyticsPage() {
  return (
    <>
      <Sidebar />
      <main className="main">
        <div className="page active">
          <div className="ph">
            <div className="ph-left">
              <div className="ph-title">📈 Analytics & Reviews</div>
              <div className="ph-sub">Deep performance analysis · Growth tracking over time</div>
            </div>
            <div className="ph-actions">
              <button className="btn"><i className="fa-solid fa-calendar-week"></i> Weekly Review</button>
              <button className="btn btn-b"><i className="fa-solid fa-file-chart-column"></i> Monthly Report</button>
            </div>
          </div>

          <div className="g2">
            <div className="card">
              <div className="card-title"><i className="fa-solid fa-chart-line"></i> Full Equity Curve — YTD</div>
              <div className="cw" style={{ height: '195px' }}><canvas id="c-eq2" role="img" aria-label="Full equity curve showing growth from $20,000 to $38,420">Full equity curve showing consistent upward growth with two drawdown periods.</canvas></div>
            </div>
            <div className="card">
              <div className="card-title"><i className="fa-solid fa-arrow-down-short-wide"></i> Drawdown Chart</div>
              <div className="cw" style={{ height: '195px' }}><canvas id="c-dd" role="img" aria-label="Drawdown chart showing max drawdown of 14.2% in February">Drawdown chart with max drawdown of 14.2% in Feb, now recovering to -1.1%.</canvas></div>
            </div>
          </div>

          <div className="card mb14">
            <div className="card-title"><i className="fa-solid fa-table-cells"></i> Weekly P&L Heatmap — June 2025</div>
            <div className="hmap-grid">
              <div></div>
              <div className="hmap-head">Mon</div><div className="hmap-head">Tue</div><div className="hmap-head">Wed</div><div className="hmap-head">Thu</div><div className="hmap-head">Fri</div>
              <div className="hmap-row-label">Wk 1</div>
              <div className="hmap-cell" style={{ background: 'var(--gbg)', color: 'var(--green)' }}>+$840</div>
              <div className="hmap-cell" style={{ background: 'var(--gbg)', color: 'var(--green)' }}>+$320</div>
              <div className="hmap-cell" style={{ background: 'var(--rbg)', color: 'var(--red)' }}>-$180</div>
              <div className="hmap-cell" style={{ background: 'rgba(34,212,122,0.18)', color: 'var(--green)' }}>+$1,240</div>
              <div className="hmap-cell" style={{ background: 'var(--gbg)', color: 'var(--green)' }}>+$580</div>
              <div className="hmap-row-label">Wk 2</div>
              <div className="hmap-cell" style={{ background: 'rgba(34,212,122,0.18)', color: 'var(--green)' }}>+$1,820</div>
              <div className="hmap-cell" style={{ background: 'var(--rbg)', color: 'var(--red)' }}>-$420</div>
              <div className="hmap-cell" style={{ background: 'var(--gbg)', color: 'var(--green)' }}>+$940</div>
              <div className="hmap-cell" style={{ background: 'var(--gbg)', color: 'var(--green)' }}>+$380</div>
              <div className="hmap-cell" style={{ background: 'var(--rbg)', color: 'var(--red)' }}>-$250</div>
              <div className="hmap-row-label">Wk 3</div>
              <div className="hmap-cell" style={{ background: 'rgba(34,212,122,0.22)', color: 'var(--green)' }}>+$2,140</div>
              <div className="hmap-cell" style={{ background: 'var(--gbg)', color: 'var(--green)' }}>+$680</div>
              <div className="hmap-cell" style={{ background: 'var(--gbg)', color: 'var(--green)' }}>+$490</div>
              <div className="hmap-cell" style={{ background: 'var(--gbg)', color: 'var(--green)' }}>+$720</div>
              <div className="hmap-cell" style={{ background: 'var(--gbg)', color: 'var(--green)' }}>+$310</div>
            </div>
          </div>

          <div className="toggle open" style={{ marginTop: '6px' }}>
            <div className="toggle-h"><i className="fa-solid fa-calendar-week" style={{ color: 'var(--t3)', fontSize: '12px' }}></i>&nbsp; Weekly Review Template — Week of Jun 2–6</div>
            <div className="toggle-body">
              <div className="rev-q">What was the market environment this week?</div>
              <div className="rev-a">Bullish trend with tech leading. High volatility Mon–Tue due to NVDA earnings. Choppy mid-week. Friday had clean directional moves — best day for setups.</div>
              <div className="rev-q">What setups worked best?</div>
              <div className="rev-a">Bull Flag Breakouts remained highest-probability. VWAP reclaims worked well Wed and Fri. Opening Drive plays were clean on non-news days.</div>
              <div className="rev-q">Top 3 improvements for next week</div>
              <div className="rev-a" style={{ marginBottom: 0 }}>1. Use price alerts instead of staring at charts — reduces emotional interference.<br />2. Record a pre-market video walkthrough to stay accountable to thesis.<br />3. Journal within 30 min of close — not in the evening when memory fades.</div>
            </div>
          </div>
          <div className="toggle" style={{ marginTop: '6px' }}>
            <div className="toggle-h"><i className="fa-solid fa-chart-mixed" style={{ color: 'var(--t3)', fontSize: '12px' }}></i>&nbsp; Monthly Deep Review — May 2025</div>
            <div className="toggle-body">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '8px', marginBottom: '14px' }}>
                <div className="stat-card sc-g" style={{ padding: '10px' }}><div className="stat-label">May Net P&L</div><div className="stat-value sv-g" style={{ fontSize: '16px' }}>+$4,220</div></div>
                <div className="stat-card sc-b" style={{ padding: '10px' }}><div className="stat-label">Trades</div><div className="stat-value sv-b" style={{ fontSize: '16px' }}>28</div></div>
                <div className="stat-card sc-a" style={{ padding: '10px' }}><div className="stat-label">Win Rate</div><div className="stat-value sv-a" style={{ fontSize: '16px' }}>63%</div></div>
                <div className="stat-card sc-p" style={{ padding: '10px' }}><div className="stat-label">Avg R-Mult</div><div className="stat-value sv-p" style={{ fontSize: '16px' }}>+1.72R</div></div>
              </div>
              <div className="rev-a" style={{ marginBottom: 0 }}>May was a strong month driven by excellent execution in weeks 1–2. The mid-month drawdown was handled well — respected daily loss limits, stopped early on two days. Biggest lesson: scaling into winners when price action confirms is leaving money on the table.</div>
            </div>
          </div>

          <div className="callout co-g" style={{ marginTop: '14px' }}>
            <i className="fa-solid fa-chart-simple"></i>
            <div>
              <div className="co-title">Live Chart Integration Guide</div>
              <div className="co-body">Export Notion database as CSV weekly → import to Google Sheets → publish as webpage → embed URL in Notion using /embed block. Or use TradingView paper portfolio for live equity curve tracking.</div>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
