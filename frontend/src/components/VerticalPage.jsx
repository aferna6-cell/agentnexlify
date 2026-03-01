import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";

const VERTICALS = [
  { slug: "restaurant-chatbot", label: "Restaurants" },
  { slug: "salon-booking-chatbot", label: "Salons" },
  { slug: "dental-chatbot", label: "Dental" },
  { slug: "auto-shop-chatbot", label: "Auto Shops" },
  { slug: "medical-office-chatbot", label: "Medical Offices" },
];

export default function VerticalPage({ meta, hero, features, stats, slug, children }) {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "LocalBusiness",
    name: meta.title,
    description: meta.description,
    url: meta.canonical,
  };

  const otherVerticals = VERTICALS.filter((v) => v.slug !== slug);

  return (
    <>
      <Helmet>
        <title>{meta.title}</title>
        <meta name="description" content={meta.description} />
        <link rel="canonical" href={meta.canonical} />
        <meta property="og:title" content={meta.title} />
        <meta property="og:description" content={meta.description} />
        <meta property="og:url" content={meta.canonical} />
        <meta property="og:type" content="website" />
        <script type="application/ld+json">{JSON.stringify(jsonLd)}</script>
      </Helmet>

      <style>{styles}</style>

      {/* Hero */}
      <section className="vp-hero">
        <div className="vp-container">
          <h1 className="vp-hero__h1">{hero.h1}</h1>
          <p className="vp-hero__subhead">{hero.subhead}</p>
          <p className="vp-hero__pain">{hero.painPoint}</p>
          <div className="vp-hero__cta">
            <Link to="/signup" className="vp-btn vp-btn--primary">
              Start Free
            </Link>
            <a href="/demo" className="vp-btn vp-btn--outline">
              Book a Demo
            </a>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="vp-features">
        <div className="vp-container">
          <div className="vp-features__grid">
            {features.map((f, i) => (
              <div key={i} className="vp-card">
                <span className="vp-card__icon">{f.icon}</span>
                <h3 className="vp-card__title">{f.title}</h3>
                <p className="vp-card__desc">{f.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Extra content (disclaimers, etc.) */}
      {children}

      {/* Stats */}
      <section className="vp-stats">
        <div className="vp-container">
          <div className="vp-stats__row">
            {stats.map((s, i) => (
              <div key={i} className="vp-stat">
                <span className="vp-stat__number">{s.number}</span>
                <span className="vp-stat__label">{s.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Internal Links */}
      <nav className="vp-links">
        <div className="vp-container">
          <p className="vp-links__heading">Also explore:</p>
          <div className="vp-links__list">
            {otherVerticals.map((v) => (
              <Link key={v.slug} to={`/${v.slug}`} className="vp-links__link">
                {v.label}
              </Link>
            ))}
            <Link to="/free-widget" className="vp-links__link">
              Free Chatbot
            </Link>
            <a href="/#pricing" className="vp-links__link">
              Pricing
            </a>
          </div>
        </div>
      </nav>
    </>
  );
}

const styles = `
/* ── VerticalPage ── */

.vp-container {
  max-width: 1120px;
  margin: 0 auto;
  padding: 0 1rem;
}

/* Hero */

.vp-hero {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
  padding: 4rem 0 3.5rem;
  text-align: center;
}

.vp-hero__h1 {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
  margin-bottom: 1rem;
}

.vp-hero__subhead {
  font-size: 1.125rem;
  color: var(--text-secondary);
  max-width: 600px;
  margin: 0 auto 1rem;
}

.vp-hero__pain {
  color: var(--accent);
  font-weight: 600;
  font-size: 1rem;
  margin-bottom: 2rem;
}

.vp-hero__cta {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
  flex-wrap: wrap;
}

.vp-btn {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  border-radius: var(--radius);
  font-family: var(--font);
  font-size: 0.9375rem;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  transition: background 0.2s, box-shadow 0.2s;
}

.vp-btn--primary {
  background: var(--accent);
  color: var(--bg-primary);
}

.vp-btn--primary:hover {
  box-shadow: 0 0 20px var(--accent-glow);
}

.vp-btn--outline {
  background: transparent;
  color: var(--accent);
  border: 1px solid var(--accent);
}

.vp-btn--outline:hover {
  background: var(--accent-dim);
}

/* Features */

.vp-features {
  padding: 4rem 0;
}

.vp-features__grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.25rem;
}

.vp-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.75rem;
  transition: border-color 0.2s;
}

.vp-card:hover {
  border-color: var(--border-hover);
}

.vp-card__icon {
  font-size: 1.75rem;
  display: block;
  margin-bottom: 0.75rem;
}

.vp-card__title {
  font-size: 1.0625rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.vp-card__desc {
  font-size: 0.9375rem;
  color: var(--text-secondary);
  line-height: 1.6;
}

/* Stats */

.vp-stats {
  background: var(--bg-secondary);
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  padding: 3rem 0;
}

.vp-stats__row {
  display: flex;
  justify-content: center;
  gap: 3rem;
  flex-wrap: wrap;
}

.vp-stat {
  text-align: center;
}

.vp-stat__number {
  display: block;
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--accent);
  line-height: 1.1;
}

.vp-stat__label {
  display: block;
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-top: 0.25rem;
}

/* Internal Links */

.vp-links {
  padding: 3rem 0;
  text-align: center;
}

.vp-links__heading {
  font-size: 0.875rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 1rem;
}

.vp-links__list {
  display: flex;
  justify-content: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.vp-links__link {
  color: var(--accent);
  text-decoration: none;
  font-size: 0.875rem;
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  transition: background 0.2s, border-color 0.2s;
}

.vp-links__link:hover {
  background: var(--accent-dim);
  border-color: var(--accent);
}

/* Disclaimer */

.vp-disclaimer {
  max-width: 1120px;
  margin: 0 auto;
  padding: 1rem 1.25rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 0.875rem;
  color: var(--text-secondary);
  line-height: 1.6;
}

/* Responsive: tablet+ */

@media (min-width: 768px) {
  .vp-hero {
    padding: 5rem 0 4.5rem;
  }

  .vp-hero__h1 {
    font-size: 2.75rem;
  }

  .vp-hero__subhead {
    font-size: 1.25rem;
  }

  .vp-features__grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .vp-stat__number {
    font-size: 3rem;
  }

  .vp-stats__row {
    gap: 5rem;
  }
}

@media (min-width: 1024px) {
  .vp-hero__h1 {
    font-size: 3.25rem;
  }

  .vp-hero {
    padding: 6rem 0 5rem;
  }
}
`;
