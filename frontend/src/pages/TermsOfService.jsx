import { Link } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import "../styles/legal.css";

export default function TermsOfService() {
  return (
    <div className="legal-page">
      <Helmet>
        <title>Terms of Service | AgentNexLiFy</title>
        <meta
          name="description"
          content="AgentNexLiFy Terms of Service - the rules and guidelines for using our AI chat widget platform."
        />
      </Helmet>

      <nav className="legal-nav">
        <Link to="/" className="legal-back">
          &larr; Back to Home
        </Link>
        <Link to="/privacy" className="legal-sibling">
          Privacy Policy
        </Link>
        <Link to="/contact" className="legal-sibling">
          Contact
        </Link>
      </nav>

      <article className="legal-content">
        <h1>Terms of Service</h1>
        <p className="legal-updated">Last updated: March 2026</p>

        <p className="legal-disclaimer">
          <strong>Note:</strong> This document is a starting point. We recommend
          consulting with a qualified attorney before relying on it for legal
          compliance.
        </p>

        <section>
          <h2>1. What AgentNexLiFy Is</h2>
          <p>
            AgentNexLiFy, operated by Pinpoint Financial Group, LLC
            (&ldquo;we,&rdquo; &ldquo;us,&rdquo; &ldquo;our&rdquo;), is a
            software-as-a-service (SaaS) platform that provides AI-powered chat
            widgets for business websites. Our widget lets your website visitors
            ask questions, get instant AI-generated answers, and submit their
            contact information &mdash; all without you lifting a finger.
          </p>
          <p>
            By creating an account or using any part of our service, you
            (&ldquo;you,&rdquo; &ldquo;your&rdquo;) agree to these Terms of
            Service. If you don&rsquo;t agree, please don&rsquo;t use
            AgentNexLiFy.
          </p>
        </section>

        <section>
          <h2>2. Account Registration</h2>
          <ul>
            <li>
              You must provide accurate business and contact information when
              signing up.
            </li>
            <li>
              You are responsible for keeping your login credentials secure.
            </li>
            <li>
              One account per business. Don&rsquo;t share accounts or create
              multiple accounts to circumvent plan limits.
            </li>
            <li>You must be at least 18 years old to create an account.</li>
            <li>
              You&rsquo;re responsible for all activity that happens under your
              account.
            </li>
          </ul>
        </section>

        <section>
          <h2>3. Acceptable Use</h2>
          <p>You agree not to use AgentNexLiFy to:</p>
          <ul>
            <li>
              Send spam, unsolicited messages, or misleading content through the
              chat widget.
            </li>
            <li>
              Collect personal data from visitors without proper notice or
              consent on your website.
            </li>
            <li>
              Engage in any illegal activity, including fraud, harassment, or
              discrimination.
            </li>
            <li>
              Attempt to reverse-engineer, hack, or interfere with our platform
              or infrastructure.
            </li>
            <li>
              Use the AI to generate content that is harmful, abusive, or
              violates any law.
            </li>
            <li>
              Resell or redistribute access to our service without written
              permission.
            </li>
          </ul>
          <p>
            We reserve the right to suspend or terminate accounts that violate
            these guidelines, with or without notice.
          </p>
        </section>

        <section>
          <h2>4. Payment Terms</h2>
          <ul>
            <li>
              <strong>Free plan:</strong> Available at no cost with usage
              limits. No credit card required.
            </li>
            <li>
              <strong>Paid plans:</strong> Billed monthly via Stripe. Your
              subscription auto-renews each billing cycle unless you cancel.
            </li>
            <li>
              <strong>Cancellation:</strong> You can cancel anytime from your
              dashboard. Your access continues through the end of the current
              billing period. No refunds for partial months.
            </li>
            <li>
              <strong>Price changes:</strong> We&rsquo;ll notify you at least 30
              days before any price increase. Continued use after the change
              constitutes acceptance.
            </li>
            <li>
              <strong>Failed payments:</strong> If a payment fails, we may
              downgrade your account to the free plan after a 7-day grace
              period.
            </li>
          </ul>
        </section>

        <section>
          <h2>5. Intellectual Property</h2>
          <p>
            <strong>We own the platform.</strong> All code, design, branding,
            and technology behind AgentNexLiFy is our intellectual property (or
            licensed to us). You don&rsquo;t gain any ownership rights by using
            the service.
          </p>
          <p>
            <strong>You own your data.</strong> Your business information, FAQ
            content, lead data, and conversation history belong to you. We
            don&rsquo;t claim ownership over your content.
          </p>
          <p>
            <strong>Limited license.</strong> You grant us a limited license to
            process your data solely to provide the service (e.g., sending your
            FAQ content to the AI to generate responses).
          </p>
        </section>

        <section>
          <h2>6. How We Use Data for AI Responses</h2>
          <p>
            When a visitor sends a message through your widget, we send the
            conversation (along with your business context and FAQ data) to
            Anthropic&rsquo;s Claude API to generate a response. This is the
            core of how the service works.
          </p>
          <p>
            We do not use your conversations to train AI models. However,
            Anthropic may process data according to their own terms of service.
            See our <Link to="/privacy">Privacy Policy</Link> for more details
            on third-party data handling.
          </p>
        </section>

        <section>
          <h2>7. Third-Party Services</h2>
          <p>AgentNexLiFy relies on the following third-party providers:</p>
          <ul>
            <li>
              <strong>Anthropic (Claude API)</strong> - Powers AI-generated chat
              responses.
            </li>
            <li>
              <strong>Stripe</strong> - Processes payments and manages
              subscriptions.
            </li>
            <li>
              <strong>Supabase</strong> - Stores your account data,
              conversations, and leads.
            </li>
          </ul>
          <p>
            Each of these services has its own terms and privacy policies. We
            are not responsible for their practices, but we select providers
            with strong security and privacy standards.
          </p>
        </section>

        <section>
          <h2>8. Service Availability</h2>
          <p>
            We strive for high uptime but don&rsquo;t guarantee 100%
            availability. The service may be temporarily unavailable for
            maintenance, updates, or circumstances beyond our control.
            We&rsquo;ll do our best to notify you of planned downtime.
          </p>
        </section>

        <section>
          <h2>9. Limitation of Liability</h2>
          <p>To the maximum extent permitted by law:</p>
          <ul>
            <li>
              AgentNexLiFy is provided &ldquo;as is&rdquo; without warranties of
              any kind.
            </li>
            <li>
              We are not liable for any indirect, incidental, special, or
              consequential damages, including lost revenue, lost leads, or
              business interruption.
            </li>
            <li>
              Our total liability is limited to the amount you paid us in the 12
              months before the claim.
            </li>
            <li>
              AI-generated responses may contain errors. You&rsquo;re
              responsible for reviewing and ensuring the accuracy of information
              provided to your visitors.
            </li>
          </ul>
        </section>

        <section>
          <h2>10. Termination</h2>
          <ul>
            <li>
              <strong>By you:</strong> Cancel anytime from your dashboard or by
              emailing us.
            </li>
            <li>
              <strong>By us:</strong> We may suspend or terminate your account
              for violations of these terms, non-payment, or at our discretion
              with 30 days&rsquo; notice.
            </li>
            <li>
              <strong>After termination:</strong> We&rsquo;ll retain your data
              for 30 days so you can export it. After that, we may delete it
              permanently.
            </li>
          </ul>
        </section>

        <section>
          <h2>11. Changes to These Terms</h2>
          <p>
            We may update these terms from time to time. If we make material
            changes, we&rsquo;ll notify you via email or a notice in the
            dashboard. Your continued use after changes take effect means you
            accept the updated terms.
          </p>
        </section>

        <section>
          <h2>12. Governing Law</h2>
          <p>
            These terms are governed by the laws of the State of South Carolina,
            United States. Any disputes will be resolved in the state or federal
            courts located in South Carolina.
          </p>
        </section>

        <section>
          <h2>13. Contact Us</h2>
          <p>Questions about these terms? Reach out:</p>
          <ul className="legal-contact">
            <li>
              <strong>Email:</strong>{" "}
              <a href="mailto:help@agentnexlify.com">help@agentnexlify.com</a>
            </li>
            <li>
              <strong>Website:</strong>{" "}
              <a href="https://agentnexlify.com">agentnexlify.com</a>
            </li>
          </ul>
        </section>
      </article>
    </div>
  );
}
