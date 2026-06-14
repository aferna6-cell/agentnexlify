import { Link } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import "../styles/legal.css";

/**
 * Public help / docs page (/help).
 * Written for non-technical small-business owners.
 * Reuses the standalone-page styling conventions from TermsOfService.jsx
 * (legal-page / legal-nav / legal-content classes in styles/legal.css).
 */
export default function HelpPage() {
  return (
    <div className="legal-page">
      <Helmet>
        <title>Help Center | AgentNexLiFy</title>
        <meta
          name="description"
          content="AgentNexLiFy Help Center - getting started, your 8 AI departments, approvals, memory, the website widget, billing, and support."
        />
      </Helmet>

      <nav className="legal-nav">
        <Link to="/" className="legal-back">
          &larr; Back to Home
        </Link>
        <Link to="/privacy" className="legal-sibling">
          Privacy Policy
        </Link>
        <Link to="/terms" className="legal-sibling">
          Terms of Service
        </Link>
        <Link to="/contact" className="legal-sibling">
          Contact
        </Link>
      </nav>

      <article className="legal-content">
        <h1>Help Center</h1>
        <p className="legal-updated">
          Everything you need to run your business with AgentNexLiFy.
        </p>

        <section>
          <h2>Getting started</h2>
          <p>
            Log in and you land in a conversation with your AI staff. There is
            no complicated dashboard to learn first &mdash; type what you need,
            the way you&rsquo;d ask an employee. Ask anything: &ldquo;follow up
            with the lead from yesterday,&rdquo; &ldquo;draft an invoice for
            the Hendersons,&rdquo; &ldquo;what came in through the website this
            week?&rdquo; The right department picks it up and shows you the
            work before anything goes out.
          </p>
        </section>

        <section>
          <h2>Your 8 departments</h2>
          <p>
            Your AI staff is organized into eight departments, each focused on
            one part of running your business:
          </p>
          <ul>
            <li>
              <strong>Sales</strong> &mdash; follows up with leads, answers
              pricing questions, and moves prospects toward booked work.
            </li>
            <li>
              <strong>Marketing</strong> &mdash; drafts campaigns, emails, and
              promotions to bring in new customers.
            </li>
            <li>
              <strong>Customer Service</strong> &mdash; handles customer
              questions, complaints, and follow-ups with a consistent voice.
            </li>
            <li>
              <strong>Operations</strong> &mdash; keeps scheduling,
              appointments, and day-to-day tasks moving.
            </li>
            <li>
              <strong>Invoicing &amp; Collections</strong> &mdash; drafts
              invoices, sends payment reminders, and chases overdue balances
              politely.
            </li>
            <li>
              <strong>Accounting &amp; Finance</strong> &mdash; summarizes
              money in and money out so you know where you stand.
            </li>
            <li>
              <strong>Customer Data &amp; Admin</strong> &mdash; keeps your
              customer records organized, current, and easy to search.
            </li>
            <li>
              <strong>People Management</strong> &mdash; helps with hiring
              posts, schedules, and team communication.
            </li>
          </ul>
        </section>

        <section>
          <h2>Approvals &mdash; nothing sends without your OK</h2>
          <p>
            By default, your AI staff drafts the work and waits. Every email,
            text, and invoice sits in your approvals queue until you review it
            and say go. You stay in control of everything that reaches a
            customer. If you reach the point where you trust a department to
            send routine items on its own, you can turn on auto-send in
            Settings &mdash; and turn it back off any time.
          </p>
        </section>

        <section>
          <h2>Memory &mdash; the OS learns your business</h2>
          <p>
            As you work, the system remembers what matters: your customers,
            your prices, how you like things worded, which jobs you take. That
            means less repeating yourself over time. The Memory panel shows you
            everything it has learned &mdash; every customer, fact, and
            preference is visible, nothing is hidden. If something is wrong or
            you want it gone, hit Forget and it&rsquo;s removed.
          </p>
        </section>

        <section>
          <h2>The website widget</h2>
          <p>
            The chat widget on your website is your 24/7 lead catcher. When a
            visitor asks a question at 11 PM, the widget answers using your
            business info, captures their contact details, and can book an
            appointment on the spot. Every widget conversation feeds your AI
            staff, so Sales already knows who asked about a quote and Customer
            Service already knows what was promised. Installing it is one small
            piece of code on your site &mdash; the setup wizard walks you
            through it.
          </p>
        </section>

        <section>
          <h2>Billing &amp; plans</h2>
          <p>
            Manage your subscription from the Billing page in your dashboard:
            upgrade, downgrade, or cancel &mdash; no phone call or email
            required. If you cancel, you keep full access until the end of the
            billing period you already paid for; we never cut you off early.
            Details on refunds and payment terms are in our{" "}
            <Link to="/terms">Terms of Service</Link>.
          </p>
        </section>

        <section>
          <h2>How we compare</h2>
          <p>
            <strong>GoHighLevel.</strong> GoHighLevel is a deep, powerful CRM
            platform with hundreds of features, and plenty of agencies build
            their whole business on it. The trade-off is learning curve: it
            takes real time to set up and master. AgentNexLiFy is built around
            one conversation with approval-gated AI staff &mdash; you describe
            what you need in plain language and review the work before it
            sends, instead of configuring pipelines and funnels yourself.
          </p>
          <p>
            <strong>Podium and Birdeye.</strong> Both are strong at reviews and
            customer messaging &mdash; if review management is your main need,
            they do it well. Our focus is the follow-through after the message:
            the same system that catches the lead also runs the sales
            follow-up, schedules the job, sends the invoice, and chases the
            payment, end to end.
          </p>
          <p>
            <strong>AI receptionists (Phonely, Toma, and similar).</strong>{" "}
            These answer your phone so you never miss a call, and they&rsquo;re
            good at that single job. We cover the work that starts after the
            call is answered: following up with the caller, booking them in,
            invoicing the job, and keeping their record current.
          </p>
          <p>
            <strong>Budget chat widgets.</strong> A low-cost widget answers
            website questions, and for some businesses that&rsquo;s enough. For
            us, the widget is the data source rather than the whole product:
            what visitors say feeds your AI departments, which then act on it
            &mdash; sales follow-up, scheduling, invoicing &mdash; with your
            approval.
          </p>
        </section>

        <section>
          <h2>Deleting your account</h2>
          <p>
            You can delete your account yourself from Settings &mdash; no email
            or support ticket needed. Deletion is a full erasure: it removes
            your business profile, customer records, leads, conversations,
            appointments, invoices, learned memory, and your billing record
            with our payment processor. This is permanent and cannot be undone,
            so export anything you want to keep first.
          </p>
        </section>

        <section>
          <h2>Getting help</h2>
          <p>We answer real questions from real people. Reach out any time:</p>
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
