-- Operational alert feed for the notifications centre, one row per alert.
--
-- Modelled on the Cold Provisions storefront notification rail: a severity, a
-- short title, a one-line body and an age. Kept deliberately small and
-- display-ready because each card reads a single row via SumIf/MaxIf on the
-- alert order -- repeated containers still cannot bind per-card from code.
SELECT
    CAST(alert_key AS VARCHAR)       AS "Alert Key",
    CAST(alert_order AS NUMBER)      AS "Alert Order",
    CAST(severity AS VARCHAR)        AS "Severity",
    CAST(title AS VARCHAR)           AS "Title",
    CAST(body AS VARCHAR)            AS "Body",
    CAST(age AS VARCHAR)             AS "Age",
    CAST(owner AS VARCHAR)           AS "Owner",
    CAST(impact AS NUMBER(12,0))     AS "Impact"
FROM (
    SELECT 'a1' AS alert_key, 1 AS alert_order, 'critical' AS severity,
           'Fraud pattern detected' AS title,
           'Card-not-present velocity spike on 1,240 Credit Card accounts' AS body,
           '18m ago' AS age, 'Financial Crimes' AS owner, 1240 AS impact
    UNION ALL SELECT 'a2', 2, 'critical', 'Funding cost breach',
           'Cost of funds on SoFi Money exceeded the 4.35% plan ceiling', '2h ago', 'Treasury', 16
    UNION ALL SELECT 'a3', 3, 'warning', 'Underwriting queue backing up',
           '412 Personal Loan applications past the 24-hour decision SLA', '3h ago', 'Credit Ops', 412
    UNION ALL SELECT 'a4', 4, 'warning', 'Delinquency drift',
           'Credit Card 30-day DQ up 41 bps week over week, concentrated in Near Prime', '6h ago', 'Risk', 41
    UNION ALL SELECT 'a5', 5, 'info', 'Rate change published',
           'Savings APY moved 4.20% to 4.35%, effective for all new deposits', '1d ago', 'Product', 15
    UNION ALL SELECT 'a6', 6, 'info', 'Refi demand surge',
           'Student Refinancing applications up 22% following the Treasury rally', '1d ago', 'Growth', 22
)
