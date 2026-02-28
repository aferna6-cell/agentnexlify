/**
 * Demo Configuration — reads URL parameters to customize the demo per prospect.
 *
 * URL params:
 *   ?biz=       Business name (default: Smith's Home Solutions)
 *   ?industry=  Industry preset (default: plumbing)
 *   ?city=      City name (default: Austin)
 *
 * Example: ?biz=Austin+Dental+Group&industry=dental&city=Austin
 */

const params = new URLSearchParams(window.location.search);

// ── Industry Presets ──

const INDUSTRY_PRESETS = {
  plumbing: {
    services: ['Plumbing', 'HVAC', 'Electrical', 'Kitchen/Bath Remodeling'],
    hours: 'Mon-Fri 7am-6pm, Sat 8am-2pm, Emergency service 24/7',
    botName: 'AI Assistant',
    serviceKeywords: {
      plumbing: 'Plumbing', hvac: 'HVAC', heating: 'HVAC', cooling: 'HVAC',
      'air conditioning': 'HVAC', electrical: 'Electrical', kitchen: 'Kitchen Remodel',
      bath: 'Bath Remodel', remodel: 'Remodeling',
    },
    dashboardLabels: {
      leads: 'New Leads Today',
      booked: 'Appointments Booked',
    },
    quickQuestions: [
      'What are your hours?',
      'Do you offer emergency service?',
      'What areas do you serve?',
      'How do I schedule an appointment?',
      'Do you offer financing?',
      "What's your warranty policy?",
    ],
    faqKnowledge: {
      hours: {
        keywords: ['hours', 'open', 'close', 'time', 'schedule', 'when'],
        response: "We're open Monday through Friday 7am-6pm, Saturday 8am-2pm. For emergencies, we offer 24/7 service.",
      },
      services: {
        keywords: ['services', 'offer', 'do you do', 'plumbing', 'hvac', 'electrical'],
        response: 'We offer Plumbing, HVAC (heating & cooling), Electrical work, and Kitchen/Bath Remodeling. What type of project do you have in mind?',
      },
      emergency: {
        keywords: ['emergency', 'urgent', 'asap', 'leak', 'broken', 'flood'],
        response: 'Yes! We offer 24/7 emergency service for plumbing, HVAC, and electrical issues. I can have someone call you right back.',
      },
      area: {
        keywords: ['area', 'serve', 'location', 'where', 'city'],
        response: null, // filled dynamically with city
      },
      appointment: {
        keywords: ['appointment', 'book', 'schedule', 'available', 'come out'],
        response: "I'd love to help you schedule! Can I get your name and phone number to book you in?",
      },
      financing: {
        keywords: ['financing', 'finance', 'payment', 'pay', 'credit'],
        response: 'We offer financing options on larger projects. Want me to connect you with our team for details?',
      },
      warranty: {
        keywords: ['warranty', 'guarantee', 'coverage', 'insured'],
        response: 'All our work comes with a labor warranty and we pass through manufacturer warranties on all parts and equipment.',
      },
    },
  },

  dental: {
    services: ['Checkups', 'Cleanings', 'Implants', 'Whitening', 'Invisalign'],
    hours: 'Mon-Fri 8am-5pm',
    botName: 'Patient Coordinator',
    serviceKeywords: {
      checkup: 'Checkup', cleaning: 'Cleaning', implant: 'Implants',
      whitening: 'Whitening', invisalign: 'Invisalign', crown: 'Crowns',
      filling: 'Fillings', 'root canal': 'Root Canal', extraction: 'Extraction',
    },
    dashboardLabels: {
      leads: 'New Patients Today',
      booked: 'Appointments Booked',
    },
    quickQuestions: [
      'What are your office hours?',
      'Do you accept my insurance?',
      'How do I book a cleaning?',
      'Do you offer teeth whitening?',
      'Are you accepting new patients?',
      'Do you handle dental emergencies?',
    ],
    faqKnowledge: {
      hours: {
        keywords: ['hours', 'open', 'close', 'time', 'schedule', 'when'],
        response: "Our office is open Monday through Friday, 8am to 5pm. We're happy to help you find a convenient time.",
      },
      services: {
        keywords: ['services', 'offer', 'do you do', 'dental', 'teeth'],
        response: 'We offer checkups, cleanings, implants, whitening, Invisalign, crowns, fillings, and more. What can we help you with?',
      },
      insurance: {
        keywords: ['insurance', 'accept', 'coverage', 'plan', 'delta', 'aetna', 'cigna'],
        response: 'We accept most major dental insurance plans. Let us know your provider and we can verify your coverage before your visit.',
      },
      emergency: {
        keywords: ['emergency', 'urgent', 'pain', 'broken', 'toothache', 'swelling'],
        response: 'We offer same-day emergency appointments when possible. If you are in pain, call us directly and we will get you in as soon as we can.',
      },
      newPatient: {
        keywords: ['new patient', 'first visit', 'new', 'accepting'],
        response: 'Yes, we are accepting new patients! Your first visit includes a comprehensive exam and X-rays. Can I get your name to schedule?',
      },
      area: {
        keywords: ['area', 'serve', 'location', 'where', 'city'],
        response: null,
      },
      appointment: {
        keywords: ['appointment', 'book', 'schedule', 'available'],
        response: "We'd love to get you on the calendar. Can I grab your name and phone number?",
      },
    },
  },

  restaurant: {
    services: ['Reservations', 'Catering', 'Private Events', 'Takeout'],
    hours: 'Tue-Sun 11am-10pm, Closed Mondays',
    botName: 'Reservation Assistant',
    serviceKeywords: {
      reservation: 'Reservation', catering: 'Catering', 'private event': 'Private Event',
      'private dining': 'Private Dining', takeout: 'Takeout', delivery: 'Delivery',
      party: 'Private Event', wedding: 'Catering',
    },
    dashboardLabels: {
      leads: 'New Inquiries Today',
      booked: 'Reservations Booked',
    },
    quickQuestions: [
      'What are your hours?',
      'Can I make a reservation?',
      'Do you offer catering?',
      'Do you have a private dining room?',
      'Do you offer delivery?',
      'Can you accommodate dietary restrictions?',
    ],
    faqKnowledge: {
      hours: {
        keywords: ['hours', 'open', 'close', 'time', 'when'],
        response: "We're open Tuesday through Sunday, 11am to 10pm. We're closed on Mondays.",
      },
      reservation: {
        keywords: ['reservation', 'book', 'table', 'reserve', 'party size', 'seats'],
        response: "We'd love to have you! For parties of 6 or fewer, you can book online. For larger groups, let me get your details.",
      },
      catering: {
        keywords: ['catering', 'cater', 'event', 'corporate', 'wedding', 'party'],
        response: 'We offer full-service catering for corporate events, weddings, and private parties. Can I get your event details?',
      },
      delivery: {
        keywords: ['delivery', 'deliver', 'doordash', 'ubereats', 'grubhub', 'takeout'],
        response: 'We offer takeout directly and are available on DoorDash and UberEats. You can also call to place a pickup order.',
      },
      menu: {
        keywords: ['menu', 'dishes', 'food', 'vegetarian', 'vegan', 'gluten', 'allergy', 'dietary'],
        response: 'Our menu changes seasonally! We accommodate vegetarian, vegan, and gluten-free dietary needs. Just let your server know.',
      },
      events: {
        keywords: ['private', 'room', 'space', 'event space', 'private dining'],
        response: 'Yes! We have a private dining room that seats up to 40 guests. Would you like to inquire about availability?',
      },
      area: {
        keywords: ['area', 'location', 'where', 'address', 'directions'],
        response: null,
      },
    },
  },

  realestate: {
    services: ['Buyer Agent', 'Seller Agent', 'Property Management', 'Market Analysis'],
    hours: 'Mon-Sat 9am-7pm, Sun by appointment',
    botName: 'Real Estate Assistant',
    serviceKeywords: {
      buy: 'Buyer Agent', buying: 'Buyer Agent', sell: 'Seller Agent', selling: 'Seller Agent',
      listing: 'Seller Agent', 'property management': 'Property Management',
      rent: 'Property Management', rental: 'Property Management',
      home: 'Buyer Agent', house: 'Buyer Agent', condo: 'Buyer Agent',
    },
    dashboardLabels: {
      leads: 'New Leads Today',
      booked: 'Showings Booked',
    },
    quickQuestions: [
      "What's the market like right now?",
      'How do I start the buying process?',
      'Can you help me sell my home?',
      'Do you do property management?',
      'Can I schedule a showing?',
      'How much is my home worth?',
    ],
    faqKnowledge: {
      buying: {
        keywords: ['buy', 'buying', 'purchase', 'first-time', 'mortgage', 'pre-approved'],
        response: "Great — we'd love to help you find the right home! The first step is getting pre-approved. Can I get your name and number to set up a consultation?",
      },
      selling: {
        keywords: ['sell', 'selling', 'list', 'listing', 'worth', 'value', 'cma'],
        response: "We can help you get top dollar for your home. It starts with a free Comparative Market Analysis (CMA). Can I schedule that for you?",
      },
      services: {
        keywords: ['services', 'offer', 'do you do', 'help with'],
        response: 'We offer buyer representation, seller listing services, property management, and free market analysis. How can we help?',
      },
      showing: {
        keywords: ['showing', 'tour', 'see', 'visit', 'view', 'schedule', 'appointment'],
        response: "I'd love to set up a showing for you! Can I grab your name and the best number to reach you?",
      },
      management: {
        keywords: ['property management', 'manage', 'rent', 'rental', 'tenant', 'landlord'],
        response: 'Yes, we offer full-service property management. We handle tenant screening, maintenance, and rent collection.',
      },
      area: {
        keywords: ['area', 'serve', 'location', 'where', 'city', 'neighborhood'],
        response: null,
      },
    },
  },

  legal: {
    services: ['Consultations', 'Case Review', 'Document Preparation', 'Representation'],
    hours: 'Mon-Fri 9am-6pm',
    botName: 'Intake Coordinator',
    serviceKeywords: {
      consultation: 'Consultation', consult: 'Consultation', 'case review': 'Case Review',
      document: 'Document Preparation', contract: 'Document Preparation',
      represent: 'Representation', lawsuit: 'Representation', sue: 'Representation',
    },
    dashboardLabels: {
      leads: 'New Inquiries Today',
      booked: 'Consultations Booked',
    },
    quickQuestions: [
      'Do you offer free consultations?',
      'What areas of law do you practice?',
      'How do I schedule a consultation?',
      'What should I bring to my first meeting?',
      'What are your fees?',
      'How long does a typical case take?',
    ],
    faqKnowledge: {
      consultation: {
        keywords: ['consultation', 'consult', 'free', 'initial', 'first meeting'],
        response: 'We offer a free initial consultation to discuss your situation and determine how we can help. Can I schedule one for you?',
      },
      services: {
        keywords: ['services', 'practice', 'areas', 'specialize', 'handle', 'help with'],
        response: 'We handle consultations, case reviews, document preparation, and full representation. What type of legal matter do you need help with?',
      },
      fees: {
        keywords: ['fees', 'cost', 'price', 'charge', 'hourly', 'contingency', 'retainer'],
        response: 'Our fee structure depends on the type of case. We offer hourly, flat-fee, and contingency arrangements. We discuss all of this during your free consultation.',
      },
      appointment: {
        keywords: ['appointment', 'book', 'schedule', 'available', 'meet'],
        response: "I'd be happy to schedule a consultation. Can I get your name and the best number to reach you?",
      },
      area: {
        keywords: ['area', 'serve', 'location', 'where', 'city'],
        response: null,
      },
    },
  },

  fitness: {
    services: ['Memberships', 'Personal Training', 'Group Classes', 'Nutrition Coaching'],
    hours: 'Mon-Fri 5am-10pm, Sat-Sun 7am-8pm',
    botName: 'Membership Advisor',
    serviceKeywords: {
      membership: 'Membership', 'personal training': 'Personal Training', trainer: 'Personal Training',
      class: 'Group Classes', yoga: 'Group Classes', spin: 'Group Classes', hiit: 'Group Classes',
      nutrition: 'Nutrition Coaching', diet: 'Nutrition Coaching', 'weight loss': 'Membership',
    },
    dashboardLabels: {
      leads: 'New Members Today',
      booked: 'Classes Booked',
    },
    quickQuestions: [
      'What memberships do you offer?',
      'Do you have personal training?',
      'What classes are available?',
      'Can I get a free trial?',
      'What are your hours?',
      'Do you offer nutrition coaching?',
    ],
    faqKnowledge: {
      membership: {
        keywords: ['membership', 'join', 'sign up', 'member', 'pricing', 'cost', 'plans'],
        response: 'We offer flexible membership plans — monthly and annual options available. Can I get your info to set up a tour and discuss which plan fits best?',
      },
      services: {
        keywords: ['services', 'offer', 'do you do', 'what do you have'],
        response: 'We offer memberships, personal training, group classes (yoga, spin, HIIT, and more), and nutrition coaching. What interests you?',
      },
      training: {
        keywords: ['personal training', 'trainer', 'one on one', '1 on 1', 'pt'],
        response: 'Our certified personal trainers create custom programs tailored to your goals. We offer single sessions and packages. Want me to set up a free intro session?',
      },
      classes: {
        keywords: ['class', 'classes', 'yoga', 'spin', 'hiit', 'group', 'schedule'],
        response: 'We offer a full schedule of group classes including yoga, spin, HIIT, strength, and more. Classes are included with most memberships.',
      },
      trial: {
        keywords: ['trial', 'free', 'try', 'guest', 'day pass', 'visit'],
        response: "Yes! We offer a free day pass so you can check out the facility and try a class. Can I get your name to set one up?",
      },
      hours: {
        keywords: ['hours', 'open', 'close', 'time', 'when'],
        response: "We're open Monday through Friday 5am-10pm, and Saturday-Sunday 7am-8pm.",
      },
      area: {
        keywords: ['area', 'serve', 'location', 'where', 'city', 'address'],
        response: null,
      },
    },
  },
};

// ── Build Config ──

const bizName = params.get('biz') || "Smith's Home Solutions";
const industry = params.get('industry') || 'plumbing';
const city = params.get('city') || 'Austin';
const preset = INDUSTRY_PRESETS[industry] || INDUSTRY_PRESETS.plumbing;

// Fill in dynamic area response for all presets
if (preset.faqKnowledge.area && !preset.faqKnowledge.area.response) {
  preset.faqKnowledge.area.response = `We serve the ${city} area and surrounding communities. Can I help you with anything else?`;
}

const servicesList = preset.services.join(', ');

const systemPrompt = `You are a friendly AI assistant for a business called "${bizName}" in ${city}. You help capture leads and answer questions.

Services offered: ${servicesList}
Hours: ${preset.hours}
Service area: ${city} and surrounding areas

Your job:
1. Greet warmly and ask how you can help
2. Understand what service they need
3. Capture their name, phone, and email (give a reason: "so we can send you more details")
4. Ask about timeline and any specifics
5. Offer to book an appointment or consultation
6. Be conversational, not robotic

When you capture contact info, confirm it back to them.`;

const faqSystemPrompt = `You are a support bot for ${bizName}. Answer questions about hours (${preset.hours}), services (${servicesList}), and service area (${city} area). Be warm and offer to book appointments or connect them with the team.`;

// Set page title
document.title = `${bizName} — AgentNexLiFy Demo`;

const demoConfig = {
  bizName,
  industry,
  city,
  services: preset.services,
  servicesList,
  hours: preset.hours,
  botName: preset.botName,
  serviceKeywords: preset.serviceKeywords,
  dashboardLabels: preset.dashboardLabels,
  quickQuestions: preset.quickQuestions,
  faqKnowledge: preset.faqKnowledge,
  systemPrompt,
  faqSystemPrompt,
  greeting: `Hello! Welcome to ${bizName}. I'm your ${preset.botName}. How can I help you today?`,
  faqGreeting: `Hi there! I'm the AI support bot for ${bizName}. Ask me anything about our services, hours, or policies. You can also tap one of the quick questions below!`,
};

export default demoConfig;
