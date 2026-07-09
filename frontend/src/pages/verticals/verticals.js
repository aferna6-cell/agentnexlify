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
      {
        q: "How does it answer pricing questions for color or balayage?",
        a: "You set your price ranges during setup. The AI explains that color pricing depends on hair length, stylist level, and how many sessions the look needs, gives your range, and offers to book a consultation for an exact quote. It never states a fixed price for a service that needs a consultation first.",
      },
      {
        q: "Can it handle walk-in and same-day questions?",
        a: "Yes. When a visitor asks whether they can get in today, the AI explains that shorter services are easier to fit on short notice and shows the soonest opening for the service they want. Popular slots like Friday afternoon and Saturday fill first, so turning walk-in questions into bookings keeps your calendar predictable.",
      },
      {
        q: "How does it reduce no-shows and late cancellations?",
        a: "You set your cancellation window, often 24 to 48 hours, and any late fee during setup. The AI explains the policy when clients book, and automated reminders before each appointment let clients confirm or reschedule by text instead of simply not showing up.",
      },
    ],
    related: [
      { slug: "med-spas", label: "Med Spas" },
      { slug: "fitness", label: "Fitness Studios" },
      { slug: "cleaning-services", label: "Cleaning Services" },
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
      {
        q: "How does it answer pricing questions without committing me to a number?",
        a: "The AI explains your service-call or diagnostic fee, notes when it is applied toward the repair, and tells the customer the technician quotes the job on site. For big jobs like a water heater or full system replacement, it books an estimate visit instead of guessing a price.",
      },
      {
        q: "Can it check whether a customer is in my service area?",
        a: "Yes. Set your coverage by towns or radius during setup. The AI asks for the customer's city or zip code before booking and only schedules jobs inside your area, so your techs stop driving to addresses you never should have booked.",
      },
      {
        q: "What does it do when someone reports a gas smell?",
        a: "Safety first. The AI tells the visitor to leave the building, avoid switches and flames, and call the gas utility or emergency services from outside. Once the customer is safe, it captures the lead so you can schedule the inspection and repair.",
      },
    ],
    related: [
      { slug: "roofing", label: "Roofing Contractors" },
      { slug: "auto-repair", label: "Auto Repair Shops" },
      { slug: "cleaning-services", label: "Cleaning Services" },
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
      {
        q: "How does it handle patients with a toothache who need to be seen today?",
        a: "Severe pain, swelling, and a broken or knocked-out tooth are flagged as urgent. The AI routes those patients toward your soonest available slot and notes the symptoms for the dentist. Swelling that affects breathing or swallowing gets directed to emergency medical care instead of a booking.",
      },
      {
        q: "What does it tell patients who do not have insurance?",
        a: "You add your self-pay pricing and any membership or discount plan during setup. The AI explains those options and books the visit, so uninsured patients become appointments instead of hang-ups.",
      },
    ],
    related: [
      { slug: "med-spas", label: "Med Spas" },
      { slug: "veterinary", label: "Veterinary Clinics" },
      { slug: "fitness", label: "Fitness Studios" },
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
      {
        q: "Can it answer how long Botox or filler results last?",
        a: "Yes, with the general guidance you approve during setup. Botox results commonly last around three to four months, and filler often lasts from several months to over a year depending on the product and the area. For a person-specific answer, it books the consultation.",
      },
      {
        q: "Does it surface my packages and memberships?",
        a: "Yes. Add your memberships, treatment packages, and financing options during setup and the AI brings them up when visitors ask about cost. Bundled pricing on treatments like laser hair removal moves a price-checking visitor toward a booked consultation.",
      },
    ],
    related: [
      { slug: "salons", label: "Salons" },
      { slug: "dentists", label: "Dental Offices" },
      { slug: "fitness", label: "Fitness Studios" },
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
      {
        q: "What does it say when a driver asks about a check engine light?",
        a: "The AI explains that the light can mean anything from a loose gas cap to an engine issue, and that a diagnostic scan reads the actual code. If the driver says the light is flashing or the car runs rough, it treats the request as urgent and books the car in sooner.",
      },
      {
        q: "Can it answer loaner car and shuttle questions?",
        a: "Yes. Set what you offer during setup, whether that is loaners, a shuttle, or neither, and the AI gives drivers a straight answer. For longer repairs this question decides whether the customer books, so answering it up front wins jobs.",
      },
    ],
    related: [
      { slug: "plumbers", label: "Plumbers and HVAC" },
      { slug: "roofing", label: "Roofing Contractors" },
      { slug: "cleaning-services", label: "Cleaning Services" },
    ],
  },

  "law-firms": {
    slug: "law-firms",
    meta: {
      title: "AI Front Desk for Law Firms | AgentNexLiFy",
      description:
        "An AI front desk that answers potential client questions, books consultations, and handles intake 24/7 for law firms and solo practitioners. Starts at $19.99/month.",
      canonical: "https://agentnexlify.com/ai-front-desk/law-firms",
    },
    hero: {
      h1: "AI Front Desk for Law Firms",
      subhead:
        "Answers prospective client questions, books consultations, and collects intake information at any hour. The firm that responds first gets the case.",
      painPoint:
        "People with a legal problem call two or three firms and hire whoever calls back first.",
    },
    features: [
      {
        icon: "📅",
        title: "Consultation Booking",
        description:
          "Prospective clients book a consultation directly through the chat. Their matter type, timeline, and contact details land on your calendar before the call.",
      },
      {
        icon: "📋",
        title: "Intake Before the Call",
        description:
          "The AI collects the facts of the matter, the opposing party, and relevant dates before the consultation. Your attorney walks in prepared instead of starting from scratch.",
      },
      {
        icon: "💬",
        title: "24/7 Practice Area Questions",
        description:
          "Prospective clients ask whether you handle their type of case at any hour. The AI answers based on your practice areas and books a consultation for qualifying matters.",
      },
      {
        icon: "🔔",
        title: "Consultation Reminders",
        description:
          "Automated reminders go out before each scheduled consultation. Clients confirm or reschedule by text, cutting no-shows without your staff making calls.",
      },
      {
        icon: "⚖️",
        title: "Conflict and Eligibility Screening",
        description:
          "Add basic screening questions to the intake flow. The AI collects the opposing party name and key facts so you can check for conflicts before the meeting.",
      },
      {
        icon: "⭐",
        title: "Review Requests After Matters Close",
        description:
          "After a matter closes, the system sends a review request automatically. Positive Google reviews build credibility for future clients searching for counsel.",
      },
    ],
    stats: [
      { number: "$19.99", label: "per month to start" },
      { number: "24/7", label: "intake and consultation booking" },
      { number: "$99.99", label: "per month for the full platform" },
    ],
    faqs: [
      {
        q: "What is an AI front desk for a law firm?",
        a: "It is a chat widget on your website that answers prospective client questions, collects intake information, and books consultations at any hour. People with a legal matter contact two or three firms and hire whoever responds, so faster intake wins more cases.",
      },
      {
        q: "Can it screen for case type and conflicts?",
        a: "Yes. You define your practice areas and the AI only routes qualifying matters to a consultation. You can add intake questions that collect the opposing party name and key facts so you can run a conflict check before the meeting.",
      },
      {
        q: "Does the AI give legal advice?",
        a: "No. The AI answers questions about your firm, practice areas, and consultation process. It does not provide legal opinions or advice. All substantive legal questions are directed to a consultation with your attorney.",
      },
      {
        q: "What does it cost?",
        a: "The AI Front Desk plan is $19.99 per month. It includes the chat widget, intake collection, consultation booking, and FAQ management. The full platform with marketing automations, email and SMS campaigns, and analytics is $99.99 per month.",
      },
      {
        q: "How long does setup take?",
        a: "Most firms are live within an hour. Add your practice areas, consultation process, and common questions. The AI starts answering prospective client questions the same day.",
      },
      {
        q: "Will this work for a solo practitioner?",
        a: "Yes. Solo practitioners benefit most because there is no receptionist to answer calls after hours. The AI handles intake, books consultations, and sends reminders so you can focus on client work during the day.",
      },
      {
        q: "How does it answer fee questions?",
        a: "The AI explains how your firm bills by case type, flat fee, hourly, or contingency, without quoting a number for a matter no attorney has reviewed. Contingency questions get a plain explanation that the fee is a percentage of the recovery with nothing up front, when that applies to your practice.",
      },
      {
        q: "What does it say when someone asks about filing deadlines?",
        a: "It never states a deadline as fact. It explains that legal deadlines vary by case type and location, that some are strict, and that speaking with an attorney soon is the safe move. That creates urgency toward a booked consultation without giving advice.",
      },
    ],
    related: [
      { slug: "real-estate", label: "Real Estate" },
      { slug: "dentists", label: "Dental Offices" },
      { slug: "veterinary", label: "Veterinary Clinics" },
    ],
  },

  restaurants: {
    slug: "restaurants",
    meta: {
      title: "AI Front Desk for Restaurants | AgentNexLiFy",
      description:
        "An AI front desk that answers hours and menu questions, takes reservations, and handles takeout inquiries 24/7 for restaurants. Starts at $19.99/month.",
      canonical: "https://agentnexlify.com/ai-front-desk/restaurants",
    },
    hero: {
      h1: "AI Front Desk for Restaurants",
      subhead:
        "Answers hours and menu questions, books reservations, and handles takeout inquiries around the clock. Your dining room stays full even when the host is busy.",
      painPoint:
        "Guests who cannot reach a restaurant quickly move on to the next option on the list.",
    },
    features: [
      {
        icon: "🍽️",
        title: "Reservation Booking",
        description:
          "Guests pick a date, time, and party size directly through the chat. The booking lands on your reservation system with the guest's contact details and any special requests.",
      },
      {
        icon: "📋",
        title: "Menu and Hours Questions",
        description:
          "The AI answers questions about your menu, daily specials, hours, location, and parking. Guests get accurate answers without calling during the dinner rush.",
      },
      {
        icon: "📦",
        title: "Takeout and Delivery Information",
        description:
          "Guests ask about takeout ordering, delivery availability, and pickup times. The AI shares your ordering options and directs guests to the right channel.",
      },
      {
        icon: "🎂",
        title: "Private Events and Group Inquiries",
        description:
          "Guests asking about private dining, buyouts, or large parties get routed to a booking request. Collect the date, party size, and event type before your events coordinator follows up.",
      },
      {
        icon: "🔔",
        title: "Reservation Reminders",
        description:
          "Automated reminders go out before each reservation. Guests confirm or cancel by text, giving your team time to fill the table from a waitlist.",
      },
      {
        icon: "⭐",
        title: "Post-Visit Review Requests",
        description:
          "After each visit, the system sends a review request automatically. Positive Google and Yelp reviews help new guests choose your restaurant over the competition.",
      },
    ],
    stats: [
      { number: "$19.99", label: "per month to start" },
      { number: "24/7", label: "reservation and inquiry coverage" },
      { number: "$99.99", label: "per month for the full platform" },
    ],
    faqs: [
      {
        q: "What is an AI front desk for a restaurant?",
        a: "It is a chat widget on your website that answers guest questions about your hours, menu, and location, books reservations, and handles takeout inquiries at any hour. Guests who cannot reach a restaurant move on, so faster responses keep tables filled.",
      },
      {
        q: "Can it take reservations directly?",
        a: "Yes. Guests pick a date, time, and party size from the chat. The booking goes to your calendar or reservation system with the guest's contact details and any notes. You manage the final seating from your existing system.",
      },
      {
        q: "Does it handle takeout and delivery questions?",
        a: "Yes. The AI answers questions about your takeout and delivery options, hours, and ordering process. It can direct guests to your online ordering platform or phone number for placing orders.",
      },
      {
        q: "What does it cost?",
        a: "The AI Front Desk plan is $19.99 per month. It includes the chat widget, reservation booking, lead capture, and FAQ management. The full platform with marketing automations, email and SMS campaigns, and analytics is $99.99 per month.",
      },
      {
        q: "Can it handle dietary restriction and allergy questions?",
        a: "Yes. Add your menu details and common allergy information to the FAQ manager. The AI answers questions accurately and directs guests with serious allergies to call the kitchen directly for confirmation.",
      },
      {
        q: "How long does setup take?",
        a: "Most restaurants are live within an hour. Add your hours, menu highlights, reservation process, and common questions. The AI starts answering guest questions the same day.",
      },
      {
        q: "How does it handle catering and private event inquiries?",
        a: "Catering and private dining are the biggest tickets a chat can capture. The AI collects the date, headcount, event type, and contact details, then passes the inquiry to your events contact for follow-up. Nothing gets lost in a voicemail during service.",
      },
      {
        q: "Can it answer walk-in and wait time questions?",
        a: "Yes. The AI explains your walk-in policy, notes that weekend dinners are busiest, and offers a reservation where you take them. Guests who know what to expect show up instead of picking the next place on the list.",
      },
    ],
    related: [
      { slug: "salons", label: "Salons" },
      { slug: "fitness", label: "Fitness Studios" },
      { slug: "cleaning-services", label: "Cleaning Services" },
    ],
  },

  fitness: {
    slug: "fitness",
    meta: {
      title: "AI Front Desk for Gyms and Fitness Studios | AgentNexLiFy",
      description:
        "An AI front desk that answers membership questions, books free trials, and handles class inquiries 24/7 for gyms and fitness studios. Starts at $19.99/month.",
      canonical: "https://agentnexlify.com/ai-front-desk/fitness",
    },
    hero: {
      h1: "AI Front Desk for Gyms and Fitness Studios",
      subhead:
        "Answers membership questions, books free trials, and handles class schedule inquiries at any hour. Prospective members who do not get a quick answer sign up somewhere else.",
      painPoint:
        "Prospective members research two or three gyms and sign up with whoever responds to their questions first.",
    },
    features: [
      {
        icon: "🏋️",
        title: "Free Trial and Tour Booking",
        description:
          "Prospective members book a free trial class or facility tour directly through the chat. Their contact details and fitness goals land on your schedule before the visit.",
      },
      {
        icon: "💳",
        title: "Membership and Pricing Questions",
        description:
          "The AI explains your membership tiers, pricing, contract terms, and any current promotions. Prospective members get accurate answers without waiting for a sales call.",
      },
      {
        icon: "📅",
        title: "Class Schedule Inquiries",
        description:
          "Members ask about class times, instructors, and availability. The AI answers based on your current schedule and directs members to your booking platform for sign-ups.",
      },
      {
        icon: "🔄",
        title: "Member Retention Follow-Ups",
        description:
          "Reach out automatically to members who have not checked in recently. A simple message inviting them back converts dormant members before they cancel.",
      },
      {
        icon: "🎯",
        title: "Goal and Program Matching",
        description:
          "Prospective members describe their fitness goals and the AI recommends the right membership tier or class type. Matching people to the right program from the start improves retention.",
      },
      {
        icon: "⭐",
        title: "Review Requests",
        description:
          "After a member milestone or a positive check-in, the system sends a review request automatically. Positive reviews help new prospects choose your gym over the competition.",
      },
    ],
    stats: [
      { number: "$19.99", label: "per month to start" },
      { number: "24/7", label: "membership and class inquiry coverage" },
      { number: "$99.99", label: "per month for the full platform" },
    ],
    faqs: [
      {
        q: "What is an AI front desk for a gym or fitness studio?",
        a: "It is a chat widget on your website that answers prospective member questions about memberships, pricing, and classes, books free trials or tours, and handles class inquiries at any hour. Prospective members compare a few options and join wherever responds first.",
      },
      {
        q: "Can it book free trials and tours?",
        a: "Yes. Prospective members pick a date and time directly from the chat. The booking lands on your calendar with their contact details and any fitness goals they shared. Your team follows up with a welcome message before the visit.",
      },
      {
        q: "Can it answer questions about class schedules?",
        a: "Yes. Add your current class schedule and the AI answers questions about times, instructors, and formats. For live class availability and sign-ups, it directs members to your booking platform.",
      },
      {
        q: "What does it cost?",
        a: "The AI Front Desk plan is $19.99 per month. It includes the chat widget, trial booking, lead capture, and FAQ management. The full platform with member retention automations, email and SMS campaigns, and analytics is $99.99 per month.",
      },
      {
        q: "How does it help with member retention?",
        a: "The full platform includes automation rules that reach out to members who have not checked in recently with an invitation to come back. Catching dormant members early costs far less than replacing a cancelled membership.",
      },
      {
        q: "How long does setup take?",
        a: "Most gyms and studios are live within an hour. Add your membership options, class schedule, and common questions. The AI starts answering prospective member questions the same day.",
      },
      {
        q: "Can it explain contracts, freezes, and cancellation terms?",
        a: "Yes. Add your plan terms during setup: sign-up fees, month-to-month versus annual pricing, notice windows, and freeze rules for travel or injury. Prospects ask these questions before they commit, and a clear answer in chat removes the hesitation that kills sign-ups.",
      },
      {
        q: "Does it handle drop-in and day pass questions?",
        a: "Yes. The AI shares your drop-in rate or day pass option and reserves the spot. A single visit is the strongest path to a membership, so every drop-in question gets steered toward a booked first session.",
      },
    ],
    related: [
      { slug: "salons", label: "Salons" },
      { slug: "med-spas", label: "Med Spas" },
      { slug: "restaurants", label: "Restaurants" },
    ],
  },

  roofing: {
    slug: "roofing",
    meta: {
      title: "AI Front Desk for Roofing Contractors | AgentNexLiFy",
      description:
        "An AI front desk that answers homeowner questions, qualifies storm damage leads, and books inspections 24/7 for roofing contractors. Starts at $19.99/month.",
      canonical: "https://agentnexlify.com/ai-front-desk/roofing",
    },
    hero: {
      h1: "AI Front Desk for Roofing Contractors",
      subhead:
        "Answers homeowner questions, qualifies storm damage calls, and books inspection appointments around the clock. Every missed call after a storm is a job for a competitor.",
      painPoint:
        "Homeowners with storm damage contact two or three roofers and go with whoever answers first.",
    },
    features: [
      {
        icon: "🏚️",
        title: "Storm Damage Lead Capture",
        description:
          "When a storm passes through your area, the AI captures every homeowner inquiry on your website. It collects the address, the damage description, and the best contact time before you even check your phone.",
      },
      {
        icon: "📋",
        title: "Inspection Booking",
        description:
          "Homeowners pick an available inspection slot directly from the chat. The booking lands on your calendar with the property address, damage type, and contact details attached.",
      },
      {
        icon: "🔍",
        title: "Insurance Claim Questions",
        description:
          "The AI answers questions about the inspection process, what to expect during an insurance claim, and what your company handles. Homeowners get accurate information before the appointment.",
      },
      {
        icon: "⚡",
        title: "Urgency Routing",
        description:
          "Active leaks, interior water damage, or structural concerns get flagged immediately with an alert to your team. Emergency jobs rise to the top of the queue.",
      },
      {
        icon: "💰",
        title: "Estimate Follow-Up",
        description:
          "After an inspection, the system prompts you to send an estimate and follows up with the homeowner automatically. No job goes cold while you are on a roof.",
      },
      {
        icon: "⭐",
        title: "Review Requests After Completion",
        description:
          "After each completed job, the system sends a review request to the homeowner. Positive Google reviews build credibility in your service area for the next storm season.",
      },
    ],
    stats: [
      { number: "$19.99", label: "per month to start" },
      { number: "24/7", label: "lead capture with no extra staff" },
      { number: "$99.99", label: "per month for the full platform" },
    ],
    faqs: [
      {
        q: "What is an AI front desk for a roofing contractor?",
        a: "It is a chat widget on your website that answers homeowner questions, qualifies storm damage and repair leads, and books inspections at any hour. After a major storm, the contractors who respond first win the most jobs.",
      },
      {
        q: "Can it handle emergency calls like an active leak?",
        a: "Yes. Add urgency keywords and the AI flags those leads immediately and sends you an alert. Homeowners with active water intrusion get routed to a faster scheduling path so you can prioritize emergency jobs.",
      },
      {
        q: "How does it handle insurance claim questions?",
        a: "The AI answers questions about the inspection process and what to expect during a claim. It explains what your company handles and routes specific insurance or adjuster questions to your team rather than guessing.",
      },
      {
        q: "What does it cost?",
        a: "The AI Front Desk plan is $19.99 per month. It includes the chat widget, lead capture, inspection booking, and FAQ management. The full platform with marketing campaigns, estimate follow-up automations, and analytics is $99.99 per month.",
      },
      {
        q: "How long does setup take?",
        a: "Most roofing contractors are live within an hour. Add your service area, inspection process, and common questions about storm damage and insurance claims. The AI starts capturing leads the same day.",
      },
      {
        q: "Can it qualify leads by roof type or damage extent?",
        a: "Yes. Add qualifying questions to the intake flow. The AI can ask about the roof material, approximate age, and the type of damage before booking an inspection, so your team arrives prepared.",
      },
      {
        q: "Can it explain repair versus replacement to homeowners?",
        a: "The AI walks through the factors: roof age, how widespread the damage is, and how many layers are already up there. It explains that an inspector makes the call after seeing the roof and books the inspection rather than promising an answer sight unseen.",
      },
      {
        q: "Does it answer warranty and financing questions?",
        a: "Yes. It explains the difference between your workmanship warranty on labor and the manufacturer warranty on materials, using the terms you set. Homeowners who ask about financing get your options noted on the lead so your estimator can walk them through it.",
      },
    ],
    related: [
      { slug: "plumbers", label: "Plumbers and HVAC" },
      { slug: "auto-repair", label: "Auto Repair Shops" },
      { slug: "real-estate", label: "Real Estate" },
    ],
  },

  "cleaning-services": {
    slug: "cleaning-services",
    meta: {
      title: "AI Front Desk for Cleaning Services | AgentNexLiFy",
      description:
        "An AI front desk that answers questions, books recurring and deep-clean appointments, and captures leads 24/7 for residential and commercial cleaning companies. Starts at $19.99/month.",
      canonical: "https://agentnexlify.com/ai-front-desk/cleaning-services",
    },
    hero: {
      h1: "AI Front Desk for Cleaning Services",
      subhead:
        "Answers questions, books recurring cleanings and one-time deep cleans, and captures leads at any hour. Clients searching for a cleaner book with whoever responds first.",
      painPoint:
        "Clients searching for a cleaning service message two or three companies and hire whoever replies fastest.",
    },
    features: [
      {
        icon: "📅",
        title: "Recurring Booking Setup",
        description:
          "Clients choose weekly, biweekly, or monthly schedules directly through the chat. The booking lands on your calendar with the frequency, address, and any special instructions.",
      },
      {
        icon: "🧹",
        title: "Deep Clean and Move-In Quotes",
        description:
          "The AI collects the home size, number of bedrooms, and any specific requests. You get a lead with the details you need to send an accurate quote without a phone call.",
      },
      {
        icon: "💬",
        title: "Service and Pricing Questions",
        description:
          "The AI explains your service types, what is included in a standard clean versus a deep clean, and your pricing structure. Clients get accurate answers immediately.",
      },
      {
        icon: "🔔",
        title: "Appointment Reminders",
        description:
          "Automated reminders go out before each scheduled cleaning. Clients confirm or reschedule by text, reducing same-day cancellations for your crew.",
      },
      {
        icon: "🏢",
        title: "Commercial Cleaning Inquiries",
        description:
          "Office managers and property managers asking about commercial contracts get routed to a quote request. Collect the square footage, frequency, and scope before your follow-up call.",
      },
      {
        icon: "⭐",
        title: "Review Requests",
        description:
          "After each completed cleaning, the system sends a review request automatically. Positive reviews attract new clients searching for cleaners in your area.",
      },
    ],
    stats: [
      { number: "$19.99", label: "per month to start" },
      { number: "24/7", label: "booking and inquiry coverage" },
      { number: "$99.99", label: "per month for the full platform" },
    ],
    faqs: [
      {
        q: "What is an AI front desk for a cleaning company?",
        a: "It is a chat widget on your website that answers visitor questions about your services, books recurring or one-time cleanings, and captures lead details at any hour. Clients comparing cleaning companies go with whoever responds first, so faster replies win more jobs.",
      },
      {
        q: "Can it set up recurring cleaning schedules?",
        a: "Yes. Clients pick their preferred frequency, the address, and a time window directly through the chat. The booking goes to your calendar with the details attached. Your team manages the ongoing schedule from the dashboard.",
      },
      {
        q: "How does it handle deep clean and move-in pricing questions?",
        a: "The AI collects the home size, number of rooms, and any special requests, then explains that your team will confirm the final price after reviewing the details. It never quotes a fixed price for a job it has not seen.",
      },
      {
        q: "What does it cost?",
        a: "The AI Front Desk plan is $19.99 per month. It includes the chat widget, booking requests, lead capture, and FAQ management. The full platform with recurring client automations, email and SMS campaigns, and analytics is $99.99 per month.",
      },
      {
        q: "Does it handle commercial cleaning inquiries differently from residential?",
        a: "Yes. Commercial visitors asking about office or property cleaning get routed to a quote request flow that collects the square footage, cleaning frequency, and scope. Your sales team follows up with a commercial proposal.",
      },
      {
        q: "How long does setup take?",
        a: "Most cleaning companies are live within an hour. Add your service types, pricing ranges, and coverage area. The AI starts answering client questions and capturing booking requests the same day.",
      },
      {
        q: "Can it explain the difference between a standard clean and a deep clean?",
        a: "Yes. The AI explains that a standard clean covers regular upkeep while a deep clean reaches buildup like baseboards and inside appliances, and that new recurring clients usually start with a deep clean. That sets the right price expectation before your quote goes out.",
      },
      {
        q: "How does it answer clients who ask if they need to be home?",
        a: "The AI explains the access options you support, such as a key, a lockbox, or a door code, and records the client's preference on the booking. Removing the need to be home removes the most common booking objection for working clients.",
      },
    ],
    related: [
      { slug: "plumbers", label: "Plumbers and HVAC" },
      { slug: "real-estate", label: "Real Estate" },
      { slug: "salons", label: "Salons" },
    ],
  },

  veterinary: {
    slug: "veterinary",
    meta: {
      title: "AI Front Desk for Veterinary Clinics | AgentNexLiFy",
      description:
        "An AI front desk that handles pet owner questions, books appointments and wellness visits, and routes emergencies 24/7 for veterinary clinics. Starts at $19.99/month.",
      canonical: "https://agentnexlify.com/ai-front-desk/veterinary",
    },
    hero: {
      h1: "AI Front Desk for Veterinary Clinics",
      subhead:
        "Handles pet owner questions, books routine appointments and wellness visits, and routes emergencies to the right line at any hour. Pet owners with a sick animal cannot wait on hold.",
      painPoint:
        "Pet owners with a sick or injured animal contact the first clinic that answers and book on the spot.",
    },
    features: [
      {
        icon: "🐾",
        title: "Appointment and Wellness Booking",
        description:
          "Pet owners book routine checkups, vaccinations, and wellness visits directly through the chat. The booking lands on your schedule with the pet's species, age, and reason for the visit.",
      },
      {
        icon: "🚨",
        title: "Emergency Triage Routing",
        description:
          "Owners describing symptoms like labored breathing, trauma, or seizures get routed to your emergency line or the nearest emergency clinic immediately. Life-safety concerns are never handled with wait times.",
      },
      {
        icon: "💬",
        title: "24/7 Pet Owner Questions",
        description:
          "The AI answers questions about your services, accepted species, vaccine schedules, and appointment availability at any hour. Owners get a response instead of a voicemail during busy clinic hours.",
      },
      {
        icon: "📋",
        title: "New Pet Intake",
        description:
          "New clients share their pet's breed, age, vaccination history, and any known conditions before the first visit. Your vet team walks in with context instead of starting from scratch.",
      },
      {
        icon: "🔔",
        title: "Appointment Reminders and Vaccine Recalls",
        description:
          "Automated reminders go out before each appointment. The full platform adds proactive recall messages for pets overdue for vaccines or annual wellness exams.",
      },
      {
        icon: "⭐",
        title: "Post-Visit Review Requests",
        description:
          "After each appointment, the system sends a review request to the pet owner. Positive Google reviews help new pet owners in your area choose your clinic.",
      },
    ],
    stats: [
      { number: "$19.99", label: "per month to start" },
      { number: "24/7", label: "pet owner support coverage" },
      { number: "$99.99", label: "per month for the full platform" },
    ],
    faqs: [
      {
        q: "What is an AI front desk for a veterinary clinic?",
        a: "It is a chat widget on your website that answers pet owner questions, books routine and wellness appointments, and routes emergency situations to the right line at any hour. Pet owners with an urgent problem call the first clinic that picks up.",
      },
      {
        q: "How does it handle medical emergencies?",
        a: "The AI recognizes descriptions of life-threatening symptoms like labored breathing, trauma, or collapse and immediately directs the owner to your emergency line or the nearest 24-hour emergency veterinary clinic. It does not attempt to triage emergencies itself.",
      },
      {
        q: "Can it answer questions about vaccine schedules and services?",
        a: "Yes. Add your vaccine protocols, accepted species, and service list during setup. The AI answers questions about core and non-core vaccines, spay and neuter services, and what to bring to the first appointment.",
      },
      {
        q: "What does it cost?",
        a: "The AI Front Desk plan is $19.99 per month. It includes the chat widget, appointment booking, lead capture, and FAQ management. The full platform with vaccine recall automations, email and SMS campaigns, and analytics is $99.99 per month.",
      },
      {
        q: "Does it collect new patient information before the first visit?",
        a: "Yes. New clients can share the pet's species, breed, age, weight, vaccination history, and any known conditions through the intake flow. Your team reviews the information before the appointment.",
      },
      {
        q: "Will this work for a multi-doctor clinic?",
        a: "Yes. The AI captures the appointment request and the reason for the visit. Your front desk team assigns the doctor from the dashboard. Doctor-specific booking is on the roadmap.",
      },
      {
        q: "Can it handle prescription refill requests?",
        a: "Yes. The AI collects the pet's name and the medication or food needed and passes the refill request to your team, who confirm whether a recent exam is required before filling it. Refill requests stop tying up your phone line.",
      },
      {
        q: "How does it answer pet insurance questions?",
        a: "It explains that pet insurance usually works as reimbursement, where the owner pays the clinic and files with their insurer, and that coverage depends on the specific policy. It notes on the lead that the client has insurance so your team can prepare the claim paperwork.",
      },
    ],
    related: [
      { slug: "dentists", label: "Dental Offices" },
      { slug: "med-spas", label: "Med Spas" },
      { slug: "fitness", label: "Fitness Studios" },
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
      {
        q: "Can it explain application and screening requirements?",
        a: "Yes. Add your criteria per property during setup and the AI shares them before someone applies. Many companies ask for income around two to three times the rent plus a credit and rental-history check, and stating that up front cuts the unqualified applications your team has to process.",
      },
      {
        q: "Can it answer rent payment and lease questions from residents?",
        a: "Yes. The AI points residents to the payment portal and to their lease for due dates, grace periods, and late fees, and routes deposit-return and early move-out questions to the right contact. Your team stops fielding the same lease questions by phone.",
      },
    ],
    related: [
      { slug: "law-firms", label: "Law Firms" },
      { slug: "cleaning-services", label: "Cleaning Services" },
      { slug: "roofing", label: "Roofing Contractors" },
    ],
  },
};
