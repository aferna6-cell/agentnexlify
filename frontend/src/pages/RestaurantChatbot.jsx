import VerticalPage from "../components/VerticalPage";

const meta = {
  title: "AI Chatbot for Restaurants | Automate Reservations 24/7",
  description:
    "Never miss a reservation again. AI chatbot handles bookings, confirmations, and menu questions 24/7 via SMS and web.",
  canonical: "https://agentnexlify.com/restaurant-chatbot",
};

const hero = {
  h1: "Never Miss a Reservation Again — AI Chatbot for Restaurants",
  subhead: "Handle bookings, confirmations, and FAQs automatically.",
  painPoint: "Missed calls mean empty tables. Fix it tonight.",
};

const features = [
  {
    icon: "R",
    title: "24/7 Reservation Booking",
    description:
      "Customers book tables via your website or SMS any time — no staff needed.",
  },
  {
    icon: "C",
    title: "Auto Confirmations & Reminders",
    description:
      "Automated confirmation texts reduce no-shows by 35% on average.",
  },
  {
    icon: "M",
    title: "Menu & Hours on Autopilot",
    description:
      "Handle specials, hours, and common questions without tying up your staff.",
  },
];

const stats = [
  { number: "35%", label: "Reduction in no-shows" },
  { number: "47", label: "Reservations recovered/month avg" },
];

export default function RestaurantChatbot() {
  return (
    <VerticalPage
      meta={meta}
      hero={hero}
      features={features}
      stats={stats}
      slug="restaurant-chatbot"
    />
  );
}
