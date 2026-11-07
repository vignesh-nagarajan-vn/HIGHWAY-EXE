"""The Wacky Wheels ontology: entity classes and typed relations.

Edges point in the direction an incident propagates (cause -> consequence), so every
impact question is a forward walk and every graph path reads left to right.
"""
from __future__ import annotations

NAMESPACE = "https://highway.exe/ontology#"

# class -> (description, id column / key)
CLASSES: dict[str, str] = {
    "Supplier": "A company that ships parts to our plants",
    "Part": "A component listed in a model's bill of materials",
    "Model": "A vehicle model (Pioneer, Summit, ...)",
    "Plant": "A factory with a fixed number of build slots per working day",
    "Shipment": "An inbound delivery of one part to one plant with an ETA",
    "Lot": "A batch of one part from one supplier, installed at one plant over a build window",
    "ProductionOrder": "A daily build order of one model at one plant",
    "CustomerOrder": "A customer's order promised from a production order",
    "Customer": "A buyer or owner, with a loyalty tier",
    "Dealer": "A dealership that sells vehicles and holds a loaner pool",
    "Vehicle": "A finished vehicle (VIN), sold or in stock",
    "LoanerPool": "A dealer's pool of loaner cars",
    "WorkDay": "A Monday-Friday working day in the planning calendar",
    "Alias": "A human nickname for an entity",
}

# relation -> (domain, range, meaning)
RELATIONS: dict[str, tuple[str, str, str]] = {
    "SENDS": ("Supplier", "Shipment", "supplier dispatches the shipment"),
    "CARRIES": ("Shipment", "Part", "shipment contains the part"),
    "DELIVERS_TO": ("Shipment", "Plant", "shipment is received by the plant"),
    "ARRIVES_ON": ("Shipment", "WorkDay", "planned ETA"),
    "SUPPLIES": ("Supplier", "Part", "supplier provides the part"),
    "IN_BOM_OF": ("Part", "Model", "the model's bill of materials includes the part"),
    "BUILDS": ("Plant", "Model", "plant is able to build the model"),
    "RUNS": ("Plant", "ProductionOrder", "production order is scheduled at the plant"),
    "BUILT_AS": ("Model", "ProductionOrder", "production order builds the model"),
    "SCHEDULED_ON": ("ProductionOrder", "WorkDay", "planned build day"),
    "PROMISED_TO": ("ProductionOrder", "CustomerOrder", "customer order is fulfilled by the production order"),
    "VIA_DEALER": ("CustomerOrder", "Dealer", "customer order is sold through the dealer"),
    "FOR_CUSTOMER": ("CustomerOrder", "Customer", "customer order belongs to the customer"),
    "PRODUCED": ("ProductionOrder", "Vehicle", "vehicle was built by the production order"),
    "AT_DEALER": ("Vehicle", "Dealer", "vehicle was distributed to the dealer"),
    "OWNED_BY": ("Vehicle", "Customer", "sold vehicle's owner"),
    "MADE": ("Supplier", "Lot", "supplier produced the lot"),
    "LOT_OF": ("Lot", "Part", "lot is a batch of the part"),
    "INSTALLED_AT": ("Lot", "Plant", "lot was installed at the plant"),
    "HAS_POOL": ("Dealer", "LoanerPool", "dealer's loaner pool"),
    "ALIAS_OF": ("Alias", "*", "nickname resolves to the entity"),
}


def node_id(cls: str, key: str) -> str:
    return f"{cls}:{key}"


def split_id(nid: str) -> tuple[str, str]:
    cls, _, key = nid.partition(":")
    return cls, key
