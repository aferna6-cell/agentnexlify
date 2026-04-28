import ComparisonPage from "../components/ComparisonPage";

const data = {
  meta: {
    title: "Intercom Alternative for Small Business | AgentNexLiFy",
    description:
      "Intercom costs $74+/month per seat. AgentNexLiFy starts free with AI chat, SMS automation, and missed call text-back \u2014 built for local businesses, not enterprises.",
    canonical: "https://agentnexlify.com/intercom-alternative",
  },
  hero: {
    h1: "Intercom Costs $74+/Month Per Seat.",
    h1Accent: "NexLiFy Starts Free.",
    subtitle:
      "Intercom is enterprise software with enterprise pricing. If you\u2019re a local business, you\u2019re paying for product tours, advanced ticketing, and SaaS integrations you\u2019ll never use. NexLiFy gives you what you actually need \u2014 AI chat, SMS, and missed call text-back \u2014 at a price that makes sense.",
    primaryCta: "Get More for Less \u2014 Try NexLiFy Free \u2192",
    secondaryCta: "See the Comparison \u2193",
  },
  comparison: {
    label: "Feature Comparison",
    title: "NexLiFy vs. Intercom",
    subtitle:
      "Enterprise features come at enterprise prices. Here\u2019s what local businesses actually need.",
    columns: ["Feature", "NexLiFy", "Intercom"],
    rows: [
      { feature: "Starting price", nexlify: "Free (50 convos/mo)", nexlifyClass: "check", competitor: "~$74/seat/mo", competitorClass: "cross" },
      { feature: "Local business tools", nexlify: "Yes \u2014 industry-specific AI", nexlifyClass: "check", competitor: "No \u2014 built for SaaS", competitorClass: "cross" },
      { feature: "Setup time", nexlify: "< 5 minutes", nexlifyClass: "check", competitor: "Days of configuration", competitorClass: "cross" },
      { feature: "SMS channel", nexlify: "Yes \u2014 built in", nexlifyClass: "check", competitor: "No native SMS", competitorClass: "cross" },
      { feature: "Vertical AI training", nexlify: "Yes \u2014 trained for your industry", nexlifyClass: "check", competitor: "No \u2014 generic responses", competitorClass: "cross" },
      { feature: "Missed call text-back", nexlify: "Yes", nexlifyClass: "check", competitor: "No", competitorClass: "cross" },
      { feature: "Pricing model", nexlify: "Flat monthly (no per-seat)", nexlifyClass: "check", competitor: "Per agent seat + add-ons", competitorClass: "muted" },
    ],
  },
  reasons: {
    label: "Why Switch",
    title: "3 Reasons Local Businesses Choose NexLiFy Over Intercom",
    cards: [
      {
        icon: "dollar",
        heading: "Stop paying enterprise prices for basic chat",
        body: "Intercom\u2019s $74/seat/mo adds up fast. A 3-person team costs $222/mo before add-ons. NexLiFy\u2019s Growth plan is $99/mo flat \u2014 no matter how many people access the dashboard. Includes SEO, marketing campaigns, and AI content tools.",
      },
      {
        icon: "zap",
        heading: "Go live in minutes, not days",
        body: "Intercom requires CRM integration, workflow configuration, and team training. NexLiFy takes under 5 minutes: add the widget, enter your details, done. Your AI agent handles conversations from day one.",
      },
      {
        icon: "phone",
        heading: "SMS and missed call text-back are built in",
        body: "Intercom doesn\u2019t offer native SMS or missed call handling. For a local business, these are critical \u2014 customers call, and when you can\u2019t answer, NexLiFy texts them back automatically.",
      },
    ],
  },
  crossLinks: {
    others: [
      { slug: "tidio-alternative", label: "Tidio" },
      { slug: "livechat-alternative", label: "LiveChat" },
    ],
  },
  faq: {
    items: [
      {
        question: "Why is NexLiFy cheaper than Intercom?",
        answer:
          "Intercom is built for enterprise SaaS companies and charges per agent seat, starting at around $74/month per seat. NexLiFy is purpose-built for local businesses with flat monthly pricing (Free, $99, $150, or $250/mo) \u2014 no per-seat charges, no usage surprises. You get AI chat, CRM, SEO tools, social media marketing, and email campaigns without paying for enterprise tools you\u2019ll never use.",
      },
      {
        question: "Does NexLiFy have the same features as Intercom?",
        answer:
          "NexLiFy focuses on the features local businesses actually need: AI chat, missed call text-back, SMS automation, and vertical-specific AI training. Intercom offers product tours, advanced ticketing, and enterprise integrations that are designed for SaaS companies. If you\u2019re a local service business, NexLiFy gives you more relevant features at a fraction of the cost.",
      },
      {
        question: "How long does it take to set up NexLiFy compared to Intercom?",
        answer:
          "NexLiFy can be set up in under 5 minutes \u2014 add the widget to your site, enter your business details, and your AI agent is live. Intercom typically requires days of configuration, CRM integration, workflow building, and team onboarding before it\u2019s fully operational.",
      },
    ],
  },
  cta: {
    title: "Stop overpaying for enterprise software.",
    subtitle: "NexLiFy gives local businesses what they need \u2014 at a price that makes sense.",
    primaryCta: "Get More for Less \u2014 Try NexLiFy Free \u2192",
    secondaryCta: "See Pricing \u2193",
    note: "No commitment. No credit card. No enterprise sales pitch.",
  },
};

export default function IntercomAlternative() {
  return <ComparisonPage {...data} />;
}
