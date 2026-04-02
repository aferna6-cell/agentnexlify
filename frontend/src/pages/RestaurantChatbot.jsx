import VerticalPage from "../components/VerticalPage";

const meta = {
  title: "AI Chatbot for Restaurants | Handle Reservations & Orders Automatically",
  description:
    "24/7 reservation booking, menu inquiries, and event requests for restaurants. Never miss a reservation again.",
  canonical: "https://agentnexlify.com/restaurant-chatbot",
};

const hero = {
  h1: "Never Miss a Reservation \u2014 AI for Restaurants",
  subhead:
    "Handle reservations, menu questions, and catering inquiries 24/7 \u2014 even during the dinner rush.",
  painPoint: "Your host can't answer the phone when the dining room is full.",
};

const features = [
  {
    icon: "\uD83C\uDF7D\uFE0F",
    title: "24/7 Reservation Booking",
    description:
      "Guests book tables directly through your website chat. The AI checks availability and confirms instantly \u2014 no phone calls during the rush.",
  },
  {
    icon: "\uD83D\uDCCB",
    title: "Menu & Allergy Info",
    description:
      "Guests ask about ingredients, dietary options, and allergens. The AI answers accurately based on your menu data \u2014 no server needed.",
  },
  {
    icon: "\uD83C\uDF89",
    title: "Event & Catering Inquiries",
    description:
      "Capture party size, date, budget, and contact info for private events and catering. Get qualified leads instead of missed voicemails.",
  },
  {
    icon: "\u2B50",
    title: "Review Management",
    description:
      "After every visit, automatically request a Google review. The AI drafts professional responses to every review \u2014 positive or negative.",
  },
  {
    icon: "\uD83D\uDCE7",
    title: "Guest Retention Sequences",
    description:
      "First-time guests get a thank-you email with a link to book again. Regulars who haven't visited in 60 days get a 'we miss you' nudge.",
  },
  {
    icon: "\uD83D\uDCF1",
    title: "Real-Time Host Alerts",
    description:
      "Large party request? Catering inquiry? Your host or manager gets an instant SMS so they can follow up before the guest books elsewhere.",
  },
];

const stats = [
  { number: "2x", label: "More reservations captured online" },
  { number: "85%", label: "Of menu questions answered instantly" },
  { number: "30%", label: "More repeat visits from email sequences" },
];

const faqs = [
  {
    q: "Can the AI take food orders?",
    a: "AgentNexLiFy has built-in order management for restaurants. Guests can browse your menu and place orders through the chat. Orders appear in your dashboard for kitchen processing.",
  },
  {
    q: "Does it handle dietary restriction questions?",
    a: "Yes. Add your menu items with ingredient and allergen information to the system. The AI accurately answers questions about gluten-free, vegan, nut-free, and other dietary options.",
  },
  {
    q: "Can it manage waitlist during busy hours?",
    a: "The AI can capture the guest's name, party size, and phone number and add them to your waitlist. You manage the actual seating from the dashboard.",
  },
  {
    q: "How does the catering lead capture work?",
    a: "When someone asks about catering or private events, the AI collects event date, party size, budget, and contact info. This appears as a lead in your CRM with all details attached.",
  },
  {
    q: "Will it work with my POS system?",
    a: "AgentNexLiFy operates independently from your POS. Orders placed through the chat appear in the AgentNexLiFy dashboard. For POS integration, you can use our webhook system to push order data to compatible systems.",
  },
];

export default function RestaurantChatbot() {
  return (
    <VerticalPage
      meta={meta}
      hero={hero}
      features={features}
      stats={stats}
      faqs={faqs}
      slug="restaurant-chatbot"
    />
  );
}
