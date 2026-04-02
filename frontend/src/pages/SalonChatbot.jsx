import VerticalPage from "../components/VerticalPage";

const meta = {
  title: "AI Chatbot for Salons & Spas | Book More Appointments Automatically",
  description:
    "24/7 booking, service inquiries, and client follow-ups for salons and spas. Fill your chair time without answering the phone.",
  canonical: "https://agentnexlify.com/salon-booking-chatbot",
};

const hero = {
  h1: "Fill Every Chair \u2014 AI Booking for Salons & Spas",
  subhead:
    "Clients book appointments, ask about services, and get pricing \u2014 all through your website, 24/7.",
  painPoint: "40% of salon bookings happen outside business hours.",
};

const features = [
  {
    icon: "\uD83D\uDC87",
    title: "24/7 Online Booking",
    description:
      "Clients see your available time slots and book appointments directly through your website chat \u2014 no phone calls, no back-and-forth.",
  },
  {
    icon: "\uD83D\uDCCB",
    title: "Service Menu in Chat",
    description:
      "The AI knows your full service menu with pricing. Clients ask 'how much is balayage?' and get an instant, accurate answer.",
  },
  {
    icon: "\uD83D\uDD14",
    title: "Appointment Reminders",
    description:
      "Automated texts 24 hours before every appointment. Clients confirm or reschedule with a tap \u2014 reducing no-shows by 35%.",
  },
  {
    icon: "\uD83D\uDCE7",
    title: "Rebooking Sequences",
    description:
      "6 weeks after a haircut, an automated email reminds the client it's time to book again. Keep your regulars on schedule without manual follow-up.",
  },
  {
    icon: "\u2B50",
    title: "Review Requests",
    description:
      "After every appointment, the system sends a review request. Build your Google rating on autopilot.",
  },
  {
    icon: "\uD83C\uDFA8",
    title: "New Client Welcome Flow",
    description:
      "First-time clients automatically receive a welcome email with what to expect, parking info, and a link to fill out preferences before their visit.",
  },
];

const stats = [
  { number: "40%", label: "Of bookings happen after hours" },
  { number: "3x", label: "More online bookings vs phone-only" },
  { number: "35%", label: "Reduction in no-shows" },
];

const faqs = [
  {
    q: "Can clients book specific stylists?",
    a: "Currently the system books available time slots for your business. You can manage stylist assignments from the dashboard after the booking comes in. Stylist-specific booking is on our roadmap.",
  },
  {
    q: "Does it handle walk-in availability?",
    a: "The AI shows your scheduled availability. For walk-in policies, add that info to your FAQ manager and the AI will let clients know your walk-in hours and typical wait times.",
  },
  {
    q: "Can it answer questions about specific services?",
    a: "Yes. Add your service menu, pricing, duration, and any other details to the FAQ manager. The AI answers client questions accurately based on what you've entered.",
  },
  {
    q: "How do rebooking reminders work?",
    a: "Set up an email sequence triggered after appointment completion. For example: 5 weeks after a haircut, send 'Time for a trim? Book your next appointment.' Clients who don't book get a follow-up a week later.",
  },
  {
    q: "Will it work with my existing booking system?",
    a: "AgentNexLiFy has its own booking system with Google Calendar sync. If you use another platform, the AI can capture the booking request and notify you to schedule it in your existing system.",
  },
];

export default function SalonChatbot() {
  return (
    <VerticalPage
      meta={meta}
      hero={hero}
      features={features}
      stats={stats}
      faqs={faqs}
      slug="salon-booking-chatbot"
    />
  );
}
