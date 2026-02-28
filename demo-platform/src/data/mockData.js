// ── Leads Pipeline ──
export const leads = [
  { id: 1, name: 'Sarah Chen', description: 'Needs emergency plumbing, responded to missed call text', score: 'hot', source: 'Missed Call', stage: 'new', minutesAgo: 45, automationNote: 'Missed call text-back sent' },
  { id: 2, name: 'Mike Johnson', description: 'Looking for kitchen remodel, $30K budget', score: 'hot', source: 'Website Chat', stage: 'new', minutesAgo: 120, automationNote: 'AI chatbot captured lead' },
  { id: 3, name: 'Lisa Martinez', description: 'Wants quote for HVAC installation', score: 'warm', source: 'Facebook Ad', stage: 'new', minutesAgo: 180, automationNote: 'Auto follow-up sent' },
  { id: 4, name: 'Tom Anderson', description: 'Bathroom renovation inquiry', score: 'warm', source: 'Google', stage: 'new', minutesAgo: 300, automationNote: 'Drip sequence started' },
  { id: 5, name: 'James Brown', description: 'General inquiry about services', score: 'cold', source: 'Google', stage: 'new', minutesAgo: 2880, automationNote: 'Follow-up email #1 sent' },
  { id: 6, name: 'David Williams', description: 'Asking about dental cleaning pricing', score: 'warm', source: 'Website Chat', stage: 'contacted', minutesAgo: 1440, automationNote: 'Follow-up sequence active' },
  { id: 7, name: 'Rachel Kim', description: 'HVAC repair, budget $5-8K, wants appt this week', score: 'hot', source: 'Website Chat', stage: 'contacted', minutesAgo: 360, automationNote: 'AI chatbot qualified' },
  { id: 8, name: 'Kevin Patel', description: 'Electrical panel upgrade request', score: 'warm', source: 'Referral', stage: 'contacted', minutesAgo: 480, automationNote: 'Follow-up call scheduled' },
  { id: 9, name: 'Jennifer Lopez', description: 'Full kitchen and bath remodel', score: 'hot', source: 'Website Chat', stage: 'contacted', minutesAgo: 720, automationNote: 'Quote request sent' },
  { id: 10, name: 'Maria Rodriguez', description: 'Plumbing leak, responded same day', score: 'hot', source: 'Missed Call', stage: 'contacted', minutesAgo: 1440, automationNote: 'Emergency dispatch' },
  { id: 11, name: 'Brian Taylor', description: 'Furnace replacement, comparing quotes', score: 'warm', source: 'Facebook Ad', stage: 'contacted', minutesAgo: 2160, automationNote: 'Drip email #3 sent' },
  { id: 12, name: 'Amy Nguyen', description: 'Tankless water heater install', score: 'warm', source: 'Google', stage: 'contacted', minutesAgo: 2880, automationNote: 'Follow-up SMS sent' },
  { id: 13, name: 'Robert Davis', description: 'Whole-home rewiring project', score: 'hot', source: 'Referral', stage: 'qualified', minutesAgo: 1200, automationNote: 'Site visit scheduled' },
  { id: 14, name: 'Emily Watson', description: 'Master bath remodel, $20K budget', score: 'warm', source: 'Website Chat', stage: 'qualified', minutesAgo: 2400, automationNote: 'Estimate prepared' },
  { id: 15, name: 'Carlos Mendez', description: 'Commercial HVAC maintenance contract', score: 'hot', source: 'Referral', stage: 'qualified', minutesAgo: 4320, automationNote: 'Proposal sent' },
  { id: 16, name: 'Nancy Thompson', description: 'Sump pump replacement + basement waterproofing', score: 'warm', source: 'Google', stage: 'qualified', minutesAgo: 5760, automationNote: 'Follow-up scheduled' },
  { id: 17, name: 'Steve Garcia', description: 'Kitchen remodel, signed scope of work', score: 'hot', source: 'Website Chat', stage: 'appointment', minutesAgo: 7200, automationNote: 'Appointment confirmed' },
  { id: 18, name: 'Laura Kim', description: 'HVAC install, in-home estimate completed', score: 'hot', source: 'Facebook Ad', stage: 'appointment', minutesAgo: 8640, automationNote: 'Reminder sent' },
  { id: 19, name: 'Greg Wilson', description: 'Electrical upgrade, deposit paid', score: 'hot', source: 'Referral', stage: 'appointment', minutesAgo: 10080, automationNote: 'Job scheduled' },
  { id: 20, name: 'Michelle Park', description: 'Kitchen remodel $28,500 — signed contract', score: 'hot', source: 'Website Chat', stage: 'closed', minutesAgo: 14400, automationNote: 'Review request sent' },
  { id: 21, name: 'Daniel Harris', description: 'Emergency plumbing repair $1,200 — completed', score: 'hot', source: 'Missed Call', stage: 'closed', minutesAgo: 20160, automationNote: 'Invoice paid' },
];

// ── Activity Feed ──
export const activityFeed = [
  { id: 1, icon: '\u{1F916}', message: 'AI chatbot captured lead: Sarah Chen', minutesAgo: 45 },
  { id: 2, icon: '\u{1F4F1}', message: 'Missed call text-back sent to (555) 234-5678', minutesAgo: 60 },
  { id: 3, icon: '\u2B50', message: 'Review request sent to Mike Johnson', minutesAgo: 120 },
  { id: 4, icon: '\u{1F4E7}', message: 'Follow-up email #2 sent to David Williams', minutesAgo: 180 },
  { id: 5, icon: '\u{1F4C5}', message: 'Appointment reminder sent to Lisa Martinez (tomorrow 2pm)', minutesAgo: 240 },
  { id: 6, icon: '\u2705', message: 'Lead scored: James Brown \u2192 Warm (opened 3 emails)', minutesAgo: 300 },
  { id: 7, icon: '\u{1F4AC}', message: "FAQ bot handled inquiry: 'What are your hours?'", minutesAgo: 360 },
  { id: 8, icon: '\u{1F4B0}', message: 'Invoice #1047 paid by Maria Rodriguez ($2,340)', minutesAgo: 420 },
  { id: 9, icon: '\u{1F525}', message: 'Hot lead alert: Rachel Kim — HVAC repair, budget $5-8K', minutesAgo: 480 },
  { id: 10, icon: '\u{1F504}', message: 'Lead score updated: Tom Anderson Cold \u2192 Warm', minutesAgo: 540 },
];

// ── Notifications ──
export const notifications = [
  { id: 1, icon: '\u{1F534}', message: 'Hot Lead Alert: Sarah Chen responded to missed call text. Lead score: 92/100.', minutesAgo: 0, action: 'View Lead \u2192', borderColor: '#ff4444', group: 'today' },
  { id: 2, icon: '\u{1F4AC}', message: 'New Chat Lead: Mike Johnson started a conversation about kitchen remodel. Budget: $30K.', minutesAgo: 5, action: 'View Chat \u2192', borderColor: '#00bfff', group: 'today' },
  { id: 3, icon: '\u{1F4F1}', message: 'Missed Call Text Sent to (555) 234-5678. Awaiting response.', minutesAgo: 15, action: 'View \u2192', borderColor: '#9494a8', group: 'today' },
  { id: 4, icon: '\u2B50', message: 'New Google Review: Lisa Martinez left a 5-star review. "Great service, very professional!"', minutesAgo: 30, action: 'View Review \u2192', borderColor: '#f5a623', group: 'today' },
  { id: 5, icon: '\u{1F4E7}', message: 'Follow-Up Sent: Email #3 in drip sequence sent to David Williams. Subject: "Here\'s what our clients say..."', minutesAgo: 60, action: 'View Sequence \u2192', borderColor: '#9494a8', group: 'today' },
  { id: 6, icon: '\u{1F4C5}', message: "Appointment Confirmed: James Brown confirmed tomorrow's appointment at 2pm.", minutesAgo: 120, action: 'View Calendar \u2192', borderColor: '#34d399', group: 'today' },
  { id: 7, icon: '\u{1F4B0}', message: 'Invoice Paid: Maria Rodriguez paid Invoice #1047 ($2,340). Collected after 2nd reminder.', minutesAgo: 180, action: 'View Invoice \u2192', borderColor: '#34d399', group: 'today' },
  { id: 8, icon: '\u{1F916}', message: 'FAQ Bot Handled: Answered "Do you offer financing?" \u2014 Customer satisfied, no escalation needed.', minutesAgo: 240, action: 'View Chat \u2192', borderColor: '#00bfff', group: 'today' },
  { id: 9, icon: '\u{1F4CA}', message: 'Weekly Report Ready: 31 new leads, 12 appointments booked, 4 closed deals. Revenue: $18,450.', minutesAgo: 300, action: 'View Report \u2192', borderColor: '#8b5cf6', group: 'today' },
  { id: 10, icon: '\u{1F504}', message: 'Lead Score Update: Tom Anderson moved from Cold \u2192 Warm. Opened 3 emails and visited pricing page.', minutesAgo: 360, action: 'View Lead \u2192', borderColor: '#f5a623', group: 'today' },
  { id: 11, icon: '\u26A1', message: '"Post-service review request" workflow activated for all completed jobs.', minutesAgo: 1440, action: 'View Automation \u2192', borderColor: '#00bfff', group: 'yesterday' },
  { id: 12, icon: '\u{1F4E7}', message: 'Follow-Up Reply: David Williams replied: "Yes, I\'d like to schedule a consultation."', minutesAgo: 1500, action: 'View & Respond \u2192', borderColor: '#34d399', group: 'yesterday' },
  { id: 13, icon: '\u{1F4AC}', message: 'Chat Lead Qualified: AI chatbot qualified Rachel Kim \u2014 needs HVAC repair, budget $5-8K, wants appointment this week.', minutesAgo: 1560, action: 'View Lead \u2192', borderColor: '#00bfff', group: 'yesterday' },
  { id: 14, icon: '\u2705', message: 'Deal Closed: Kitchen remodel project signed with Michelle Park. Value: $28,500.', minutesAgo: 2880, action: 'View Deal \u2192', borderColor: '#34d399', group: 'older' },
  { id: 15, icon: '\u{1F4F1}', message: 'Missed Call Recovered: Call from (555) 876-5432 returned after text-back. Appointment booked.', minutesAgo: 2940, action: 'View Lead \u2192', borderColor: '#f5a623', group: 'older' },
];

// ── Weekly Chart ──
export const weeklyData = [
  { day: 'Mon', value: 4 },
  { day: 'Tue', value: 6 },
  { day: 'Wed', value: 3 },
  { day: 'Thu', value: 8 },
  { day: 'Fri', value: 7 },
  { day: 'Sat', value: 2 },
  { day: 'Sun', value: 1 },
];

// ── FAQ Knowledge Base ──
export const faqKnowledge = {
  hours: {
    keywords: ['hours', 'open', 'close', 'time', 'schedule', 'when'],
    response: "We're open Monday through Friday 7am-6pm, Saturday 8am-2pm. For emergencies, we offer 24/7 service — just call our emergency line at (555) 100-2000.",
  },
  pricing: {
    keywords: ['cost', 'price', 'pricing', 'much', 'expensive', 'quote', 'estimate', 'remodel', 'kitchen'],
    response: 'Kitchen remodels typically range from $15,000 to $50,000 depending on scope. We offer free in-home estimates — would you like to schedule one?',
  },
  emergency: {
    keywords: ['emergency', 'urgent', 'asap', 'now', 'immediate', 'leak', 'broken', 'flood'],
    response: "Yes! We offer 24/7 emergency service for plumbing, HVAC, and electrical issues. Call (555) 100-2000 for immediate assistance, or I can have someone call you right back.",
  },
  area: {
    keywords: ['area', 'serve', 'location', 'where', 'city', 'austin', 'round rock', 'cedar park'],
    response: 'We serve the entire Austin metro area, including Round Rock, Cedar Park, Pflugerville, Georgetown, and everywhere within 30 miles of downtown Austin.',
  },
  appointment: {
    keywords: ['appointment', 'book', 'schedule', 'available', 'come out', 'visit'],
    response: "I'd love to help you schedule! Our earliest availability is usually within 2-3 business days. Can I get your name and phone number to book you in?",
  },
  financing: {
    keywords: ['financing', 'finance', 'payment', 'pay', 'credit', 'loan', 'afford'],
    response: 'Yes! We offer 0% financing for 12 months on projects over $5,000 through GreenSky. We also accept all major credit cards. Want me to connect you with our financing team?',
  },
  warranty: {
    keywords: ['warranty', 'guarantee', 'warrantee', 'coverage', 'insured', 'insurance'],
    response: "All our work comes with a 2-year labor warranty and we pass through manufacturer warranties on all parts and equipment. For remodeling projects, we offer a 5-year workmanship guarantee.",
  },
  services: {
    keywords: ['services', 'offer', 'do you do', 'what do you', 'plumbing', 'hvac', 'electrical'],
    response: "We offer a full range of home services including Plumbing, HVAC (heating & cooling), Electrical work, and Kitchen/Bath Remodeling. What type of project do you have in mind?",
  },
};

// ── Automation Definitions ──
export const automations = [
  {
    id: 1,
    name: 'Missed Call Text-Back',
    status: 'active',
    trigger: 'When a call is missed',
    action: "Send SMS: 'Sorry we missed you! How can we help?'",
    stats: '47 missed calls recovered this month',
    steps: [
      { label: 'Incoming call detected', icon: '\u{1F4DE}', delay: 600 },
      { label: 'Call missed — no answer after 4 rings', icon: '\u274C', delay: 800 },
      { label: 'SMS auto-sent: "Sorry we missed your call! How can we help?"', icon: '\u{1F4F1}', delay: 1000 },
      { label: 'Customer replied: "Need plumbing repair ASAP"', icon: '\u{1F4AC}', delay: 1200 },
      { label: 'Lead captured & notification sent to owner', icon: '\u2705', delay: 800 },
    ],
  },
  {
    id: 2,
    name: 'Review Request System',
    status: 'active',
    trigger: 'After job completion',
    action: 'Send review request email + SMS with Google link',
    stats: '35 new reviews generated, 4.8 avg rating',
    steps: [
      { label: 'Job marked as completed', icon: '\u2705', delay: 600 },
      { label: 'Review request email sent', icon: '\u{1F4E7}', delay: 800 },
      { label: 'Follow-up SMS with direct Google review link', icon: '\u{1F4F1}', delay: 1000 },
      { label: 'Customer left 5-star review!', icon: '\u2B50', delay: 1200 },
      { label: 'Auto-response: "Thank you for your kind words!"', icon: '\u{1F4AC}', delay: 800 },
    ],
  },
  {
    id: 3,
    name: 'Lead Follow-Up Drip',
    status: 'active',
    trigger: 'New lead captured',
    action: '7-touch sequence over 14 days (email + SMS)',
    stats: '62% open rate, 23% reply rate',
    steps: [
      { label: 'Day 0: "Thanks for your inquiry!" (email)', icon: '\u{1F4E7}', delay: 500 },
      { label: 'Day 1: "Quick follow-up" (SMS)', icon: '\u{1F4F1}', delay: 500 },
      { label: 'Day 3: "Here\'s what our clients say..." (email)', icon: '\u{1F4E7}', delay: 500 },
      { label: 'Day 5: "Still interested?" (SMS)', icon: '\u{1F4F1}', delay: 500 },
      { label: 'Day 7: "Special offer for you" (email)', icon: '\u{1F4E7}', delay: 500 },
      { label: 'Day 10: "Last chance" (SMS)', icon: '\u{1F4F1}', delay: 500 },
      { label: 'Day 14: "We\'re here when you\'re ready" (email)', icon: '\u{1F4E7}', delay: 500 },
    ],
  },
  {
    id: 4,
    name: 'Appointment Reminders',
    status: 'active',
    trigger: '24hrs and 2hrs before appointment',
    action: 'Send SMS reminder with confirm/reschedule options',
    stats: 'No-show rate reduced from 23% to 4%',
    steps: [
      { label: 'Appointment detected: Tomorrow at 2:00 PM', icon: '\u{1F4C5}', delay: 700 },
      { label: '24hr reminder: "Your appointment is tomorrow at 2pm. Reply CONFIRM or RESCHEDULE."', icon: '\u{1F4F1}', delay: 1000 },
      { label: 'Customer replied: "CONFIRM"', icon: '\u2705', delay: 800 },
      { label: '2hr reminder: "See you in 2 hours at 123 Main St!"', icon: '\u{1F4F1}', delay: 1000 },
      { label: 'Technician notified — en route', icon: '\u{1F6E0}\uFE0F', delay: 700 },
    ],
  },
  {
    id: 5,
    name: 'Invoice Follow-Up',
    status: 'active',
    trigger: 'Invoice unpaid after 3, 7, 14 days',
    action: 'Escalating reminder sequence',
    stats: 'Avg collection time reduced from 34 to 8 days',
    steps: [
      { label: 'Invoice #1052 sent — $3,450.00', icon: '\u{1F4C4}', delay: 700 },
      { label: 'Day 3: Friendly reminder email sent', icon: '\u{1F4E7}', delay: 800 },
      { label: 'Day 7: SMS + email reminder with payment link', icon: '\u{1F4F1}', delay: 900 },
      { label: 'Day 14: Final notice with late fee warning', icon: '\u26A0\uFE0F', delay: 1000 },
      { label: 'Customer paid via link — collected on Day 8!', icon: '\u{1F4B0}', delay: 800 },
    ],
  },
  {
    id: 6,
    name: 'AI Lead Scoring',
    status: 'active',
    trigger: 'Continuous — monitors lead behavior',
    action: 'Scores leads, alerts on hot prospects',
    stats: 'Hot leads close 4x faster than unscored',
    steps: [
      { label: 'Opened email: +10 points', icon: '\u{1F4E7}', delay: 500 },
      { label: 'Clicked link: +15 points', icon: '\u{1F517}', delay: 500 },
      { label: 'Visited pricing page: +20 points', icon: '\u{1F4CA}', delay: 500 },
      { label: 'Responded to SMS: +25 points', icon: '\u{1F4F1}', delay: 500 },
      { label: 'Requested quote: +30 points', icon: '\u{1F4DD}', delay: 500 },
      { label: 'Total: 100/100 — HOT LEAD! Alert sent to owner!', icon: '\u{1F525}', delay: 700 },
    ],
  },
];

// ── Chat Simulation Responses ──
export const chatSimulation = {
  greeting: "Hello! Welcome to Smith's Home Solutions. I'm your AI assistant. How can I help you today? Whether you need plumbing, HVAC, electrical, or remodeling — I'm here to help!",
  serviceInquiry: "Great choice! We'd love to help with that. To get you the best quote, can I grab your name?",
  nameCapture: (name) => `Nice to meet you, ${name}! What's the best phone number to reach you at? We'll only use it to follow up on your request.`,
  phoneCapture: "Perfect, got it! And your email address? We'll send you a detailed quote there.",
  emailCapture: "Excellent! I have everything I need. Based on what you're looking for, I'd recommend scheduling a free in-home consultation. Our earliest availability is in 2-3 business days. Would you like me to book that?",
  scheduling: "I've got you down for a consultation! You'll receive a confirmation text shortly with the details. A senior technician will come assess the project and provide an exact quote on-site. Is there anything else I can help with?",
  closing: "You're all set! We're excited to help with your project. You'll hear from us soon. Have a great day!",
  fallback: "I'd be happy to help with that. Could you tell me a bit more about what you're looking for? We offer plumbing, HVAC, electrical, and remodeling services.",
};

// ── Utilities ──
export function formatTimeAgo(minutesAgo) {
  if (minutesAgo < 1) return 'Just now';
  if (minutesAgo < 60) return `${minutesAgo} min ago`;
  if (minutesAgo < 120) return '1 hour ago';
  if (minutesAgo < 1440) return `${Math.floor(minutesAgo / 60)} hours ago`;
  if (minutesAgo < 2880) return 'Yesterday';
  return `${Math.floor(minutesAgo / 1440)} days ago`;
}

export function getScoreEmoji(score) {
  if (score === 'hot') return '\u{1F534}';
  if (score === 'warm') return '\u{1F7E1}';
  return '\u{1F535}';
}

export const pipelineStages = [
  { key: 'new', label: 'New' },
  { key: 'contacted', label: 'Contacted' },
  { key: 'qualified', label: 'Qualified' },
  { key: 'appointment', label: 'Appointment Set' },
  { key: 'closed', label: 'Closed Won' },
];
