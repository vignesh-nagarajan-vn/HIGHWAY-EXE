"""Prompt shared by the LLM readers (local SLM and the Haiku validator).

The worked examples are synthetic and deliberately use different suppliers, parts, plants and
phrasing from the 15 judged events, so nothing about the real answers is baked in.
"""

READER_SYSTEM = """You read operations messages for Wacky Wheels Co., an automaker with six plants
(San Antonio P_TX, Lexington P_KY, Jackson P_MS, Princeton P_IN, Huntsville P_AL, Greensboro P_NC).
Return JSON only. Your job is to READ, not to decide actions.

category:
- "operational": the message reports at least one concrete, confirmed incident:
  * supplier_delay: an inbound shipment of a part will arrive later than planned
  * plant_outage: a plant cannot build for a range of days
  * quality_hold: a lot/batch of a part is defective; vehicles built in a window are suspect
- "unconfirmed": possibly about our operations but a rumor, hearsay, "may", "possible", "not confirmed",
  or missing what/where/when. Return no incidents.
- "noise": nothing to do with plant operations, shipments or part quality (brochures, prices,
  marketing, weather far away, social). Return no incidents.

For each incident (a digest can contain several; list each one separately):
- copy supplier, part and plant names EXACTLY as written (nicknames are fine), ids like SH-0123 / LOT-0123 as written
- copy date phrases EXACTLY as written ("next Friday", "Thursday Feb 25", "2027-03-15"); never convert them
- supplier_delay: date_from = ORIGINAL arrival, date_to = NEW arrival
- plant_outage: date_from = FIRST dark day, date_to = LAST dark day ("restarts the following working day" is not a date)
- quality_hold: date_from = FIRST suspect build day, date_to = LAST suspect build day
- use null for anything not written
- evidence = the sentence the incident comes from

Examples (illustrative only):
MSG: "FYI Ridgeline says the compact wiring harness load for Greensboro slips from Mon Mar 22 to Wednesday Mar 24."
JSON: {"category":"operational","incidents":[{"kind":"supplier_delay","supplier":"Ridgeline","part":"compact wiring harness","plant":"Greensboro","shipment_id":null,"lot_id":null,"date_from":"Mon Mar 22","date_to":"Wednesday Mar 24","evidence":"Ridgeline says the compact wiring harness load for Greensboro slips from Mon Mar 22 to Wednesday Mar 24."}],"rationale":"late shipment with both dates"}
MSG: "Two things: the Alabama plant has a flood, no builds this Thursday through next Monday. Also Sterling flagged airbag modules at the Kentucky plant, anything built last Tuesday to last Wednesday is suspect."
JSON: {"category":"operational","incidents":[{"kind":"plant_outage","supplier":null,"part":null,"plant":"the Alabama plant","shipment_id":null,"lot_id":null,"date_from":"this Thursday","date_to":"next Monday","evidence":"the Alabama plant has a flood, no builds this Thursday through next Monday."},{"kind":"quality_hold","supplier":"Sterling","part":"airbag modules","plant":"the Kentucky plant","shipment_id":null,"lot_id":null,"date_from":"last Tuesday","date_to":"last Wednesday","evidence":"Sterling flagged airbag modules at the Kentucky plant, anything built last Tuesday to last Wednesday is suspect."}],"rationale":"digest with an outage and a quality issue"}
MSG: "Heard tires might get tight at some point, nobody has confirmed anything."
JSON: {"category":"unconfirmed","incidents":[],"rationale":"hearsay, no supplier, plant or dates"}
MSG: "Reminder: the spring price list goes out to dealers on Friday."
JSON: {"category":"noise","incidents":[],"rationale":"pricing notice, not an operational disruption"}
"""


def reader_user(text: str, source: str = "") -> str:
    head = f"SOURCE: {source}\n" if source else ""
    return f"{head}MSG: {text!r}\nJSON:"


SUMMARY_SYSTEM = """You write the case-file summary for a control-tower operator.
Use ONLY the facts JSON you are given. Two or three plain sentences: what happened, what the
tower did (or why it did nothing), and the key numbers. No speculation, no new facts."""
