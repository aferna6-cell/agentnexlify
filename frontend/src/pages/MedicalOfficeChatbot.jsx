import VerticalPage from "../components/VerticalPage";

const meta = {
  title: "AI Chatbot for Medical Offices | Reduce Call Volume & Automate Intake",
  description:
    "Handle appointment scheduling, insurance questions, and patient inquiries 24/7. Reduce front desk call volume by 40%.",
  canonical: "https://agentnexlify.com/medical-office-chatbot",
};

const hero = {
  h1: "Cut Phone Volume in Half \u2014 AI for Medical Offices",
  subhead:
    "Patients schedule appointments, check insurance, and get answers \u2014 without calling your front desk.",
  painPoint: "Your staff spends 60% of their day answering the same 10 questions.",
};

const features = [
  {
    icon: "\uD83C\uDFE5",
    title: "24/7 Patient Scheduling",
    description:
      "Patients book, reschedule, or cancel appointments directly through your website. The AI checks availability in real-time and syncs with your calendar.",
  },
  {
    icon: "\uD83D\uDCCB",
    title: "Insurance & FAQ Automation",
    description:
      "Add your accepted insurance plans and common questions. The AI handles 'Do you take Blue Cross?' instantly \u2014 no hold music required.",
  },
  {
    icon: "\u23F0",
    title: "Appointment Reminders",
    description:
      "Automated text and email reminders 48 and 24 hours before visits. Patients confirm or request to reschedule with one tap.",
  },
  {
    icon: "\uD83D\uDCDD",
    title: "Pre-Visit Intake Routing",
    description:
      "Direct new patients to complete intake forms before their visit. Collect medical history, medications, and insurance info digitally.",
  },
  {
    icon: "\u2B50",
    title: "Patient Review Collection",
    description:
      "Satisfied patients receive an automatic review request after their visit. Build your online presence while focusing on patient care.",
  },
  {
    icon: "\uD83D\uDCE7",
    title: "Wellness Reminders",
    description:
      "Annual physical coming up? Flu shot season? Automated sequences remind patients when it's time for preventive care \u2014 keeping your schedule full.",
  },
];

const stats = [
  { number: "40%", label: "Reduction in front desk calls" },
  { number: "24/7", label: "Patient inquiry coverage" },
  { number: "90%", label: "Of common questions answered instantly" },
];

const faqs = [
  {
    q: "Is patient data handled securely?",
    a: "All data is stored in encrypted, SOC 2 compliant infrastructure with row-level security. The AI handles scheduling and general inquiries \u2014 it does not store or process clinical records. Contact us to discuss your compliance requirements.",
  },
  {
    q: "Can the AI triage urgent vs. non-urgent requests?",
    a: "The AI can be configured to recognize urgency keywords and direct patients to call 911 or your after-hours line for emergencies. For non-urgent requests, it handles scheduling and information.",
  },
  {
    q: "How does insurance verification work?",
    a: "Add your accepted insurance plans to the FAQ manager. The AI tells patients whether you accept their plan and can direct them to call for detailed coverage verification on specific procedures.",
  },
  {
    q: "Will this work for a multi-provider practice?",
    a: "Yes. Set your practice's overall availability. Appointments appear on your shared calendar and you can assign them to specific providers from the dashboard.",
  },
  {
    q: "Can patients request prescription refills through the chat?",
    a: "The AI can capture refill requests (patient name, medication, pharmacy) and notify your office. It does not process or authorize refills \u2014 that stays with your clinical team.",
  },
];

export default function MedicalOfficeChatbot() {
  return (
    <VerticalPage
      meta={meta}
      hero={hero}
      features={features}
      stats={stats}
      faqs={faqs}
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
