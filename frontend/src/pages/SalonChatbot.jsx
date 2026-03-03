import VerticalPage from "../components/VerticalPage";

const meta = {
  title: "Salon Booking Chatbot | AI Appointment Scheduling for Hair Salons",
  description:
    "AI booking automation for salons. Clients self-book 24/7, no-shows drop 30%, and you save 2 hours a day on phone calls.",
  canonical: "https://agentnexlify.com/salon-booking-chatbot",
};

const hero = {
  h1: "Your Salon\u2019s 24/7 AI Booking Agent \u2014 Book Appointments While You Sleep",
  subhead:
    "Clients self-book any time. Reminders go out automatically.",
  painPoint: "Clients call during your busiest hours. Stop losing them.",
};

const features = [
  {
    icon: "\uD83D\uDCC5",
    title: "Self-Book Any Time",
    description:
      "Clients book appointments 24/7 through your website, Facebook, or SMS \u2014 without calling.",
  },
  {
    icon: "\uD83D\uDD14",
    title: "Automatic No-Show Reminders",
    description:
      "Reminder texts go out 48hrs and 24hrs before each appointment. No-shows drop 30% on average.",
  },
  {
    icon: "\uD83D\uDD17",
    title: "Works With Your Booking Software",
    description:
      "Integrates with Mindbody, Acuity, and Square \u2014 no switching, no re-entering data.",
  },
];

const stats = [
  { number: "30%", label: "Fewer no-shows" },
  { number: "2hrs", label: "Saved per day on phone calls" },
];

export default function SalonChatbot() {
  return (
    <VerticalPage
      meta={meta}
      hero={hero}
      features={features}
      stats={stats}
      slug="salon-booking-chatbot"
    />
  );
}
