import Sidebar from '@/components/Sidebar';

export default function DailyPage() {
  return (
    <>
      <Sidebar />
      <main className="main">
        <div className="page active">
          <div className="ph">
            <div className="ph-left">
              <div className="ph-title">🌅 Daily Trading Log</div>
              <div className="ph-sub">Wednesday, June 5, 2025 · Example filled day · Duplicate for each trading day</div>
            </div>
            <div className="ph-actions">
              <button className="btn btn-b"><i className="fa-solid fa-copy"></i> Duplicate Template</button>
            </div>
          </div>

          <div className="g2">
            <div className="card">
              <div className="card-title"><i className="fa-solid fa-face-smile"></i> Pre-Market Mindset Check</div>
              <div className="mood-row">
                <div className="mood-label">Mood / Energy</div>
                <div className="mood-dots">
                  <div className="md on"></div><div className="md on"></div><div className="md on"></div><div className="md on"></div><div className="md on"></div><div className="md"></div><div className="md"></div><div className="md"></div><div className="md"></div><div className="md"></div>
                </div>
                <div className="mood-val">5/10</div>
              </div>
              <div className="mood-row">
                <div className="mood-label">Sleep Quality</div>
                <div className="mood-dots">
                  <div className="md on-g"></div><div className="md on-g"></div><div className="md on-g"></div><div className="md on-g"></div><div className="md on-g"></div><div className="md on-g"></div><div className="md on-g"></div><div className="md"></div><div className="md"></div><div className="md"></div>
                </div>
                <div className="mood-val">7/10</div>
              </div>
              <div className="mood-row">
                <div className="mood-label">Focus Level</div>
                <div className="mood-dots">
                  <div className="md on-p"></div><div className="md on-p"></div><div className="md on-p"></div><div className="md on-p"></div><div className="md on-p"></div><div className="md on-p"></div><div className="md on-p"></div><div className="md on-p"></div><div className="md"></div><div className="md"></div>
                </div>
                <div className="mood-val">8/10</div>
              </div>
              <div className="div"></div>
              <div style={{ fontSize: '9px', color: 'var(--t3)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.1em', marginBottom: '7px' }}>Market Conditions</div>
              <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
                <span className="tag tg">Trending Up</span>
                <span className="tag tb">High Volume</span>
                <span className="tag tgr">Earnings Season</span>
                <span className="tag ta">VIX: 18.4</span>
              </div>
            </div>
            <div className="card">
              <div className="card-title"><i className="fa-solid fa-note-sticky"></i> Pre-Market Notes & Game Plan</div>
              <div className="rev-a" style={{ minHeight: '120px' }}>
                <strong style={{ color: 'var(--t1)' }}>Overnight news:</strong> NVDA earnings beat after close. Tech gapping up 1.2% pre-market.<br /><br />
                <strong style={{ color: 'var(--t1)' }}>Key levels:</strong> SPY $440 (resistance), QQQ $376 (support), NVDA $480 (gap fill)<br /><br />
                <strong style={{ color: 'var(--t1)' }}>Today&apos;s focus:</strong> Wait for opening drive confirmation. Look for bull flags on high-volume leaders. NO chasing opens.
              </div>
              <div className="quote" style={{ marginTop: '10px', marginBottom: 0 }}>
                &quot;I will only take trades that fit my plan today. Quality over quantity.&quot;<cite>— Morning Intention Statement</cite>
              </div>
            </div>
          </div>

          <div className="card mb14">
            <div className="card-title" style={{ marginBottom: '14px' }}><i className="fa-solid fa-chart-candlestick"></i> Trade #1 &nbsp;<span className="tag tg">WIN</span></div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '12px', marginBottom: '14px' }}>
              <div>
                <div style={{ fontSize: '9px', color: 'var(--t3)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: '5px' }}>Symbol</div>
                <div style={{ fontSize: '18px', fontWeight: 800, fontFamily: 'var(--mono)' }}>NVDA</div>
              </div>
              <div>
                <div style={{ fontSize: '9px', color: 'var(--t3)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: '5px' }}>Direction</div>
                <span className="tag tg" style={{ fontSize: '11px' }}>📈 LONG</span>
              </div>
              <div>
                <div style={{ fontSize: '9px', color: 'var(--t3)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: '5px' }}>Setup</div>
                <span className="tag tb" style={{ fontSize: '11px' }}>Bull Flag BO</span>
              </div>
              <div>
                <div style={{ fontSize: '9px', color: 'var(--t3)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: '5px' }}>Timeframe</div>
                <div className="mono" style={{ fontSize: '12px' }}>5min / 1H</div>
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '12px', marginBottom: '14px' }}>
              <div>
                <div style={{ fontSize: '9px', color: 'var(--t3)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: '5px' }}>Entry</div>
                <div className="mono" style={{ fontSize: '14px', fontWeight: 600 }}>$468.40</div>
              </div>
              <div>
                <div style={{ fontSize: '9px', color: 'var(--t3)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: '5px' }}>Stop Loss</div>
                <div className="mono" style={{ fontSize: '14px', fontWeight: 600, color: 'var(--red)' }}>$463.20</div>
              </div>
              <div>
                <div style={{ fontSize: '9px', color: 'var(--t3)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: '5px' }}>Exit / Target</div>
                <div className="mono" style={{ fontSize: '14px', fontWeight: 600, color: 'var(--green)' }}>$479.00</div>
              </div>
              <div>
                <div style={{ fontSize: '9px', color: 'var(--t3)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: '5px' }}>R:R Ratio</div>
                <div className="mono" style={{ fontSize: '14px', fontWeight: 600, color: 'var(--purple)' }}>2.1:1</div>
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '12px', marginBottom: '14px' }}>
              <div>
                <div style={{ fontSize: '9px', color: 'var(--t3)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: '5px' }}>P&L</div>
                <div className="mono" style={{ fontSize: '16px', fontWeight: 800, color: 'var(--green)' }}>+$520</div>
              </div>
              <div>
                <div style={{ fontSize: '9px', color: 'var(--t3)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: '5px' }}>R-Multiple</div>
                <div className="mono" style={{ fontSize: '16px', fontWeight: 800, color: 'var(--green)' }}>+2.0R</div>
              </div>
              <div>
                <div style={{ fontSize: '9px', color: 'var(--t3)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: '5px' }}>Outcome</div>
                <span className="tag tg" style={{ fontSize: '11px' }}>WIN ✓</span>
              </div>
              <div>
                <div style={{ fontSize: '9px', color: 'var(--t3)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: '5px' }}>Followed Plan?</div>
                <span className="tag tg" style={{ fontSize: '11px' }}>✓ YES</span>
              </div>
            </div>
            <div style={{ fontSize: '9px', color: 'var(--t3)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: '6px' }}>Entry Thesis</div>
            <div className="rev-a" style={{ marginBottom: '12px', minHeight: '36px' }}>NVDA formed clean bull flag on 5-min after opening drive. Volume confirmed on breakout above $467 flag resistance. Strong relative strength vs SPY. Catalyst: earnings beat.</div>
            <div style={{ fontSize: '9px', color: 'var(--t3)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: '6px' }}>Emotions During Trade</div>
            <div style={{ display: 'flex', gap: '5px', marginBottom: '13px' }}><span className="tag tb">Calm & Focused</span><span className="tag tg">Confident in setup</span><span className="tag tgr">No urge to exit early</span></div>
            <div className="img-ph" style={{ height: '150px' }}><i className="fa-solid fa-image"></i><span>Click to upload annotated chart screenshot</span><span style={{ fontSize: '10px' }}>Recommended: TradingView screenshot with marked entry / exit / stop</span></div>
          </div>

          <div className="card">
            <div className="card-title"><i className="fa-solid fa-moon"></i> Daily Summary & Post-Market Reflection</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '10px', marginBottom: '18px' }}>
              <div className="stat-card sc-g" style={{ padding: '13px' }}><div className="stat-label">Day P&L</div><div className="stat-value sv-g" style={{ fontSize: '18px' }}>+$840</div></div>
              <div className="stat-card sc-b" style={{ padding: '13px' }}><div className="stat-label">Trades Taken</div><div className="stat-value sv-b" style={{ fontSize: '18px' }}>3</div></div>
              <div className="stat-card sc-g" style={{ padding: '13px' }}><div className="stat-label">Day Win Rate</div><div className="stat-value sv-g" style={{ fontSize: '18px' }}>67%</div></div>
              <div className="stat-card sc-p" style={{ padding: '13px' }}><div className="stat-label">Plan Adherence</div><div className="stat-value sv-p" style={{ fontSize: '18px' }}>9/10</div></div>
            </div>
            <div className="rev-q">What did I do well today?</div>
            <div className="rev-a">Waited patiently for the NVDA setup instead of chasing the open. Respected my stop on the AAPL trade. Took profits at planned target — didn&apos;t get greedy.</div>
            <div className="rev-q">What would I improve?</div>
            <div className="rev-a">Entered AMD a bit early — should have waited for full candle close above resistance. Also checked P&L mid-trade. Keep chart full screen, hide P&L on open positions.</div>
            <div className="rev-q">Key lesson for tomorrow</div>
            <div className="rev-a" style={{ marginBottom: 0 }}>Patience pays. The best setup (NVDA) came 45 minutes after open. Trust the plan, trust the stop, let the trade breathe.</div>
          </div>
        </div>
      </main>
    </>
  );
}
