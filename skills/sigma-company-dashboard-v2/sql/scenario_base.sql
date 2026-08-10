-- One row per product: the base book the scenario modeler cross-joins against.
--
-- This has to be genuinely one row per product, NOT a grouped view over the
-- monthly loan book. A cross join operates on the underlying rows, so joining a
-- grouped 144-row table replicates each product once per month and inflates
-- every downstream sum by 24x.
--
-- Re-derives from the same constants as loan_book.sql, aggregated over the
-- trailing twelve months, so the two always agree.
WITH product AS (
__PRODUCTS__
),
months AS (
    SELECT DATEADD('month', SEQ4(), DATE '2024-08-01') AS period_month,
           SEQ4() AS month_index
    FROM TABLE(GENERATOR(ROWCOUNT => 24))
),
monthly AS (
    SELECT
        p.product, p.product_order,
        ROUND(p.bal_base * POWER(1 + p.annual_growth / 12, m.month_index)
              * (1 + 0.035 * SIN(2 * PI() * (m.month_index / 12.0) + p.phase)), 0) AS bal,
        ROUND(p.fee_base * POWER(1 + p.annual_growth / 12, m.month_index)
              * (1 + 0.035 * SIN(2 * PI() * (m.month_index / 12.0) + p.phase))
              * CASE WHEN p.product = 'Home Loans' AND MONTH(m.period_month) IN (4,5,6) THEN 1.180
                     WHEN p.product = 'Credit Card' AND MONTH(m.period_month) IN (11,12) THEN 1.140
                     ELSE 1.0 END, 2) AS fee,
        p.yield_rate,
        CASE WHEN p.funding_rate > 0
             THEN p.funding_rate - 0.0045 * (m.month_index / 23.0) ELSE 0 END AS funding_eff
    FROM product p CROSS JOIN months m
    WHERE m.month_index >= 12          -- trailing twelve months
)
SELECT
    product                                                     AS "Product",
    MIN(product_order)                                          AS "Product Order",
    CAST(ROUND(SUM(bal * yield_rate / 12 - bal * funding_eff / 12 + fee), 0)
         AS NUMBER(12,0))                                       AS "Revenue",
    CAST(ROUND(AVG(bal), 0) AS NUMBER(12,0))                    AS "Balances",
    CAST(ROUND(AVG(yield_rate) * 100, 2) AS NUMBER(6,2))        AS "Yield Pct",
    CAST(ROUND(AVG(funding_eff) * 100, 2) AS NUMBER(6,2))       AS "Funding Pct"
FROM monthly
GROUP BY product
