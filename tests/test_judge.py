from tower.ground.judge import ground_reading, judge
from tower.intake import grammar_reader
from tower.intake.schemas import EventReading, IncidentReading


def reading(*incs, cat="operational", reader="x"):
    return EventReading(category=cat, incidents=list(incs), reader=reader)


def test_graph_picks_the_reading_the_data_supports():
    # "next Friday" could be 3/12 or 3/19; only 3/19 is after the 3/15 ETA, so the graph decides.
    r = reading(IncidentReading(kind="supplier_delay", supplier="Quanta", part="infotainment chip",
                                plant="Princeton", date_from="next Monday", date_to="next Friday"))
    _, [inc] = ground_reading(r)
    assert inc.actionable and inc.shipment_id == "SH-0190"
    assert (inc.start, inc.end) == ("2027-03-15", "2027-03-19")


def test_digest_phrase_pinned_across_incidents():
    r = reading(
        IncidentReading(kind="plant_outage", plant="San Antonio", date_from="next Friday", date_to="Monday Mar 22"),
        IncidentReading(kind="supplier_delay", supplier="Quanta", part="infotainment chip", plant="Princeton",
                        date_from="next Monday", date_to="next Friday"))
    _, (out, delay) = ground_reading(r)
    assert out.actionable and (out.start, out.end, out.resume_on) == ("2027-03-19", "2027-03-22", "2027-03-23")
    assert delay.actionable


def test_quality_window_must_equal_whole_lots():
    r = reading(IncidentReading(kind="quality_hold", supplier="Kestrel", part="infotainment chip", plant="Jackson",
                                date_from="Thursday Feb 25", date_to="last Monday"))
    _, [inc] = ground_reading(r)
    assert inc.lot_ids == ["LOT-0130"]
    bad = reading(IncidentReading(kind="quality_hold", part="infotainment chip", plant="Jackson",
                                  date_from="Feb 26", date_to="Feb 27"))
    _, [inc2] = ground_reading(bad)
    assert not inc2.actionable and inc2.missing


def test_wrong_supplier_is_not_actionable():
    r = reading(IncidentReading(kind="supplier_delay", supplier="Kestrel", part="infotainment chip",
                                plant="Princeton", date_from="Mar 15", date_to="Mar 19"))
    _, [inc] = ground_reading(r)
    assert not inc.actionable
    assert any("does not ship" in m for m in inc.missing)


def test_agreement_between_readers():
    ev = {"event_id": "T", "text": "Plant operations alert: Wacky Wheels Lexington (P_KY) lost production to a "
                                   "power failure. Production is stopped from 2027-03-24 through 2027-03-25 inclusive."}
    a = grammar_reader.read(ev)
    b = a.model_copy(update={"reader": "slm"})
    v, _ = judge([a, b])
    assert v and v.agreement == "unanimous" and v.incidents[0].plant == "P_KY"
    c = reading(cat="noise", reader="slm")
    v2, _ = judge([a, c])
    assert v2 is None    # disagreement -> validator needed
