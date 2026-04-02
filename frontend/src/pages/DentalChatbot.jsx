import VerticalPage from "../components/VerticalPage";

const meta = {
  title: "AI Chatbot for Dental Offices | Reduce No-Shows & Automate Intake",
  description:
    "Automated appointment reminders, online intake forms, and easy rescheduling via chat. Every no-show recovered is $200+ back.",
  canonical: "https://agentnexlify.com/dental-chatbot",
};

const hero = {
  h1: "Stop Losing Revenue to No-Shows \u2014 AI for Dental Offices",
  subhead:
    "Automated reminders, intake forms, and rescheduling \u2014 all on autopilot.",
  painPoint: "Every no-show costs your practice $200+.",
};

const features = [
  {
    icon: "\u23F0",
    title: "48hr & 24hr Appointment Reminders",
    description:
      "Automated reminder texts before every appointment. Patients confirm or reschedule without calling your front desk.",
  },
  {
    icon: "\uD83D\uDCCB",
    title: "Online Intake Before the Visit",
    description:
      "New patient forms completed before they arrive. Insurance info, medical history, and consent forms \u2014 your front desk starts each appointment ready.",
  },
  {
    icon: "\uD83D\uDCAC",
    title: "24/7 Patient Chat",
    description:
      "Answer insurance questions, explain procedures, and handle scheduling after hours. Patients get instant responses instead of leaving voicemails.",
  },
  {
    icon: "\uD83D\uDD04",
    title: "Recall & Reactivation",
    description:
      "Automatically reach out to patients overdue for cleanings or checkups. Turn your inactive patient list into booked appointments.",
  },
  {
    icon: "\u2B50",
    title: "Review Collection",
    description:
      "After every appointment, automatically ask satisfied patients for a Google review. AI drafts professional responses to every review.",
  },
  {
    icon: "\uD83D\uDCE7",
    title: "Treatment Follow-Up Sequences",
    description:
      "Post-procedure care instructions, follow-up reminders, and check-ins sent automatically based on the treatment performed.",
  },
];

const stats = [
  { number: "35%+", label: "Reduction in no-shows" },
  { number: "$1,400", label: "Avg monthly revenue recovered" },
  { number: "24/7", label: "Patient support coverage" },
];

const faqs = [
  {
    q: "Is patient data secure and HIPAA-compliant?",
    a: "AgentNexLiFy stores data in encrypted, SOC 2 compliant infrastructure. The AI never stores or transmits protected health information \u2014 it handles scheduling, general inquiries, and intake routing. Contact us to discuss your specific compliance requirements.",
  },
  {
    q: "Can the chatbot handle insurance questions?",
    a: "Yes. Add your accepted insurance plans and coverage details to the FAQ manager, and the AI will answer patient questions accurately. It can also direct patients to call for complex coverage verification.",
  },
  {
    q: "How does the recall system work?",
    a: "Set up an email sequence triggered by appointment completion. For example: 5 months after a cleaning, send a friendly reminder to schedule their next visit. Patients who don't respond get a follow-up 2 weeks later.",
  },
  {
    q: "Will this replace my front desk staff?",
    a: "No \u2014 it handles the repetitive tasks (appointment confirmations, basic questions, review requests) so your front desk can focus on patients in the office. Think of it as a digital assistant that works the hours your staff doesn't.",
  },
  {
    q: "How long does setup take for a dental practice?",
    a: "Most practices are live within an hour. Add your services, hours, insurance info, and common FAQs. The AI learns your practice instantly \u2014 no training period required.",
  },
  {
    q: "Can patients book appointments directly through the chat?",
    a: "Yes. Connect your Google Calendar, set your available hours, and patients can see open slots and request appointments right from the chat widget on your website.",
  },
];

export default function DentalChatbot() {
  return (
    <VerticalPage
      meta={meta}
      hero={hero}
      features={features}
      stats={stats}
      faqs={faqs}
      slug="dental-chatbot"
    >
      <div className="vp-disclaimer">
        Built with patient privacy in mind. Contact us to discuss your specific
        compliance requirements before deploying.
      </div>
    </VerticalPage>
  );
}
