import { Link } from "react-router-dom";
import StripeCta from "./StripeCta";

export default function Pricing() {
  return (
    <section className="section" id="pricing">
      <div className="container">
        <div className="lp-pricing-header">
          <div className="section-label reveal">Pricing</div>
          <h2 className="section-title reveal">
            One platform. Every tool your business needs.
          </h2>
          <p className="section-subtitle reveal">
            CRM, marketing, SEO, social media, and AI automation - all included.
            Hands-on setup and ongoing support with every plan.
          </p>
        </div>
        <div className="lp-pricing-grid">
          <div className="lp-pricing-card start-here reveal">
            <div className="lp-pricing-plan-name">Free</div>
            <div className="lp-pricing-tagline">
              See what AI can do for your business
            </div>
            <div className="lp-pricing-amount">
              <span className="lp-pricing-dollar">$0</span>
              <span className="lp-pricing-period">/month</span>
            </div>
            <div className="lp-pricing-setup">No credit card required</div>
            <div className="lp-pricing-divider"></div>
            <ul className="lp-pricing-features">
              <li>AI chat widget</li>
              <li>Customer capture</li>
              <li>Unlimited conversations</li>
              <li>Free forever</li>
              <li>Basic dashboard</li>
              <li>Email notifications</li>
              <li>Widget customization</li>
              <li>FAQ knowledge base</li>
              <li>Basic hosted business page</li>
              <li>Dashboard analytics</li>
              <li>Community support</li>
            </ul>
            <Link to="/signup" className="pricing-cta">
              Get Started {"→"}
            </Link>
          </div>

          <div className="lp-pricing-card reveal">
            <div className="lp-pricing-plan-name">Growth</div>
            <div className="lp-pricing-tagline">Your AI front desk</div>
            <div className="lp-pricing-amount">
              <span className="lp-pricing-dollar">$99</span>
              <span className="lp-pricing-period">/month</span>
            </div>
            <div className="lp-pricing-setup">
              <span className="lp-pricing-waived-badge pulse-glow">
                7-day free trial included
              </span>
            </div>
            <div className="lp-pricing-divider"></div>
            <ul className="lp-pricing-features">
              <li>AI chat widget</li>
              <li>Email &amp; form lead capture</li>
              <li>Auto follow-up email &amp; SMS</li>
              <li>Customer management</li>
              <li>Appointment booking</li>
              <li>2 automation sequences</li>
              <li>Up to 500 conversations/month</li>
              <li>Basic SEO audit &amp; recommendations</li>
              <li>AI content writer</li>
              <li>Hosted business page</li>
              <li>Basic analytics &amp; reporting</li>
              <li>Email support</li>
            </ul>
            <StripeCta plan="growth">Get Started {"→"}</StripeCta>
          </div>

          <div className="lp-pricing-card popular reveal">
            <div className="lp-pricing-plan-name">Professional</div>
            <div className="lp-pricing-tagline">Automate your follow-ups</div>
            <div className="lp-pricing-amount">
              <span className="lp-pricing-dollar">$150</span>
              <span className="lp-pricing-period">/month</span>
            </div>
            <div className="lp-pricing-setup">No setup fee. Cancel anytime</div>
            <div className="lp-pricing-divider"></div>
            <div className="lp-pricing-includes">
              Everything in Growth, plus:
            </div>
            <ul className="lp-pricing-features">
              <li>Up to 6 automation sequences</li>
              <li>Lead nurturing sequences</li>
              <li>Pipeline automation</li>
              <li>AI-powered email responses</li>
              <li>Review request automation</li>
              <li>Full SEO audit suite &amp; keyword tracking</li>
              <li>Social media content &amp; scheduling</li>
              <li>Email &amp; SMS marketing campaigns</li>
              <li>AI marketing content generator</li>
              <li>Custom business page styling</li>
              <li>Advanced analytics &amp; insights</li>
              <li>Priority email &amp; chat support</li>
            </ul>
            <StripeCta plan="professional">Get Started {"→"}</StripeCta>
          </div>

          <div className="lp-pricing-card reveal">
            <div className="lp-pricing-plan-name">Enterprise</div>
            <div className="lp-pricing-tagline">Your full AI employee</div>
            <div className="lp-pricing-amount">
              <span className="lp-pricing-dollar">$250</span>
              <span className="lp-pricing-period">/month</span>
            </div>
            <div className="lp-pricing-setup">No setup fee. Cancel anytime</div>
            <div className="lp-pricing-divider"></div>
            <div className="lp-pricing-includes">
              Everything in Professional, plus:
            </div>
            <ul className="lp-pricing-features">
              <li>Unlimited automation sequences</li>
              <li>AI appointment booking agent</li>
              <li>Team accounts &amp; roles</li>
              <li>AI visibility tracking (GEO score)</li>
              <li>Priority onboarding &amp; migration support</li>
              <li>Unlimited social media campaigns</li>
              <li>Webhook integrations</li>
              <li>White-label branding &amp; custom CSS</li>
              <li>White-glove business page design</li>
              <li>Full analytics suite</li>
              <li>Dedicated account manager</li>
            </ul>
            <StripeCta plan="enterprise">Get Started {"→"}</StripeCta>
          </div>
        </div>
        <p className="lp-pricing-footer-note reveal">
          No setup fees. No contracts. All paid plans include hands-on
          onboarding and ongoing optimization. Cancel anytime.
        </p>
      </div>
    </section>
  );
}
