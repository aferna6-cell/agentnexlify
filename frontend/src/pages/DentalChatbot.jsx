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
    icon: "R",
    title: "48hr & 24hr Appointment Reminders",
    description:
      "Automated reminder texts before every appointment. Patients confirm or reschedule without calling.",
  },
  {
    icon: "I",
    title: "Online Intake Before the Visit",
    description:
      "New patient forms completed before they arrive \u2014 your front desk starts each appointment ready.",
  },
  {
    icon: "C",
    title: "Easy Rescheduling via Chat",
    description:
      "Patients reschedule through a simple SMS conversation instead of calling during office hours.",
  },
];

const stats = [
  { number: "35%+", label: "Reduction in no-shows" },
  { number: "$1,400", label: "Avg monthly revenue recovered" },
];

export default function DentalChatbot() {
  return (
    <VerticalPage
      meta={meta}
      hero={hero}
      features={features}
      stats={stats}
      slug="dental-chatbot"
    >
      <div className="vp-disclaimer">
        Built with patient privacy in mind. Contact us to discuss your specific
        compliance requirements before deploying.
      </div>
    </VerticalPage>
  );
}
