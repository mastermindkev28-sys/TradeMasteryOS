import Sidebar from '@/components/Sidebar';

export default function PsychologyPage() {
  return (
    <>
      <Sidebar />
      <main className="main">
        <div className="page active">
          <div className="ph">
            <div className="ph-left">
              <div className="ph-title">🧠 Psychology & Emotions Journal</div>
              <div className="ph-sub">Self-awareness is your greatest trading edge</div>
            </div>
          </div>

          <div className="callout co-b">
            <i className="fa-solid fa-circle-info"></i>
            <div>
              <div className="co-title">Why track emotions?</div>
              <div className="co-body">Research shows 80%+ of trading losses are psychology-driven. By tracking emotional states, you identify patterns that predict poor decision-making — before they cost real money.</div>
            </div>
          </div>

          <div className="card mb14">
            <div className="card-title"><i className="fa-solid fa-face-grin-beam"></i> Emotion Frequency Gallery — This Month</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6,1fr)', gap: '8px' }}>
              <div className="em-card"><div className="em-emoji">😌</div><div className="em-name">Calm</div><div className="em-freq">18 trades</div><div style={{ marginTop: '6px' }}><div className="prog-bg"><div className="prog-fill" style={{ width: '90%', background: 'var(--green)' }}></div></div></div></div>
              <div className="em-card"><div className="em-emoji">🎯</div><div className="em-name">Focused</div><div className="em-freq">14 trades</div><div style={{ marginTop: '6px' }}><div className="prog-bg"><div className="prog-fill" style={{ width: '70%', background: 'var(--blue)' }}></div></div></div></div>
              <div className="em-card"><div className="em-emoji">🤔</div><div className="em-name">Uncertain</div><div className="em-freq">4 trades</div><div style={{ marginTop: '6px' }}><div className="prog-bg"><div className="prog-fill" style={{ width: '20%', background: 'var(--purple)' }}></div></div></div></div>
              <div className="em-card"><div className="em-emoji">😰</div><div className="em-name">Anxious</div><div className="em-freq">6 trades</div><div style={{ marginTop: '6px' }}><div className="prog-bg"><div className="prog-fill" style={{ width: '30%', background: 'var(--amber)' }}></div></div></div></div>
              <div className="em-card"><div className="em-emoji">😤</div><div className="em-name">FOMO</div><div className="em-freq">3 trades</div><div style={{ marginTop: '6px' }}><div className="prog-bg"><div className="prog-fill" style={{ width: '15%', background: 'var(--red)' }}></div></div></div></div>
              <div className="em-card"><div className="em-emoji">😡</div><div className="em-name">Revenge</div><div className="em-freq">1 trade</div><div style={{ marginTop: '6px' }}><div className="prog-bg"><div className="prog-fill" style={{ width: '5%', background: 'var(--red)' }}></div></div></div></div>
            </div>
          </div>

          <div className="g2">
            <div className="card">
              <div className="card-title"><i className="fa-solid fa-triangle-exclamation"></i> Trigger Log</div>
              <div className="toggle open"><div className="toggle-h"><span className="tag tr" style={{ fontSize: '9px' }}>FOMO</span>&nbsp; Missing a big move causes me to chase</div>
                <div className="toggle-body"><strong style={{ color: 'var(--t1)' }}>Trigger:</strong> Watching a stock run without me after passing on the setup.<br /><strong style={{ color: 'var(--t1)' }}>Pattern:</strong> I enter late, chasing price near a short-term top.<br /><strong style={{ color: 'var(--t1)' }}>Fix:</strong> Write &quot;There will always be another trade&quot; pre-market. Keep watchlist loaded with quality setups so I&apos;m never desperate.</div>
              </div>
              <div className="toggle"><div className="toggle-h"><span className="tag tr" style={{ fontSize: '9px' }}>REVENGE</span>&nbsp; After a loss I want to win it back</div>
                <div className="toggle-body"><strong style={{ color: 'var(--t1)' }}>Trigger:</strong> Hitting stop on a confident trade.<br /><strong style={{ color: 'var(--t1)' }}>Pattern:</strong> Immediately looking for next trade, sizing up.<br /><strong style={{ color: 'var(--t1)' }}>Fix:</strong> Mandatory 30-min break after any loss. Log the trade immediately while emotions are fresh.</div>
              </div>
              <div className="toggle"><div className="toggle-h"><span className="tag ta" style={{ fontSize: '9px' }}>OVERCONFIDENCE</span>&nbsp; Winning streak makes me size too large</div>
                <div className="toggle-body"><strong style={{ color: 'var(--t1)' }}>Trigger:</strong> Multiple consecutive wins creating an &quot;invincible&quot; feeling.<br /><strong style={{ color: 'var(--t1)' }}>Fix:</strong> Position size is ALWAYS calculated from the formula — never gut feeling. Spreadsheet check before every entry.</div>
              </div>
            </div>
            <div className="card">
              <div className="card-title"><i className="fa-solid fa-chart-bar"></i> Win Rate by Emotional State</div>
              <div className="cw" style={{ height: '220px' }}><canvas id="c-emotion" role="img" aria-label="Win rate by emotion: Calm 74%, Focused 71%, Uncertain 48%, Anxious 38%, FOMO 22%, Revenge 0%">Win rate drops dramatically with negative emotions — from 74% when calm to 0% when revenge trading.</canvas></div>
            </div>
          </div>

          <div className="quote">&quot;When you trade from fear, anger, or greed — you&apos;re not trading the market. You&apos;re trading your emotions.&quot;<cite>— Trading Psychology Principle</cite></div>
        </div>
      </main>
    </>
  );
}
