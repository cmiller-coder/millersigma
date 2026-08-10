-- One row per (product, sub-product). This is the storefront-persona grain: an
-- exec reads the six product cards, a product lead opens a card and wants the
-- individual SKUs underneath it.
--
-- Balances roll up to the same six product totals used on the cards, so opening
-- a card never contradicts the number printed on its face.
SELECT
    CAST(product AS VARCHAR)              AS "Product",
    CAST(sku AS VARCHAR)                  AS "Sub-Product",
    CAST(sku_order AS NUMBER)             AS "Sub-Product Order",
    CAST(balances_b AS NUMBER(10,2))      AS "Balances $B",
    CAST(members_k AS NUMBER(10,1))       AS "Members K",
    CAST(rate_pct AS NUMBER(6,2))         AS "Rate Pct",
    CAST(qoq_pct AS NUMBER(6,2))          AS "QoQ Growth Pct",
    CAST(status AS VARCHAR)               AS "Status"
FROM (
    -- Personal Loans -> 18.42
    SELECT 'Personal Loans' AS product, 'Debt Consolidation' AS sku, 1 AS sku_order,
           9.85 AS balances_b, 2180.0 AS members_k, 12.90 AS rate_pct,
            3.10 AS qoq_pct, 'On plan' AS status
    UNION ALL SELECT 'Personal Loans','Home Improvement',   2, 4.12,  920.0, 13.40,  5.40,'Ahead'
    UNION ALL SELECT 'Personal Loans','Major Purchase',     3, 2.90,  760.0, 13.75,  1.20,'On plan'
    UNION ALL SELECT 'Personal Loans','Medical & Dental',   4, 1.55,  480.0, 14.10, -0.80,'Behind'
    -- Student Refinancing -> 10.11
    UNION ALL SELECT 'Student Refinancing','Undergraduate Refi', 1, 4.90, 640.0, 6.20, 2.10,'On plan'
    UNION ALL SELECT 'Student Refinancing','Graduate Refi',      2, 3.35, 410.0, 6.55, 3.60,'Ahead'
    UNION ALL SELECT 'Student Refinancing','Parent PLUS Refi',   3, 1.24, 240.0, 6.80,-1.40,'Behind'
    UNION ALL SELECT 'Student Refinancing','In-School Loans',    4, 0.62, 140.0, 7.10, 0.40,'On plan'
    -- Home Loans -> 4.62
    UNION ALL SELECT 'Home Loans','Purchase Mortgage', 1, 2.28, 190.0, 6.65, 8.20,'Ahead'
    UNION ALL SELECT 'Home Loans','Refinance',         2, 1.10,  95.0, 6.90, 4.10,'Ahead'
    UNION ALL SELECT 'Home Loans','HELOC',             3, 0.86,  110.0,7.35, 6.70,'Ahead'
    UNION ALL SELECT 'Home Loans','Jumbo',             4, 0.38,  45.0, 6.45, 1.90,'On plan'
    -- Credit Card -> 1.28
    UNION ALL SELECT 'Credit Card','Unlimited 2% Cash Back', 1, 0.74, 560.0, 21.20,-2.40,'Behind'
    UNION ALL SELECT 'Credit Card','Everyday Cash',          2, 0.39, 340.0, 21.90,-1.10,'Behind'
    UNION ALL SELECT 'Credit Card','Secured Starter',        3, 0.15, 140.0, 23.40, 4.30,'Ahead'
    -- SoFi Money -> 39.85
    UNION ALL SELECT 'SoFi Money','Checking',       1, 12.40, 2610.0, 0.50, 2.80,'On plan'
    UNION ALL SELECT 'SoFi Money','Savings',        2, 21.90, 2480.0, 4.20, 4.60,'Ahead'
    UNION ALL SELECT 'SoFi Money','Vaults',         3,  3.85,  610.0, 4.20, 6.10,'Ahead'
    UNION ALL SELECT 'SoFi Money','Joint Accounts', 4,  1.70,  230.0, 4.20, 1.50,'On plan'
    -- SoFi Invest -> 12.74
    UNION ALL SELECT 'SoFi Invest','Active Brokerage',  1, 6.10, 1240.0, 0.00, 3.30,'On plan'
    UNION ALL SELECT 'SoFi Invest','Robo Portfolios',   2, 3.05,  620.0, 0.25, 5.80,'Ahead'
    UNION ALL SELECT 'SoFi Invest','Retirement (IRA)',  3, 2.85,  530.0, 0.00, 2.20,'On plan'
    UNION ALL SELECT 'SoFi Invest','Fractional Shares', 4, 0.74,  150.0, 0.00,-0.60,'Behind'
)
