"""
Build the routing training dataset.

Written independently of the frozen action benchmark. No frozen ask, name or
phrasing was consulted while authoring the templates below, and
`datasets.check_leakage` verifies that empirically after generation rather than
on trust.

Design notes that matter more than the line count:

  * A training example carries only what a production router actually sees at
    inference time — the owner's words — plus its label. No rationale, no
    expected tool, no expected behaviour. A router that learns from downstream
    labels is not solving routing; it is reading the answer key.
  * Templates are authored per intent FAMILY, not per department, because the
    thing that separates People from Marketing is not the department, it is
    "hiring ad" versus "weekend sale". Families make those boundaries explicit.
  * Surface style is applied round-robin, one per instance, so the corpus
    contains terse, conversational, typo-ridden and long-context phrasings of
    genuinely different scenarios rather than six copies of each sentence.
  * Verticals other than auto repair are deliberately over-represented relative
    to the benchmark. The frozen set is one auto shop; a router that has only
    ever seen brake jobs has memorised a vocabulary, not learned a task.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SEED = 20260828
OUT = Path(__file__).resolve().parent / "data" / "train-v1.jsonl"
DATASET_VERSION = "routing-train-v1"

# --- Slot vocabularies -------------------------------------------------------
# Names chosen to not overlap the benchmark's cast. Overlap would not be
# leakage on its own, but keeping the pools disjoint makes the leakage report
# easier to trust.
NAMES = [
    "Elena Vargas", "Jamal Whitaker", "Nina Petrova", "Owen Brady", "Carla Mendes",
    "Devon Okafor", "Aisha Karim", "Marcus Feldman", "Lila Nakamura", "Theo Brennan",
    "Rosa Iglesias", "Kwame Adjei", "Sasha Volkov", "Ibrahim Nasser", "Greta Lindqvist",
    "Hugo Marchetti", "Yara Haddad", "Callum Frost", "Bianca Ferreira", "Nadia Rahman",
    "Otis Blackwell", "Freya Sorensen", "Rafael Duarte", "Imani Clarke", "Viktor Novak",
    "Amara Diallo", "Simon Cortez", "Leila Ahmadi", "Gus Hollander", "Petra Kowalski",
]
FIRST = [n.split()[0] for n in NAMES]

SERVICES = {
    "auto": ["brake job", "oil change", "transmission flush", "wheel alignment", "timing belt",
             "coolant flush", "suspension work", "diagnostic", "exhaust repair"],
    "salon": ["balayage", "keratin treatment", "cut and colour", "bridal updo", "deep conditioning"],
    "plumbing": ["water heater install", "drain clearing", "repipe", "leak detection", "sump pump swap"],
    "dental": ["cleaning", "crown fitting", "whitening", "root canal", "implant consult"],
    "landscaping": ["spring cleanup", "irrigation repair", "sod install", "tree trimming", "mulch delivery"],
    "hvac": ["furnace tune-up", "AC install", "duct cleaning", "thermostat swap", "refrigerant top-up"],
}
ALL_SERVICES = [s for v in SERVICES.values() for s in v]

AMOUNTS = ["$240", "$480", "$1,150", "$2,300", "$95", "$620", "$3,400", "$780", "$1,850"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "next week",
        "the 14th", "tomorrow", "this afternoon"]
TIMES = ["8:30", "10am", "1:15", "3pm", "4:45", "noon"]
CHANNELS = ["email", "text", "message"]
PLATFORMS = ["Google", "Yelp", "Facebook", "Instagram", "Nextdoor"]
ROLES = ["front desk clerk", "junior tech", "weekend receptionist", "apprentice", "shop assistant",
         "delivery driver", "part-time stylist", "service advisor"]
MONTHS = ["January", "March", "June", "September", "November", "last month", "this quarter"]

# --- Templates ---------------------------------------------------------------
# {n} full name, {f} first name, {svc} service, {amt} amount, {day} day,
# {time} time, {ch} channel, {plat} platform, {role} role, {mon} month.
TEMPLATES: dict[str, dict[str, list[str]]] = {
    "sales": {
        "quote_followup": [
            "follow up with {n} on the {svc} quote we sent",
            "check whether {f} ever decided on that {amt} estimate",
            "{f} never got back to us about the {svc} quote, nudge her",
            "circle back to {n} about the proposal from {mon}",
            "we quoted {f} {amt} and heard nothing, chase it",
            "touch base with {n} on the estimate before it goes stale",
            "see if {f} still wants the {svc} we priced up",
        ],
        "quote_create": [
            "put together a quote for {n} for a {svc}",
            "price out a {svc} for {f}, parts and labour separately",
            "write up an estimate for {n}, {amt} all in",
            "build {f} a proposal for the {svc} she asked about",
            "draft a quote covering the {svc} plus the diagnostic",
            "{n} wants numbers on a {svc}, put an estimate together",
        ],
        "cold_outreach": [
            "reach out to the three shops on Milburn Road about our services",
            "cold email the property managers we met at the trade show",
            "put together outreach for local fleet operators",
            "contact the new builds on the east side about a service contract",
            "prospect the dealerships that keep sending us overflow",
        ],
        "lead_nurture": [
            "get back in touch with {n}, she enquired in {mon} and went quiet",
            "warm up the leads from the {plat} ads that never booked",
            "re-engage everyone who asked about {svc} and never scheduled",
            "we have not heard from {f} in months, send something friendly",
            "nurture the enquiries sitting in the pipeline since {mon}",
        ],
        "referral_upsell": [
            "ask {n} if she knows anyone else who needs a {svc}",
            "{f} was thrilled with the work, see if she will refer us",
            "offer {n} the maintenance package now that the {svc} is done",
            "suggest the extended plan to customers who just had a {svc}",
        ],
    },
    "marketing": {
        "campaign": [
            "put together a {mon} promotion for {svc} bookings",
            "we want a campaign around the {amt} off special",
            "build an email blast announcing the new {svc} service",
            "plan a seasonal push for {svc} before the weather turns",
            "announce our extended hours to the whole list",
        ],
        "social": [
            "write a {plat} post about our weekend sale",
            "something for {plat} showing the shop's new bay",
            "post about the {svc} special on {plat}",
            "we need a caption for the before-and-after photos",
            "put up something on {plat} for the holiday weekend",
        ],
        "content": [
            "write a paragraph about us for the website",
            "a short blog on why {svc} matters before winter",
            "copy for the new services page",
            "an article explaining what a {svc} actually involves",
            "write the about section for the new site",
        ],
        "reviews": [
            "ask the customers from {mon} to leave us a {plat} review",
            "respond to the {plat} review complaining about our pricing",
            "we need more {plat} reviews, put a request together",
            "reply to the two-star on {plat} about the wait",
        ],
        "seo_research": [
            "how do we rank better for {svc} in our area",
            "look at what the other shops charge for a {svc}",
            "what are competitors doing on {plat}",
            "give me search recommendations for the website",
        ],
    },
    "customer_service": {
        "question_reply": [
            "a customer asked whether we handle hybrids, write a reply",
            "{f} wants to know if we take walk-ins, answer her",
            "someone asked through the site about {svc} pricing, respond",
            "reply to the enquiry about whether we service fleet vehicles",
            "respond to the question about our warranty",
        ],
        "complaint": [
            "{n} is furious the {svc} did not hold, handle it carefully",
            "we have an upset customer over the {amt} charge",
            "{f} says the work was rushed and she is unhappy",
            "deal with the complaint about the scratch on the bumper",
            "customer is threatening to post about us, respond carefully",
        ],
        "apology_retention": [
            "apologise to {n} for keeping the car an extra day",
            "we let {f} down on timing, write something to smooth it over",
            "win back the customer who left after the billing mixup",
            "reach out to {n} who cancelled and was polite about it",
        ],
        "faq_warranty": [
            "someone wants to know if the {svc} is under warranty, reply",
            "answer the question about whether we price match",
            "{f} asked what our guarantee covers, write back",
            "a caller asked about parking, draft the reply",
            "reply to the enquiry about whether we do same-day {svc}",
        ],
        "escalation": [
            "this one needs a careful answer, the customer is threatening a chargeback",
            "{n} has emailed three times and is getting angrier, respond",
            "escalating complaint about the {amt} job, draft something measured",
            "the customer wants to speak to the owner, write the holding reply",
        ],
        "post_service": [
            "check in with {n} a week after her {svc}",
            "follow up with {f} to make sure the {svc} is holding up",
            "ask {n} how the {svc} has been since she collected the car",
        ],
    },
    "operations": {
        "booking": [
            "{n} called wanting a {svc} on {day} at {time}",
            "book {f} in for the {svc} she asked about",
            "get {n} on the schedule for {day}",
            "fit the {svc} in on {day} if we can",
            "{f} needs a slot for a {svc}, anything on {day}",
        ],
        "reschedule_cancel": [
            "move {n}'s appointment from {day} to the week after",
            "{f} cannot make {day}, find her another slot",
            "cancel the {time} on {day} and let the customer know",
            "push everything on {day} back an hour",
        ],
        "reminders": [
            "send {day}'s appointments their reminders",
            "remind everyone booked for {day} about their {time} slots",
            "day-before reminders for the {svc} bookings",
            "let {n} know her {svc} is still on for {day}",
        ],
        "status_notices": [
            "tell {n} her car is finished and ready to collect",
            "let {f} know the part came in",
            "we are closing early {day}, notify anyone booked",
            "the {svc} is running long, warn the {time} customer",
            "notify {n} that the job is done",
        ],
    },
    "invoicing": {
        "send_invoice": [
            "invoice {n} {amt} for the {svc}",
            "send {f} the bill for {mon}",
            "get the invoice out for the {svc} we finished",
            "bill {n} for the parts and the labour separately",
        ],
        "reminders": [
            "remind {n} about the outstanding {amt}",
            "{f}'s invoice is two weeks overdue, send a nudge",
            "chase the unpaid balance on the {svc}",
            "send a second notice on the {amt} from {mon}",
        ],
        "collections": [
            "escalate the past-due account for {n}",
            "final notice for the {amt} that has been outstanding since {mon}",
            "offer {f} a payment plan on the balance",
            "the {amt} is ninety days out now, what do we send",
        ],
        "receipts_disputes": [
            "{n} says she already paid, look into the {amt}",
            "send {f} a receipt for the {svc}",
            "there is a dispute on the {amt} charge, draft a response",
        ],
    },
    "accounting": {
        "revenue": [
            "what did we take in {mon}",
            "summarise revenue for {mon}",
            "how much came through in {mon} compared to the one before",
            "give me the numbers for {mon}",
            "where are we on receivables",
        ],
        "pricing": [
            "should we raise the price on {svc}",
            "our {svc} margin feels thin, look at pricing",
            "put together a pricing memo for the {svc} line",
            "we charge {amt} for a {svc}, is that right",
        ],
        "tax": [
            "what do we need for quarterly filings",
            "put together the tax prep checklist",
            "payroll taxes are due, what is outstanding",
            "which expenses from {mon} are deductible",
        ],
        "cashflow": [
            "how is cash flow looking into {mon}",
            "we have {amt} in outstanding invoices, what does that do to the month",
            "break down where the money went in {mon}",
            "forecast the next quarter based on {mon}",
        ],
    },
    "admin_records": {
        "note_record": [
            "note on {n}'s record that she prefers mornings",
            "log on {f}'s file that she wants text not calls",
            "add to {n}'s record that she approved the {svc}",
            "record on {f}'s account that she disputed the {amt}",
            "put a note on {n}'s file about the warranty conversation",
            "flag on {f}'s record that she is a fleet account",
        ],
        "documents": [
            "draft a service agreement for new customers",
            "write up our refund policy as a one-pager",
            "put together an intake form for the front desk",
            "we need a standard contract for fleet accounts",
            "draft the terms we hand out with every {svc}",
        ],
        "sop": [
            "write the closing checklist for the shop",
            "document how we handle a {svc} from drop-off to pickup",
            "put our warranty process into a written procedure",
            "a step-by-step for onboarding a new fleet account",
        ],
        "record_lookup_cleanup": [
            "which contact number is showing on our listing",
            "the customer list has duplicates, clean it up",
            "is the address on our profile still the old unit",
            "pull up what we have on {n}",
            "our business hours on file are wrong",
        ],
    },
    "people": {
        "hiring": [
            "post a hiring ad for a {role}",
            "we need a {role}, write the job listing",
            "put an ad up for a weekend {role}",
            "advertise the {role} opening",
            "write the posting for the {role} position",
        ],
        "training": [
            "put together a training checklist for a new {role}",
            "we need an onboarding doc for the {role}",
            "write up how a {role} should handle phone bookings",
            "training material for the new hires starting {mon}",
        ],
        "hr": [
            "write up the {role} who has been late three times",
            "memo to the team about the new time-off policy",
            "{f} keeps missing shifts, document it",
            "announce the schedule change to staff",
        ],
        "staff_admin": [
            "add our new employee to payroll",
            "get the new {role} set up on the rota",
            "who is covering {day} and {time}",
            "sort out the team schedule for {mon}",
            "let the crew know about the holiday roster",
        ],
    },
}

# --- Boundary contrasts ------------------------------------------------------
# Authored as explicit pairs. These are the cases where a subject noun points
# one way and the task points another, and they are the reason the whole
# intent/subject distinction exists.
BOUNDARY_PAIRS: list[tuple[str, str, str, str]] = [
    ("post a hiring ad for a mechanic", "people", "post our weekend sale", "marketing"),
    ("payroll taxes are due this quarter", "accounting", "add our new employee to payroll", "people"),
    ("note on {n}'s record that she approved the quote", "admin_records", "put together a quote for {n}", "sales"),
    ("what did we invoice in {mon}", "accounting", "send {n} the invoice for the {svc}", "invoicing"),
    ("reply to the customer asking about {svc} pricing", "customer_service", "email {n} our new {svc} pricing", "sales"),
    ("write a post about the {role} opening", "people", "write a post about the {svc} special", "marketing"),
    ("log the complaint on {n}'s record", "admin_records", "respond to {n}'s complaint", "customer_service"),
    ("book {n} in for {day}", "operations", "invoice {n} for {day}'s work", "invoicing"),
    ("draft our refund policy document", "admin_records", "refund {n} the {amt}", "invoicing"),
    ("training doc for handling angry customers", "people", "handle this angry customer", "customer_service"),
    ("what do we charge for a {svc}", "accounting", "quote {n} for a {svc}", "sales"),
    ("remind {n} about her appointment", "operations", "remind {n} about her unpaid invoice", "invoicing"),
    ("ask {n} for a {plat} review", "marketing", "reply to {n}'s {plat} review", "marketing"),
    ("schedule the team for {mon}", "people", "schedule {n} for a {svc}", "operations"),
    ("write the contract template", "admin_records", "write the campaign copy", "marketing"),
    ("our costs went up, review pricing", "accounting", "tell customers prices are going up", "marketing"),
    ("note that {f} paid in cash", "admin_records", "chase {f} for payment", "invoicing"),
    ("onboarding checklist for a new {role}", "people", "intake form for a new customer", "admin_records"),
]

# --- Surface transforms ------------------------------------------------------

CONVERSATIONAL = [
    "hey, can you {}", "when you get a sec, {}", "i need you to {}", "could you {}",
    "morning - {}", "quick one: {}", "if you have time, {}", "would you mind, {}",
]
LONG_CONTEXT = [
    " {} - we are slammer than usual this week so it slipped",
    " {}. been meaning to do it since {mon} honestly",
    " {}, the shop has been chaos and this keeps falling off the list",
    " {} - she has been a customer for years so worth doing properly",
    " {}. not urgent but do not want it forgotten",
]
TYPO_MAP = {
    "receive": "recieve", "separate": "seperate", "tomorrow": "tommorow",
    "appointment": "apointment", "invoice": "invocie", "schedule": "schedual",
    "definitely": "definately", "customer": "custmer", "quote": "quotte",
    "the": "teh", "and": "adn", "your": "you're",
}


def _typo(text: str, rng: random.Random) -> str:
    words = text.split()
    swapped = False
    for i, w in enumerate(words):
        base = w.strip(".,'").lower()
        if base in TYPO_MAP and rng.random() < 0.8:
            words[i] = w.lower().replace(base, TYPO_MAP[base])
            swapped = True
            break
    if not swapped:
        # Drop or transpose a character in a longer word.
        idxs = [i for i, w in enumerate(words) if len(w) > 5]
        if idxs:
            i = rng.choice(idxs)
            w = words[i]
            c = rng.randrange(1, len(w) - 1)
            words[i] = w[:c] + w[c + 1:] if rng.random() < 0.5 else w[:c] + w[c + 1] + w[c] + w[c + 2:]
    return " ".join(words)


def _apply_style(text: str, style: str, rng: random.Random) -> str:
    if style == "plain":
        return text[0].upper() + text[1:] + "."
    if style == "terse":
        t = text.replace(" the ", " ").replace(" a ", " ").replace(" our ", " ")
        return t.lower()
    if style == "conversational":
        return rng.choice(CONVERSATIONAL).format(text)
    if style == "long_context":
        # Resolve the frame's own month slot before formatting, so `.format`
        # only ever sees the one positional field it is meant to fill.
        frame = rng.choice(LONG_CONTEXT).replace("{mon}", rng.choice(MONTHS))
        return frame.format(text[0].upper() + text[1:]).strip()
    if style == "typo":
        return _typo(text[0].upper() + text[1:], rng) + "."
    if style == "shouty":
        return text.upper()
    return text


STYLES = ["plain", "terse", "conversational", "long_context", "typo", "plain", "terse", "shouty"]


def _tpl_hash(template: str) -> str:
    """Stable across processes. `hash()` is salted per interpreter run, which
    would make the grouping key — and therefore the cross-validation folds —
    differ between runs of a script whose whole point is reproducibility."""
    return hashlib.sha1(template.encode()).hexdigest()[:8]


def _fill(template: str, rng: random.Random) -> str:
    name = rng.choice(NAMES)
    return (
        template
        .replace("{n}", name)
        .replace("{f}", name.split()[0])
        .replace("{svc}", rng.choice(ALL_SERVICES))
        .replace("{amt}", rng.choice(AMOUNTS))
        .replace("{day}", rng.choice(DAYS))
        .replace("{time}", rng.choice(TIMES))
        .replace("{ch}", rng.choice(CHANNELS))
        .replace("{plat}", rng.choice(PLATFORMS))
        .replace("{role}", rng.choice(ROLES))
        .replace("{mon}", rng.choice(MONTHS))
    )


def build(per_department: int = 150) -> list[dict]:
    """
    Fill each department to roughly `per_department` examples.

    Balancing per DEPARTMENT rather than per template matters: departments do
    not have equal numbers of authored families, so a flat round-robin over
    templates would permanently under-sample whichever department has the
    narrowest surface — and that is exactly the department a macro-F1 score
    then punishes the model for.
    """
    rng = random.Random(SEED)
    rows: list[dict] = []
    style_i = 0

    for dept, fams in TEMPLATES.items():
        plan = [(family, tpl) for family, tpls in fams.items() for tpl in tpls]
        rng.shuffle(plan)
        made = 0
        attempts = 0
        while made < per_department and attempts < per_department * 12:
            for family, tpl in plan:
                if made >= per_department:
                    break
                attempts += 1
                style = STYLES[style_i % len(STYLES)]
                style_i += 1
                ask = _apply_style(_fill(tpl, rng), style, rng)
                rows.append({
                    "ask": ask,
                    "department_label": dept,
                    "family": family,
                    "style": style,
                    # Provenance, for grouped cross-validation. Random k-fold on
                    # templated data splits the SAME template across folds and
                    # reports memorisation as generalisation: the first run of
                    # this experiment scored CV macro-F1 0.998 against 0.70 on
                    # real validation data. Grouping by template closes that gap.
                    "template_id": f"{dept}:{family}:{_tpl_hash(tpl)}",
                })
                made += 1

    # Boundary contrasts, both halves, several fills each.
    for a_tpl, a_dept, b_tpl, b_dept in BOUNDARY_PAIRS:
        for _ in range(4):
            for tpl, dept in ((a_tpl, a_dept), (b_tpl, b_dept)):
                style = STYLES[style_i % len(STYLES)]
                style_i += 1
                rows.append({
                    "ask": _apply_style(_fill(tpl, rng), style, rng),
                    "department_label": dept,
                    "family": "boundary_contrast",
                    "style": style,
                    "template_id": f"{dept}:boundary:{_tpl_hash(tpl)}",
                })

    # De-duplicate within the training set itself.
    seen: set[str] = set()
    unique: list[dict] = []
    for r in rows:
        key = " ".join(r["ask"].lower().split())
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    return unique


def drop_eval_overlaps(rows: list[dict], threshold: float = 0.8) -> tuple[list[dict], list[dict]]:
    """
    Remove any generated row that collides with a validation or test ask.

    Authoring templates without consulting the benchmark is not a guarantee of
    independence — two people describing the same small-business task will
    sometimes land on the same sentence, and one did: an early version of this
    generator produced "what phone number do we have on file for the business"
    against a frozen "what phone number do we have on file for the shop?".
    Rewriting that template fixed the instance. This filter fixes the class,
    for every template anyone adds later.
    """
    from datasets import Split, find_overlaps, load_test, load_validation  # local import: keeps this file runnable standalone

    split = Split("generated", DATASET_VERSION, [r["ask"] for r in rows], [r["department_label"] for r in rows])
    bad: set[int] = set()
    dropped: list[dict] = []
    for other in (load_validation(), load_test()):
        for o in find_overlaps(split, other, threshold):
            if o.train_index not in bad:
                bad.add(o.train_index)
                dropped.append({"ask": o.train_ask, "collided_with": o.other_ask, "id": o.other_id, "similarity": o.similarity})
    return [r for i, r in enumerate(rows) if i not in bad], dropped


def main() -> None:
    rows = build()
    rows, dropped = drop_eval_overlaps(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")

    from collections import Counter
    print(f"{len(rows)} examples -> {OUT}")
    print(f"dropped for overlapping an evaluation ask: {len(dropped)}")
    for d in dropped:
        print(f"  sim={d['similarity']} {d['ask'][:60]!r} ~ {d['collided_with'][:60]!r} ({d['id']})")
    print("by department:", dict(Counter(r["department_label"] for r in rows).most_common()))
    print("by style:     ", dict(Counter(r["style"] for r in rows).most_common()))
    print("families:     ", len({r["family"] for r in rows}))


if __name__ == "__main__":
    main()
