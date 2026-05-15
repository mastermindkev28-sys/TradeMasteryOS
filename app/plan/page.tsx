import Sidebar from '@/components/Sidebar';

export default function PlanPage() {
  return (
    <>
      <Sidebar />
      <main className="main">
        <div className="page active">
          <div className="ph">
            <div className="ph-left">
              <div className="ph-title">📋 Trading Plan & Rules</div>
              <div className="ph-sub">Last updated: Jun 1, 2025 · Version 3.2 · Read every morning</div>
            </div>
            <div className="ph-actions">
              <button className="btn"><i className="fa-solid fa-pen"></i> Edit Plan</button>
            </div>
          </div>

          <div className="callout co-a">
            <i className="fa-solid fa-triangle-exclamation"></i>
            <div>
              <div className="co-title">⚠️ Read This Every Morning Before Trading</div>
              <div className="co-body">Your trading plan is your constitution. Every deviation is a vote against your future self. If a trade isn't in the plan — don't take it. Consistency beats perfection every time.</div>
            </div>
          </div>

          <div className="g2" style={{ marginTop: '14px' }}>
            <div className="card">
              <div className="card-title"><i className="fa-solid fa-shield"></i> Core Trading Rules</div>
              <div className="rule-item"><span className="rnum">01</span>Never risk more than 1% of account per trade</div>
              <div className="rule-item"><span className="rnum">02</span>Max 3 open positions at any time</div>
              <div className="rule-item"><span className="rnum">03</span>Stop trading after 2 consecutive losses — 30 min break minimum</div>
              <div className="rule-item"><span className="rnum">04</span>Daily max loss: -$500. Hit it → trading day is over. No exceptions.</div>
              <div className="rule-item"><span className="rnum">05</span>Only trade high-quality setups — patience is a position</div>
              <div className="rule-item"><span className="rnum">06</span>Never move stop loss to increase risk — only to lock profits</div>
              <div className="rule-item"><span className="rnum">07</span>Minimum R:R must be 2:1 before entry</div>
              <div className="rule-item"><span className="rnum">08</span>No trading first 15 minutes of open — observe only</div>
              <div className="rule-item"><span className="rnum">09</span>No news trades unless pre-planned and sized down 50%</div>
              <div className="rule-item"><span className="rnum">10</span>Log EVERY trade. No exceptions. Ever.</div>
            </div>
            <div>
              <div className="card mb14">
                <div className="card-title"><i className="fa-solid fa-sliders"></i> Risk Parameters</div>
                <table className="mtable">
                  <tr><td>Account Size</td><td className="mono">$25,000</td></tr>
                  <tr><td>Max Risk / Trade</td><td className="mono" style={{ color: 'var(--amber)' }}>1% = $250</td></tr>
                  <tr><td>Daily Loss Limit</td><td className="mono" style={{ color: 'var(--red)' }}>-$500</td></tr>
                  <tr><td>Weekly Loss Limit</td><td className="mono" style={{ color: 'var(--red)' }}>-$1,500</td></tr>
                  <tr><td>Min R:R</td><td className="mono" style={{ color: 'var(--green)' }}>2:1</td></tr>
                  <tr><td>Position Sizing</td><td className="mono">Fixed Risk $</td></tr>
                  <tr><td>Instruments</td><td className="mono">US Equities, ETFs</td></tr>
                </table>
              </div>
              <div className="card">
                <div className="card-title"><i className="fa-solid fa-check-double"></i> Allowed Setups</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginBottom: '12px' }}>
                  <span className="tag tg">Bull Flag Breakout</span>
                  <span className="tag tg">VWAP Reclaim</span>
                  <span className="tag tg">Opening Drive</span>
                  <span className="tag tb">Momentum Pullback</span>
                  <span className="tag tb">Gap & Go</span>
                  <span className="tag tb">EMA Bounce</span>
                  <span className="tag ta">Range Breakout</span>
                  <span className="tag ta">Trend Continuation</span>
                </div>
                <div className="div"></div>
                <div className="card-title" style={{ color: 'var(--red)', marginBottom: '6px' }}><i className="fa-solid fa-ban"></i> Forbidden</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                  <span className="tag tr">Reversal catches</span>
                  <span className="tag tr">FOMO chases</span>
                  <span className="tag tr">Untested levels</span>
                  <span className="tag tr">Pre-market low float</span>
                </div>
              </div>
            </div>
          </div>

          <div className="toggle open"><div className="toggle-h"><i className="fa-solid fa-clock" style={{ color: 'var(--t3)', fontSize: '12px' }}></i>&nbsp; Trading Hours & Sessions</div>
            <div className="toggle-body">
              <strong style={{ color: 'var(--green)' }}>Prime Session:</strong> 9:45 AM – 11:30 AM EST — highest quality setups, most follow-through<br />
              <strong style={{ color: 'var(--blue)' }}>Afternoon Session:</strong> 2:00 PM – 3:30 PM EST — trend continuation only, half size<br />
              <strong style={{ color: 'var(--red)' }}>Avoid:</strong> 12:00 PM – 1:30 PM EST (lunch chop), last 30 min (erratic fills)
            </div>
          </div>
          <div className="toggle"><div className="toggle-h"><i className="fa-solid fa-chart-candlestick" style={{ color: 'var(--t3)', fontSize: '12px' }}></i>&nbsp; Timeframe Hierarchy</div>
            <div className="toggle-body">
              <strong style={{ color: 'var(--t1)' }}>Top-down approach every morning:</strong><br />
              Daily chart → bias & key support/resistance levels<br />
              1H chart → structure, trend direction, major S/R<br />
              5-min chart → entry timing, pattern confirmation<br />
              1-min chart → precision entry only (never for analysis)
            </div>
          </div>
          <div className="toggle"><div className="toggle-h"><i className="fa-solid fa-brain" style={{ color: 'var(--t3)', fontSize: '12px' }}></i>&nbsp; Mental Framework & Mindset Rules</div>
            <div className="toggle-body">
              Every trade is a probability, not a certainty. You are playing the long game across hundreds of executions.<br /><br />
              Before every trade ask: <em style={{ color: 'var(--t1)' }}>&quot;Would I be comfortable if 100 traders took this exact same trade right now?&quot;</em><br /><br />
              Losses are tuition. Log them, learn from them, move forward with discipline.
            </div>
          </div>

          <div className="quote">"The market is designed to transfer money from the impatient to the patient."<cite>— Warren Buffett</cite></div>
        </div>
      </main>
    </>
  );
}
