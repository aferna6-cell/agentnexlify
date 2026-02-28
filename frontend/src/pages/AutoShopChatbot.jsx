import VerticalPage from "../components/VerticalPage";

const meta = {
  title: "AI Chatbot for Auto Repair Shops | Quote Requests & Scheduling",
  description:
    "Customers request quotes via SMS any time. Chatbot collects year/make/model upfront so your advisors are ready.",
  canonical: "https://agentnexlify.com/auto-shop-chatbot",
};

const hero = {
  h1: "More Cars on Your Lift \u2014 AI Customer Service for Auto Shops",
  subhead:
    "Capture quote requests and intake info automatically, even when you're in the bay.",
  painPoint: "Customers hang up when you're busy on the lift.",
};

const features = [
  {
    icon: "\uD83D\uDCF2",
    title: "Quote Requests 24/7",
    description:
      "Customers request quotes via SMS or your website any time \u2014 no hold music, no missed calls.",
  },
  {
    icon: "\uD83D\uDE97",
    title: "Smart Vehicle Intake",
    description:
      "Chatbot collects year, make, model, and issue before the first call. Advisors arrive prepared.",
  },
  {
    icon: "\uD83D\uDD27",
    title: "Automated Repair Updates",
    description:
      "Keep customers informed during service with automated status texts \u2014 fewer 'is my car ready?' calls.",
  },
];

const stats = [
  { number: "23%", label: "More service requests captured" },
  { number: "4hrs", label: "Faster intake turnaround" },
];

export default function AutoShopChatbot() {
  return (
    <VerticalPage
      meta={meta}
      hero={hero}
      features={features}
      stats={stats}
      slug="auto-shop-chatbot"
    />
  );
}
