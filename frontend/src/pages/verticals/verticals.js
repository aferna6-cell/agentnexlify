/**
 * Data for /ai-front-desk/* SEO landing pages.
 * Targets "AI front desk for [vertical]" search intent.
 *
 * Rules enforced in this file:
 * - No em dashes (use periods or commas instead)
 * - No banned marketing vocab (unlock, leverage, seamless, empower, elevate, supercharge, etc.)
 * - Pricing exact: $19.99 / $99.99
 * - No fabricated stats or testimonials
 */

export const VERTICAL_DATA = {
  salons: {
    slug: "salons",
    meta: {
      title: "AI Front Desk for Salons | AgentNexLiFy",
      description:
        "An AI front desk that answers client questions, captures leads, and books appointments 24/7 for salons and spas. Starts at $19.99/month.",
      canonical: "https://agentnexlify.com/ai-front-desk/salons",
    },
    hero: {
      h1: "AI Front Desk for Salons",
      subhead:
        "Answers questions, captures leads, and books appointments 24 hours a day. Your chair stays full even when the phone goes to voicemail.",
      painPoint:
        "Most salon booking requests come in after hours or between appointments.",
    },
    features: [
      {
        icon: "📅",
        title: "24/7 Appointment Booking",
        description:
          "Clients see your available slots and book directly through your website chat. No phone tag. No missed bookings.",
      },
      {
        icon: "💬",
        title: "Service and Pricing Questions",
        description:
          "The AI knows your full service menu and pricing. Clients get accurate answers immediately rather than waiting for a callback.",
      },
      {
        icon: "🔔",
        title: "Appointment Reminders",
        description:
          "Automated reminders go out before each appointment. Clients confirm or reschedule by text, cutting down on no-shows.",
      },
      {
        icon: "📧",
        title: "Rebooking Follow-Ups",
        description:
          "A few weeks after a visit, an automated message invites the client to book again. Keeps regulars on schedule without manual work.",
      },
      {
        icon: "⭐",
        title: "Review Requests",
        description:
          "After each appointment, the system sends a review request automatically. Build your Google rating while you focus on clients.",
      },
      {
        icon: "🎨",
        title: "New Client Welcome Flow",
        description:
          "First-time clients get a welcome message with what to expect, parking details, and a link to fill out preferences before arrival.",
      },
    ],
    stats: [
      { number: "$19.99", label: "per month to start" },
      { number: "24/7", label: "coverage with no extra staff" },
      { number: "$99.99", label: "per month for the full platform" },
    ],
    faqs: [
      {
        q: "What is an AI front desk for a salon?",
        a: "It is a chat widget on your website that answers client questions, captures contact info, and books appointments at any hour. It connects to your calendar and handles the back-and-forth so you can focus on clients in the chair.",
      },
      {
        q: "Can it book specific stylists?",
        a: "The system books available time slots for your business. You manage stylist assignments from the dashboard after the booking arrives. Stylist-specific booking is on the roadmap.",
      },
      {
        q: "How long does setup take?",
        a: "Most salons are live within an hour. Add your services, hours, and pricing. The AI starts answering questions the same day.",
      },
      {
        q: "What does it cost?",
        a: "The AI Front Desk plan is $19.99 per month. It includes the chat widget, lead capture, appointment requests, and FAQ management. The full platform with marketing tools, automations, and analytics is $99.99 per month.",
      },
      {
        q: "Does it work with my existing booking system?",
        a: "AgentNexLiFy has its own booking system with Google Calendar sync. If you use another platform, the AI can capture the request and notify you to schedule it there.",
      },
    ],
  },

  plumbers: {
    slug: "plumbers",
    meta: {
      title: "AI Front Desk for Plumbers and HVAC | AgentNexLiFy",
      description:
        "An AI front desk that answers service calls, qualifies leads, and books jobs 24/7 for plumbers and HVAC companies. Starts at $19.99/month.",
      canonical: "https://agentnexlify.com/ai-front-desk/plumbers",
    },
    hero: {
      h1: "AI Front Desk for Plumbers and HVAC",
      subhead:
        "Captures every call, qualifies the job, and books the appointment. Runs day and night so you never miss a service request while you are on a job.",
      painPoint:
        "Missed calls from potential customers are a constant problem for home service businesses.",
    },
    features: [
      {
        icon: "📞",
        title: "Capture Leads Around the Clock",
        description:
          "When you are under a sink or on a roof, the AI answers your website visitors, collects their contact info, and describes the job. You see the lead the moment you check the dashboard.",
      },
      {
        icon: "🔧",
        title: "Service Type Qualification",
        description:
          "The AI asks the right questions to understand what the customer needs, urgency level, and location. Emergency calls get flagged immediately.",
      },
      {
        icon: "📆",
        title: "Job Scheduling",
        description:
          "Customers pick an available time slot directly from the chat. The booking lands on your calendar with job details attached.",
      },
      {
        icon: "📋",
        title: "Estimate Follow-Up",
        description:
          "After a visit, the system can send a follow-up message and prompt you to send an estimate. No job falls through the cracks.",
      },
      {
        icon: "⭐",
        title: "Review Collection",
        description:
          "After each completed job, the system asks the customer for a Google review. Positive reviews build credibility in your service area.",
      },
      {
        icon: "📱",
        title: "SMS and Email Notifications",
        description:
          "Get a text or email the moment a new lead comes in. Respond fast or let the AI hold the customer until you are available.",
      },
    ],
    stats: [
      { number: "$19.99", label: "per month to start" },
      { number: "24/7", label: "lead capture with no extra staff" },
      { number: "$99.99", label: "per month for the full platform" },
    ],
    faqs: [
      {
        q: "What is an AI front desk for a plumbing or HVAC business?",
        a: "It is a chat widget on your website that answers visitor questions, collects job details, and books service calls. It works while you are on jobs, so no service request goes unanswered.",
      },
      {
        q: "Can it handle emergency calls?",
        a: "Yes. Add emergency keywords and the AI flags those leads immediately and sends you an alert. You decide how to respond to urgent requests.",
      },
      {
        q: "How does lead qualification work?",
        a: "The AI asks visitors about the problem, urgency, and their location. It collects contact info and summarizes the job so you know what you are walking into before you call back.",
      },
      {
        q: "What does it cost?",
        a: "The AI Front Desk plan is $19.99 per month. It includes the chat widget, lead capture, appointment booking, and FAQ management. The full platform with estimates, automations, and campaign tools is $99.99 per month.",
      },
      {
        q: "Does it integrate with my dispatch software?",
        a: "AgentNexLiFy syncs with Google Calendar. For other dispatch systems, outbound webhooks connect to Zapier and 5,000 plus apps so lead data flows to wherever you manage jobs.",
      },
    ],
  },

  dentists: {
    slug: "dentists",
    meta: {
      title: "AI Front Desk for Dental Offices | AgentNexLiFy",
      description:
        "An AI front desk that handles patient questions, appointment requests, and intake before the visit for dental offices. Starts at $19.99/month.",
      canonical: "https://agentnexlify.com/ai-front-desk/dentists",
    },
    hero: {
      h1: "AI Front Desk for Dental Offices",
      subhead:
        "Handles new patient questions, appointment requests, and intake forms before the visit. Your front desk team focuses on patients in the office, not the phone.",
      painPoint:
        "Dental front desks spend a large share of the day answering the same questions by phone.",
    },
    features: [
      {
        icon: "⏰",
        title: "Appointment Reminders",
        description:
          "Automated reminders go out before each appointment. Patients confirm or reschedule by text without calling the office.",
      },
      {
        icon: "📋",
        title: "Online Intake Before the Visit",
        description:
          "New patient forms completed before arrival. Insurance info, medical history, and consent forms ready when the patient walks in.",
      },
      {
        icon: "💬",
        title: "24/7 Patient Chat",
        description:
          "Answers insurance questions, explains procedures, and handles scheduling after hours. Patients get a response instead of leaving a voicemail.",
      },
      {
        icon: "🔄",
        title: "Recall and Reactivation",
        description:
          "Reach out automatically to patients overdue for cleanings or checkups. Your inactive patient list turns into booked appointments.",
      },
      {
        icon: "⭐",
        title: "Review Collection",
        description:
          "After each appointment, the system asks satisfied patients for a Google review. Professional responses to reviews are drafted for your approval.",
      },
      {
        icon: "📧",
        title: "Treatment Follow-Up",
        description:
          "Post-procedure care instructions, follow-up reminders, and check-ins go out automatically based on the treatment performed.",
      },
    ],
    stats: [
      { number: "$19.99", label: "per month to start" },
      { number: "24/7", label: "patient support coverage" },
      { number: "$99.99", label: "per month for the full platform" },
    ],
    faqs: [
      {
        q: "What is an AI front desk for a dental office?",
        a: "It is a chat widget on your website that answers patient questions, handles appointment requests, and collects intake information before the visit. It runs at all hours so new patients get a response even when your office is closed.",
      },
      {
        q: "Is patient data handled securely?",
        a: "AgentNexLiFy stores data in encrypted, SOC 2 compliant infrastructure. The AI handles scheduling, general inquiries, and intake routing. Contact us to discuss your specific compliance requirements before deploying.",
      },
      {
        q: "Can the AI answer insurance questions?",
        a: "Yes. Add your accepted insurance plans and coverage details to the FAQ manager. The AI answers patient questions accurately and directs patients to call for complex verification.",
      },
      {
        q: "What does it cost?",
        a: "The AI Front Desk plan is $19.99 per month. It includes the chat widget, patient lead capture, appointment requests, and FAQ management. The full platform with campaigns, automations, and analytics is $99.99 per month.",
      },
      {
        q: "How long does setup take?",
        a: "Most dental offices are live within an hour. Add your services, hours, insurance info, and common questions. The AI starts answering patient questions the same day.",
      },
      {
        q: "Will this replace my front desk team?",
        a: "No. It handles repetitive tasks, appointment confirmations, basic questions, and review requests so your team can focus on patients in the office.",
      },
    ],
  },
};
