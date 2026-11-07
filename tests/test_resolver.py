from tower.ground.resolver import resolve, scan, unique


def ids(cands):
    return [c.entity_id for c in cands]


def test_aliases_and_nicknames():
    assert ids(resolve("the Texas plant", "plant")) == ["P_TX"]
    assert ids(resolve("Huntsville", "plant")) == ["P_AL"]
    assert ids(resolve("Wacky Wheels Lexington (P_KY)", "plant")) == ["P_KY"]
    assert ids(resolve("Volt", "supplier")) == ["SUP-05"]
    assert ids(resolve("Quanta", "supplier")) == ["SUP-12"]
    assert ids(resolve("heavy-duty wiring harness", "part")) == ["HARN-B"]
    assert ids(resolve("60 kWh battery packs", "part")) == ["BATT-60"]
    assert ids(resolve("surround-view cameras", "part")) == ["CAM-360"]
    assert ids(resolve("CAM-360", "part")) == ["CAM-360"]
    assert ids(resolve("infotainment chip run", "part")) == ["CHIP-IVI"]


def test_vague_mentions_stay_ambiguous_or_unknown():
    assert unique(resolve("seat material", "part")) is None
    assert resolve("something electronic", "part") == [] or unique(resolve("something electronic", "part")) is None


def test_scan_free_text():
    s = scan("Quick heads up from Orbit: the surround-view cameras run for Huntsville can't make it.")
    assert ids(s["supplier"]) == ["SUP-11"]
    assert ids(s["part"]) == ["CAM-360"]
    assert ids(s["plant"]) == ["P_AL"]
    noise = scan("Dealer Amarillo, TX asks where to find the new brochure PDF.")
    assert not noise["plant"] and not noise["part"] and not noise["supplier"]
