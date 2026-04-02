import VerticalPage from "../components/VerticalPage";

const meta = {
  title: "AI Chatbot for Auto Shops | Capture More Repair Leads 24/7",
  description:
    "Automate appointment booking, repair inquiries, and follow-ups for your auto shop. Capture leads even after hours.",
  canonical: "https://agentnexlify.com/auto-shop-chatbot",
};

const hero = {
  h1: "Stop Missing Repair Jobs \u2014 AI for Auto Shops",
  subhead:
    "Capture every repair inquiry, book appointments, and follow up automatically \u2014 even at 2 AM.",
  painPoint: "62% of customers call your competitor when you don't answer.",
};

const features = [
  {
    icon: "\uD83D\uDE97",
    title: "24/7 Repair Inquiry Capture",
    description:
      "Customers describe their car trouble at any hour. The AI collects vehicle info, symptoms, and contact details \u2014 you get a qualified lead by morning.",
  },
  {
    icon: "\uD83D\uDCC5",
    title: "Automated Appointment Scheduling",
    description:
      "Show available bay times and let customers book drop-offs directly. Syncs with your Google Calendar to prevent double-booking.",
  },
  {
    icon: "\uD83D\uDCB0",
    title: "Estimate Follow-Ups",
    description:
      "After sending a quote, automated sequences follow up at day 2, 5, and 10. Customers who ghost your quotes get gentle nudges to approve the work.",
  },
  {
    icon: "\u2B50",
    title: "Review Generation",
    description:
      "After every completed repair, automatically request a Google review. The AI drafts professional responses to build your online reputation.",
  },
  {
    icon: "\uD83D\uDCF1",
    title: "SMS Alerts for New Leads",
    description:
      "Get an instant text when someone submits a repair inquiry through your website. Respond while they're still deciding \u2014 before they call the shop down the road.",
  },
  {
    icon: "\uD83D\uDCE7",
    title: "Service Reminder Sequences",
    description:
      "Oil change due? Tire rotation coming up? Automated emails remind past customers when it's time for their next service \u2014 bringing them back without a phone call.",
  },
];

const stats = [
  { number: "3x", label: "More leads captured after hours" },
  { number: "45%", label: "Quote-to-job conversion improvement" },
  { number: "<5 min", label: "Average response time to inquiries" },
];

const faqs = [
  {
    q: "Can the AI give repair estimates?",
    a: "The AI doesn't diagnose or quote. It captures the customer's vehicle info, symptoms, and photos, then notifies you instantly so you can provide an accurate estimate. This keeps you in control of pricing.",
  },
  {
    q: "Does it work for multi-bay shops?",
    a: "Yes. Set your available appointment slots based on how many bays you have and your working hours. The system prevents double-booking automatically.",
  },
  {
    q: "How does the quote follow-up work?",
    a: "After you send a customer an estimate, enroll them in an email sequence. Day 2: 'Any questions about the estimate?' Day 5: 'Ready to schedule?' Day 10: 'Your quote is still valid \u2014 book today.' You write the emails once, they send automatically.",
  },
  {
    q: "What information does the AI collect from customers?",
    a: "Vehicle year/make/model, description of the issue, name, phone number, and email. Everything appears in your dashboard as a qualified lead with a conversation summary.",
  },
  {
    q: "Can customers send photos of their car issue?",
    a: "The chat widget supports text-based conversations. For photo intake, the AI can direct customers to email or text photos to your shop number.",
  },
];

export default function AutoShopChatbot() {
  return (
    <VerticalPage
      meta={meta}
      hero={hero}
      features={features}
      stats={stats}
      faqs={faqs}
      slug="auto-shop-chatbot"
    />
  );
}
