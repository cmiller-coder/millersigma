# Sigma Motors — demo script (~4 min)

*A day-in-the-life walkthrough: two roles, one workbook. Every number below is pulled live from the actual workbook — not invented. Two beats are narrated instead of clicked, noted inline, with why.*

**Setup line:** "This is Sigma Motors — a fictional EV/Hybrid automaker. Demand for EVs is surging faster than they can build them, and battery-cell supply is the constraint. Let me show you this the way it'd actually get used — not a tour of features, but two people doing their jobs."

## The story

**Role 1: Priya, Supply Chain Planning Analyst (West region).** It's Monday morning. She opens Market Signal.

- **She sees:** the KPI row — EV Waitlist 4,120 (+400 this month), Margin at Risk $1.8M (+$180k), 2 of 5 regions now over the 5-week backlog threshold. The AI Insight banner has already flagged it: demand is up 11% month-over-month and margin is increasingly exposed.
- **She realizes:** she doesn't yet know if *her* region — West — is one of the two flagged. She filters **Region → West**.
- **She sees:** the whole KPI row narrows with her — West alone is carrying a 1,120-unit waitlist, $490k of the margin at risk, and a 6.2-week backlog. It's confirmed: West is one of the two at-risk regions, and it's the worse of the two.
- **She decides:** this isn't a "watch and wait" number, it's a "do something" number. She clicks **Explore Scenarios**.

**Now she's in the scenario modeler (EV & Hybrid Reallocation).** Baseline: 5,600 EV units / 7,300 Hybrid units, $0 margin impact, battery-cell supply at 90% committed.

- **She adjusts:** the EV-share shift lever to **+15** — shifting production capacity from Hybrid toward EV, to start working down that West backlog.
- **She sees it recompute live:** EV units 6,440 (+840), Hybrid units 6,460 (−840), margin impact **+$630k**, battery-cell supply now **99% committed** — right at the edge, but not over it.
- **She reads the AI feasibility read:** feasible, but battery-cell supply is now the binding constraint — any further shift past this point likely isn't feasible without more cell supply. That's exactly the kind of call an analyst shouldn't have to make from a gut feeling.
- **She decides:** feasible, and $630k of margin upside is worth taking to her manager. "So I can try a few mixes here — 10, 15, 20 — until I land on the one I'm comfortable defending." She lands on +15.
- **She submits:** points at **Save & submit for approval** without clicking it — "This sends the scenario to my ops manager for sign-off, with the numbers already validated — not a slide he has to take my word for." *(The live write-back on this connection has a known permission issue — don't click it live; narrate the handoff instead.)*

**Role 2: her manager — VP of Operations.** Different login, same workbook, Approvals page.

- **He sees:** the Submission Queue — a scenario sitting in Pending, with the mix, the margin impact, and the same cell-supply feasibility read Priya saw, right in the same workbook. No screenshot pasted into an email, no separate spreadsheet to reconcile against.
- **He decides:** approve or reject, right there — and the loop closes. Signal → decision → governance, one source of truth, two people, zero meetings.

**Why this matters:** *this is the whole point — an analyst doesn't need a BI tool, a modeling spreadsheet, AND a workflow/email chain to get a production decision from "I noticed a problem" to "it's approved." It's one workbook, two logins.*

**Optional bonus beat (page 1):** click **Reservation Statement** in the header. "One more thing — this is a completely different kind of deliverable: not a dashboard, an actual printed statement. Reservation activity, Sigma Rewards points, estimated delivery window — laid out pixel-perfect, real typography, nothing hand-placed or screenshotted into a template. Here's why that matters: it's built from the *exact same* data model as the dashboard you just saw. Same warehouse, same governance, zero extra data engineering. So if your team ever needs to hand someone an actual document — a statement, an invoice, a compliance report — you don't need to bolt on a separate reporting tool. It's the same Sigma infrastructure, just pointed at a print layout instead of a screen. And like everything else here, it's generated from a spec, not built by hand in a report builder — so it templates the same way the dashboard does, across any company or customer." *(Opens a real, separately-published Sigma report in a new tab. Skip if running short on time — nice-to-have, not core to the arc.)*

## Known caveats — don't get caught off guard

- **The map (Regional Demand Pulse) is a static snapshot.** Point at it for its accuracy, don't click it or expect it to move with any control.
- **Don't click "Save & submit for approval" live** — the connection's write-back has a known permission error. Narrate it instead (as scripted above).
- **The scenario shown in Approvals is a real, already-existing example, not literally the one "submitted" in the story above** — same workflow, same shape, just don't claim it's the exact one from the live walkthrough if someone's paying close attention.
- **Known bug, not yet fixed:** on page 2, the AI feasibility text currently says EV production moves "to 7,290 units" at a +15 shift — the real KPI card says **6,440**. The AI prompt has its own hardcoded copy of the math instead of referencing the live table (same root cause as a bug fixed on this same page in an earlier round). Low risk of anyone catching it live, but worth fixing before a repeat demo — say the word and I'll patch it.

## Closing line

"Everything you just saw — the KPIs, the AI insight, the custom map, the scenario model, the approval queue, even the customer statement — is one Sigma workbook, on one semantic model. No separate BI tool, no separate modeling tool, no separate workflow tool. And because Sigma workbooks are buildable as code, I built and iterated this entire thing conversationally."
