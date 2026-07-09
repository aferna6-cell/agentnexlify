/**
 * VerticalLanding.jsx
 * Data-driven SEO landing page for /ai-front-desk/[vertical] routes.
 *
 * Uses the existing VerticalPage component for consistent dark theme,
 * Helmet SEO tags, and layout patterns.
 *
 * Routes:
 *   /ai-front-desk/salons    -> salons vertical
 *   /ai-front-desk/plumbers  -> plumbers vertical
 *   /ai-front-desk/dentists  -> dentists vertical
 */
import { useParams, Navigate } from "react-router-dom";
import VerticalPage from "../../components/VerticalPage";
import { VERTICAL_DATA } from "./verticals";

const pricingStyles = `
/* VerticalLanding pricing section */

.vl-pricing {
  padding: 4rem 0;
  border-top: 1px solid var(--border);
}

.vl-pricing__heading {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary);
  text-align: center;
  margin-bottom: 2.5rem;
}

.vl-pricing__grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.25rem;
  max-width: 820px;
  margin: 0 auto;
}

@media (min-width: 700px) {
  .vl-pricing__grid {
    grid-template-columns: 1fr 1fr;
  }
}

.vl-plan {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  position: relative;
}

.vl-plan--featured {
  border-color: var(--accent);
}

.vl-plan__badge {
  position: absolute;
  top: -0.75rem;
  left: 50%;
  transform: translateX(-50%);
  background: var(--accent);
  color: var(--bg-primary);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  padding: 0.2rem 0.75rem;
  border-radius: 999px;
  white-space: nowrap;
}

.vl-plan__name {
  font-size: 1.0625rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-top: 0.5rem;
}

.vl-plan__price {
  font-size: 2rem;
  font-weight: 700;
  color: var(--accent);
  line-height: 1;
}

.vl-plan__price span {
  font-size: 1rem;
  color: var(--text-secondary);
  font-weight: 400;
}

.vl-plan__desc {
  font-size: 0.9375rem;
  color: var(--text-secondary);
  line-height: 1.6;
}

.vl-plan__list {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.vl-plan__list li {
  font-size: 0.9375rem;
  color: var(--text-secondary);
  padding-left: 1.25rem;
  position: relative;
}

.vl-plan__list li::before {
  content: "+";
  position: absolute;
  left: 0;
  color: var(--accent);
  font-weight: 700;
}

.vl-btn {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  border-radius: var(--radius);
  font-size: 0.9375rem;
  font-weight: 600;
  text-decoration: none;
  text-align: center;
  cursor: pointer;
  transition: background 0.2s, box-shadow 0.2s;
  margin-top: auto;
}

.vl-btn--primary {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border);
}

.vl-btn--primary:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.vl-btn--accent {
  background: var(--accent);
  color: var(--bg-primary);
  border: 1px solid var(--accent);
}

.vl-btn--accent:hover {
  box-shadow: 0 0 18px var(--accent-glow);
}

.vl-pricing__note {
  text-align: center;
  font-size: 0.875rem;
  color: var(--text-muted);
  margin-top: 1.5rem;
}

/* Related verticals cross-links */

.vl-related {
  padding: 3rem 0;
  border-top: 1px solid var(--border);
}

.vl-related__heading {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--text-primary);
  text-align: center;
  margin-bottom: 1.25rem;
}

.vl-related__links {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.75rem;
}

.vl-related__link {
  display: inline-block;
  padding: 0.5rem 1rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 0.875rem;
  font-weight: 600;
  text-decoration: none;
  transition: border-color 0.2s, color 0.2s;
}

.vl-related__link:hover {
  border-color: var(--accent);
  color: var(--accent);
}
`;

export default function VerticalLanding() {
  const { vertical } = useParams();
  const data = VERTICAL_DATA[vertical];

  if (!data) {
    return <Navigate to="/" replace />;
  }

  const isDental = vertical === "dentists";

  return (
    <>
      <style>{pricingStyles}</style>
      <VerticalPage
        meta={data.meta}
        hero={data.hero}
        features={data.features}
        stats={data.stats}
        faqs={data.faqs}
        slug={`ai-front-desk-${data.slug}`}
      >
        {isDental && (
          <div className="vp-disclaimer">
            Built with patient privacy in mind. Contact us to discuss your
            specific compliance requirements before deploying.
          </div>
        )}

        {/* Pricing section specific to the /ai-front-desk/* pages */}
        <section className="vl-pricing">
          <div className="vp-container">
            <h2 className="vl-pricing__heading">Simple pricing for every size business</h2>
            <div className="vl-pricing__grid">
              <div className="vl-plan">
                <div className="vl-plan__name">AI Front Desk</div>
                <div className="vl-plan__price">$19.99<span>/mo</span></div>
                <p className="vl-plan__desc">
                  The chat widget, lead capture, appointment requests, and FAQ
                  management. Everything you need to stop missing customers.
                </p>
                <ul className="vl-plan__list">
                  <li>AI chat widget on your website</li>
                  <li>Lead capture with instant notifications</li>
                  <li>Appointment requests through chat</li>
                  <li>FAQ knowledge base trained on your business</li>
                  <li>No setup fee. Cancel anytime.</li>
                </ul>
                <a href="/signup?plan=chatbot" className="vl-btn vl-btn--primary">
                  Get Started
                </a>
              </div>
              <div className="vl-plan vl-plan--featured">
                <div className="vl-plan__badge">Full Platform</div>
                <div className="vl-plan__name">AI Workforce</div>
                <div className="vl-plan__price">$99.99<span>/mo</span></div>
                <p className="vl-plan__desc">
                  Everything in AI Front Desk plus marketing automations, email
                  and SMS campaigns, SEO tools, and advanced analytics.
                </p>
                <ul className="vl-plan__list">
                  <li>Everything in AI Front Desk</li>
                  <li>Email and SMS campaigns</li>
                  <li>Automation rules</li>
                  <li>SEO audit suite</li>
                  <li>Social media scheduling</li>
                  <li>Advanced analytics</li>
                  <li>Priority support</li>
                </ul>
                <a href="/signup?plan=agent_os" className="vl-btn vl-btn--accent">
                  Get Started
                </a>
              </div>
            </div>
            <p className="vl-pricing__note">No setup fees. No contracts. Cancel anytime.</p>
          </div>
        </section>

        {/* Cross-links to sibling vertical pages. Optional field; renders nothing when absent. */}
        {Array.isArray(data.related) && data.related.length > 0 && (
          <section className="vl-related">
            <div className="vp-container">
              <h2 className="vl-related__heading">AI Front Desk for other industries</h2>
              <div className="vl-related__links">
                {data.related.map((r) => (
                  <a
                    key={r.slug}
                    href={`/ai-front-desk/${r.slug}`}
                    className="vl-related__link"
                  >
                    {r.label}
                  </a>
                ))}
              </div>
            </div>
          </section>
        )}
      </VerticalPage>
    </>
  );
}
