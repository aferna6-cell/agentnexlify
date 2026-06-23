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

  "med-spas": {
    slug: "med-spas",
    meta: {
      title: "AI Front Desk for Med Spas and Aesthetics Clinics | AgentNexLiFy",
      description:
        "An AI front desk that answers treatment questions, books consultations, and captures leads 24/7 for med spas and aesthetics clinics. Starts at $19.99/month.",
      canonical: "https://agentnexlify.com/ai-front-desk/med-spas",
    },
    hero: {
      h1: "AI Front Desk for Med Spas and Aesthetics Clinics",
      subhead:
        "Answers treatment questions, books consultations, and captures leads at any hour. The clinic that responds first wins the booking.",
      painPoint:
        "Visitors comparing clinics for injectables or laser book with whoever answers first.",
    },
    features: [
      {
        icon: "📅",
        title: "Consultation Booking",
        description:
          "Visitors book a consultation directly from the chat. Their treatment interest and timing go to your calendar with the lead details attached.",
      },
      {
        icon: "💬",
        title: "Treatment and Pricing Questions",
        description:
          "The AI explains how Botox is priced per unit, how filler is priced per syringe, and what to expect at a consultation. Accurate answers without overpromising.",
      },
      {
        icon: "⏱",
        title: "Downtime and Safety Guidance",
        description:
          "Visitors ask about recovery before they book. The AI gives realistic downtime ranges per treatment and routes medical screening questions to your provider.",
      },
      {
        icon: "📋",
        title: "Candidacy and Intake",
        description:
          "Collects the visitor's main concern and any relevant conditions before the consultation. Your provider walks in prepared.",
      },
      {
        icon: "💳",
        title: "Financing and Packages",
        description:
          "Surfaces your financing options and package deals to visitors who ask. Moves high-consideration buyers toward a booked consultation instead of a lost tab.",
      },
      {
        icon: "⭐",
        title: "Post-Treatment Review Requests",
        description:
          "After each appointment, an automated message asks satisfied clients for a Google review. Builds your rating without manual follow-up.",
      },
    ],
    stats: [
      { number: "$19.99", label: "per month to start" },
      { number: "24/7", label: "coverage with no extra staff" },
      { number: "$99.99", label: "per month for the full platform" },
    ],
    faqs: [
      {
        q: "What is an AI front desk for a med spa?",
        a: "It is a chat widget on your website that answers visitor questions about treatments, books consultations, and captures lead details at any hour. Visitors researching injectables or laser compare a few clinics before booking, so the clinic that answers fast wins.",
      },
      {
        q: "Can it answer pricing questions for Botox or filler?",
        a: "Yes. The AI explains that Botox is priced per unit and filler is priced per syringe, gives a starting range, and books a consultation where your provider confirms the final plan and cost. It never quotes a fixed total before a provider sees the client.",
      },
      {
        q: "How does it handle candidacy and medical questions?",
        a: "The AI collects the visitor's main concern and flags any conditions or medications they mention. It routes anything medical to your provider rather than answering it directly, which keeps the clinic accurate and the client safe.",
      },
      {
        q: "What does it cost?",
        a: "The AI Front Desk plan is $19.99 per month. It includes the chat widget, lead capture, consultation booking, and FAQ management. The full platform with marketing automations, email and SMS campaigns, and analytics is $99.99 per month.",
      },
      {
        q: "How long does setup take?",
        a: "Most med spas are live within an hour. Add your treatment menu, pricing ranges, and consultation process. The AI starts answering visitor questions the same day.",
      },
      {
        q: "Does it handle downtime and safety questions?",
        a: "Yes. You add the typical downtime for each treatment during setup and the AI gives visitors accurate expectations. For anything that needs a clinical answer, it routes them to book a consultation rather than guessing.",
      },
    ],
  },

  "auto-repair": {
    slug: "auto-repair",
    meta: {
      title: "AI Front Desk for Auto Repair Shops | AgentNexLiFy",
      description:
        "An AI front desk that answers customer questions, qualifies repair jobs, and books drop-offs 24/7 for auto repair shops. Starts at $19.99/month.",
      canonical: "https://agentnexlify.com/ai-front-desk/auto-repair",
    },
    hero: {
      h1: "AI Front Desk for Auto Repair Shops",
      subhead:
        "Answers questions, qualifies the job, and books the car while you are under a hood. Drivers with a problem shop two or three shops and go with whoever responds first.",
      painPoint:
        "Drivers with a warning light or a noise message multiple shops and book with whoever responds first.",
    },
    features: [
      {
        icon: "🔧",
        title: "Job Qualification",
        description:
          "The AI asks for the vehicle year, make, model, and the symptom. It flags urgent issues like a flashing check engine light or brake problems and routes them for faster scheduling.",
      },
      {
        icon: "📆",
        title: "Appointment and Drop-Off Booking",
        description:
          "Drivers pick an available drop-off or appointment slot directly from the chat. The booking lands on your calendar with the vehicle details and the job description attached.",
      },
      {
        icon: "💰",
        title: "Pricing and Estimate Questions",
        description:
          "The AI gives typical ranges for common jobs like oil changes or brake pads and explains that a final price comes after a diagnostic. Sets expectations without overpromising.",
      },
      {
        icon: "🚗",
        title: "Vehicle Fit Check",
        description:
          "Before booking, the AI confirms you service the customer's make and model. No wasted trips for vehicles outside your scope.",
      },
      {
        icon: "🔔",
        title: "Towing and Urgency Routing",
        description:
          "Drivers with a car that will not start get a towing path and faster scheduling. Urgent safety issues like brake grinding are flagged immediately.",
      },
      {
        icon: "⭐",
        title: "Post-Job Review Requests",
        description:
          "After each completed job, the system asks the customer for a Google review. Positive reviews build credibility in your service area.",
      },
    ],
    stats: [
      { number: "$19.99", label: "per month to start" },
      { number: "24/7", label: "lead capture with no extra staff" },
      { number: "$99.99", label: "per month for the full platform" },
    ],
    faqs: [
      {
        q: "What is an AI front desk for an auto repair shop?",
        a: "It is a chat widget on your website that answers driver questions, collects the vehicle details and job description, and books a drop-off or appointment. It runs while you are on a job so no service request goes unanswered.",
      },
      {
        q: "Can it handle urgent issues like a car that will not start?",
        a: "Yes. Add urgency keywords and the AI flags those leads immediately and routes them to a faster scheduling path or sends you an alert. It can also explain towing options to drivers with an undrivable car.",
      },
      {
        q: "How does it handle pricing questions?",
        a: "The AI gives typical ranges for common jobs like oil changes and brake pads. For unknown problems, it explains that a diagnostic confirms the real number and books the car in. It never quotes a final repair cost before a tech sees the vehicle.",
      },
      {
        q: "What does it cost?",
        a: "The AI Front Desk plan is $19.99 per month. It includes the chat widget, lead capture, appointment booking, and FAQ management. The full platform with marketing campaigns, automations, and analytics is $99.99 per month.",
      },
      {
        q: "Does it confirm whether you service a specific vehicle?",
        a: "Yes. Set the makes and models you service during setup. The AI confirms fit before booking so drivers do not show up with a vehicle you do not work on.",
      },
      {
        q: "How does it integrate with my existing workflow?",
        a: "AgentNexLiFy syncs with Google Calendar. Bookings land on your calendar with the vehicle details and job description. Outbound webhooks connect to Zapier and 5,000 plus apps so lead data flows to whatever you use to manage jobs.",
      },
    ],
  },

  "real-estate": {
    slug: "real-estate",
    meta: {
      title: "AI Front Desk for Real Estate and Property Management | AgentNexLiFy",
      description:
        "An AI front desk that schedules showings, handles maintenance requests, and captures leads 24/7 for real estate agents and property managers. Starts at $19.99/month.",
      canonical: "https://agentnexlify.com/ai-front-desk/real-estate",
    },
    hero: {
      h1: "AI Front Desk for Real Estate and Property Management",
      subhead:
        "Books showings, handles tenant requests, and captures buyer and renter leads at any hour. Two different visitors, both answered immediately.",
      painPoint:
        "Prospective renters and buyers move on to the next listing if no one answers their question quickly.",
    },
    features: [
      {
        icon: "🏠",
        title: "Showing and Tour Booking",
        description:
          "Prospective renters and buyers book showings directly through the chat with a property and a time. The booking lands on your calendar with the lead's contact details and what they are looking for.",
      },
      {
        icon: "📋",
        title: "Application and Screening Questions",
        description:
          "The AI explains the application process, the documents needed, and the screening criteria for a specific property. Qualified leads start the process faster.",
      },
      {
        icon: "🔔",
        title: "Maintenance Request Routing",
        description:
          "Current residents submit maintenance requests through the chat. Urgent issues like a major leak, no heat, or a lockout get flagged for the emergency maintenance line.",
      },
      {
        icon: "💬",
        title: "Availability Checks",
        description:
          "Visitors ask whether a unit is still available. The AI confirms against your current listings and books a showing or captures the lead for a similar property.",
      },
      {
        icon: "🏢",
        title: "Owner and Investor Inquiries",
        description:
          "Property owners asking about management services get routed to a consultation booking. Covers tenant screening, rent collection, and maintenance coordination questions.",
      },
      {
        icon: "📧",
        title: "Follow-Up and Review Requests",
        description:
          "After a closing or a lease signing, the system sends a follow-up and review request automatically. Builds your reputation without manual outreach.",
      },
    ],
    stats: [
      { number: "$19.99", label: "per month to start" },
      { number: "24/7", label: "lead capture and tenant support" },
      { number: "$99.99", label: "per month for the full platform" },
    ],
    faqs: [
      {
        q: "What is an AI front desk for real estate and property management?",
        a: "It is a chat widget on your website that handles two types of visitors: prospective renters or buyers who want to see a property and apply, and current residents who need to report a problem or ask about rent. Both get answered immediately.",
      },
      {
        q: "Can it book property showings?",
        a: "Yes. A visitor picks the property and a time and the booking goes to your calendar with their contact details and what they are looking for. Some properties can also be set up for self-guided or virtual tour options.",
      },
      {
        q: "How does it handle maintenance requests from current tenants?",
        a: "Residents submit a request through the chat and it gets routed to the right team. Urgent issues like a major leak, no heat, or a lockout are flagged for the emergency maintenance line. Life-safety issues are directed to emergency services first.",
      },
      {
        q: "What does it cost?",
        a: "The AI Front Desk plan is $19.99 per month. It includes the chat widget, showing bookings, lead capture, maintenance request routing, and FAQ management. The full platform with marketing campaigns, automations, and analytics is $99.99 per month.",
      },
      {
        q: "Can it handle both renters and property owners?",
        a: "Yes. The AI routes each visitor based on their intent. A renter or buyer goes to a showing or application. A property owner asking about management services gets routed to a consultation booking that covers screening, rent collection, and maintenance.",
      },
      {
        q: "How does it handle pricing and availability questions?",
        a: "The AI confirms availability against your current listings and points visitors to the listing for the exact rent or sale price. It does not quote a specific price as a fact across many properties, which keeps your responses accurate as listings change.",
      },
    ],
  },
};
