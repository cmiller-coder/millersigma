# Origin Investments demo script

Audience: Dayna McCue + the new data analyst. Visual learner. Do not pitch a
Tableau replacement as stack-shrink — she said the firm is 1.5 years into
architecture. Pitch **transparency for IM** and **one click for sales**.

Through-line: **AskSimon answers. This puts Peter’s model in the warehouse
with permissions so quarter-end is not a scavenger hunt.**

## Open on Model of Record

1. Header: Origin mark, Sunbelt multifamily language.
2. Four KPIs: GAV, occupancy, NOI, **desktop models outstanding**.
3. Filter **Source of truth → Desktop Excel**. Grid should collapse to the
   assets still on a laptop. That is the pain she named.
4. Chase list on the right: named files, owners (Peter), who consumes them
   (marketing decks, IC). Numbers are not usually wrong — they are late.

Hand her the keyboard on the source-of-truth filter.

## Sales & Marketing

She guessed the warehouse is more built-out here. Show:

- YTD closed vs FY target (pace comparison is 75% of year elapsed).
- Pipeline by stage (Prospecting → Closed Won).
- Campaign bars for the road show.

One-click story vs Salesforce MFA then Tableau.

## Quarter-end Writeback

This is the Excel wedge.

1. Grid already has a **Base Case** so it is not dead-empty.
2. Type **Your Occupancy** on IncomePlus (try 96%). Projected NOI and uplift
   move; variance bars are unstacked (not a stacked sum).
3. Type a comment in **IC comment**. That is writeback with a permission
   story — not a shared inbox spreadsheet.

If they ask Redshift: this POV is Snowflake-generated on staging; production
would point at their Redshift + AskSimon YAML/semantic layer.

## Do not say

- We will replace AskSimon.
- We will shut off Tableau next quarter.
- This is production NAV.
- RLS is enforced by these workbook filters.
