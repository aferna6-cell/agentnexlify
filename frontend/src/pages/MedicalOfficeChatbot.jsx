import VerticalPage from "../components/VerticalPage";

const meta = {
  title: "AI Chatbot for Medical Offices | Patient Scheduling & Follow-Up",
  description:
    "Automate scheduling calls, appointment reminders, and new patient intake. Your staff saves 8 hours a week.",
  canonical: "https://agentnexlify.com/medical-office-chatbot",
};

const hero = {
  h1: "AI That Works for Your Medical Practice \u2014 Without the Compliance Headaches",
  subhead:
    "Scheduling, reminders, and intake \u2014 handled automatically.",
  painPoint: "Your staff spends 2 hours a day on scheduling calls.",
};

const features = [
  {
    icon: "\uD83D\uDCC5",
    title: "Appointment Scheduling via SMS & Web",
    description:
      "Patients schedule, confirm, and reschedule through chat \u2014 no phone tag.",
  },
  {
    icon: "\uD83D\uDD14",
    title: "Automated Reminders",
    description:
      "Reminder messages go out automatically before every appointment. No-shows drop significantly.",
  },
  {
    icon: "\uD83D\uDCDD",
    title: "New Patient Intake Before the Visit",
    description:
      "Collect patient information before they arrive so your team can focus on care, not paperwork.",
  },
];

const stats = [
  { number: "40%", label: "Of calls handled automatically" },
  { number: "8hrs", label: "Saved per staff member per week" },
];

export default function MedicalOfficeChatbot() {
  return (
    <VerticalPage
      meta={meta}
      hero={hero}
      features={features}
      stats={stats}
      slug="medical-office-chatbot"
    >
      <div className="vp-disclaimer">
        AI customer service tools in clinical settings may have regulatory
        considerations. Contact us to discuss your compliance requirements
        before deploying.
      </div>
    </VerticalPage>
  );
}
