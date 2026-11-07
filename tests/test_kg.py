from tower.kg import kg


def test_graph_covers_every_class():
    s = kg().stats()
    for cls in ["Supplier", "Part", "Model", "Plant", "Shipment", "Lot", "ProductionOrder",
                "CustomerOrder", "Customer", "Dealer", "Vehicle", "LoanerPool", "WorkDay", "Alias"]:
        assert s["by_class"].get(cls, 0) > 0, cls
    assert s["nodes"] > 16000


def test_typed_navigation():
    g = kg()
    assert g.out("Shipment:SH-0182", "CARRIES") == ["Part:CAM-360"]
    assert g.out("Shipment:SH-0182", "DELIVERS_TO") == ["Plant:P_IN"]
    assert set(g.out("Part:CAM-360", "IN_BOM_OF")) == {"Model:SUMMIT", "Model:VOYAGER"}
    assert "Plant:P_TX" in g.out("Alias:the texas plant", "ALIAS_OF")
