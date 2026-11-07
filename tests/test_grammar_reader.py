from tower.intake.grammar_reader import read, segments


def ev(text):
    return {"event_id": "T", "text": text}


def test_digest_is_split_into_incidents():
    r = read(ev("Two items. (1) Greensboro: power failure, dark from next Tuesday through next Wednesday. "
                "(2) Ridgeline says the compact wiring harness for Greensboro was due Mar 22, will now arrive Mar 24."))
    assert r.category == "operational"
    assert [i.kind for i in r.incidents] == ["plant_outage", "supplier_delay"]
    out, delay = r.incidents
    assert out.plant == "P_NC" and (out.date_from, out.date_to) == ("next Tuesday", "next Wednesday")
    assert delay.part == "HARN-C" and delay.supplier == "SUP-16"
    assert (delay.date_from, delay.date_to) == ("Mar 22", "Mar 24")


def test_quality_bulletin_with_ids():
    r = read(ev("Bulletin: Lot LOT-0042 (TIRE-17) at P_KY on vehicles built 2027-03-02 to 2027-03-03 is defective."))
    i = r.incidents[0]
    assert i.kind == "quality_hold" and i.lot_id == "LOT-0042" and i.plant == "P_KY"
    assert (i.date_from, i.date_to) == ("2027-03-02", "2027-03-03")


def test_rumor_and_noise():
    assert read(ev("Someone heard the brake kits might be late, nothing confirmed.")).category == "unconfirmed"
    assert read(ev("Dealer Tulsa, OK asks for the updated price sheet.")).category == "noise"


def test_segments_keep_plain_messages_whole():
    assert segments("Plain message without numbering.") == ["Plain message without numbering."]
