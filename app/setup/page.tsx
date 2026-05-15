import Sidebar from '@/components/Sidebar';

export default function SetupPage() {
  return (
    <>
      <Sidebar />
      <main className="main">
        <div className="page active">
          <div className="ph">
            <div className="ph-left">
              <div className="ph-title">📖 Setup Guide</div>
              <div className="ph-sub">Get fully operational in under 30 minutes</div>
            </div>
            <div className="ph-actions">
              <button className="btn btn-b"><i className="fa-solid fa-download"></i> Download PDF Guide</button>
            </div>
          </div>

          <div className="callout co-g"><i className="fa-solid fa-rocket"></i>
            <div>
              <div className="co-title">Quick Start — 3 Steps</div>
              <div className="co-body">Step 1: Duplicate template → Step 2: Fill in your Trading Plan & Rules → Step 3: Log your first trade in Daily Log. You&apos;re up and running today.</div>
            </div>
          </div>

          <div className="toggle open"><div className="toggle-h"><span style={{ background: 'var(--bbg)', color: 'var(--blue)', borderRadius: '50%', width: '20px', height: '20px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', fontWeight: 800, flexShrink: 0 }}>1</span>&nbsp; How to Duplicate This Template</div>
            <div className="toggle-body">1. Open the template link while logged into Notion.<br />2. Click &quot;Duplicate&quot; button in the top-right corner.<br />3. Choose your workspace from the dropdown.<br />4. Wait 30–60 seconds for all pages and databases to copy.<br />5. Template appears in sidebar as &quot;TradingOS — Trading Journal&quot;.<br /><br /><strong style={{ color: 'var(--amber)' }}>Important:</strong> Don&apos;t share your duplicated copy publicly — this shares your personal trade data.</div>
          </div>
          <div className="toggle"><div className="toggle-h"><span style={{ background: 'var(--bbg)', color: 'var(--blue)', borderRadius: '50%', width: '20px', height: '20px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', fontWeight: 800, flexShrink: 0 }}>2</span>&nbsp; Personalizing Your Trading Plan</div>
            <div className="toggle-body">1. Navigate to &quot;📋 Trading Plan &amp; Rules&quot;.<br />2. Replace all placeholder text with YOUR actual rules.<br />3. Update Risk Parameters table with your account size.<br />4. Edit Allowed Setups to match your specific strategy.<br />5. Read your plan every morning before markets open.<br /><br /><strong style={{ color: 'var(--green)' }}>Pro tip:</strong> Screenshot your rules and set it as your phone wallpaper.</div>
          </div>
          <div className="toggle"><div className="toggle-h"><span style={{ background: 'var(--bbg)', color: 'var(--blue)', borderRadius: '50%', width: '20px', height: '20px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', fontWeight: 800, flexShrink: 0 }}>3</span>&nbsp; Setting Up the Trade Database</div>
            <div className="toggle-body">1. Go to &quot;🗃️ Master Trade Database&quot;.<br />2. Pre-configured with all properties and formulas — nothing to set up.<br />3. Click &quot;+ New&quot; to add your first trade.<br />4. Fill in: Date, Symbol, Direction, Setup, Entry/Exit, Stop, Target.<br />5. Formulas auto-calculate R-Multiple, P&L%, and R:R Ratio.<br />6. Upload chart screenshot to the Files property.<br /><br /><strong style={{ color: 'var(--blue)' }}>Note:</strong> Dashboard stats pull from this database. Log every trade here for accurate metrics.</div>
          </div>
          <div className="toggle"><div className="toggle-h"><span style={{ background: 'var(--bbg)', color: 'var(--blue)', borderRadius: '50%', width: '20px', height: '20px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', fontWeight: 800, flexShrink: 0 }}>4</span>&nbsp; Daily Workflow — How to Use Every Day</div>
            <div className="toggle-body"><strong style={{ color: 'var(--t1)' }}>Pre-Market (30 min before open):</strong><br />→ Duplicate Daily Log template for today&apos;s date<br />→ Complete mindset check (mood, sleep, energy)<br />→ Write pre-market notes and game plan<br /><br /><strong style={{ color: 'var(--t1)' }}>During Trading:</strong><br />→ Log each trade immediately after execution<br />→ Upload chart screenshots right after each trade closes<br />→ Note emotional state during each trade<br /><br /><strong style={{ color: 'var(--t1)' }}>Post-Market (within 60 min of close):</strong><br />→ Complete daily summary section<br />→ Answer the 3 reflection questions honestly<br />→ Add trades to the Master Trade Database</div>
          </div>
          <div className="toggle"><div className="toggle-h"><span style={{ background: 'var(--bbg)', color: 'var(--blue)', borderRadius: '50%', width: '20px', height: '20px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', fontWeight: 800, flexShrink: 0 }}>5</span>&nbsp; Connecting Live Charts (Google Sheets / TradingView)</div>
            <div className="toggle-body"><strong style={{ color: 'var(--t1)' }}>Method 1 — Google Sheets (Recommended):</strong><br />1. Export Notion database as CSV weekly<br />2. Import into Google Sheets → auto-generates charts<br />3. Publish Google Sheet as webpage<br />4. Embed URL in Notion using /embed block<br /><br /><strong style={{ color: 'var(--t1)' }}>Method 2 — TradingView:</strong><br />1. Create paper portfolio on TradingView with trade history<br />2. Share → Publish Chart → Embed code → paste into Notion /embed<br /><br /><strong style={{ color: 'var(--t1)' }}>Method 3 — Notion Native Charts:</strong><br />In any linked database view → switch to &quot;Chart&quot; view type → select Bar or Line for monthly P&amp;L visualization.</div>
          </div>

          <div className="card" style={{ marginTop: '14px' }}>
            <div className="card-title"><i className="fa-solid fa-books"></i> Recommended Reading — Trader&apos;s Library</div>
            <div className="g2" style={{ marginBottom: 0 }}>
              <div>
                <div className="rule-item"><span style={{ fontSize: '16px' }}>📗</span><div><div style={{ fontWeight: 600, fontSize: '12px' }}>Trading in the Zone</div><div style={{ fontSize: '11px', color: 'var(--t3)' }}>Mark Douglas · Psychology foundation</div></div></div>
                <div className="rule-item"><span style={{ fontSize: '16px' }}>📘</span><div><div style={{ fontWeight: 600, fontSize: '12px' }}>Market Wizards</div><div style={{ fontSize: '11px', color: 'var(--t3)' }}>Jack Schwager · Pro trader interviews</div></div></div>
                <div className="rule-item" style={{ border: 'none' }}><span style={{ fontSize: '16px' }}>📙</span><div><div style={{ fontWeight: 600, fontSize: '12px' }}>The Disciplined Trader</div><div style={{ fontSize: '11px', color: 'var(--t3)' }}>Mark Douglas · Mental discipline</div></div></div>
              </div>
              <div>
                <div className="rule-item"><span style={{ fontSize: '16px' }}>📕</span><div><div style={{ fontWeight: 600, fontSize: '12px' }}>Reminiscences of a Stock Operator</div><div style={{ fontSize: '11px', color: 'var(--t3)' }}>Edwin Lefèvre · Classic biography</div></div></div>
                <div className="rule-item"><span style={{ fontSize: '16px' }}>📗</span><div><div style={{ fontWeight: 600, fontSize: '12px' }}>How to Make Money in Stocks</div><div style={{ fontSize: '11px', color: 'var(--t3)' }}>William O&apos;Neil · CAN SLIM method</div></div></div>
                <div className="rule-item" style={{ border: 'none' }}><span style={{ fontSize: '16px' }}>📘</span><div><div style={{ fontWeight: 600, fontSize: '12px' }}>One Good Trade</div><div style={{ fontSize: '11px', color: 'var(--t3)' }}>Mike Bellafiore · Professional training</div></div></div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
