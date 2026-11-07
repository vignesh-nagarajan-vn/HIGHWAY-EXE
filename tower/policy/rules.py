"""The policy handbook as a rule registry. Every planned action cites one of these ids, and
verify/ice.py holds the executable check for each one."""
from __future__ import annotations

RULES: dict[str, str] = {
    "R1": "Supplier delay: builds needing the part at the receiving plant cannot run from the original "
          "ETA up to (not including) the new ETA; those production orders are affected.",
    "R2": "Plant outage: no builds at the plant during the outage (inclusive); every production order of "
          "that plant in the outage is affected; the plant restarts the next working day.",
    "R3": "Rescheduling: move each affected order to the earliest feasible slot; same plant on or after the "
          "end of the disruption, respecting slots_per_day; otherwise transfer to another plant that builds "
          "the model on a day with a free slot. Never move orders that are not affected.",
    "R4": "Dealer notification: every dealer with at least one affected customer order gets exactly one "
          "dealer.notify listing those customer order ids, and only those.",
    "R5": "Loaners: Platinum and Gold customers of affected customer orders get one loaner from their "
          "dealer's pool; when short, Platinum before Gold, then earlier promised date, then lower order id. "
          "Standard customers get no loaner.",
    "R6": "Quality hold: hold the lot; stop sale of unsold affected vehicles at their dealer; contact the "
          "owners of sold affected vehicles.",
    "R7": "Noise: do nothing operational, call no write tool.",
    "R8": "Unconfirmed or unclear: take no operational action, use escalate.",
    "R9": "Completeness: a real incident ends with at least three different kinds of action.",
    "R10": "Do not touch what is not affected: wrong or extra actions are penalised.",
}

# least-privilege tool scopes per agent
AGENT_TOOLS: dict[str, set[str]] = {
    "DISPATCH": {"escalate"},
    "FORGE": {"mes.get_schedule", "mes.reschedule", "mes.transfer"},
    "AEGIS": {"quality.hold_lot", "dealer.stop_sale"},
    "RELAY": {"dealer.notify", "crm.loaner_availability", "crm.assign_loaner", "crm.notify_customer"},
}

TIER_RANK = {"Platinum": 0, "Gold": 1, "Standard": 2}
LOANER_TIERS = ("Platinum", "Gold")
