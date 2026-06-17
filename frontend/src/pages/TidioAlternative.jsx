import ComparisonPage from "../components/ComparisonPage";

const data = {
  meta: {
    title: "Tidio Alternative for Local Businesses | AgentNexLiFy",
    description:
      "Looking for a Tidio alternative built for local service businesses? AgentNexLiFy offers missed call text-back, SMS automation, and flat pricing \u2014 starting free.",
    canonical: "https://agentnexlify.com/tidio-alternative",
  },
  hero: {
    h1: "Better Than Tidio for Local Businesses \u2014",
    h1Accent: "Here\u2019s Why",
    subtitle:
      "Tidio is great for ecommerce. NexLiFy is built for service businesses \u2014 plumbers, dentists, salons, law firms, and any local business that needs to capture leads and respond fast, even after hours.",
    primaryCta: "Switch from Tidio \u2014 Get Started \u2192",
    secondaryCta: "See the Comparison \u2193",
  },
  comparison: {
    label: "Feature Comparison",
    title: "NexLiFy vs. Tidio",
    subtitle:
      "A side-by-side look at what matters for local service businesses.",
    columns: ["Feature", "NexLiFy", "Tidio"],
    rows: [
      {
        feature: "Starting price",
        nexlify: "From $19.99/mo",
        nexlifyClass: "check",
        competitor: "Yes (limited features)",
        competitorClass: "muted",
      },
      {
        feature: "Local business focus",
        nexlify: "Yes \u2014 vertical-specific AI",
        nexlifyClass: "check",
        competitor: "No \u2014 generic chatbot",
        competitorClass: "cross",
      },
      {
        feature: "Missed call text-back",
        nexlify: "Yes \u2014 built in",
        nexlifyClass: "check",
        competitor: "No",
        competitorClass: "cross",
      },
      {
        feature: "Pricing model",
        nexlify: "Flat monthly pricing",
        nexlifyClass: "check",
        competitor: "Per agent seat",
        competitorClass: "muted",
      },
      {
        feature: "SMS automation",
        nexlify: "Yes \u2014 full SMS channel",
        nexlifyClass: "check",
        competitor: "Limited",
        competitorClass: "muted",
      },
      {
        feature: "AI trained for your industry",
        nexlify: "Yes \u2014 vertical AI models",
        nexlifyClass: "check",
        competitor: "No \u2014 one-size-fits-all",
        competitorClass: "cross",
      },
      {
        feature: "Setup time",
        nexlify: "< 5 minutes",
        nexlifyClass: "check",
        competitor: "15\u201330 minutes",
        competitorClass: "muted",
      },
    ],
  },
  reasons: {
    label: "Why Switch",
    title: "3 Reasons Local Businesses Choose NexLiFy Over Tidio",
    cards: [
      {
        icon: "phone",
        heading: "Missed call text-back captures leads Tidio can\u2019t",
        body: "When a customer calls and you can\u2019t pick up, NexLiFy automatically sends a text within seconds. Tidio doesn\u2019t have this capability \u2014 and for service businesses, missed calls are missed revenue.",
      },
      {
        icon: "target",
        heading: "AI that understands your industry",
        body: "NexLiFy\u2019s AI is trained on service-business conversations \u2014 appointment booking, service inquiries, pricing questions. Tidio\u2019s chatbot is built for ecommerce product questions and cart recovery.",
      },
      {
        icon: "tag",
        heading: "Flat pricing means no surprises",
        body: "Tidio charges per agent seat, which gets expensive as your team grows. NexLiFy uses flat monthly pricing \u2014 $19.99/mo (AI Front Desk) or $99.99/mo (AI Workforce) \u2014 regardless of how many people use the dashboard. Plus, you get SEO tools, social media marketing, and AI content generation included.",
      },
    ],
  },
  crossLinks: {
    others: [
      { slug: "intercom-alternative", label: "Intercom" },
      { slug: "livechat-alternative", label: "LiveChat" },
    ],
  },
  faq: {
    items: [
      {
        question: "Is NexLiFy really a good alternative to Tidio?",
        answer:
          "Yes. Tidio is designed primarily for ecommerce stores and online retailers. NexLiFy is purpose-built for local service businesses \u2014 plumbers, dentists, salons, law firms, and similar. It includes features like missed call text-back and SMS automation that Tidio does not offer, with flat pricing instead of per-seat costs.",
      },
      {
        question: "Can I migrate from Tidio to NexLiFy?",
        answer:
          "Absolutely. NexLiFy can be set up in under 5 minutes. There\u2019s no complex migration process \u2014 just add the NexLiFy widget to your site and configure your business details. Your AI agent starts handling conversations immediately.",
      },
      {
        question: "Does NexLiFy have a free plan?",
        answer:
          "No. NexLiFy has no free plan. AI Front Desk is $19.99/mo and AI Workforce is $99.99/mo. No setup fees. Cancel anytime.",
      },
    ],
  },
  cta: {
    title: "Ready to switch from Tidio?",
    subtitle: "Set up NexLiFy in under 5 minutes. No setup fees. Cancel anytime.",
    primaryCta: "Switch from Tidio \u2014 Get Started \u2192",
    secondaryCta: "See Pricing \u2193",
    note: "No commitment. No pressure. Just a conversation.",
  },
};

export default function TidioAlternative() {
  return <ComparisonPage {...data} />;
}
