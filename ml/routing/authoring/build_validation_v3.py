"""
Author the independent validation-v3 split.

This set is a *held-out routing label set*. It is not a model-selection split
and it is not a replacement for validation-v2. Frozen action-eval-v1.json is
not read, copied, or written by this file.

Independence rules (enforced, not asserted):

  * New template families (`v3:<dept>:<family>:<nn>`). None of these ids exist
    on train-v1, frozen, v1, or v2.
  * New surface styles and new asks — veterinary, bakery, photography, pest,
    tutoring, gym, grooming, catering, house-clean, moving, optometry,
    florist, locksmith, daycare, bike shop — not slot-fills of auto-shop
    train templates or paraphrases of frozen emails.
  * Hard-negative pairs live entirely inside this file (`v3_pair_*`).
  * No `none` label. The eight ML-router departments only.
  * `rationale` is human documentation. It is never a model feature.

If any authored template collides (exact / Jaccard >= 0.8 / template_id /
pair_id), the *whole template* is closed. A pair is never split across this
set and another split; if one half would drop, both drop.

Run:  python ml/routing/authoring/build_validation_v3.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from leakage_v3 import (  # noqa: E402
    filter_colliding_templates,
    leftover_jaccard_below_threshold,
    load_reference_splits,
)

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "agent-service/evals/datasets/validation/validation-v3.json"
REPORT = Path(__file__).resolve().parent / "baselines" / "validation-v3-leakage-report.json"

DEPARTMENTS = [
    "accounting",
    "admin_records",
    "customer_service",
    "invoicing",
    "marketing",
    "operations",
    "people",
    "sales",
]

CASES: list[dict] = []


def case(
    cid: str,
    ask: str,
    dept: str,
    stress: str,
    why: str,
    *,
    family: str,
    behavior: str | None = None,
    also_dept: list[str] | None = None,
    also_behavior: list[str] | None = None,
    pair: str | None = None,
    tags: list[str] | None = None,
) -> None:
    if dept not in DEPARTMENTS:
        raise ValueError(f"{cid}: {dept!r} is not in the 8-label space")
    row: dict = {
        "id": cid,
        "ask": ask,
        "expected_department": dept,
        "department_label": dept,
        "stress": stress,
        "rationale": why,
        "split": "validation",
        "template_id": f"v3:{dept}:{family}",
        "family": family,
        "tags": tags or [stress, "validation-v3"],
    }
    if behavior:
        row["expected_behavior"] = behavior
    if also_dept:
        row["acceptable_departments"] = also_dept
    if also_behavior:
        row["acceptable_behaviors"] = also_behavior
    if pair:
        row["pair_id"] = pair
    CASES.append(row)


# =============================================================================
# SALES — new-business pricing and outbound persuasion (not auto-shop quotes)
# =============================================================================

case("v3_sal_001",
     "Keiko Tanaka's golden retriever finished the cruciate consult; write the TPLO packet that lists hardware, overnight stay, and rehab visits as separate lines.",
     "sales", "novel_phrasing",
     "A written price packet for a named veterinary procedure is quote creation.",
     family="tplo_packet", behavior="draft_only", pair="v3_pair_tplo")
case("v3_sal_002",
     "The 80-person rehearsal dinner on the 19th still has no signed retainer. Draft the catering hold that locks the menu and the staffing minimum.",
     "sales", "high_evidence",
     "A retainer that locks scope and price is a sales proposal, not an invoice.",
     family="catering_retainer", behavior="draft_only")
case("v3_sal_003",
     "Willa Nguyen asked what a newborn session actually includes. Put the three-hour in-home bundle on one page with prints called out separately.",
     "sales", "high_evidence",
     "Itemising a photography package for a prospect is quoting.",
     family="newborn_bundle", behavior="draft_only")
case("v3_sal_004",
     "Nilesh Gupta vanished after the SAT diagnostic. Write the note that puts the Tuesday block back in front of him without stacking a discount.",
     "sales", "novel_phrasing",
     "Reopening a priced tutoring block is outbound sales follow-up.",
     family="sat_nudge", behavior="draft_only")
case("v3_sal_005",
     "Three independent pharmacies on Harbor asked about a weekly lobby arrangement. Draft the cold one-pager that prices stems plus Thursday swap-out.",
     "sales", "novel_phrasing",
     "Unsolicited pricing to new accounts is outbound sales.",
     family="pharmacy_lobby", behavior="draft_only")
case("v3_sal_006",
     "Harper Quinn's engagement gallery is done. Offer the linen album as an add-on before she leaves the proofing gallery.",
     "sales", "subject_intent_mismatch",
     "The gallery is a finished job; the ask is an upsell, not a marketing post.",
     family="album_addon", behavior="draft_only")
case("v3_sal_007",
     "Pax Holloway's bungalow failed the termite inspection. Price the exclusion skirt, bait stations, and the 90-day revisit as one package.",
     "sales", "high_evidence",
     "A bundled pest-exclusion proposal is a quote.",
     family="termite_exclusion", behavior="draft_only")
case("v3_sal_008",
     "Yasmin Farouk's sister wants the same floral arch from the June wedding. Draft the intro that names the arch, not a new consultation.",
     "sales", "novel_phrasing",
     "Referral outreach that restates a known package is sales.",
     family="arch_referral", behavior="draft_only")
case("v3_sal_009",
     "Enzo Ricci's wheel rebuild quote ages out on the 30th. Write the hold-the-number letter that expires with the month, not a booking.",
     "sales", "misleading_noun",
     "'Hold' sounds like a calendar hold; the object is the priced number.",
     family="wheel_hold_price", behavior="draft_only")
case("v3_sal_010",
     "Twelve families toured the toddler room in July and never paid the waitlist deposit. Write the one email that asks who is still in.",
     "sales", "department_boundary",
     "Re-engaging tour no-converts is sales; Operations owns the waitlist itself.",
     family="tour_reopen", behavior="draft_only", also_dept=["operations"])
case("v3_sal_011",
     "Cedric Blum is deciding between packing-only and a full studio move. Split labor hours and truck time on the page so the two options are comparable.",
     "sales", "high_evidence",
     "Two comparable move options with money on the page is quoting.",
     family="move_options", behavior="draft_only")
case("v3_sal_012",
     "Nadine Cho never signed the myopia-control plan after the consult. Ask whether she wants the overnight lenses or the daytime drops package.",
     "sales", "novel_phrasing",
     "Narrowing a priced clinical package is sales, not a medical record update.",
     family="myopia_plan", behavior="draft_only")
case("v3_sal_013",
     "Blythe Carmichael is stuck between the two-tier tasting and a cupcake tower. Write the note that makes her pick one for the 19th.",
     "sales", "novel_phrasing",
     "Forcing a menu decision on a priced catering option is sales.",
     family="tasting_vs_tower", behavior="draft_only")
case("v3_sal_014",
     "The HOA board asked for a quarterly rodent walk-through. Draft the neighborhood circuit proposal with per-building pricing.",
     "sales", "high_evidence",
     "A multi-building service proposal is new-business quoting.",
     family="hoa_circuit", behavior="draft_only")
case("v3_sal_015",
     "Otto Langford needs the house rekeyed after a roommate left, plus four extra keys. Put the cylinder count and key copies on one estimate.",
     "sales", "high_evidence",
     "A locksmith estimate with unit counts is a quote.",
     family="rekey_estimate", behavior="draft_only")
case("v3_sal_016",
     "A downtown gym asked whether we run a corporate on-ramp for their staff. Write the six-week assessment package aimed at that buyer, not consumers.",
     "sales", "novel_phrasing",
     "A B2B fitness package for a named prospect is sales.",
     family="corp_onramp", behavior="draft_only")
case("v3_sal_017",
     "Sable Ortiz loved the first deshed. Offer the six-visit membership before she books another one-off.",
     "sales", "department_boundary",
     "Membership conversion is sales; the next groom slot is Operations.",
     family="deshed_membership", behavior="draft_only", also_dept=["operations"])
case("v3_sal_018",
     "The Langford funeral is Thursday. Price the standing spray, the casket spray, and midday delivery as three lines.",
     "sales", "high_evidence",
     "Itemised sympathy florals are a quote.",
     family="funeral_spray", behavior="draft_only")
case("v3_sal_019",
     "Quinn Adler left the progressive-lens worksheet on the counter. Write the recap that restates the anti-fatigue coating price.",
     "sales", "low_evidence",
     "Restating an unsigned optical price is sales follow-up.",
     family="lens_recap", behavior="draft_only")
case("v3_sal_020",
     "The rehearsal-dinner couple is stalling on the staffing minimum. Write the note that keeps the date without cutting the crew.",
     "sales", "zero_evidence",
     "No quote noun; the shape is 'keep the deal intact'.",
     family="keep_the_date", behavior="draft_only")
case("v3_sal_021",
     "Ines Kovacs wants progressives and an anti-fatigue coat. Put both on the same worksheet with the upgrade called out.",
     "sales", "high_evidence",
     "An optical worksheet with an upgrade line is quoting.",
     family="progressive_sheet", behavior="draft_only")
case("v3_sal_022",
     "Two property managers on Pier 9 asked about a monthly lobby bouquet. Draft the standing-order sheet with swap day and vase rental.",
     "sales", "novel_phrasing",
     "A standing floral contract proposal is sales.",
     family="lobby_standing", behavior="draft_only")
case("v3_sal_023",
     "Felix Brandt's winter tune is priced; he asked if a new chain is extra. Write the one-line addendum that answers that before he ghosts.",
     "sales", "short_command",
     "A priced addendum on an existing bike-shop estimate is still a quote change.",
     family="chain_addendum", behavior="draft_only")
case("v3_sal_024",
     "Arjun Mehta cannot decide between the SAT block and essay-only hours. Write the comparison that prices both without recommending a school.",
     "sales", "multi_intent",
     "Two priced tutoring options in one ask; the task is the comparison sheet.",
     family="sat_vs_essay", behavior="draft_only")
case("v3_sal_025",
     "Mateo Ruiz wants a written number on the 12-week hypertrophy coaching before he talks to his spouse.",
     "sales", "novel_phrasing",
     "'Written number' on a coaching package is a quote request.",
     family="hypertrophy_number", behavior="draft_only")
case("v3_sal_026",
     "The bakery tasting for Blythe is still verbal. Turn it into a signed cake agreement with flavour, servings, and delivery window.",
     "sales", "high_evidence",
     "Converting a verbal tasting into a signed priced agreement is sales.",
     family="cake_agreement", behavior="draft_only")


# =============================================================================
# OPERATIONS — calendar, capacity, holds (not auto-shop bays)
# =============================================================================

case("v3_ops_001",
     "Hold Saturday 11:00 for Harper Quinn's engagement session and keep the golden-hour buffer after it.",
     "operations", "high_evidence",
     "A named calendar hold with a time is scheduling.",
     family="session_hold", behavior="clarification", also_behavior=["action"], pair="v3_pair_hold_vs_bill")
case("v3_ops_002",
     "Move the toddler-room tours off Monday; the licensing visitor is in the building that morning.",
     "operations", "novel_phrasing",
     "Bulk-moving tours for a site visit is schedule capacity, not marketing.",
     family="tour_shift", behavior="clarification")
case("v3_ops_003",
     "Keiko's golden cannot stay overnight the 12th; the isolation ward is already full. Offer the next two recovery nights.",
     "operations", "long_context",
     "Ward capacity and alternate nights are operations.",
     family="ward_capacity", behavior="clarification")
case("v3_ops_004",
     "Cancel Jonah Krieger's SAT block this Thursday and do not auto-fill the hour.",
     "operations", "high_evidence",
     "Cancelling a booked tutoring hour is scheduling.",
     family="block_cancel", behavior="clarification", also_behavior=["action"])
case("v3_ops_005",
     "Freeze Bodhi Ellison's gym access for six weeks while he is overseas; keep the locker until he is back.",
     "operations", "subject_intent_mismatch",
     "Freezing access and a locker is membership operations, not a billing instruction.",
     family="membership_hold", behavior="clarification", pair="v3_pair_membership_pause")
case("v3_ops_006",
     "Is the studio free Sunday at 7am for a newborn session, or is the heater still out?",
     "operations", "low_evidence",
     "A bare availability plus equipment constraint is operations.",
     family="studio_heat", behavior="direct_answer", also_behavior=["clarification"])
case("v3_ops_007",
     "Push every house-clean on the 14th by one day; the water main on Cedar is shut off.",
     "operations", "long_context",
     "Weather/utility delay across a route is operations.",
     family="water_main_shift", behavior="clarification")
case("v3_ops_008",
     "Park the pest truck at the Holloway bungalow first; the termite crew needs daylight on the skirt.",
     "operations", "novel_phrasing",
     "Crew sequencing against daylight is dispatch.",
     family="daylight_dispatch", behavior="clarification")
case("v3_ops_009",
     "Pull the next three daycare names off the August waitlist and assign rooms.",
     "operations", "high_evidence",
     "Waitlist-to-slot assignment is operations.",
     family="waitlist_pull", behavior="clarification", pair="v3_pair_waitlist_blast")
case("v3_ops_010",
     "Sable's deshed ran long; bump the 3pm nail-trim to 3:40 and text the next guardian.",
     "operations", "multi_intent",
     "A running-late bump plus a notice is still the schedule.",
     family="groom_slip", behavior="clarification")
case("v3_ops_011",
     "Block the bike stand all Friday morning; the wheel-true jig is being calibrated.",
     "operations", "zero_evidence",
     "No appointment noun; the request is shop-capacity blocking.",
     family="jig_block", behavior="clarification")
case("v3_ops_012",
     "Remind the Langford family that the funeral spray leaves the cooler at 10:15.",
     "operations", "department_boundary",
     "A timed pickup reminder is operations; the message is incidental.",
     family="cooler_reminder", behavior="draft_only", also_dept=["sales"])
case("v3_ops_013",
     "Can we take a same-day rekey at 4 if Otto brings the extra cylinders?",
     "operations", "short_command",
     "Same-day capacity against a constraint is operations.",
     family="same_day_rekey", behavior="direct_answer", also_behavior=["clarification"])
case("v3_ops_014",
     "Open a second tasting table on the 19th; the rehearsal dinner just jumped to 80.",
     "operations", "novel_phrasing",
     "Adding capacity for a known event is operations.",
     family="second_table", behavior="clarification")
case("v3_ops_015",
     "Nadine's myopia follow-up cannot be the same afternoon as the school screening bus.",
     "operations", "long_context",
     "A calendar conflict with an external bus is scheduling.",
     family="screening_clash", behavior="clarification")
case("v3_ops_016",
     "who has the loading dock tuesday after lunch",
     "operations", "typo",
     "A dock-time lookup is operations even with missing capitals.",
     family="dock_lookup", behavior="direct_answer", also_behavior=["clarification"])
case("v3_ops_017",
     "Cedric's movers cannot start until the elevator reservation is confirmed with the building.",
     "operations", "novel_phrasing",
     "A dependency on a building reservation is scheduling.",
     family="elevator_gate", behavior="clarification")
case("v3_ops_018",
     "Put the isolation kennel offline Thursday for the deep clean and reroute boarders.",
     "operations", "high_evidence",
     "Taking a kennel offline and rerouting is operations.",
     family="kennel_offline", behavior="clarification")
case("v3_ops_019",
     "Harper's golden-hour buffer collided with a newborn hold. Keep the engagement; slide the newborn.",
     "operations", "multi_intent",
     "Resolving two holds is the calendar, not a sales choice.",
     family="hold_collision", behavior="clarification")
case("v3_ops_020",
     "Do we still have a two-hour window Saturday for a move-out clean on Pier 4?",
     "operations", "low_evidence",
     "A window-availability question is operations.",
     family="pier_window", behavior="direct_answer", also_behavior=["clarification"])
case("v3_ops_021",
     "The florist van's cooler died. Stop new same-day deliveries until the spare unit is in.",
     "operations", "zero_evidence",
     "Halting a delivery channel is operational capacity.",
     family="cooler_halt", behavior="clarification")
case("v3_ops_022",
     "Set Arjun's makeup SAT hour to the unused Wednesday 6am slot.",
     "operations", "high_evidence",
     "Placing a makeup hour on the book is scheduling.",
     family="makeup_hour", behavior="clarification")
case("v3_ops_023",
     "Rain moved the outdoor family session. Offer Harper the covered atrium or the following Sunday.",
     "operations", "novel_phrasing",
     "Weather-moved session options are rescheduling.",
     family="rain_atrium", behavior="clarification")
case("v3_ops_024",
     "Lock the tutoring rooms during the fire-drill at 2 so nobody is mid-session.",
     "operations", "zero_evidence",
     "A drill blackout on rooms is operations.",
     family="drill_blackout", behavior="clarification")
case("v3_ops_025",
     "Idris Pell's lockout is waiting in the lot; slot him ahead of the scheduled rekey if the truck is back.",
     "operations", "long_context",
     "Queue priority for an emergency lockout is dispatch.",
     family="lockout_priority", behavior="clarification")
case("v3_ops_026",
     "Close the bakery counter at 2 on the 19th so plating for the rehearsal dinner can start.",
     "operations", "high_evidence",
     "Changing public hours for a private event is operations.",
     family="counter_close", behavior="clarification", also_dept=["marketing"])


# =============================================================================
# INVOICING — bills, deposits, chargebacks (not Wallace INV-*)
# =============================================================================

case("v3_inv_001",
     "Raise the TPLO invoice for Keiko Tanaka now that the overnight stay actually happened.",
     "invoicing", "misleading_noun",
     "Same animal and procedure as the sales packet; the instruction is to bill.",
     family="tplo_bill", behavior="draft_only", pair="v3_pair_tplo")
case("v3_inv_002",
     "Issue Harper Quinn the engagement-session invoice now that Saturday 11:00 is on the book.",
     "invoicing", "subject_intent_mismatch",
     "The hold is already made; this ask is to raise the bill.",
     family="session_bill", behavior="draft_only", pair="v3_pair_hold_vs_bill")
case("v3_inv_003",
     "Stop the monthly draft for Bodhi Ellison while the six-week travel hold is on.",
     "invoicing", "subject_intent_mismatch",
     "Same membership freeze; here the instruction is to stop charging.",
     family="membership_draft", behavior="clarification", pair="v3_pair_membership_pause")
case("v3_inv_004",
     "Assemble the chargeback packet for the wedding-cake card dispute, including the signed tasting sheet.",
     "invoicing", "high_evidence",
     "A card-dispute packet is collections documentation.",
     family="cake_chargeback", behavior="draft_only", pair="v3_pair_chargeback")
case("v3_inv_005",
     "Send the rehearsal-dinner catering invoice to the couple, not to the venue.",
     "invoicing", "high_evidence",
     "Directing a finished-job invoice to the payer is invoicing.",
     family="dinner_invoice", behavior="draft_only", pair="v3_pair_vendor_ap")
case("v3_inv_006",
     "CAT-4419 is 41 days out. Write the second notice for the termite exclusion, firm but not theatrical.",
     "invoicing", "high_evidence",
     "A named aging invoice and a second notice is collections.",
     family="cat4419_notice", behavior="draft_only")
case("v3_inv_007",
     "Blythe dropped a cash deposit for the two-tier cake; apply it to CAKE-208 and show the remaining balance.",
     "invoicing", "high_evidence",
     "Applying a deposit to a named bill is invoicing.",
     family="cake_deposit", behavior="clarification")
case("v3_inv_008",
     "split the moving bill so cedric's landlord pays the truck and he pays packing",
     "invoicing", "typo",
     "Splitting a bill across two payers is invoicing even with missing capitals.",
     family="split_move_bill", behavior="clarification")
case("v3_inv_009",
     "Resend the myopia-control invoice to Nadine; she says the portal never showed it.",
     "invoicing", "high_evidence",
     "Re-delivering a specific bill is invoicing.",
     family="myopia_resend", behavior="draft_only", also_behavior=["clarification"])
case("v3_inv_010",
     "Write off the no-show SAT hour for Jonah; he is not going to pay a missed-block fee.",
     "invoicing", "novel_phrasing",
     "Writing off a missed-block fee is an invoice-state change.",
     family="noshow_writeoff", behavior="clarification", also_dept=["accounting"])
case("v3_inv_011",
     "Add the extra key copies to Otto's rekey bill; he took four, not two.",
     "invoicing", "novel_phrasing",
     "A line-item amendment on an existing bill is invoicing.",
     family="key_line", behavior="clarification")
case("v3_inv_012",
     "The funeral spray was delivered; turn the verbal Langford number into a bill before Thursday closes.",
     "invoicing", "misleading_noun",
     "'Number' was a quote; the instruction is to bill a delivered job.",
     family="spray_to_bill", behavior="draft_only")
case("v3_inv_013",
     "money never landed for the HOA rodent walk-through",
     "invoicing", "zero_evidence",
     "No invoice noun; unpaid completed work is collections.",
     family="hoa_unpaid", behavior="clarification", also_dept=["accounting"])
case("v3_inv_014",
     "Mark GROOM-77 paid; Sable's guardian Venmo'd the deshed this morning.",
     "invoicing", "high_evidence",
     "Marking a named bill paid is invoicing.",
     family="groom_paid", behavior="clarification")
case("v3_inv_015",
     "Set a standing first-of-month invoice for the Pier 9 lobby bouquet once they sign.",
     "invoicing", "novel_phrasing",
     "Recurring billing setup is invoicing.",
     family="lobby_standing_bill", behavior="clarification")
case("v3_inv_016",
     "Give Willa 10 percent off the print package if she pays the session balance this week.",
     "invoicing", "multi_intent",
     "A discount-to-close on an open balance is invoicing.",
     family="print_discount", behavior="clarification")
case("v3_inv_017",
     "Receipt for Ines on the anti-fatigue coat; she needs it for her FSA.",
     "invoicing", "short_command",
     "A receipt for a completed optical add-on is invoicing.",
     family="fsa_receipt", behavior="draft_only", also_behavior=["clarification"])
case("v3_inv_018",
     "Pause the daycare tuition draft for the Solis family during the two-week closure.",
     "invoicing", "department_boundary",
     "Stopping a tuition draft is billing; the closure itself is operations.",
     family="tuition_pause", behavior="clarification", also_dept=["operations"])
case("v3_inv_019",
     "Felix still owes the chain addendum. Nudge the balance, not the tune itself.",
     "invoicing", "low_evidence",
     "A remaining-balance nudge is collections.",
     family="chain_balance", behavior="draft_only")
case("v3_inv_020",
     "Convert Arjun's unsigned SAT comparison into a bill only if he picks a track.",
     "invoicing", "ambiguous",
     "Conditional billing on an unsigned choice needs a pick first.",
     family="sat_conditional", behavior="clarification")
case("v3_inv_021",
     "The gym corporate on-ramp needs a deposit invoice to the downtown club, not to individual staff.",
     "invoicing", "high_evidence",
     "A deposit bill to a company payer is invoicing.",
     family="corp_deposit", behavior="draft_only")
case("v3_inv_022",
     "invoic the holloway exclusion once the skirt is in",
     "invoicing", "typo",
     "Misspelt; billing a completed exclusion still survives.",
     family="skirt_invoice", behavior="draft_only", also_behavior=["clarification"])
case("v3_inv_023",
     "Cedric's landlord rejected the truck half. Put the whole move back on Cedric's bill.",
     "invoicing", "long_context",
     "Reassigning a rejected split is invoicing.",
     family="reassign_truck", behavior="clarification")
case("v3_inv_024",
     "How much is still open on funeral work this week?",
     "invoicing", "department_boundary",
     "Open funeral balances are receivables; Accounting could also answer a period question.",
     family="funeral_open", behavior="direct_answer", also_dept=["accounting"])
case("v3_inv_025",
     "Draft a payment-plan offer for the 80-person dinner if they cannot clear the catering balance before the 19th.",
     "invoicing", "novel_phrasing",
     "A payment plan on an event balance is collections.",
     family="dinner_plan", behavior="draft_only")
case("v3_inv_026",
     "Credit the unused isolation night back to Keiko; the golden went home the same day.",
     "invoicing", "novel_phrasing",
     "A credit for unused boarding is an invoice adjustment.",
     family="isolation_credit", behavior="clarification")


# =============================================================================
# ACCOUNTING — books, tax, AP, margin (not 'revenue last week')
# =============================================================================

case("v3_acc_001",
     "Enter the flour supplier's bill from last Thursday into accounts payable; do not send it to the couple.",
     "accounting", "misleading_noun",
     "A vendor AP entry is accounting; the couple's catering bill is AR.",
     family="flour_ap", behavior="clarification", pair="v3_pair_vendor_ap")
case("v3_acc_002",
     "Get the quarterly 941 packet together for the CPA, including the two new sitters' wages.",
     "accounting", "department_boundary",
     "Payroll *tax* filings are accounting; putting sitters on Friday's run is People.",
     family="941_packet", behavior="clarification", also_behavior=["direct_answer"], pair="v3_pair_941")
case("v3_acc_003",
     "Did the second espresso machine pay back yet if we count only pastry-counter tickets?",
     "accounting", "novel_phrasing",
     "Payback on a capital asset by ticket type is finance.",
     family="espresso_payback", behavior="clarification", also_behavior=["direct_answer"])
case("v3_acc_004",
     "Break July's bakery take by wedding cakes versus counter walk-ins.",
     "accounting", "high_evidence",
     "Revenue segmentation by product line is accounting.",
     family="cake_vs_counter", behavior="direct_answer", also_behavior=["clarification"])
case("v3_acc_005",
     "Where is cash actually going after we started the overnight boarding?",
     "accounting", "zero_evidence",
     "No finance noun; the shape is an expense-flow question after a new service.",
     family="boarding_cash", behavior="clarification", also_behavior=["direct_answer"])
case("v3_acc_006",
     "Reconcile the Square batch from the tasting Saturday against the bank deposit.",
     "accounting", "high_evidence",
     "Card-batch-to-bank reconciliation is bookkeeping.",
     family="square_recon", behavior="clarification")
case("v3_acc_007",
     "Are we making money on TPLO recoveries once hardware and overnight wages are in?",
     "accounting", "misleading_noun",
     "TPLO is a clinical noun; profitability after costs is finance.",
     family="tplo_margin", behavior="direct_answer", also_behavior=["clarification"])
case("v3_acc_008",
     "Before I bag the deposit, peel the tax off this week's anti-fatigue coating upgrades and park it in the liability account.",
     "accounting", "misleading_noun",
     "Coating upgrades sound like sales; isolating tax into a liability account is finance.",
     family="optical_tax", behavior="clarification")
case("v3_acc_009",
     "How much did we spend on fresh stems in August versus what we billed in lobby contracts?",
     "accounting", "multi_intent",
     "Inventory spend versus billed standing orders is a leakage analysis.",
     family="stem_leakage", behavior="clarification", also_dept=["invoicing"])
case("v3_acc_010",
     "quarterly use-tax on the out-of-state jig parts?",
     "accounting", "short_command",
     "Use-tax on imported parts is a tax question.",
     family="use_tax_jig", behavior="direct_answer", also_behavior=["clarification"])
case("v3_acc_011",
     "The CPA wants 1099s for the Saturday DJ and the freelance decorator on the 19th.",
     "accounting", "high_evidence",
     "Contractor 1099 prep is accounting, not People hiring.",
     family="event_1099", behavior="clarification")
case("v3_acc_012",
     "cashflw after we floated the rehearsal dinner deposit",
     "accounting", "typo",
     "Misspelt cash-flow after floating a deposit.",
     family="floated_deposit", behavior="direct_answer", also_behavior=["clarification"])
case("v3_acc_013",
     "Lease versus buy the second photography strobe kit; I want the three-year comparison.",
     "accounting", "long_context",
     "Lease-versus-buy is a finance comparison.",
     family="strobe_lease", behavior="clarification")
case("v3_acc_014",
     "Track tip-out from the tasting counter separately from wages so the 941 stays clean.",
     "accounting", "department_boundary",
     "Tip classification for tax is accounting; the tip policy itself is People.",
     family="tip_out", behavior="clarification", also_dept=["people"])
case("v3_acc_015",
     "What did the corporate on-ramp actually contribute after we comped two assessments?",
     "accounting", "novel_phrasing",
     "Contribution after comps is margin analysis.",
     family="onramp_contribution", behavior="clarification", also_behavior=["direct_answer"])
case("v3_acc_016",
     "Are the Groupon redemptions covering the frosting and box cost, or are we donating cake?",
     "accounting", "misleading_noun",
     "Groupon sounds like marketing; the question is unit economics.",
     family="groupon_unit", behavior="direct_answer", also_dept=["marketing"])
case("v3_acc_017",
     "I need a monthly P&L that a bakery owner can read, not a 40-line export.",
     "accounting", "novel_phrasing",
     "A readable recurring P&L is a finance artefact.",
     family="readable_pl", behavior="clarification", also_behavior=["draft_only"])
case("v3_acc_018",
     "Deductions we might be missing on the van and the cooler unit.",
     "accounting", "high_evidence",
     "Tax-deduction review on named assets.",
     family="van_cooler_deduct", behavior="direct_answer", also_behavior=["clarification"])
case("v3_acc_019",
     "receivables on event work only",
     "accounting", "short_command",
     "A scoped receivables question; Invoicing also has a claim.",
     family="event_ar", behavior="clarification", also_dept=["invoicing"], also_behavior=["direct_answer"])
case("v3_acc_020",
     "Compare what the HOA circuit earns against drive time between buildings.",
     "accounting", "long_context",
     "Revenue versus travel cost is contribution analysis.",
     family="hoa_drive", behavior="clarification")
case("v3_acc_021",
     "Bookkeeping for the gift-card liability is behind again after the holiday boxes.",
     "accounting", "high_evidence",
     "Gift-card liability is a balance-sheet task.",
     family="gift_card_liability", behavior="clarification")
case("v3_acc_022",
     "Is the downtown gym contract cheaper for us if they prepay the six weeks?",
     "accounting", "zero_evidence",
     "Prepay-versus-monthly is a cash-timing / margin question.",
     family="prepay_math", behavior="clarification", also_dept=["sales"])
case("v3_acc_023",
     "The school-screening bus day wrecked optical volume. Show me the hour-by-hour take.",
     "accounting", "misleading_noun",
     "A screening bus is operations context; the ask is revenue by hour.",
     family="screening_hours", behavior="direct_answer", also_behavior=["clarification"])
case("v3_acc_024",
     "Should hardware for TPLO sit in COGS or inventory until the overnight starts?",
     "accounting", "long_context",
     "Cost classification of surgical hardware is accounting.",
     family="tplo_cogs", behavior="clarification")
case("v3_acc_025",
     "How much of August tutoring was unused-package liability versus earned hours?",
     "accounting", "novel_phrasing",
     "Deferred revenue versus earned hours is accounting.",
     family="unused_hours", behavior="direct_answer", also_behavior=["clarification"])
case("v3_acc_026",
     "Flag any sales-tax-exempt daycare invoices that are missing the certificate on file.",
     "accounting", "department_boundary",
     "Exemption certificates are a tax-compliance check; the file itself is Admin.",
     family="exempt_certs", behavior="clarification", also_dept=["admin_records"])


# =============================================================================
# CUSTOMER SERVICE — inbound replies and recovery (not Robert AC)
# =============================================================================

case("v3_cs_001",
     "A parent is furious we kept the toddler-room deposit after they cancelled Tuesday. Draft the reply that explains the 48-hour rule without escalating.",
     "customer_service", "high_evidence",
     "A private cancellation complaint is customer service.",
     family="deposit_anger", behavior="draft_only", pair="v3_pair_cancel_policy")
case("v3_cs_002",
     "Reply in the Instagram DM from the bride who says the two-tier cake leaned. Keep it off the public comments.",
     "customer_service", "subject_intent_mismatch",
     "A private inbound message is CS; the public Yelp thread is Marketing.",
     family="cake_dm", behavior="draft_only", pair="v3_pair_yelp_dm")
case("v3_cs_003",
     "Call the couple back and walk through the cake charge line-by-line; they think the tasting was free.",
     "customer_service", "misleading_noun",
     "Explaining a charge in a conversation is service recovery, not the chargeback packet.",
     family="charge_walkthrough", behavior="draft_only", pair="v3_pair_chargeback")
case("v3_cs_004",
     "Keiko says the golden's incision looks angry. Draft the after-hours message that does not diagnose over text.",
     "customer_service", "high_evidence",
     "An inbound post-op worry is customer service.",
     family="incision_worry", behavior="draft_only")
case("v3_cs_005",
     "someone left a voicemail ripping the wait at the optical desk",
     "customer_service", "low_evidence",
     "Inbound negative wait feedback; the task is a reply, not a review post.",
     family="optical_wait", behavior="clarification", also_behavior=["draft_only"])
case("v3_cs_006",
     "Answer the guardian who asked whether we can groom a dog on Apoquel without a vet note.",
     "customer_service", "novel_phrasing",
     "An inbound safety/policy question needs a reply.",
     family="apoquel", behavior="draft_only", also_behavior=["direct_answer"])
case("v3_cs_007",
     "Nilesh is polite but tight: the SAT hour felt rushed. Write the response that offers a makeup without admitting the tutor was unprepared.",
     "customer_service", "long_context",
     "A dissatisfied tutoring session needs a careful reply.",
     family="rushed_hour", behavior="draft_only")
case("v3_cs_008",
     "apologise to the holloways about the bait-station delay",
     "customer_service", "short_command",
     "An apology for a delayed pest visit is complaint handling.",
     family="bait_apology", behavior="draft_only", also_behavior=["clarification"])
case("v3_cs_009",
     "Willa says the newborn gallery is missing the sibling shots she was promised. Reply before she posts about it.",
     "customer_service", "high_evidence",
     "A missing-deliverable complaint is CS.",
     family="missing_sibling", behavior="draft_only")
case("v3_cs_010",
     "custmer sais the movers scuffed the elevator panel",
     "customer_service", "typo",
     "Property-damage complaint under misspelling.",
     family="elevator_scuff", behavior="clarification", also_behavior=["draft_only"])
case("v3_cs_011",
     "Reply to whoever asked if the daycare can give Benadryl without a signed form.",
     "customer_service", "novel_phrasing",
     "Inbound medication-consent question.",
     family="benadryl", behavior="clarification", also_behavior=["draft_only"])
case("v3_cs_012",
     "Deal with the florist delivery that went to the wrong funeral home.",
     "customer_service", "ambiguous",
     "A misdelivery with no named contact still needs recovery.",
     family="wrong_funeral", behavior="clarification")
case("v3_cs_013",
     "We over-plucked Sable's dog. I want to own that before the guardian comes back.",
     "customer_service", "zero_evidence",
     "No complaint noun; the shape is service recovery.",
     family="over_pluck", behavior="clarification", also_behavior=["draft_only"])
case("v3_cs_014",
     "Otto is locked out again and thinks we billed a second trip he did not authorise. Explain the after-hours fee.",
     "customer_service", "misleading_noun",
     "The fee is financial vocabulary; the task is explaining it to an upset customer.",
     family="afterhours_fee", behavior="draft_only", also_dept=["invoicing"])
case("v3_cs_015",
     "The tutoring parent wants a written recap of what Arjun still misses. Reply without turning it into a new quote.",
     "customer_service", "department_boundary",
     "A progress recap is a customer reply, not a new sales sheet.",
     family="progress_recap", behavior="draft_only", also_dept=["sales"])
case("v3_cs_016",
     "Someone asked whether the gym on-ramp includes a body-comp scan. Answer from what we actually offer.",
     "customer_service", "novel_phrasing",
     "Inbound scope question.",
     family="bodycomp", behavior="draft_only", also_behavior=["direct_answer"])
case("v3_cs_017",
     "Whatever we tell Harper about the rain move, do not promise the atrium lights will match golden hour.",
     "customer_service", "long_context",
     "A constraint on an outbound reply to a booked client.",
     family="atrium_promise", behavior="clarification", also_dept=["operations"])
case("v3_cs_018",
     "The Patel family tour question about nut-free rooms never got an answer.",
     "customer_service", "low_evidence",
     "An unanswered inbound; 'tour question' is the only signal.",
     family="nut_free", behavior="clarification", also_behavior=["draft_only"])
case("v3_cs_019",
     "Draft the reusable 'sorry the cooler delayed your bouquet' note.",
     "customer_service", "department_boundary",
     "Reusable apology copy: CS content, Admin-shaped artefact.",
     family="cooler_sorry", behavior="draft_only", also_dept=["admin_records"])
case("v3_cs_020",
     "Ring the three families whose kids cried at pickup this week.",
     "customer_service", "novel_phrasing",
     "Bulk service recovery, not a marketing blast.",
     family="pickup_tears", behavior="clarification")
case("v3_cs_021",
     "Tell the bride we will remake the leaning tier and will not refund the tasting.",
     "customer_service", "multi_intent",
     "A remedy plus a refusal in one outbound reply.",
     family="remake_no_refund", behavior="draft_only", also_dept=["invoicing"])
case("v3_cs_022",
     "why do guardians keep complaining about the lobby smell",
     "customer_service", "typo",
     "A pattern question about complaints.",
     family="lobby_smell", behavior="clarification", also_dept=["operations"], also_behavior=["direct_answer"])
case("v3_cs_023",
     "Felix thinks the new chain was installed without asking. Write the reply that shows the signed addendum.",
     "customer_service", "high_evidence",
     "A disputed add-on needs a customer reply pointing at the signed paper.",
     family="unsigned_chain", behavior="draft_only")
case("v3_cs_024",
     "Ines says the progressives make her nauseous. Draft the check-in that offers an adjustment visit, not a new sale.",
     "customer_service", "department_boundary",
     "Post-dispense discomfort is CS; a new lens package would be sales.",
     family="nauseous_lenses", behavior="draft_only", also_dept=["operations"])
case("v3_cs_025",
     "A property manager is annoyed the lobby bouquet arrived a day late. Reply and do not offer a free month.",
     "customer_service", "high_evidence",
     "A late standing-order complaint with a constraint.",
     family="late_bouquet", behavior="draft_only")
case("v3_cs_026",
     "Cedric's building emailed about pad protection. Answer them; he is not the complainant.",
     "customer_service", "novel_phrasing",
     "Inbound from a building, not the paying customer.",
     family="pad_protection", behavior="draft_only")


# =============================================================================
# MARKETING — public promo and reviews (not Facebook weekend hours)
# =============================================================================

case("v3_mkt_001",
     "Reply on Yelp to the one-star about the leaning wedding cake. Keep the remake offer out of the public thread.",
     "marketing", "high_evidence",
     "A public review response is marketing.",
     family="yelp_cake", behavior="draft_only", also_dept=["customer_service"], pair="v3_pair_yelp_dm")
case("v3_mkt_002",
     "Write the Groupon blurb for Saturday's cupcake-tower tasting, 12 servings, pickup only.",
     "marketing", "high_evidence",
     "Promotional deal copy is marketing.",
     family="groupon_tasting", behavior="draft_only", pair="v3_pair_indeed_groupon")
case("v3_mkt_003",
     "Blast the neighborhood list about leftover August toddler-room openings. Do not name waitlisted families.",
     "marketing", "subject_intent_mismatch",
     "A public leftover-capacity blast is marketing; pulling the waitlist is operations.",
     family="august_blast", behavior="draft_only", pair="v3_pair_waitlist_blast")
case("v3_mkt_004",
     "Post Harper's engagement highlights only after the photo-release is in the file.",
     "marketing", "subject_intent_mismatch",
     "Publishing highlights is marketing; filing the release is Admin.",
     family="engagement_post", behavior="draft_only", pair="v3_pair_photo_consent")
case("v3_mkt_005",
     "Ask Sable's guardian for a Google review of the deshed, not a testimonial we write ourselves.",
     "marketing", "high_evidence",
     "Review solicitation is marketing.",
     family="deshed_review_ask", behavior="draft_only")
case("v3_mkt_006",
     "Caption the before/after of the Holloway exclusion skirt for Nextdoor. No prices.",
     "marketing", "novel_phrasing",
     "Social proof content from a finished pest job.",
     family="skirt_nextdoor", behavior="draft_only")
case("v3_mkt_007",
     "summer SAT crash-course flyer",
     "marketing", "short_command",
     "Three tokens naming a seasonal campaign artefact.",
     family="sat_flyer", behavior="clarification", also_behavior=["draft_only"])
case("v3_mkt_008",
     "Tuesdays are dead at the gym and the studio two floors up started a sunrise yoga coupon, so I want something that reminds the building we exist before fall sign-ups.",
     "marketing", "long_context",
     "Competitive quiet-day narrative resolving to a campaign.",
     family="sunrise_coupon", behavior="draft_only", also_behavior=["clarification"])
case("v3_mkt_009",
     "Put a window board up about same-week newborn openings in September.",
     "marketing", "zero_evidence",
     "No campaign noun; a window board is point-of-sale promo.",
     family="window_newborn", behavior="draft_only")
case("v3_mkt_010",
     "How are the bakery reviews trending after the leaning-tier week?",
     "marketing", "novel_phrasing",
     "Review analytics, not a single reply.",
     family="review_trend", behavior="direct_answer", also_behavior=["clarification"])
case("v3_mkt_011",
     "Get the word out that the daycare is closed the week of the 14th for licensing.",
     "marketing", "subject_intent_mismatch",
     "Announces an operations closure; the task is the public notice.",
     family="closure_notice", behavior="draft_only", also_dept=["operations"])
case("v3_mkt_012",
     "newsleter for the optical back-to-school push",
     "marketing", "typo",
     "Misspelt newsletter for a seasonal optical campaign.",
     family="optical_newsletter", behavior="draft_only", also_behavior=["clarification"])
case("v3_mkt_013",
     "Something for the cooler door about funeral-spray lead times.",
     "marketing", "novel_phrasing",
     "Point-of-sale copy, not a document SOP.",
     family="cooler_door", behavior="draft_only")
case("v3_mkt_014",
     "Thank Blythe publicly for the five-star tasting note. Keep the menu off the post.",
     "marketing", "high_evidence",
     "Public review engagement.",
     family="blythe_thanks", behavior="draft_only")
case("v3_mkt_015",
     "Are the Nextdoor pest coupons actually turning into booked exclusions?",
     "marketing", "misleading_noun",
     "Sounds financial; it is campaign attribution.",
     family="nextdoor_attr", behavior="clarification", also_dept=["accounting"], also_behavior=["direct_answer"])
case("v3_mkt_016",
     "Draft a florist flyer aimed at Harbor-area funeral homes, not brides.",
     "marketing", "high_evidence",
     "Targeted B2B campaign material.",
     family="funeral_home_flyer", behavior="draft_only")
case("v3_mkt_017",
     "we shud be on the neighborhood parents slack",
     "marketing", "typo",
     "Channel-expansion idea, misspelt.",
     family="parents_slack", behavior="clarification")
case("v3_mkt_018",
     "Ask everyone who sat for a newborn session in August to leave a review, and separately list who still has an open print balance.",
     "marketing", "multi_intent",
     "A review ask plus a receivables side-list.",
     family="newborn_reviews_ar", behavior="clarification", also_dept=["invoicing"])
case("v3_mkt_019",
     "What do people say about the gym in places we do not read?",
     "marketing", "zero_evidence",
     "Reputation question with no marketing vocabulary.",
     family="unheard_rep", behavior="clarification", also_behavior=["direct_answer"])
case("v3_mkt_020",
     "Run the referral card for grooming again. I do not remember the last offer.",
     "marketing", "ambiguous",
     "A prior campaign referenced without reconstructable detail.",
     family="groom_referral", behavior="clarification")
case("v3_mkt_021",
     "Post the bike-stand calibration as a 'shop day' story so people know Friday mornings are closed.",
     "marketing", "department_boundary",
     "Explaining a closure to the public is marketing; the closure is operations.",
     family="shop_day_story", behavior="draft_only", also_dept=["operations"])
case("v3_mkt_022",
     "Write three Instagram stories for the rehearsal-dinner plating, no faces of guests.",
     "marketing", "high_evidence",
     "Social content with a privacy constraint.",
     family="plating_stories", behavior="draft_only")
case("v3_mkt_023",
     "SEO notes for the optometry site: myopia control pages are thin.",
     "marketing", "high_evidence",
     "On-page SEO recommendations.",
     family="myopia_seo", behavior="draft_only", also_behavior=["direct_answer"])
case("v3_mkt_024",
     "Ask Keiko if we may use the golden's recovery photos on the clinic wall. That is a public ask, not the chart note.",
     "marketing", "department_boundary",
     "Permission to display photos is a marketing consent ask.",
     family="wall_photos", behavior="draft_only", also_dept=["admin_records"])
case("v3_mkt_025",
     "Put together a September promotion for first-time lockout customers. No dollar amount yet.",
     "marketing", "high_evidence",
     "A first-time promo with the price unset is still a campaign brief.",
     family="lockout_promo", behavior="clarification", also_behavior=["draft_only"])
case("v3_mkt_026",
     "Reply to the three-star about the lobby smell. Do not mention the mop brand.",
     "marketing", "high_evidence",
     "Public review response with a constraint.",
     family="smell_review", behavior="draft_only", also_dept=["customer_service"])


# =============================================================================
# ADMIN_RECORDS — files, policies, consents (not Sarah prefers text)
# =============================================================================

case("v3_adm_001",
     "File Harper Quinn's signed photo-release before anyone posts a frame from the engagement set.",
     "admin_records", "high_evidence",
     "Filing a signed release is a records task.",
     family="photo_release_file", behavior="clarification", also_behavior=["action"], pair="v3_pair_photo_consent")
case("v3_adm_002",
     "Write the 48-hour cancellation policy for the daycare intake packets. Do not send it as a reply to the angry parent.",
     "admin_records", "misleading_noun",
     "Authoring a policy document is Admin; the angry parent is CS.",
     family="cancel_policy_doc", behavior="draft_only", pair="v3_pair_cancel_policy")
case("v3_adm_003",
     "Log that Keiko's golden is crate-rest only and that the guardian prefers voice notes after 8pm.",
     "admin_records", "novel_phrasing",
     "'Log that' is a chart/record update without the word record.",
     family="crate_rest_note", behavior="clarification", also_behavior=["action"])
case("v3_adm_004",
     "update the wrong felix in the bike shop file, not the one who bought the chain",
     "admin_records", "ambiguous",
     "A record edit that does not identify which Felix or what field.",
     family="wrong_felix", behavior="clarification")
case("v3_adm_005",
     "Nilesh's mother called to say the SAT scores go to a different email than the billing one, and she wants that stored where tutors will actually see it.",
     "admin_records", "long_context",
     "Narrative resolving to 'store this contact detail on the student file'.",
     family="score_email", behavior="clarification", also_behavior=["action"])
case("v3_adm_006",
     "Draft a reusable catering-allergens addendum we can staple to every rehearsal-dinner agreement.",
     "admin_records", "high_evidence",
     "A reusable legal/ops addendum is document authoring.",
     family="allergen_addendum", behavior="draft_only")
case("v3_adm_007",
     "Where do we keep the signed lockout authorisations after a roommate change?",
     "admin_records", "low_evidence",
     "Document retrieval; 'signed authorisations' is the signal.",
     family="lockout_auth_where", behavior="direct_answer", also_behavior=["clarification"])
case("v3_adm_008",
     "Put the new late-pickup fee schedule in writing for the toddler room.",
     "admin_records", "misleading_noun",
     "'Fee' is financial vocabulary; authoring the schedule is a document.",
     family="late_pickup_fee_doc", behavior="draft_only")
case("v3_adm_009",
     "recrd that the holloway bungalow has a dog door the bait stations must avoid",
     "admin_records", "typo",
     "Misspelt record instruction about a site constraint.",
     family="dog_door_note", behavior="clarification", also_behavior=["action"], also_dept=["operations"])
case("v3_adm_010",
     "Willa Nguyen and Willa Tran keep getting merged. Separate the newborn files.",
     "admin_records", "ambiguous",
     "A data-quality problem with no stated field mapping.",
     family="two_willas", behavior="clarification")
case("v3_adm_011",
     "Draft a one-pager on crate-rest rules to hand to TPLO guardians at discharge.",
     "admin_records", "department_boundary",
     "Document authoring with a clinical flavour; still a handout, not a sales packet.",
     family="crate_handout", behavior="draft_only", also_dept=["customer_service"])
case("v3_adm_012",
     "Keep a note that Blythe's cake may not contain almond extract.",
     "admin_records", "high_evidence",
     "A standing allergen preference on the customer file.",
     family="no_almond", behavior="clarification", also_behavior=["action"])
case("v3_adm_013",
     "Tidy the tutoring roster; half the students have two spellings.",
     "admin_records", "novel_phrasing",
     "Bulk record hygiene.",
     family="roster_dupes", behavior="clarification")
case("v3_adm_014",
     "Which gym members never gave us an emergency contact?",
     "admin_records", "novel_phrasing",
     "A completeness query over member records.",
     family="missing_ice", behavior="direct_answer", also_behavior=["clarification"])
case("v3_adm_015",
     "Write the closing checklist for the bakery after a private plating night.",
     "admin_records", "zero_evidence",
     "Internal procedure document; no customer-record vocabulary.",
     family="plating_closeout", behavior="draft_only", also_dept=["operations", "people"])
case("v3_adm_016",
     "Mark the downtown gym as a corporate account rather than a consumer walk-in.",
     "admin_records", "high_evidence",
     "Changing an account classification.",
     family="corp_flag", behavior="clarification", also_behavior=["action"])
case("v3_adm_017",
     "Attach the termite photos to the Holloway property file, not to Pax's personal card.",
     "admin_records", "novel_phrasing",
     "Associating artefacts with the right record.",
     family="termite_photos", behavior="clarification")
case("v3_adm_018",
     "Note on Ines's optical file that progressives made her nauseous, then stop. No email.",
     "admin_records", "multi_intent",
     "An explicit record-only instruction.",
     family="nausea_note_only", behavior="clarification", also_behavior=["action"])
case("v3_adm_019",
     "We should have something that says what happens when a mover scuffs a building.",
     "admin_records", "zero_evidence",
     "Policy document request with no document noun.",
     family="scuff_policy", behavior="draft_only", also_dept=["operations"], also_behavior=["clarification"])
case("v3_adm_020",
     "Get Nadine's insurance card on file before the myopia follow-up.",
     "admin_records", "subject_intent_mismatch",
     "Mentions a follow-up; the instruction is a record completion.",
     family="insurance_card", behavior="clarification", also_dept=["operations"])
case("v3_adm_021",
     "standing-order contract for the pier 9 lobby bouquet",
     "admin_records", "short_command",
     "A contract is a document; no verb.",
     family="lobby_contract", behavior="draft_only", also_behavior=["clarification"])
case("v3_adm_022",
     "Change Otto's after-hours number to the one he texted from during the lockout. We do not have that number in front of us.",
     "admin_records", "ambiguous",
     "A record edit whose new value is not actually held.",
     family="missing_number", behavior="clarification")
case("v3_adm_023",
     "Save the signed allergen addendum from the rehearsal-dinner couple.",
     "admin_records", "novel_phrasing",
     "Document filing.",
     family="save_addendum", behavior="clarification")
case("v3_adm_024",
     "put sable down as muzzle-only for face work",
     "admin_records", "short_command",
     "Terse handling-preference annotation.",
     family="muzzle_note", behavior="clarification", also_behavior=["action"])
case("v3_adm_025",
     "Draft the client-facing after-hours dropoff form for the clinic. This is not the CEU tracker.",
     "admin_records", "department_boundary",
     "A client form is Admin; the staff CEU tracker is People.",
     family="dropoff_form", behavior="draft_only", pair="v3_pair_ceu_form")
case("v3_adm_026",
     "Flag any daycare files missing the sales-tax exemption certificate so accounting can see the gap.",
     "admin_records", "department_boundary",
     "The file gap is Admin; the tax treatment is Accounting.",
     family="cert_gap", behavior="clarification", also_dept=["accounting"])


# =============================================================================
# PEOPLE — staff, hiring, training (not Craigslist mechanic)
# =============================================================================

case("v3_ppl_001",
     "Write the Indeed listing for a Saturday bakery assistant who can ice cupcakes and close the dishwasher.",
     "people", "high_evidence",
     "A job listing for a role is People, even though it will be 'posted'.",
     family="indeed_baker", behavior="draft_only", pair="v3_pair_indeed_groupon")
case("v3_ppl_002",
     "Add the two new evening sitters to Friday's direct-deposit run.",
     "people", "department_boundary",
     "Putting staff on a pay run is People; the 941 packet is Accounting.",
     family="sitter_deposit", behavior="clarification", pair="v3_pair_941")
case("v3_ppl_003",
     "Draft the CEU tracker the vet techs have to finish this year, including the anesthesia hours.",
     "people", "high_evidence",
     "Staff continuing-education tracking is People.",
     family="ceu_tracker", behavior="draft_only", pair="v3_pair_ceu_form")
case("v3_ppl_004",
     "What should I ask a candidate who would cover overnight lockouts alone?",
     "people", "short_command",
     "A hiring-question list for a night locksmith role.",
     family="locksmith_qs", behavior="draft_only", also_behavior=["clarification"])
case("v3_ppl_005",
     "Juniper Hale has been late to open the gym three times and the 6am regulars noticed. I need a conversation that is firm before it becomes a write-up.",
     "people", "long_context",
     "Narrative resolving to a staff coaching conversation.",
     family="late_open", behavior="draft_only", also_behavior=["clarification"])
case("v3_ppl_006",
     "List, in order, the rides a new florist driver has to sit shotgun on during week one.",
     "people", "high_evidence",
     "Onboarding sequence for a driver is People.",
     family="driver_shadow", behavior="draft_only", also_dept=["admin_records"])
case("v3_ppl_007",
     "The 19th dinner only has one plater on the crew. I need a second pair of hands or we plate late.",
     "people", "zero_evidence",
     "Staffing shortfall with no HR noun; Operations has a capacity claim.",
     family="plater_short", behavior="clarification", also_dept=["operations"])
case("v3_ppl_008",
     "hirng an evening tutor tonight, which forms dose the district want",
     "people", "typo",
     "Misspelt hiring/onboarding question about required forms.",
     family="tutor_paperwork", behavior="clarification", also_behavior=["direct_answer"])
case("v3_ppl_009",
     "Put Juniper's third late open into a formal note I can hand her at close.",
     "people", "high_evidence",
     "Formal disciplinary documentation.",
     family="late_writeup", behavior="draft_only")
case("v3_ppl_010",
     "What do evening sitters make at the other daycares on the harbor?",
     "people", "department_boundary",
     "Compensation benchmarking: staff subject, financial flavour.",
     family="sitter_rate", behavior="direct_answer", also_dept=["accounting"], also_behavior=["clarification"])
case("v3_ppl_011",
     "Post the Saturday bakery assistant role on Indeed and the shop Instagram, not a cupcake special.",
     "people", "misleading_noun",
     "Same channels as a promo; the subject is a vacancy.",
     family="assistant_channels", behavior="draft_only")
case("v3_ppl_012",
     "Sort the December holiday rota for the clinic so someone licensed is always on.",
     "people", "department_boundary",
     "Staff roster; Operations owns the appointment book.",
     family="holiday_rota", behavior="clarification", also_dept=["operations"])
case("v3_ppl_013",
     "Someone needs to tell the movers about the new pad-protection rule.",
     "people", "zero_evidence",
     "Internal staff communication, no HR keyword.",
     family="pad_briefing", behavior="draft_only", also_dept=["admin_records"])
case("v3_ppl_014",
     "Can the apprentice locksmith run a solo rekey, or does a licensed tech have to be on site?",
     "people", "novel_phrasing",
     "Supervision / qualification question.",
     family="solo_rekey", behavior="clarification", also_behavior=["direct_answer"])
case("v3_ppl_015",
     "Offer letter for the new optician starting the 15th, part-time, Tuesday through Saturday.",
     "people", "high_evidence",
     "Employment document.",
     family="optician_offer", behavior="draft_only", also_dept=["admin_records"])
case("v3_ppl_016",
     "The new baker keeps under-proofing the dinner rolls and I do not think anyone walked her through the overnight dough.",
     "people", "long_context",
     "A training-gap observation about a staff member.",
     family="underproof", behavior="clarification", also_behavior=["draft_only"])
case("v3_ppl_017",
     "Who is on the gym floor next Thursday at 6am?",
     "people", "department_boundary",
     "Staff rota lookup that reads like a schedule query.",
     family="floor_rota", behavior="clarification", also_dept=["operations"], also_behavior=["direct_answer"])
case("v3_ppl_018",
     "Time-off request from Kasper Lind for the last week of September; he is the only licensed pest tech that week.",
     "people", "high_evidence",
     "Leave management with a coverage constraint.",
     family="kasper_pto", behavior="clarification")
case("v3_ppl_019",
     "We need a staff handbook for the daycare that a licensing visitor would accept.",
     "people", "short_command",
     "Employee handbook — staff document with a compliance flavour.",
     family="licensing_handbook", behavior="draft_only", also_dept=["admin_records"])
case("v3_ppl_020",
     "The ER clinic offered our lead tech another two dollars an hour. What do we have to match to keep her?",
     "people", "novel_phrasing",
     "Retention counter-offer is People; the dollar math is secondary.",
     family="tech_retention", behavior="clarification", also_dept=["accounting"], also_behavior=["direct_answer"])
case("v3_ppl_021",
     "The three driver packets on my desk need a yes/no by Friday morning. Who is worth a sit-down?",
     "people", "high_evidence",
     "Candidate screening is People.",
     family="driver_screen", behavior="clarification")
case("v3_ppl_022",
     "Nobody wants Saturday night lockouts and I cannot leave the van unmanned.",
     "people", "zero_evidence",
     "Staffing constraint framed as coverage, not a calendar question.",
     family="saturday_lockout", behavior="clarification", also_dept=["operations"])
case("v3_ppl_023",
     "Background-check packet for the new evening sitter before she is left alone with toddlers.",
     "people", "high_evidence",
     "Hiring compliance artefact.",
     family="sitter_bg", behavior="draft_only", also_dept=["admin_records"])
case("v3_ppl_024",
     "Coach Hanae Mori on how to take a cake complaint without promising a remake.",
     "people", "novel_phrasing",
     "Staff coaching on complaint handling; the complaint itself is CS.",
     family="complaint_coach", behavior="draft_only", also_dept=["customer_service"])
case("v3_ppl_025",
     "Tip-pooling rules for the tasting counter so front and kitchen split the Saturday envelopes the same way.",
     "people", "department_boundary",
     "A tip-pool *policy for staff* is People; the 941 treatment is Accounting.",
     family="tip_pool_rules", behavior="draft_only", also_dept=["accounting"])
case("v3_ppl_026",
     "Write a one-shift safety briefing for the new mover about elevator pads and building keys.",
     "people", "high_evidence",
     "Staff safety briefing is People / training.",
     family="mover_safety", behavior="draft_only")


SCHEMA = {
    "id": "stable case id, prefixed v3_<dept>_<nn>",
    "ask": "the owner's request, verbatim - the ONLY thing given to a router",
    "expected_department": "one of the 8 department agent_ids; never none",
    "department_label": "same 8-label field the ML router trains on",
    "stress": "which routing boundary this case exists to probe",
    "expected_behavior": "draft_only | clarification | direct_answer (routing set; no action-layer tools)",
    "acceptable_departments": "other defensible departments, scored as correct",
    "acceptable_behaviors": "other defensible behaviours, scored as correct",
    "pair_id": "links the halves of a hard-negative pair; both halves live in this file",
    "template_id": "v3:<dept>:<family> — closed as a class on any leakage hit",
    "family": "intent family, not a train-v1 family id",
    "tags": "category labels for error analysis",
    "rationale": "why this label is correct - documentation only, never model input",
}

LEAKAGE_RULES = [
    "This split is independent of train-v1, action-eval-v1 (frozen 215), validation-v1, and validation-v2.",
    "Do not copy a case between this file and any of those sets in either direction.",
    "This set is NOT for model selection yet. Do not pick a router or report a winner from it.",
    "Frozen action-eval-v1.json was not modified, copied, or extended by this authoring path.",
    "Production routing (classify / classifyWithHaiku / classifyHeuristic) is unchanged.",
    "`rationale` and `stress` are documentation. Neither is a model feature.",
    "A colliding template is closed as a class. A pair is never split across sets.",
]


def _validate_pairs(rows: list[dict]) -> None:
    by_pair: dict[str, list[dict]] = {}
    for c in rows:
        if c.get("pair_id"):
            by_pair.setdefault(c["pair_id"], []).append(c)
    for pid, halves in by_pair.items():
        if len(halves) != 2:
            raise SystemExit(f"pair {pid} must have exactly 2 members, has {len(halves)}")
        depts = {h["expected_department"] for h in halves}
        if len(depts) < 2:
            raise SystemExit(f"pair {pid} does not cross departments: {depts}")


def main() -> None:
    seen: set[str] = set()
    for c in CASES:
        if c["id"] in seen:
            raise SystemExit(f"duplicate id {c['id']}")
        seen.add(c["id"])

    refs = load_reference_splits()
    filtered = filter_colliding_templates(CASES, refs)
    leftover = leftover_jaccard_below_threshold(filtered.kept, refs)
    filtered.leftover_near_duplicates = leftover

    if not (150 <= len(filtered.kept) <= 250):
        print(
            f"WARNING: kept n={len(filtered.kept)} is outside the 150-250 target. "
            "Reporting the honest count; not padding.",
            file=sys.stderr,
        )

    depts = Counter(c["expected_department"] for c in filtered.kept)
    missing = [d for d in DEPARTMENTS if depts[d] == 0]
    if missing:
        raise SystemExit(f"kept set is missing departments: {missing}")
    if any(c["expected_department"] == "none" or c["department_label"] == "none" for c in filtered.kept):
        raise SystemExit("none is not allowed on validation-v3")

    _validate_pairs(filtered.kept)

    payload = {
        "dataset_version": "action-eval-validation-v3",
        "frozen": False,
        "created": "2026-08-29",
        "independent_of": [
            "ml/routing/data/train-v1.jsonl",
            "agent-service/evals/datasets/action-eval-v1.json",
            "agent-service/evals/datasets/validation/validation-v1.json",
            "agent-service/evals/datasets/validation/validation-v2.json",
        ],
        "not_for_model_selection": True,
        "description": (
            "Independent routing validation split (workstream A). Authored for "
            "Milestone 6 as a held-out label set that does not reuse train-v1, "
            "the frozen 215-case action-eval-v1, validation-v1, or validation-v2. "
            "Eight department labels only; no `none`. Hard-negative pairs are "
            "complete inside this file. Leakage-checked with exact / Jaccard>=0.8 "
            "/ template_id / pair_id drop rules. Not for model selection yet. "
            "Frozen action-eval-v1.json was not modified. Production routing is "
            "unchanged."
        ),
        "leakage_rules": LEAKAGE_RULES,
        "schema": SCHEMA,
        "business_context": {
            "note": (
                "Routing-only set. Asks span veterinary, bakery, photography, "
                "pest, tutoring, gym, grooming, catering, house-clean, moving, "
                "optometry, florist, locksmith, and daycare owner surfaces. "
                "Not the Sunset Auto Care action-eval fixture. Routers receive "
                "only `ask`."
            )
        },
        "cases": filtered.kept,
        "leakage_filter": filtered.as_report(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    REPORT.write_text(json.dumps(filtered.as_report(), indent=2) + "\n")

    print(f"authored {len(CASES)}")
    print(f"kept     {len(filtered.kept)} -> {OUT.relative_to(REPO)}")
    print(f"dropped  {len(filtered.dropped)}")
    print(f"drop reasons: {filtered.drop_reasons or '{}'}")
    print(f"closed templates: {len(filtered.closed_templates)}")
    print(f"closed pairs (would-have-split): {filtered.closed_pairs or []}")
    print(f"leftover near-duplicates (0.55<=J<0.8): {len(leftover)}")
    print("\n  department      n")
    for d in DEPARTMENTS:
        print(f"    {d:<16}{depts[d]}")
    print("\n  stress axis            n")
    stress = Counter(c["stress"] for c in filtered.kept)
    for s, n in sorted(stress.items(), key=lambda kv: -kv[1]):
        print(f"    {s:<22}{n}")
    pairs = Counter(c.get("pair_id") for c in filtered.kept if c.get("pair_id"))
    print(f"\n  complete pairs: {len(pairs)}")
    for p, n in sorted(pairs.items()):
        print(f"    {p:<28}{n}")


if __name__ == "__main__":
    main()
