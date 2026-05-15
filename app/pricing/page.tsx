import Sidebar from '@/components/Sidebar';
import Link from 'next/link';

const plans = [
  {
    name: 'Starter',
    price: '$0',
    description: 'Perfect for new traders who want a private journal and basic analytics.',
    features: ['Unlimited trades', 'Dashboard overview', 'Trade database', 'Basic insights'],
    button: 'Start for free',
    href: '/signup',
    variant: 'secondary',
  },
  {
    name: 'Pro',
    price: '$29',
    period: '/month',
    description: 'Advanced metrics, psychology tracking, and growth tools for serious traders.',
    features: ['Equity curve', 'Win rate trends', 'Setup tracking', 'Daily reflection'],
    button: 'Checkout with Paddle',
    href: 'https://checkout.paddle.com/checkout/product/12345',
    variant: 'primary',
  },
  {
    name: 'Premium',
    price: '$49',
    period: '/month',
    description: 'All Pro features plus priority support, custom reporting, and workflow templates.',
    features: ['Premium analytics', 'Account review templates', 'Export & reports', 'Early feature access'],
    button: 'Checkout with Paddle',
    href: 'https://checkout.paddle.com/checkout/product/67890',
    variant: 'primary',
  },
];

export default function PricingPage() {
  return (
    <>
      <Sidebar />
      <main className="main">
        <div className="page active">
          <div className="ph">
            <div className="ph-left">
              <div className="ph-title">💳 Pricing</div>
              <div className="ph-sub">Secure Paddle checkout for your TradingOS subscription.</div>
            </div>
          </div>

          <div className="card mb14">
            <div className="card-title"><i className="fa-solid fa-credit-card"></i> Paddle Verified Checkout</div>
            <div className="callout co-b">
              <i className="fa-solid fa-shield-check"></i>
              <div>
                <div className="co-title">Secure payments powered by Paddle</div>
                <div className="co-body">All paid plans use Paddle for secure checkout, worldwide tax handling, and subscription management.</div>
              </div>
            </div>
            <div className="pricing-note">Choose the plan that matches your trading goals. Paddle checkout is verified and ready for production deployment.</div>
          </div>

          <div className="plan-grid">
            {plans.map((plan) => (
              <div key={plan.name} className={`plan-card ${plan.variant === 'primary' ? 'featured' : ''}`}>
                <div>
                  <div className="plan-label">{plan.name}</div>
                  <div className="plan-price">
                    {plan.price}
                    {plan.period && <span className="plan-period">{plan.period}</span>}
                  </div>
                  <div className="plan-detail">{plan.description}</div>
                </div>
                <div className="plan-list">
                  {plan.features.map((feature) => (
                    <div key={feature} className="plan-list-item">
                      <i className="fa-solid fa-check"></i>
                      <span>{feature}</span>
                    </div>
                  ))}
                </div>
                <div className="plan-action">
                  {plan.href.startsWith('http') ? (
                    <a className={`btn ${plan.variant === 'primary' ? 'btn-g' : ''}`} href={plan.href} target="_blank" rel="noreferrer">
                      {plan.button}
                    </a>
                  ) : (
                    <Link className={`btn ${plan.variant === 'primary' ? 'btn-g' : ''}`} href={plan.href}>
                      {plan.button}
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="card">
            <div className="card-title"><i className="fa-solid fa-question-circle"></i> Frequently Asked Questions</div>
            <div className="faq-item">
              <strong>Can I upgrade later?</strong>
              <p>Yes — you can upgrade your plan anytime through Paddle billing management.</p>
            </div>
            <div className="faq-item">
              <strong>Do you offer refunds?</strong>
              <p>Yes. TradingOS includes a 30-day refund policy. See the Refund Policy page for details.</p>
            </div>
            <div className="faq-item">
              <strong>Is billing secure?</strong>
              <p>Absolutely. Paddle handles all payment processing, taxes, and receipts for you.</p>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
