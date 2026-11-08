# To-Be order-to-delivery process (draw in Miro / Whimsical)

Swimlanes: **Customer · Payment · Seller · Carrier · BazaarLink (Ops / Seller Success / CX)**.
Mark each change from the As-Is map with a green sticky note. Data evidence in brackets.

| # | Stage | Owner (lane) | As-Is | To-Be change | KPI / control |
|---|---|---|---|---|---|
| 1 | Customer places order | Customer + BazaarLink | One padded estimate for everyone (23.7 days promised, 12.6 actual) | **Route-based estimate** shown at checkout (pilot on same-state routes first) | On-time %, avg promised days |
| 2 | Payment approved | Payment | 0.4 days on average | No change (not a bottleneck) | Avg approval days |
| 3 | Seller packs and hands to carrier | Seller | No rule; 2.9 days average, some sellers 10+ days | **Handover rule: max 3 days**; automatic alert to seller on day 2; breach logged | Avg handover days, % orders handed over ≤ 3 days |
| 4 | Seller performance review | BazaarLink Seller Success | No monitoring | **Weekly seller scorecard** (Power BI); **watch list** = 30+ orders and late ≥ 12% or review < 3.8; coaching → penalties | Late % per seller, watch-list size (110 today) |
| 5 | Carrier transports | Carrier | Capacity flat all year; carrier leg 9.3 days | **Peak-season capacity plan** for Nov (Black Friday) and Feb-Mar; regional carriers for North/Northeast | On-time % in peak months (target ≥ 95%) |
| 6 | Customer receives order | Customer | Late orders unflagged | **Late-delivery alert**: if delay > 0, proactive message and voucher | Negative review % for late orders |
| 7 | Customer reviews | Customer + CX | No link back to cause | Reviews tagged with delay bucket and seller; fed into the scorecard | Negative review % by delay bucket |
| 8 | Repeat purchase | Customer + Marketing | No follow-up after a bad first order | **Win-back offer** to customers whose first order was late | Repeat customer % (3.1% today) |

**Decision points (diamonds):** after stage 3 "Handed over within 3 days?" → No → alert seller and log breach;
after stage 6 "Delivered after estimated date?" → Yes → late-delivery alert and voucher.
