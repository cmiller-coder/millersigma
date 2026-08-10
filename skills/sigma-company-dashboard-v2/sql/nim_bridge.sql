-- Net revenue -> contribution profit bridge for the waterfall chart.
-- Re-derives from the same product constants as loan_book.sql so the two agree;
-- aggregates the trailing-twelve-month window into signed bridge steps ($MM).
WITH product AS (
    SELECT 'Personal Loans' AS product, 17500 AS bal_base, 0.1320 AS yield_rate, 0.0410 AS funding_rate,
           22.0 AS fee_base, 0.0360 AS provision_rate, 0.380 AS opex_ratio, 0.052 AS annual_growth, 0.0 AS phase
    UNION ALL SELECT 'Student Refinancing',  9800, 0.0640, 0.0410,  6.0, 0.0050, 0.340, 0.028, 1.1
    UNION ALL SELECT 'Home Loans',           4200, 0.0680, 0.0410, 14.0, 0.0030, 0.520, 0.115, 2.2
    UNION ALL SELECT 'Credit Card',          1150, 0.2150, 0.0410,  5.0, 0.0850, 0.460, 0.140, 0.6
    UNION ALL SELECT 'SoFi Money',          38000, 0.0000, 0.0000, 45.0, 0.0000, 0.620, 0.180, 1.7
    UNION ALL SELECT 'SoFi Invest',             0, 0.0000, 0.0000, 18.0, 0.0000, 0.700, 0.095, 2.8
),
months AS (
    SELECT DATEADD('month', SEQ4(), DATE '2024-08-01') AS period_month, SEQ4() AS month_index
    FROM TABLE(GENERATOR(ROWCOUNT => 24))
),
bridge_rows AS (
    SELECT
        p.product, m.month_index,
        ROUND(p.bal_base * POWER(1 + p.annual_growth / 12, m.month_index)
              * (1 + 0.035 * SIN(2 * PI() * (m.month_index / 12.0) + p.phase)), 0) AS bal,
        ROUND(p.fee_base * POWER(1 + p.annual_growth / 12, m.month_index)
              * (1 + 0.035 * SIN(2 * PI() * (m.month_index / 12.0) + p.phase))
              * CASE WHEN p.product = 'Home Loans' AND MONTH(m.period_month) IN (4,5,6) THEN 1.180
                     WHEN p.product = 'Credit Card' AND MONTH(m.period_month) IN (11,12) THEN 1.140
                     ELSE 1.0 END, 2) AS fee,
        p.yield_rate,
        CASE WHEN p.funding_rate > 0 THEN p.funding_rate - 0.0045 * (m.month_index / 23.0) ELSE 0 END AS funding_eff,
        p.provision_rate, p.opex_ratio
    FROM product p CROSS JOIN months m
    WHERE m.month_index >= 12          -- trailing twelve months only
),
agg AS (
    SELECT
        SUM(bal * yield_rate / 12)                                        AS interest_income,
        SUM(bal * funding_eff / 12)                                       AS interest_expense,
        SUM(fee)                                                          AS fee_income,
        SUM(bal * provision_rate / 12)                                    AS provision,
        SUM((bal * yield_rate / 12 - bal * funding_eff / 12 + fee) * opex_ratio) AS opex
    FROM bridge_rows
)
SELECT CAST(step AS VARCHAR) AS "Step",
       CAST(step_order AS NUMBER) AS "Step Order",
       CAST(ROUND(amount, 1) AS NUMBER(12,1)) AS "Amount",
       CAST(step_type AS VARCHAR) AS "Step Type"
FROM (
    SELECT 'Interest Income'      AS step, 1 AS step_order, interest_income        AS amount, 'start' AS step_type FROM agg
    UNION ALL SELECT 'Interest Expense', 2, -interest_expense, 'decrease' FROM agg
    UNION ALL SELECT 'Fee Income',       3,  fee_income,      'increase' FROM agg
    UNION ALL SELECT 'Provision',        4, -provision,       'decrease' FROM agg
    UNION ALL SELECT 'Opex',             5, -opex,            'decrease' FROM agg
    -- No explicit total row: the waterfall renders its own End bar, so adding
    -- one here draws the total twice.
)
