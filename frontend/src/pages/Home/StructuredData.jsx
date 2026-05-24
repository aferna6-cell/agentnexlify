import { Helmet } from "react-helmet-async";

export default function StructuredData() {
  return (
    <Helmet>
      <link rel="canonical" href="https://agentnexlify.com/" />
      <meta
        name="google-site-verification"
        content="87NEEvBU6dL3QuI_1iZK9wgq4Jtws60z1M3bKu-mS6s"
      />
      <script type="application/ld+json">{`
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "AgentNexLiFy",
  "url": "https://agentnexlify.com",
  "logo": "https://agentnexlify.com/logo.png",
  "description": "Your 24/7 AI employee that answers customers, captures leads, books appointments, and follows up automatically.",
  "address": {
    "@type": "PostalAddress",
    "addressLocality": "Clemson",
    "addressRegion": "SC",
    "addressCountry": "US"
  },
  "contactPoint": {
    "@type": "ContactPoint",
    "contactType": "sales",
    "url": "https://agentnexlify.com/contact"
  }
}
      `}</script>
      <script type="application/ld+json">{`
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "AgentNexLiFy",
  "applicationCategory": "BusinessApplication",
  "operatingSystem": "Web",
  "description": "AI-powered business automation platform.",
  "url": "https://agentnexlify.com",
  "offers": [
    { "@type": "Offer", "name": "Free", "price": "0", "priceCurrency": "USD" },
    { "@type": "Offer", "name": "Growth", "price": "99", "priceCurrency": "USD",
      "priceSpecification": { "@type": "UnitPriceSpecification", "price": "99", "priceCurrency": "USD", "billingDuration": "P1M" }
    },
    {
      "@type": "Offer", "name": "Professional", "price": "150", "priceCurrency": "USD",
      "priceSpecification": { "@type": "UnitPriceSpecification", "price": "150", "priceCurrency": "USD", "billingDuration": "P1M" }
    },
    {
      "@type": "Offer", "name": "Enterprise", "price": "250", "priceCurrency": "USD",
      "priceSpecification": { "@type": "UnitPriceSpecification", "price": "250", "priceCurrency": "USD", "billingDuration": "P1M" }
    }
  ]
}
      `}</script>
      <script type="application/ld+json">{`
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    { "@type": "Question", "name": "What's included in each plan?", "acceptedAnswer": { "@type": "Answer", "text": "Every plan builds on the previous tier. Free includes the chat widget, customer capture, and FAQ knowledge base. Growth starts at $99/month and includes a 7-day free trial, booking, SMS, automation, basic SEO audit, and the AI content writer. Professional is $150/month with the full SEO suite, social media marketing, email/SMS campaigns, and advanced analytics. Enterprise is $250/month with AI visibility tracking, competitor analysis, team accounts, webhooks, and white-label branding." } },
    { "@type": "Question", "name": "Do I need any technical skills?", "acceptedAnswer": { "@type": "Answer", "text": "Not at all. We handle 100% of the setup, integration, and ongoing management." } },
    { "@type": "Question", "name": "What tools do you integrate with?", "acceptedAnswer": { "@type": "Answer", "text": "Google Calendar (built-in), plus outbound webhooks to connect with Zapier, Slack, HubSpot, and 5,000+ other tools. We also integrate with Twilio for SMS and Stripe for payments." } },

    { "@type": "Question", "name": "Can I upgrade my plan later?", "acceptedAnswer": { "@type": "Answer", "text": "Absolutely! We suggest starting with Growth and upgrading within a few months as your business scales. You can change your plan anytime from the Billing page." } },
    { "@type": "Question", "name": "Is there a contract?", "acceptedAnswer": { "@type": "Answer", "text": "No long-term contracts. Month-to-month billing. Cancel anytime." } },
    { "@type": "Question", "name": "What if AI makes a mistake?", "acceptedAnswer": { "@type": "Answer", "text": "You stay in control. Emails are drafted for your approval before sending. Your AI assistant helps identify promising customers - you decide how to follow up." } },
    { "@type": "Question", "name": "How is this different from Zapier or ChatGPT?", "acceptedAnswer": { "@type": "Answer", "text": "Those are tools you have to build and manage yourself. Agent NexLiFy is a done-for-you service." } }
  ]
}
      `}</script>
    </Helmet>
  );
}
