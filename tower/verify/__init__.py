"""The three gates every plan passes before execution: ICE, TWIN, CROSSCHECK."""
from __future__ import annotations

from . import crosscheck, ice, twin


def verify(plan) -> dict:
    ice_res = ice.check(plan)
    cross = []
    for wo in plan.orders:
        inc = wo.incident
        if inc.kind == "supplier_delay":
            r = crosscheck.compare(wo.impact, inc.kind, shipment_id=inc.shipment_id, new_eta=inc.end)
        elif inc.kind == "plant_outage":
            r = crosscheck.compare(wo.impact, inc.kind, plant_id=inc.plant, start=inc.start, end=inc.end)
        else:
            r = crosscheck.compare(wo.impact, inc.kind, lot_ids=inc.lot_ids)
        cross.append({"incident": wo.incident_no, **r})
    tw = twin.dry_run(plan.event["event_id"], plan.packets)
    ice_ok = not ice.blocking(ice_res)
    cross_ok = all(c["agree"] for c in cross)
    for p in plan.packets:
        p.proof.update({"ice": "pass" if ice_ok else "blocked",
                        "crosscheck": "agree" if cross_ok else "disagree"})
    return {"ok": ice_ok and cross_ok and tw["ok"], "ice": ice_res, "crosscheck": cross, "twin": tw}
