-- One row per product, for the repeated-container card grid on page 1.
-- A repeated container renders a card per row of its source, so this stays
-- deliberately small and pre-formatted: its children can only be text / image /
-- divider / button, so every number has to arrive display-ready.
SELECT
    CAST(product AS VARCHAR)            AS "Product",
    CAST(product_order AS NUMBER)       AS "Product Order",
    CAST(tagline AS VARCHAR)            AS "Tagline",
    CAST(balances_b AS NUMBER(10,2))    AS "Balances $B",
    CAST(rate_label AS VARCHAR)         AS "Rate Label",
    CAST(rate_value AS VARCHAR)         AS "Rate Value",
    CAST(members_m AS NUMBER(10,2))     AS "Members M",
    CAST(goal_pct AS NUMBER(10,3))      AS "Goal Pct",
    CAST(status AS VARCHAR)             AS "Status"
FROM (
    SELECT 'Personal Loans' AS product, 1 AS product_order,
           'Fixed-rate consolidation & major purchases' AS tagline,
           18.42 AS balances_b, 'Avg APR' AS rate_label, '13.20%' AS rate_value,
           4.34 AS members_m, 0.968 AS goal_pct, 'On plan' AS status
    UNION ALL SELECT 'Student Refinancing', 2, 'Refinance federal & private student debt',
           10.11, 'Avg APR', '6.40%',  1.43, 0.712, 'Behind'
    UNION ALL SELECT 'Home Loans', 3, 'Purchase, refinance and HELOC',
            4.62, 'Avg APR', '6.80%',  0.44, 1.118, 'Ahead'
    UNION ALL SELECT 'Credit Card', 4, 'Unlimited cash back on everyday spend',
            1.28, 'Avg APR', '21.50%', 1.04, 0.643, 'Behind'
    UNION ALL SELECT 'SoFi Money', 5, 'Checking & savings with direct deposit',
           39.85, 'APY',     '4.20%',  5.93, 0.994, 'On plan'
    UNION ALL SELECT 'SoFi Invest', 6, 'Active investing, IRAs and robo portfolios',
           12.74, 'Fee',     '0.00%',  2.54, 1.047, 'Ahead'
)
