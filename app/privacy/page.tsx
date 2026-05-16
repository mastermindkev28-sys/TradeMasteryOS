import Sidebar from '@/components/Sidebar';

export default function PrivacyPage() {
  return (
    <>
      <Sidebar />
      <main className="main">
        <div className="page active">
          <div className="ph">
            <div className="ph-left">
              <div className="ph-title">🔒 Privacy Policy</div>
              <div className="ph-sub">How TradingOS collects, uses, and protects your data. Last updated: May 2025.</div>
            </div>
          </div>

          <div className="card mb14">
            <div className="card-title"><i className="fa-solid fa-shield-halved"></i> Introduction</div>
            <p>
              TradingOS (&quot;we&quot;, &quot;us&quot;, or &quot;our&quot;) operates a trading journal platform at TradingOS. This Privacy Policy describes how we collect,
              use, and safeguard your personal information when you use our service. By using TradingOS, you agree to the collection and
              use of information in accordance with this policy.
            </p>
          </div>

          <div className="card mb14">
            <div className="card-title"><i className="fa-solid fa-database"></i> Data We Collect</div>
            <p>We collect the following categories of information:</p>
            <ul style={{ paddingLeft: '1.25rem', marginTop: '0.75rem', lineHeight: '1.8' }}>
              <li><strong>Account information</strong> — your email address and password (stored securely via Supabase Auth).</li>
              <li><strong>Trade data</strong> — trade entries, notes, tags, and journal content that you manually enter into the platform.</li>
              <li><strong>Usage data</strong> — page views, feature interactions, and session information used to improve the product.</li>
              <li><strong>Payment information</strong> — payment processing is handled entirely by Paddle. We do not collect or store card numbers, bank details, or billing addresses.</li>
            </ul>
          </div>

          <div className="card mb14">
            <div className="card-title"><i className="fa-solid fa-gear"></i> How We Use Your Data</div>
            <p>We use the data we collect to:</p>
            <ul style={{ paddingLeft: '1.25rem', marginTop: '0.75rem', lineHeight: '1.8' }}>
              <li>Provide and maintain the TradingOS service and your account.</li>
              <li>Process payments and manage your subscription via Paddle.</li>
              <li>Improve and develop new features based on usage patterns.</li>
              <li>Send transactional emails such as account confirmations and billing receipts.</li>
              <li>Respond to support requests or enquiries you submit.</li>
            </ul>
            <p style={{ marginTop: '0.75rem' }}>We do not sell your personal data to third parties and do not use it for advertising purposes.</p>
          </div>

          <div className="card mb14">
            <div className="card-title"><i className="fa-solid fa-credit-card"></i> Payment Processing</div>
            <div className="callout co-b">
              <i className="fa-solid fa-shield-check"></i>
              <div>
                <div className="co-title">Paddle is our Merchant of Record</div>
                <div className="co-body">
                  All payments are processed by Paddle.com Market Limited (&quot;Paddle&quot;), who acts as the Merchant of Record for all transactions.
                  Paddle collects and processes your payment data directly. We never see, transmit, or store card numbers or full billing details.
                  Paddle&apos;s own privacy policy governs the handling of your payment information and can be found at{' '}
                  <a href="https://www.paddle.com/legal/privacy" target="_blank" rel="noreferrer">paddle.com/legal/privacy</a>.
                </div>
              </div>
            </div>
          </div>

          <div className="card mb14">
            <div className="card-title"><i className="fa-solid fa-server"></i> Data Storage &amp; Security</div>
            <p>
              Your data is stored in Supabase, a managed database and authentication platform with infrastructure hosted in the EU and US regions.
              All data is encrypted at rest using AES-256 and in transit using TLS 1.2 or higher. We apply Row Level Security (RLS) policies
              so that users can only access their own data. While no system is 100% secure, we take commercially reasonable steps to protect
              your personal information.
            </p>
          </div>

          <div className="card mb14">
            <div className="card-title"><i className="fa-solid fa-user-shield"></i> Your Rights</div>
            <p>Depending on your location, you may have the following rights regarding your personal data:</p>
            <ul style={{ paddingLeft: '1.25rem', marginTop: '0.75rem', lineHeight: '1.8' }}>
              <li><strong>Access</strong> — request a copy of the personal data we hold about you.</li>
              <li><strong>Rectification</strong> — request correction of inaccurate or incomplete data.</li>
              <li><strong>Deletion</strong> — request that we delete your account and associated data.</li>
              <li><strong>Portability</strong> — request an export of your trade data in a portable format.</li>
            </ul>
            <p style={{ marginTop: '0.75rem' }}>
              To exercise any of these rights, please contact us at{' '}
              <a href="mailto:privacy@tradingos.com">privacy@tradingos.com</a>.
              We will respond within 30 days.
            </p>
          </div>

          <div className="card mb14">
            <div className="card-title"><i className="fa-solid fa-cookie-bite"></i> Cookies</div>
            <p>
              TradingOS uses session cookies provided by Supabase to maintain your authenticated session. These cookies are strictly necessary
              for the platform to function and do not track you across external websites. We do not use advertising cookies, tracking pixels,
              or third-party analytics cookies. You can disable cookies in your browser settings, but doing so will prevent you from logging in.
            </p>
          </div>

          <div className="card mb14">
            <div className="card-title"><i className="fa-solid fa-link"></i> Third-Party Services</div>
            <p>We use the following third-party services to operate TradingOS:</p>
            <ul style={{ paddingLeft: '1.25rem', marginTop: '0.75rem', lineHeight: '1.8' }}>
              <li>
                <strong>Supabase</strong> — database, authentication, and storage. Data is processed under Supabase&apos;s{' '}
                <a href="https://supabase.com/privacy" target="_blank" rel="noreferrer">Privacy Policy</a>.
              </li>
              <li>
                <strong>Paddle</strong> — payment processing and subscription management as Merchant of Record. Data is processed under{' '}
                <a href="https://www.paddle.com/legal/privacy" target="_blank" rel="noreferrer">Paddle&apos;s Privacy Policy</a>.
              </li>
            </ul>
          </div>

          <div className="card mb14">
            <div className="card-title"><i className="fa-solid fa-rotate"></i> Changes to This Policy</div>
            <p>
              We may update this Privacy Policy from time to time. When we do, we will revise the &quot;last updated&quot; date at the top of this page.
              Your continued use of TradingOS after any changes constitutes your acceptance of the revised policy. We encourage you to
              review this page periodically.
            </p>
          </div>

          <div className="card">
            <div className="card-title"><i className="fa-solid fa-envelope"></i> Contact</div>
            <p>
              If you have any questions, concerns, or requests regarding this Privacy Policy or how we handle your data, please contact us:
            </p>
            <p style={{ marginTop: '0.75rem' }}>
              <strong>Email:</strong>{' '}
              <a href="mailto:privacy@tradingos.com">privacy@tradingos.com</a>
            </p>
          </div>
        </div>
      </main>
    </>
  );
}
