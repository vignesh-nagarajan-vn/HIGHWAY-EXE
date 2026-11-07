# HIGHWAY.EXE case files

## E-01 - RESOLVED

> Morning digest, two items. (1) San Antonio update: a software outage on the line. We're dark from next Friday through Monday Mar 22; the line restarts the following working day. (2) Quick heads up from Quanta: the infotainment chip run for Princeton can't make it next Monday. Carrier says next Friday now (severe weather on the route).

**Summary.** Late CHIP-IVI shipment SH-0190 to P_IN (ETA 2027-03-15 -> 2027-03-19): 8 production orders blocked, 8 rescheduled and 0 transferred; 67 customer orders at 29 dealers affected. P_TX dark 2027-03-19 to 2027-03-22 (restart 2027-03-23): 6 production orders blocked, 6 rescheduled and 0 transferred; 55 customer orders at 27 dealers affected. The tower sent one notice per affected dealer and assigned 26 loaners (4 entitled customers waitlisted, pools empty).

**Why.** 2 grounded incident(s) (readers: unanimous, slm, grammar)

**Graph path #1.** `Supplier:SUP-12 -SENDS-> Shipment:SH-0190 -CARRIES-> Part:CHIP-IVI -DELIVERS_TO-> Plant:P_IN -IN_BOM_OF-> 2xModel -BUILT_AS-> 8xProductionOrder -PROMISED_TO-> 67xCustomerOrder -VIA_DEALER-> 29xDealer -FOR_CUSTOMER-> 67xCustomer`

```
traceroute to SUPPLIER_DELAY via Shipment:SH-0190, 9 hops max
 1  anchor           Supplier:SUP-12
 2  -SENDS->         Shipment:SH-0190  (ETA 2027-03-15 -> 2027-03-19)
 3  -CARRIES->       Part:CHIP-IVI
 4  -DELIVERS_TO->   Plant:P_IN
 5  -IN_BOM_OF->     Model:2x [NOVA, VOYAGER]  (BOM filter at receiving plant)
 6  -BUILT_AS->      ProductionOrder:8x [PO-0316, PO-0318, PO-0319, ...]
 7  -PROMISED_TO->   CustomerOrder:67x [CO-01756, CO-01757, CO-01758, ...]
 8  -VIA_DEALER->    Dealer:29x [D01, D02, D04, ...]  (notify)
 9  -FOR_CUSTOMER->  Customer:67x [C0197, C0280, C0352, ...]  (loaner check)
```

**Graph path #2.** `Plant:P_TX -BUILT_AS-> 6xProductionOrder -PROMISED_TO-> 55xCustomerOrder -VIA_DEALER-> 27xDealer -FOR_CUSTOMER-> 55xCustomer`

```
traceroute to PLANT_OUTAGE via Plant:P_TX, 5 hops max
 1  anchor           Plant:P_TX  (dark 2027-03-19 .. 2027-03-22)
 2  -BUILT_AS->      ProductionOrder:6x [PO-0058, PO-0059, PO-0060, ...]
 3  -PROMISED_TO->   CustomerOrder:55x [CO-00247, CO-00248, CO-00249, ...]
 4  -VIA_DEALER->    Dealer:27x [D02, D04, D06, ...]  (notify)
 5  -FOR_CUSTOMER->  Customer:55x [C0330, C0667, C0718, ...]  (loaner check)
```

**Actions.** crm.assign_loaner x26, dealer.notify x41, mes.reschedule x14

## E-02 - ESCALATED - UNCONFIRMED

> Rumor from a supplier rep: something may be off with a seat material coming up. No dates, no details, nothing confirmed.

**Summary.** Unconfirmed report: possibly about our operations but unconfirmed or not specific. The tower escalated it to a human and changed nothing. Missing: a confirmed source, which part / plant / supplier, the dates affected.

**Why.** possibly about our operations but unconfirmed or not specific (readers: unanimous, slm, grammar)

**Missing intel.** a confirmed source; which part / plant / supplier; the dates affected

**Actions.** escalate x1

## E-03 - RESOLVED

> Quality alert: Kestrel says the infotainment chip sent to Jackson had a faulty weld. Anything built Thursday Feb 25 through last Monday is suspect.

**Summary.** Quality hold on LOT-0130 (CHIP-IVI installed at P_MS, built 2027-02-25 to 2027-03-01): lot held, 110 unsold vehicles stopped from sale, 150 owners of sold vehicles contacted.

**Why.** 1 grounded incident(s) (readers: unanimous, slm, grammar)

**Graph path #1.** `Supplier:SUP-06 -MADE-> Lot:LOT-0130 -LOT_OF-> Part:CHIP-IVI -IN_BOM_OF-> 3xModel -BUILT_AS-> 9xProductionOrder -PRODUCED-> 260xVehicle -AT_DEALER-> 37xDealer -OWNED_BY-> 150xCustomer`

```
traceroute to QUALITY_HOLD via Lot:LOT-0130, 8 hops max
 1  anchor           Supplier:SUP-06
 2  -MADE->          Lot:LOT-0130  (built 2027-02-25 .. 2027-03-01)
 3  -LOT_OF->        Part:CHIP-IVI
 4  -IN_BOM_OF->     Model:3x [NOVA, PIONEER, TERRA]
 5  -BUILT_AS->      ProductionOrder:9x [PO-0190, PO-0191, PO-0192, ...]  (at P_MS in window)
 6  -PRODUCED->      Vehicle:260x [AUR0002037, AUR0002038, AUR0002041, ...]  (110 in stock / 150 sold)
 7  -AT_DEALER->     Dealer:37x [D02, D03, D04, ...]  (stop sale)
 8  -OWNED_BY->      Customer:150x [C0022, C0038, C0088, ...]  (contact owners)
```

**Actions.** crm.notify_customer x150, dealer.stop_sale x37, quality.hold_lot x1

## E-04 - RESOLVED

> The Kentucky plant update: a software outage on the line. We're dark from next Tuesday through next Thursday; the line restarts the following working day.

**Summary.** P_KY dark 2027-03-16 to 2027-03-18 (restart 2027-03-19): 9 production orders blocked, 9 rescheduled and 0 transferred; 79 customer orders at 32 dealers affected. The tower sent one notice per affected dealer and assigned 18 loaners (4 entitled customers waitlisted, pools empty).

**Why.** 1 grounded incident(s) (readers: unanimous, slm, grammar)

**Graph path #1.** `Plant:P_KY -BUILT_AS-> 9xProductionOrder -PROMISED_TO-> 79xCustomerOrder -VIA_DEALER-> 32xDealer -FOR_CUSTOMER-> 79xCustomer`

```
traceroute to PLANT_OUTAGE via Plant:P_KY, 5 hops max
 1  anchor           Plant:P_KY  (dark 2027-03-16 .. 2027-03-18)
 2  -BUILT_AS->      ProductionOrder:9x [PO-0139, PO-0140, PO-0141, ...]
 3  -PROMISED_TO->   CustomerOrder:79x [CO-00717, CO-00718, CO-00719, ...]
 4  -VIA_DEALER->    Dealer:32x [D02, D03, D04, ...]  (notify)
 5  -FOR_CUSTOMER->  Customer:79x [C0063, C0205, C0214, ...]  (loaner check)
```

**Actions.** crm.assign_loaner x18, dealer.notify x32, mes.reschedule x9

## E-05 - NO ACTION - NOISE

> Dealer Amarillo, TX asks where to find the new brochure PDF.

**Summary.** Judged noise: not about plant operations, shipments or part quality. The tower took no action and called no tools.

**Why.** not about plant operations, shipments or part quality (readers: unanimous, slm, grammar)

**Actions.** none

## E-06 - NO ACTION - NOISE

> Dealer Little Rock, AR asks where to find the new brochure PDF.

**Summary.** Judged noise: not about plant operations, shipments or part quality. The tower took no action and called no tools.

**Why.** not about plant operations, shipments or part quality (readers: unanimous, slm, grammar)

**Actions.** none

## E-07 - NO ACTION - NOISE

> Dealer Pensacola, FL asks where to find the new brochure PDF.

**Summary.** Judged noise: not about plant operations, shipments or part quality. The tower took no action and called no tools.

**Why.** not about plant operations, shipments or part quality (readers: unanimous, slm, grammar)

**Actions.** none

## E-08 - RESOLVED

> Plant operations alert: Wacky Wheels Lexington (P_KY) lost production to a power failure. Production is stopped from 2027-03-24 through 2027-03-25 inclusive.

**Summary.** P_KY dark 2027-03-24 to 2027-03-25 (restart 2027-03-26): 6 production orders blocked, 6 rescheduled and 0 transferred; 56 customer orders at 25 dealers affected. The tower sent one notice per affected dealer and assigned 15 loaners.

**Why.** 1 grounded incident(s) (readers: unanimous, slm, grammar)

**Graph path #1.** `Plant:P_KY -BUILT_AS-> 6xProductionOrder -PROMISED_TO-> 56xCustomerOrder -VIA_DEALER-> 25xDealer -FOR_CUSTOMER-> 56xCustomer`

```
traceroute to PLANT_OUTAGE via Plant:P_KY, 5 hops max
 1  anchor           Plant:P_KY  (dark 2027-03-24 .. 2027-03-25)
 2  -BUILT_AS->      ProductionOrder:6x [PO-0157, PO-0158, PO-0159, ...]
 3  -PROMISED_TO->   CustomerOrder:56x [CO-00876, CO-00877, CO-00878, ...]
 4  -VIA_DEALER->    Dealer:25x [D02, D03, D05, ...]  (notify)
 5  -FOR_CUSTOMER->  Customer:56x [C0213, C0283, C0298, ...]  (loaner check)
```

**Actions.** crm.assign_loaner x15, dealer.notify x25, mes.reschedule x6

## E-09 - RESOLVED

> Quick heads up from Orbit: the surround-view cameras run for Huntsville can't make it Monday Mar 29. Carrier says Thursday Apr 1 now (a customs inspection).

**Summary.** Late CAM-360 shipment SH-0256 to P_AL (ETA 2027-03-29 -> 2027-04-01): 6 production orders blocked, 4 rescheduled and 2 transferred; 54 customer orders at 26 dealers affected. The tower sent one notice per affected dealer and assigned 10 loaners (2 entitled customers waitlisted, pools empty).

**Why.** 1 grounded incident(s) (readers: unanimous, slm, grammar)

**Graph path #1.** `Supplier:SUP-11 -SENDS-> Shipment:SH-0256 -CARRIES-> Part:CAM-360 -DELIVERS_TO-> Plant:P_AL -IN_BOM_OF-> 2xModel -BUILT_AS-> 6xProductionOrder -PROMISED_TO-> 54xCustomerOrder -VIA_DEALER-> 26xDealer -FOR_CUSTOMER-> 54xCustomer`

```
traceroute to SUPPLIER_DELAY via Shipment:SH-0256, 9 hops max
 1  anchor           Supplier:SUP-11
 2  -SENDS->         Shipment:SH-0256  (ETA 2027-03-29 -> 2027-04-01)
 3  -CARRIES->       Part:CAM-360
 4  -DELIVERS_TO->   Plant:P_AL
 5  -IN_BOM_OF->     Model:2x [SUMMIT, VOYAGER]  (BOM filter at receiving plant)
 6  -BUILT_AS->      ProductionOrder:6x [PO-0436, PO-0438, PO-0439, ...]
 7  -PROMISED_TO->   CustomerOrder:54x [CO-02567, CO-02568, CO-02569, ...]
 8  -VIA_DEALER->    Dealer:26x [D02, D03, D04, ...]  (notify)
 9  -FOR_CUSTOMER->  Customer:54x [C0378, C0448, C0458, ...]  (loaner check)
```

**Actions.** crm.assign_loaner x10, dealer.notify x26, mes.reschedule x4, mes.transfer x2

## E-10 - RESOLVED

> Huntsville line is waiting on 60 kWh battery packs from Lumen. Original drop was Monday Mar 29, new ETA is Thursday Apr 1 because of a truck breakdown.

**Summary.** Late BATT-60 shipment SH-0248 to P_AL (ETA 2027-03-29 -> 2027-04-01): 3 production orders blocked, 3 rescheduled and 0 transferred; 29 customer orders at 18 dealers affected. The tower sent one notice per affected dealer and assigned 7 loaners.

**Why.** 1 grounded incident(s) (readers: unanimous, slm, grammar)

**Graph path #1.** `Supplier:SUP-18 -SENDS-> Shipment:SH-0248 -CARRIES-> Part:BATT-60 -DELIVERS_TO-> Plant:P_AL -IN_BOM_OF-> Model:NOVA -BUILT_AS-> 3xProductionOrder -PROMISED_TO-> 29xCustomerOrder -VIA_DEALER-> 18xDealer -FOR_CUSTOMER-> 29xCustomer`

```
traceroute to SUPPLIER_DELAY via Shipment:SH-0248, 9 hops max
 1  anchor           Supplier:SUP-18
 2  -SENDS->         Shipment:SH-0248  (ETA 2027-03-29 -> 2027-04-01)
 3  -CARRIES->       Part:BATT-60
 4  -DELIVERS_TO->   Plant:P_AL
 5  -IN_BOM_OF->     Model:NOVA  (BOM filter at receiving plant)
 6  -BUILT_AS->      ProductionOrder:3x [PO-0437, PO-0440, PO-0443]
 7  -PROMISED_TO->   CustomerOrder:29x [CO-02575, CO-02576, CO-02577, ...]
 8  -VIA_DEALER->    Dealer:18x [D02, D04, D08, ...]  (notify)
 9  -FOR_CUSTOMER->  Customer:29x [C0208, C0466, C0979, ...]  (loaner check)
```

**Actions.** crm.assign_loaner x7, dealer.notify x18, mes.reschedule x3

## E-11 - RESOLVED

> Jackson update: a power failure. We're dark from Friday Mar 26 through Tuesday Mar 30; the line restarts the following working day.

**Summary.** P_MS dark 2027-03-26 to 2027-03-30 (restart 2027-03-31): 9 production orders blocked, 6 rescheduled and 3 transferred; 79 customer orders at 36 dealers affected. The tower sent one notice per affected dealer and assigned 17 loaners (1 entitled customers waitlisted, pools empty).

**Why.** 1 grounded incident(s) (readers: unanimous, slm, grammar)

**Graph path #1.** `Plant:P_MS -BUILT_AS-> 9xProductionOrder -PROMISED_TO-> 79xCustomerOrder -VIA_DEALER-> 36xDealer -FOR_CUSTOMER-> 79xCustomer`

```
traceroute to PLANT_OUTAGE via Plant:P_MS, 5 hops max
 1  anchor           Plant:P_MS  (dark 2027-03-26 .. 2027-03-30)
 2  -BUILT_AS->      ProductionOrder:9x [PO-0253, PO-0254, PO-0255, ...]
 3  -PROMISED_TO->   CustomerOrder:79x [CO-01460, CO-01461, CO-01462, ...]
 4  -VIA_DEALER->    Dealer:36x [D01, D02, D03, ...]  (notify)
 5  -FOR_CUSTOMER->  Customer:79x [C0203, C0209, C0244, ...]  (loaner check)
```

**Actions.** crm.assign_loaner x17, dealer.notify x36, mes.reschedule x6, mes.transfer x3

## E-12 - RESOLVED

> Subject: Shipment SH-0182 delayed
From: dispatch@orbit.example

Our shipment SH-0182 of CAM-360 (surround-view camera kit) for Wacky Wheels Princeton (P_IN) was due 2027-03-15 and will now arrive 2027-03-18. Reason: port congestion.

**Summary.** Late CAM-360 shipment SH-0182 to P_IN (ETA 2027-03-15 -> 2027-03-18): 3 production orders blocked, 3 rescheduled and 0 transferred; 26 customer orders at 14 dealers affected. The tower sent one notice per affected dealer and assigned 10 loaners.

**Why.** 1 grounded incident(s) (readers: unanimous, slm, grammar)

**Graph path #1.** `Supplier:SUP-11 -SENDS-> Shipment:SH-0182 -CARRIES-> Part:CAM-360 -DELIVERS_TO-> Plant:P_IN -IN_BOM_OF-> Model:VOYAGER -BUILT_AS-> 3xProductionOrder -PROMISED_TO-> 26xCustomerOrder -VIA_DEALER-> 14xDealer -FOR_CUSTOMER-> 26xCustomer`

```
traceroute to SUPPLIER_DELAY via Shipment:SH-0182, 9 hops max
 1  anchor           Supplier:SUP-11
 2  -SENDS->         Shipment:SH-0182  (ETA 2027-03-15 -> 2027-03-18)
 3  -CARRIES->       Part:CAM-360
 4  -DELIVERS_TO->   Plant:P_IN
 5  -IN_BOM_OF->     Model:VOYAGER  (BOM filter at receiving plant)
 6  -BUILT_AS->      ProductionOrder:3x [PO-0316, PO-0319, PO-0322]
 7  -PROMISED_TO->   CustomerOrder:26x [CO-01756, CO-01757, CO-01758, ...]
 8  -VIA_DEALER->    Dealer:14x [D01, D02, D06, ...]  (notify)
 9  -FOR_CUSTOMER->  Customer:26x [C0380, C0746, C1115, ...]  (loaner check)
```

**Actions.** crm.assign_loaner x10, dealer.notify x14, mes.reschedule x3

## E-13 - ESCALATED - UNCONFIRMED

> Someone on the floor mentioned a possible shortage of something electronic sometime soon. Not confirmed by anyone.

**Summary.** Unconfirmed report: possibly about our operations but unconfirmed or not specific. The tower escalated it to a human and changed nothing. Missing: a confirmed source, which part / plant / supplier, the dates affected.

**Why.** possibly about our operations but unconfirmed or not specific (readers: unanimous, slm, grammar)

**Missing intel.** a confirmed source; which part / plant / supplier; the dates affected

**Actions.** escalate x1

## E-14 - RESOLVED

> Quality alert: Atlas says the heavy-duty wiring harness sent to the Texas plant had a moisture contamination. Anything built Monday Feb 22 through Wednesday Feb 24 is suspect.

**Summary.** Quality hold on LOT-0017 (HARN-B installed at P_TX, built 2027-02-22 to 2027-02-24): lot held, 86 unsold vehicles stopped from sale, 94 owners of sold vehicles contacted.

**Why.** 1 grounded incident(s) (readers: unanimous, slm, grammar)

**Graph path #1.** `Supplier:SUP-07 -MADE-> Lot:LOT-0017 -LOT_OF-> Part:HARN-B -IN_BOM_OF-> 2xModel -BUILT_AS-> 6xProductionOrder -PRODUCED-> 180xVehicle -AT_DEALER-> 36xDealer -OWNED_BY-> 94xCustomer`

```
traceroute to QUALITY_HOLD via Lot:LOT-0017, 8 hops max
 1  anchor           Supplier:SUP-07
 2  -MADE->          Lot:LOT-0017  (built 2027-02-22 .. 2027-02-24)
 3  -LOT_OF->        Part:HARN-B
 4  -IN_BOM_OF->     Model:2x [RANGER, SUMMIT]
 5  -BUILT_AS->      ProductionOrder:6x [PO-0001, PO-0002, PO-0004, ...]  (at P_TX in window)
 6  -PRODUCED->      Vehicle:180x [AUR0000002, AUR0000003, AUR0000006, ...]  (86 in stock / 94 sold)
 7  -AT_DEALER->     Dealer:36x [D02, D03, D04, ...]  (stop sale)
 8  -OWNED_BY->      Customer:94x [C0130, C0226, C0419, ...]  (contact owners)
```

**Actions.** crm.notify_customer x94, dealer.stop_sale x36, quality.hold_lot x1

## E-15 - RESOLVED

> QUALITY BULLETIN QB-368: Lot LOT-0191 (CHIP-IVI, supplier SUP-12) installed at P_IN on vehicles built 2027-03-02 to 2027-03-03 has a faulty weld. Place the lot on hold, stop sale of unsold vehicles and contact owners.

**Summary.** Quality hold on LOT-0191 (CHIP-IVI installed at P_IN, built 2027-03-02 to 2027-03-03): lot held, 40 unsold vehicles stopped from sale, 76 owners of sold vehicles contacted.

**Why.** 1 grounded incident(s) (readers: unanimous, slm, grammar)

**Graph path #1.** `Supplier:SUP-12 -MADE-> Lot:LOT-0191 -LOT_OF-> Part:CHIP-IVI -IN_BOM_OF-> 2xModel -BUILT_AS-> 4xProductionOrder -PRODUCED-> 116xVehicle -AT_DEALER-> 25xDealer -OWNED_BY-> 76xCustomer`

```
traceroute to QUALITY_HOLD via Lot:LOT-0191, 8 hops max
 1  anchor           Supplier:SUP-12
 2  -MADE->          Lot:LOT-0191  (built 2027-03-02 .. 2027-03-03)
 3  -LOT_OF->        Part:CHIP-IVI
 4  -IN_BOM_OF->     Model:2x [NOVA, VOYAGER]
 5  -BUILT_AS->      ProductionOrder:4x [PO-0289, PO-0291, PO-0292, ...]  (at P_IN in window)
 6  -PRODUCED->      Vehicle:116x [AUR0003175, AUR0003176, AUR0003180, ...]  (40 in stock / 76 sold)
 7  -AT_DEALER->     Dealer:25x [D02, D03, D04, ...]  (stop sale)
 8  -OWNED_BY->      Customer:76x [C0053, C0093, C0100, ...]  (contact owners)
```

**Actions.** crm.notify_customer x76, dealer.stop_sale x25, quality.hold_lot x1
