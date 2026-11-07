from datetime import date

from tower.ground import calendar as cal
from tower.ground.dates import find_mentions, resolve, resolve_one


def test_calendar_matches_vendor_helpers():
    from tower.vendor import enterprise
    for i in range(-10, 20):
        assert cal.date_of(i) == enterprise.idx_to_date(i)
        assert cal.idx_of(cal.date_of(i)) == i
    assert cal.today() == date(2027, 3, 8)
    assert cal.next_workday(date(2027, 3, 12)) == date(2027, 3, 15)


def test_next_and_last_weekday_convention():
    nf = resolve("next Friday")
    assert nf[0].value == date(2027, 3, 19) and nf[0].primary
    assert nf[1].value == date(2027, 3, 12) and not nf[1].primary
    assert resolve_one("next Monday") == date(2027, 3, 15)
    assert resolve_one("next Tuesday") == date(2027, 3, 16)
    assert resolve_one("next Thursday") == date(2027, 3, 18)
    assert resolve_one("last Monday") == date(2027, 3, 1)
    assert resolve_one("last Thursday") == date(2027, 3, 4)


def test_explicit_dates():
    assert resolve_one("2027-03-15") == date(2027, 3, 15)
    assert resolve_one("Thursday Feb 25") == date(2027, 2, 25)
    assert resolve_one("Monday Mar 22") == date(2027, 3, 22)
    assert resolve_one("Apr 1") == date(2027, 4, 1)
    assert resolve_one("March 29th") == date(2027, 3, 29)
    assert resolve_one("tomorrow") == date(2027, 3, 9)
    assert resolve("the following working day") == []


def test_find_mentions_in_messy_text():
    t = ("We're dark from next Friday through Monday Mar 22; the line restarts the following "
         "working day. Carrier says Thursday Apr 1 now. Was due 2027-03-15.")
    got = [m.text for m in find_mentions(t)]
    assert got == ["next Friday", "Monday Mar 22", "Thursday Apr 1", "2027-03-15"]
    assert [m.text for m in find_mentions("something may be off with a seat material")] == []
