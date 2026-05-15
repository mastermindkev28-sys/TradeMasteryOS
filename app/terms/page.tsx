import Sidebar from '@/components/Sidebar';

export default function TermsPage() {
  return (
    <>
      <Sidebar />
      <main className="main">
        <div className="page active">
          <div className="ph">
            <div className="ph-left">
              <div className="ph-title">📝 Terms & Conditions</div>
              <div className="ph-sub">The rules, responsibilities, and terms for using TradingOS.</div>
            </div>
          </div>

          <div className="card mb14">
            <div className="card-title"><i className="fa-solid fa-balance-scale"></i> TradingOS Terms</div>
            <p>By using TradingOS, you agree to these terms and conditions. These terms govern your access to the application, the purchase of subscriptions, and your relationship with the service.</p>
          </div>

          <div className="section">
            <h2>1. Acceptance of Terms</h2>
            <p>By registering for an account, purchasing a subscription, or using the product, you accept these Terms & Conditions.</p>
          </div>

          <div className="section">
            <h2>2. User Accounts</h2>
            <p>Users must provide accurate account information and are responsible for maintaining the confidentiality of their login credentials. You are responsible for all activity on your account.</p>
          </div>

          <div className="section">
            <h2>3. Subscriptions & Billing</h2>
            <p>Paid plans are billed through Paddle. All billing, invoicing, and payment processing is managed by Paddle, and your subscription will continue until canceled.</p>
          </div>

          <div className="section">
            <h2>4. Content and Data</h2>
            <p>You retain ownership of your trade data. TradingOS stores your journal and analytics data securely using Supabase. We do not claim ownership of your trades, notes, or journals.</p>
          </div>

          <div className="section">
            <h2>5. Refunds</h2>
            <p>Refunds are handled according to our Refund Policy. In most cases, requests within 30 days of purchase are eligible for a refund.</p>
          </div>

          <div className="section">
            <h2>6. Disclaimer</h2>
            <p>TradingOS is a tool for recording and reviewing trading activity. It does not provide financial advice, recommendations, or guaranteed results.</p>
          </div>

          <div className="section">
            <h2>7. Changes to Terms</h2>
            <p>We may update these Terms at any time. Continued use of the service after changes constitutes acceptance of the new terms.</p>
          </div>
        </div>
      </main>
    </>
  );
}
