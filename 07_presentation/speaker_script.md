# Speaker script: 10 slides, 10 minutes

Speak slowly. Each slide has a target time; the total is 10:00.
**Bold** = numbers to say clearly. Pause after every big number.

---

## Slide 1: Delivering on the Promise (0:30) · total 0:30
"Good morning. I'm Nepstina. For this capstone I acted as the analytics team for BazaarLink, an online marketplace
for small sellers in Brazil. The question was simple: **what is late delivery costing us, and where should we act first?**
In the next ten minutes I'll show you the problem, the evidence, and four sized recommendations."

## Slide 2: The problem (0:45) · total 1:15
"BazaarLink's growth has stalled. Shoppers who get a bad delivery leave bad reviews and don't come back.
And each team had its own spreadsheet: nobody agreed on the on-time rate, which sellers were the problem,
or whether our delivery promises were realistic. Leadership is setting next year's logistics budget,
so they needed one trusted view first."

## Slide 3: Data, approach and headline numbers (1:00) · total 2:15
"I used the Olist public dataset: **99,441 orders** across 9 linked tables, 2016 to 2018.
I cleaned it in Python and logged **48 data issues**, each with a reason. For example, customer_id changes with every
order, so I counted customers by customer_unique_id; otherwise repeat customers look like zero.
Then MySQL with 25 queries and 3 views, Python statistics, and three dashboards.
One set of KPI definitions everywhere, and all the tools match exactly.
The headline: on-time is **93.2%**, average delivery **12.6 days**, review score **4.09**,
but only **3.1%** of customers ever order twice."

## Slide 4: Late delivery is strongly linked to bad reviews (1:15) · total 3:30
"Here's the key finding. Late orders average **2.27 stars**; on-time orders **4.29**.
A Mann-Whitney test gives p below 0.001: if lateness made no difference, a gap this big would almost never happen by chance.
A late order is **6.7 times** as likely to get a one- or two-star review.
And there's no safe lateness: the chance of a bad review is **9%** on time, **32%** at just one to three days late,
**68%** at four to seven, and **79%** at eight days or more.
I say 'linked', not 'caused': some late orders also had other problems."

## Slide 5: When: on-time collapses at peaks (0:45) · total 4:15
"When does it go wrong? 93% sounds good, but look at the peaks: **87.6%** in November 2017, Black Friday,
and **81%** in March 2018. The red line is the proposed **95% target**. The problem isn't every day; it's when volume spikes."

## Slide 6: Where time is lost (1:00) · total 5:15
"Where is the time lost? Of the 12.6 days, approval takes 0.4, the seller holds the order **2.9 days**,
and the carrier takes **9.3**. The Logistics Manager said 'carriers are the problem'. The carrier leg is the biggest,
but the seller handover is the part we control. My regression shows each extra handover day adds about
**one delivery day**, and inter-state orders take **15 days vs 8** same-state."

## Slide 7: Who: a concentrated group of sellers (0:45) · total 6:00
"Who? I built a seller watch list: sellers with at least **30 orders**, so small sellers aren't judged on tiny samples,
and a late rate of 12% or more or a review below 3.8. That's **110 sellers**. Their orders are late **12.2%** of the time,
double the **6.1%** for everyone else."

## Slide 8: Recommendations, sized (1:30) · total 7:30
"Four recommendations, each tied to a KPI and sized from the data.
**One:** a peak-season plan, with extra carrier capacity before Black Friday and February–March. If peak months hit 95%,
overall on-time rises from **93.2% to 95.6%**, and we avoid an estimated **1,200** bad reviews.
**Two:** a seller handover rule, three days maximum. That alone lifts on-time to **94.6%**, about **680** fewer bad reviews.
**Three:** a watch-list programme for the 110 sellers: coaching first, then penalties; about **350** fewer bad reviews.
**Four:** route-based delivery estimates, but only as a pilot. Promises are padded, but cutting every estimate by
three days would drop on-time to **89%**, so a blanket cut would backfire.
These impacts overlap, so they're not additive; one and two are the priority."

## Slide 9: Dashboard demo (1:30) · total 9:00
(Switch to Power BI. Practise this path until it's smooth.)
1. "This is the **Executive** page for the COO: headline KPIs and the on-time trend against the 95% target."
2. "On the **Delivery** page I filter to the Northeast, the worst region: you can see the stage split and the review buckets."
3. "The **Seller scorecard** shows the watch list. I right-click a seller and **drill through** to their detail."
4. (Switch to Tableau) "In **Tableau**, clicking a state on the map filters every other chart."
"Every number here matches SQL exactly; I checked on a KPI Check page before building anything."

## Slide 10: Next steps and limits (0:45) · total 9:45
"Next steps: approve recommendations one to three, pilot four, and roll out the KPIs with the change management plan.
The limits: this is observational data, so these are associations, not proven causes; there's no distance or carrier
data; and the regression explains 28% of delivery time. Thank you. I'm happy to take questions."

---

## Practice plan (60 minutes)
1. **Read it aloud once** with the slides (about 15 min). Mark any word that feels awkward and change it to your own words.
2. **Second run with a timer.** If it's over 10 minutes, shorten slides 3 and 6 first.
3. **Practise the demo path** (slide 9) three times: Power BI Executive → Delivery (Northeast filter) → Seller scorecard → drill-through → Tableau map click.
4. **Q&A:** cover the answers in `deck_outline.md` ("Likely Q&A"), then answer each question aloud in 2–3 sentences.
5. **Final run** standing up, without reading.

## Backup if the demo fails
Show the screenshots in `06_dashboards/screenshots/` and say: "Here's the same page as a screenshot."
