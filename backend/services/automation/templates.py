"""Automation template constants — no logic."""

_REMINDER_EXTRAS: dict[str, list[str]] = {
    "dental": ["Insurance card", "Photo ID", "List of current medications"],
    "medical": [
        "Insurance card",
        "Photo ID",
        "List of current medications",
        "Medical records if transferring",
    ],
    "salon": ["Arrive 5-10 minutes early", "Photos of desired style (if applicable)"],
    "auto_shop": ["Vehicle registration", "Description of any issues"],
    "legal": ["Relevant documents or contracts", "Photo ID", "List of questions"],
    "realestate": ["Pre-approval letter (if buying)", "Photo ID"],
    "plumbing": [
        "Photos of the issue (if possible)",
        "Clear access to the problem area",
    ],
    "contractor": ["Photos of the project area", "Any permits or HOA approvals"],
    "fitness": ["Comfortable workout clothes", "Water bottle", "Towel"],
}

_REBOOK_INTERVALS: dict[str, tuple[int, str]] = {
    "dental": (180, "6-month checkup and cleaning"),
    "medical": (365, "annual physical"),
    "salon": (42, "next appointment"),
    "fitness": (30, "next session"),
}

_AFTERCARE_TEMPLATES: dict[str, dict[str, str]] = {
    "dental": {
        "default": "Thank you for your visit! Please wait 30 minutes before eating or drinking. If you experience any sensitivity, over-the-counter pain relief should help.",
        "cleaning": "Your teeth have been professionally cleaned! Avoid dark foods and beverages for 24 hours. Continue brushing twice daily and flossing.",
        "filling": "Your filling is complete. The numbness should wear off in 2-3 hours. Avoid chewing on the treated side until then. If you experience persistent pain, please contact us.",
        "extraction": "Please bite on the gauze for 30-45 minutes. Avoid spitting, straws, and hot liquids for 24 hours. Rinse gently with warm salt water after 24 hours.",
        "root canal": "Some tenderness is normal for a few days. Avoid chewing on the treated tooth until your permanent crown is placed. Take prescribed medications as directed.",
    },
    "medical": {
        "default": "Thank you for your visit. Follow the care plan discussed during your appointment. Contact us if symptoms worsen.",
    },
    "salon": {
        "default": "Thank you for visiting us! To maintain your new look, follow the care tips your stylist shared.",
        "color": "Avoid washing your hair for 48 hours to let the color set. Use color-safe shampoo and conditioner.",
    },
    "fitness": {
        "default": "Great session! Stay hydrated, stretch, and rest as needed. See you next time!",
    },
    "auto_shop": {
        "default": "Your vehicle service is complete. Please keep your receipt for warranty purposes. If you notice any issues, bring it back and we'll take a look.",
    },
}

_ONBOARDING_STEPS = [
    {
        "day": 1,
        "min_hours": 23,
        "max_hours": 26,
        "subject": "Quick win: teach your AI about {{business_name}}",
        "body": (
            "<h2>Hi {{owner_name}},</h2>"
            "<p>Your chat widget is ready to go. Now let's make it sound like <em>you</em>.</p>"
            "<p><strong>The fastest way to improve your AI: add your top 5 FAQs.</strong></p>"
            "<p>Go to your <a href='https://app.agentnexlify.com'>FAQ Manager</a> and add the "
            "questions your customers ask the most: your hours, pricing, service area, what makes "
            "you different, and how to book.</p>"
            "<p>Each FAQ you add makes the AI smarter. Customers get instant, accurate answers "
            "instead of &ldquo;I'm not sure.&rdquo;</p>"
            "<p><strong>Bonus:</strong> If you have a website, go to Settings and paste your URL. "
            "Click &ldquo;Scan Website&rdquo; &mdash; the AI will read your site and learn your "
            "services automatically.</p>"
            "<p><a href='https://app.agentnexlify.com' style='background:#3b82f6;color:#fff;"
            "padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:600;'>"
            "Open your dashboard &rarr;</a></p>"
            "<p>Talk soon,<br>The AgentNexLiFy Team</p>"
        ),
    },
    {
        "day": 3,
        "min_hours": 71,
        "max_hours": 74,
        "subject": "Your AI had its first conversations — here's what happened",
        "body": (
            "<h2>Hi {{owner_name}},</h2>"
            "<p>By now your AI assistant has probably had a few conversations with visitors.</p>"
            "<p><strong>See every conversation:</strong> Go to "
            "<a href='https://app.agentnexlify.com'>Conversations</a> to see what visitors "
            "asked and how the AI responded.</p>"
            "<p><strong>Improve the AI with one click:</strong> See a response you don't love? "
            "Click the thumbs-down button and type what the AI <em>should</em> have said. "
            "It learns from your corrections.</p>"
            "<p><strong>Check your leads:</strong> Go to Leads to see everyone who shared their "
            "contact info. Follow up within an hour for the best results.</p>"
            "<p><a href='https://app.agentnexlify.com' style='background:#3b82f6;color:#fff;"
            "padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:600;'>"
            "Check your conversations &rarr;</a></p>"
            "<p>&mdash; The AgentNexLiFy Team</p>"
        ),
    },
    {
        "day": 7,
        "min_hours": 167,
        "max_hours": 170,
        "subject": "One week in — are you capturing every lead?",
        "body": (
            "<h2>Hi {{owner_name}},</h2>"
            "<p>It's been a week since you set up your AI assistant for {{business_name}}.</p>"
            "<p><strong>Is your widget on every page?</strong> The AI can only talk to visitors "
            "on pages where the widget is installed. Check that the embed code is on every page.</p>"
            "<p><strong>Are you following up on leads?</strong> Go to your Leads page and check "
            "for any &ldquo;New&rdquo; leads you haven't contacted yet.</p>"
            "<p><strong>Set up automations:</strong> Go to Automations and create a follow-up "
            "sequence &mdash; emails that go out automatically after a lead comes in.</p>"
            "<p><a href='https://app.agentnexlify.com' style='background:#3b82f6;color:#fff;"
            "padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:600;'>"
            "Open your dashboard &rarr;</a></p>"
            "<p>&mdash; The AgentNexLiFy Team</p>"
        ),
    },
    {
        "day": 14,
        "min_hours": 335,
        "max_hours": 338,
        "subject": "You're leaving money on the table, {{owner_name}}",
        "body": (
            "<h2>Hi {{owner_name}},</h2>"
            "<p>Two weeks in. Your AI assistant has been working 24/7 for {{business_name}}.</p>"
            "<p>Here's what you might be missing on the free plan:</p>"
            "<ul>"
            "<li><strong>Automated follow-ups</strong> &mdash; emails and SMS that fire instantly when a new lead comes in</li>"
            "<li><strong>SMS notifications</strong> &mdash; get a text the moment someone fills out your chat</li>"
            "<li><strong>Google Calendar sync</strong> &mdash; appointments appear on your calendar automatically</li>"
            "<li><strong>Review management</strong> &mdash; auto-request reviews, draft AI responses</li>"
            "<li><strong>Team collaboration</strong> &mdash; invite team members, assign leads, internal notes</li>"
            "</ul>"
            "<p>One captured lead that turns into a customer pays for months of AgentNexLiFy. "
            "The Growth plan is $249/month &mdash; less than a single Google ad click in most industries. "
            "Now with SEO audit tools and AI content writer included.</p>"
            "<p><a href='https://app.agentnexlify.com' style='background:#3b82f6;color:#fff;"
            "padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:600;'>"
            "See what you're missing &rarr;</a></p>"
            "<p>&mdash; The AgentNexLiFy Team</p>"
        ),
    },
]
