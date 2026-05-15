import Sidebar from '@/components/Sidebar';

export default function RefundPolicyPage() {
  return (
    <>
      <Sidebar />
      <main className="main">
        <div className="page active">
          <div className="ph">
            <div className="ph-left">
              <div className="ph-title">💰 Refund Policy</div>
              <div className="ph-sub">Our 30-day refund guarantee for TradingOS subscriptions.</div>
            </div>
          </div>

          <div className="card mb14">
            <div className="card-title"><i className="fa-solid fa-hand-holding-dollar"></i> 30-Day Refund Guarantee</div>
            <p>We want you to feel confident in your purchase. If you are not satisfied within 30 days, you can request a refund through Paddle.</p>
          </div>

          <div className="section">
            <h2>Eligibility</h2>
            <p>Refunds are available for subscriptions purchased through Paddle within 30 days of the original transaction date.</p>
          </div>

          <div className="section">
            <h2>How to Request a Refund</h2>
            <p>Contact support through the email address provided in your Paddle receipt or use the Paddle customer portal. Include your transaction details and reason for requesting a refund.</p>
          </div>

          <div className="section">
            <h2>Non-Refundable Items</h2>
            <p>Refunds do not apply to account misuse, shared accounts, or requests made after the 30-day window. Additional terms may apply based on Paddle policy.</p>
          </div>

          <div className="section">
            <h2>Processing Time</h2>
            <p>Refunds are processed by Paddle and may take up to 10 business days to appear on your original payment method.</p>
          </div>

          <div className="section">
            <h2>Questions?</h2>
            <p>If you need help, contact support via the email on your Paddle receipt or visit the Paddle help center.</p>
          </div>
        </div>
      </main>
    </>
  );
}
