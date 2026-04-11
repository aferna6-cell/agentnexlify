import { Link } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import "../styles/legal.css";

export default function PrivacyPolicy() {
  return (
    <div className="legal-page">
      <Helmet>
        <title>Privacy Policy | AgentNexLiFy</title>
        <meta
          name="description"
          content="AgentNexLiFy Privacy Policy - how we collect, use, and protect your data."
        />
      </Helmet>

      <nav className="legal-nav">
        <Link to="/" className="legal-back">
          &larr; Back to Home
        </Link>
        <Link to="/terms" className="legal-sibling">
          Terms of Service
        </Link>
        <Link to="/contact" className="legal-sibling">
          Contact
        </Link>
      </nav>

      <article className="legal-content">
        <h1>Privacy Policy</h1>
        <p className="legal-updated">Last updated: March 2026</p>

        <p className="legal-disclaimer">
          <strong>Note:</strong> This document is a starting point. We recommend
          consulting with a qualified attorney before relying on it for legal
          compliance.
        </p>

        <section>
          <h2>1. Overview</h2>
          <p>
            AgentNexLiFy, operated by Pinpoint Financial Group, LLC
            (&ldquo;we,&rdquo; &ldquo;us,&rdquo; &ldquo;our&rdquo;), provides an
            AI-powered chat widget platform for businesses. This Privacy Policy
            explains what data we collect, how we use it, and your rights
            regarding that data.
          </p>
          <p>This policy applies to two groups of people:</p>
          <ul>
            <li>
              <strong>Business owners</strong> who sign up for an AgentNexLiFy
              account and embed our widget on their websites.
            </li>
            <li>
              <strong>Website visitors</strong> who interact with an
              AgentNexLiFy-powered chat widget on a business&rsquo;s website.
            </li>
          </ul>
        </section>

        <section>
          <h2>2. What Data We Collect</h2>

          <h3>From Business Owners (Account Holders)</h3>
          <ul>
            <li>
              <strong>Account information:</strong> Name, email address,
              business name, industry, and city.
            </li>
            <li>
              <strong>Authentication data:</strong> Hashed password (we never
              store plaintext passwords).
            </li>
            <li>
              <strong>Payment information:</strong> Processed and stored by
              Stripe. We do not store your credit card number on our servers.
            </li>
            <li>
              <strong>Widget configuration:</strong> Bot name, colors, greeting
              messages, FAQ entries, and allowed domains.
            </li>
          </ul>

          <h3>From Website Visitors (Chat Users)</h3>
          <ul>
            <li>
              <strong>Conversation data:</strong> Messages sent and received
              through the chat widget.
            </li>
            <li>
              <strong>Contact information:</strong> Name, email, and phone
              number - only if voluntarily provided during the chat
              conversation.
            </li>
            <li>
              <strong>Session data:</strong> A randomly generated session ID
              stored in the visitor&rsquo;s browser (localStorage). This is not
              a tracking cookie.
            </li>
          </ul>

          <h3>Automatically Collected</h3>
          <ul>
            <li>
              <strong>Server logs:</strong> IP address, request timestamps, and
              browser user-agent for security and debugging purposes.
            </li>
            <li>
              We do <strong>not</strong> use analytics trackers, advertising
              pixels, or fingerprinting.
            </li>
          </ul>
        </section>

        <section>
          <h2>3. How We Use Your Data</h2>
          <ul>
            <li>
              <strong>Provide the service:</strong> Generate AI responses,
              manage conversations, capture and store leads.
            </li>
            <li>
              <strong>Process payments:</strong> Manage subscriptions and
              billing through Stripe.
            </li>
            <li>
              <strong>Improve the platform:</strong> Analyze aggregate usage
              patterns (e.g., average conversations per account) to improve our
              product. We do not sell your data or use individual conversations
              for marketing.
            </li>
            <li>
              <strong>Communicate with you:</strong> Send account-related emails
              (billing receipts, service updates, security alerts). We
              don&rsquo;t send marketing emails unless you opt in.
            </li>
            <li>
              <strong>Enforce our terms:</strong> Detect and prevent abuse,
              fraud, or violations of our Terms of Service.
            </li>
          </ul>
        </section>

        <section>
          <h2>4. Third-Party Data Sharing</h2>
          <p>
            We share data with the following third parties, solely to provide
            the service:
          </p>

          <table className="legal-table">
            <thead>
              <tr>
                <th>Provider</th>
                <th>What We Share</th>
                <th>Purpose</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <strong>Anthropic</strong> (Claude API)
                </td>
                <td>Conversation messages, business context, FAQ data</td>
                <td>Generate AI chat responses</td>
              </tr>
              <tr>
                <td>
                  <strong>Stripe</strong>
                </td>
                <td>Email, payment method</td>
                <td>Process payments and manage subscriptions</td>
              </tr>
              <tr>
                <td>
                  <strong>Supabase</strong>
                </td>
                <td>All account, conversation, and lead data</td>
                <td>Database storage and authentication</td>
              </tr>
            </tbody>
          </table>

          <p>
            We do <strong>not</strong> sell, rent, or trade your personal data
            to advertisers, data brokers, or any other third party.
          </p>
        </section>

        <section>
          <h2>5. AI Data Processing</h2>
          <p>
            When a visitor sends a message through the chat widget, we transmit
            the conversation to Anthropic&rsquo;s Claude API to generate a
            response. Specifically, we send:
          </p>
          <ul>
            <li>
              The visitor&rsquo;s message and prior conversation history for
              that session.
            </li>
            <li>
              Your business name, type, city, and FAQ entries (to give the AI
              context).
            </li>
          </ul>
          <p>
            We do not use your conversations to train our own AI models.
            Anthropic&rsquo;s handling of data sent through their API is
            governed by their own privacy policy and terms of service, which we
            encourage you to review.
          </p>
        </section>

        <section>
          <h2>6. Data Retention</h2>
          <ul>
            <li>
              <strong>Conversations:</strong> Stored as long as your account is
              active. You can delete individual conversations from your
              dashboard.
            </li>
            <li>
              <strong>Leads:</strong> Stored as long as your account is active.
              You can delete leads from your dashboard.
            </li>
            <li>
              <strong>Account data:</strong> Retained while your account exists.
              After account deletion, we retain data for up to 30 days for
              recovery purposes, then permanently delete it.
            </li>
            <li>
              <strong>Server logs:</strong> Retained for up to 90 days for
              security and debugging, then automatically purged.
            </li>
          </ul>
        </section>

        <section>
          <h2>7. Your Rights</h2>
          <p>Depending on your location, you may have the following rights:</p>
          <ul>
            <li>
              <strong>Access:</strong> Request a copy of all data we hold about
              you or your business.
            </li>
            <li>
              <strong>Deletion:</strong> Request that we delete your account and
              all associated data.
            </li>
            <li>
              <strong>Export:</strong> Request a machine-readable export of your
              leads and conversations.
            </li>
            <li>
              <strong>Correction:</strong> Request corrections to inaccurate
              personal information.
            </li>
            <li>
              <strong>Opt-out:</strong> Opt out of any non-essential
              communications at any time.
            </li>
          </ul>
          <p>
            To exercise any of these rights, email us at{" "}
            <a href="mailto:help@agentnexlify.com">help@agentnexlify.com</a>.
            We&rsquo;ll respond within 30 days.
          </p>
        </section>

        <section>
          <h2>8. Cookies &amp; Local Storage</h2>
          <p>We use minimal browser storage:</p>
          <ul>
            <li>
              <strong>JWT authentication token:</strong> Stored in localStorage
              to keep you logged into your dashboard. This is not a tracking
              cookie.
            </li>
            <li>
              <strong>Widget session ID:</strong> A random string stored in the
              visitor&rsquo;s localStorage to maintain the chat conversation
              within a session. Not linked to any personal identity.
            </li>
            <li>
              <strong>Widget state:</strong> Remembers whether the chat window
              is open or closed.
            </li>
          </ul>
          <p>
            We do <strong>not</strong> use third-party tracking cookies,
            advertising cookies, or analytics cookies.
          </p>
        </section>

        <section>
          <h2>9. Children&rsquo;s Privacy</h2>
          <p>
            AgentNexLiFy is not intended for use by anyone under 13 years of
            age. We do not knowingly collect personal information from children.
            If you believe a child under 13 has provided us with personal data
            through a chat widget, please contact us and we will promptly delete
            it.
          </p>
        </section>

        <section>
          <h2>10. California Privacy Rights (CCPA)</h2>
          <p>If you are a California resident, you have the right to:</p>
          <ul>
            <li>
              <strong>Know</strong> what personal information we collect and how
              it is used.
            </li>
            <li>
              <strong>Delete</strong> your personal information (subject to
              certain exceptions).
            </li>
            <li>
              <strong>Opt-out of sale:</strong> We do not sell your personal
              information, so this right is already satisfied.
            </li>
            <li>
              <strong>Non-discrimination:</strong> We will not discriminate
              against you for exercising your privacy rights.
            </li>
          </ul>
          <p>
            To make a CCPA request, email{" "}
            <a href="mailto:help@agentnexlify.com">help@agentnexlify.com</a>{" "}
            with the subject line &ldquo;CCPA Request.&rdquo;
          </p>
        </section>

        <section>
          <h2>11. Data Security</h2>
          <p>We take reasonable measures to protect your data, including:</p>
          <ul>
            <li>
              Encrypted data transmission (HTTPS/TLS) for all API communication.
            </li>
            <li>Hashed passwords (never stored in plaintext).</li>
            <li>API key authentication for widget access.</li>
            <li>Row-level security in our database to isolate tenant data.</li>
          </ul>
          <p>
            Your data is stored securely on Supabase, a SOC 2 Type 2 compliant
            cloud database platform hosted on Amazon Web Services (AWS). All
            data is encrypted at rest and in transit. Supabase does not sell,
            trade, or share your personal information with third parties. For
            more information, see Supabase&rsquo;s privacy policy at{" "}
            <a
              href="https://supabase.com/privacy"
              target="_blank"
              rel="noopener noreferrer"
            >
              supabase.com/privacy
            </a>
            .
          </p>
          <p>
            No system is 100% secure. If we discover a data breach that affects
            your personal information, we will notify you promptly.
          </p>
        </section>

        <section>
          <h2>12. Changes to This Policy</h2>
          <p>
            We may update this Privacy Policy from time to time. If we make
            material changes, we&rsquo;ll notify you via email or a notice in
            the dashboard. The &ldquo;Last updated&rdquo; date at the top
            reflects the most recent revision.
          </p>
        </section>

        <section>
          <h2>13. Contact Us</h2>
          <p>Questions or concerns about your privacy? Reach out:</p>
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

        <section>
          <h2>14. For Website Visitors</h2>
          <p>
            If you interacted with an AgentNexLiFy chat widget on a
            business&rsquo;s website and have questions about how{" "}
            <em>that business</em> handles your data, please contact the
            business directly. They are the data controller for the information
            you provide through their widget. AgentNexLiFy acts as a data
            processor on their behalf.
          </p>
          <p>
            If you want AgentNexLiFy to delete your conversation data directly,
            email us at{" "}
            <a href="mailto:help@agentnexlify.com">help@agentnexlify.com</a>{" "}
            with the business name and approximate date of your interaction.
          </p>
        </section>
      </article>
    </div>
  );
}
