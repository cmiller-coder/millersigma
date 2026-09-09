# OneMedNet demo script — iRWD Intelligence Layer

Audience: Michael Wong (VP Product), Durand Dunsmore, Steven Chartier, Aaron
Green. Runtime about 20 minutes, leaving 20 for discussion.

Workbook: papercrane staging, URL ID `3OCeIV1S7bV6fybbrXUBqK`, version 14.

## The one thing to prove

Michael's last verdict was that Claude plus graphs did not show Sigma's value.
He is right that a chart is not a differentiator. The differentiator is that
every number here is a **living, governed, shareable asset that his customers
can act on**, not a snapshot someone generated once and pasted into a deck.

Say the through-line out loud three times during the demo:

> Claude gives you an answer. This gives your customers an application.

Everything below is in service of that sentence. Do not narrate features.

## Before you start

Open all four pages once to warm the queries, then return to page 1. Have the
Signal Watchlist tab and the Trial Feasibility page pre-loaded in adjacent tabs
so nothing renders cold in front of them.

---

## 1. Frame (2 min, no screen)

"You told me last time that graphs don't move you, and that you'd only leave
Foundry if someone showed you why. So I'm not going to show you charts. I built
the four products you'd actually sell, on one governed model, and I want you to
try to break the last one."

Name the four audiences you built for: the quant fund, the contributing
hospital, the life sciences sponsor, and the trial feasibility team. Note that
all four run off one model, which is the thing that makes this a platform rather
than four dashboards.

## 2. Quant fund — the signal that cannot come from claims (5 min)

Open page 1, Therapeutic Signal Intelligence.

Start with the top row: 37,091 tracked new patient starts trailing twelve
months against 34,948 prior, 8,756 prescribers, and a Grade 3+ adverse-event
rate of 13.6%.

Then go to the off-label GLP-1 tab and let the chart do the work. Off-label
share of GLP-1 new starts climbs from 5.0% in July 2024 to 19.3% in June 2026,
and the headline card reads 14.3% for the trailing year against 7.5% the year
before. Say plainly what that is worth: a fund watching semaglutide and
tirzepatide demand gets a two-year ramp in real prescribing behavior, defined as
a morbid-obesity problem list with no type 2 diabetes code.

Now the strongest beat in the whole demo. Open the Symptom and AE Profile tab
and point at ARIA on donanemab: 24.8% imaging-detected incidence against a 15%
reference. Then say:

> This number does not exist in a claims feed. ARIA-E is only detectable on
> protocol surveillance MRI. It doesn't exist in EHR either, unless the imaging
> is linked to the record. This is the one signal that is uniquely yours.

That is the moment to stop talking and let him react.

## 3. Contributing hospital — same model, different buyer (3 min)

Move to page 2, Utilization and Throughput.

Do not re-explain the data. The point of this page is that it is the *same
model* pointed at a different audience: 215,304 facility encounters, 4.6-day
average length of stay, 12.8% thirty-day readmission, 43.0-minute imaging
turnaround, and 94.7% column completeness.

Use the site and service-line filters live. Then make the platform argument:

> Building the second product cost almost nothing, because it's the same
> governed model with a different lens. That's the part that's hard to do when
> every surface is a bespoke Foundry app.

## 4. Life sciences — why de-identification doesn't cost you the analysis (3 min)

Page 3, Patient Journey and Real-World Evidence.

Lead with the therapy-line transitions and the time-to-next-treatment table.
100,596 patients have 24 months of follow-up, 47.1% progress from first to
second line, median time to next treatment is 9.0 months, and five-year implant
survivorship is 96.3%.

Then make the credibility point that most RWD vendors fumble:

> Every date carries a per-patient consistent shift, so no real service date is
> recoverable, but because the shift is constant within a patient, every
> interval survives intact. Time to next treatment and survivorship are
> numerically identical to the unshifted source. You get privacy without losing
> the time-to-event analysis, which is the entire reason a sponsor licenses
> this data.

## 5. Trial feasibility — hand him the keyboard (6 min)

Page 4, RWE Trial-Feasibility Modeler. This is the close. Do not drive.

It opens on a real scenario: oncology, NSCLC C34.90, stage III or IV, ECOG 0-1,
actionable or PD-L1-high biomarker, 12-month minimum follow-up, imaging
required. That yields a projected cohort of 1,020 patients, 34.9% statistical
power, 94.1 expected events, and 85.8% data completeness, across 14 sites.

Walk the attrition funnel once so he trusts the arithmetic: 250,000 licensed
patients, 84,797 in oncology, 13,790 after diagnosis, stage and age, 6,954 after
performance status and organ function, 3,795 after biomarker, and 1,020 after
follow-up and imaging. Every stage is a distinct patient count over the same
base, so the stages always tie.

**Then ask him to loosen a criterion himself.** Have him drop the biomarker
requirement to "Any result" or relax ECOG. The cohort, the power estimate, the
funnel, the site table and the patient-level cohort detail all recompute
together against 250,000 patients.

Say the differentiator here, because this is where it is undeniable:

> You cannot do this with a chat answer. Claude can tell you a cohort size once.
> It cannot hand your sponsor a protocol they can tune themselves, see the
> statistical consequence of, and save.

Two more beats, in order:

1. **The agent acts, it doesn't just answer.** In the feasibility chat, ask it
   to set up a protocol — for example, "size a stage II to IV NSCLC cohort with
   ECOG up to 2 and no biomarker requirement." It changes the actual controls
   and the page recomputes. The agent is wired to the application's state, not
   narrating beside it.
2. **The work persists.** Click "New protocol," name it, then "Save protocol
   settings." It writes to the protocol log with the user and timestamp. Point
   out that this is the audit trail a regulated buyer asks for on day one, and
   that a chat transcript is not one.

Optionally show the same pattern on page 1's Signal Watchlist, where an analyst
escalates or dismisses a flagged signal and it lands in the action log.

## 6. Close (2 min)

Two sentences, then stop:

> This is one person, working in code against your requirements from a single
> call. Everything you just used is defined as a spec in version control, which
> is why I can change it in front of you and why feature parity is a
> conversation about weeks, not quarters.

Then ask the only question that matters: *which of these four is the one your
customers would pay for first?*

---

## Handling the pushback you will get

**"Is this our real data?"** No, and say so immediately and without hedging.
It is deterministic synthetic data generated in Snowflake so every number is
checkable. The page footers say this. Offer the obvious next step: point the
same model at a real extract and the surfaces come with it, because the logic
lives in the model rather than in the charts.

**"You said row-level security — is it enforced?"** Not in this build. The
license-grant matrix is illustrative. Real enforcement belongs in warehouse
policies and inherited RLS, which is exactly how it should work for an embedded
product, and it is not something a workbook filter should ever be trusted to do.
Do not oversell this; he will check.

**"We're not on Snowflake."** Correct, and it does not have to be Snowflake.
The point is that the semantic layer sits on their warehouse and Sigma inherits
it, rather than Sigma holding a private copy of the logic.

**"Can we embed this?"** Not demonstrated today. Be straight that the embed
path and bring-your-own-LLM through Cortex are the next build, and that you
deliberately spent this round proving the analytics and the write-back
workflows first.

**"Why leave Palantir?"** Don't argue replacement. His own stated shortcoming
was that AI search is opaque and users fall back to filters. Show him that here
the agent moves real controls the user can see, inspect and override, so the
filters and the AI are the same surface instead of competing ones. Then let
speed to market carry the rest.
