-- Account summary block for the statement — a label/value table so it renders
-- with the banded, boxed look of a real statement rather than loose text.
WITH act AS (
    SELECT
        SUM(amount) AS total_spend,
        COUNT(*) AS txn_count,
        COUNT(DISTINCT category) AS category_count,
        AVG(amount) AS avg_txn,
        SUM(points) AS points_earned
    FROM (
        SELECT 184.22 AS amount, 'Groceries' AS category, 368 AS points
        UNION ALL SELECT 612.40,'Travel',1225      UNION ALL SELECT 68.13,'Gas',136
        UNION ALL SELECT 22.99,'Entertainment',46  UNION ALL SELECT 121.87,'Groceries',244
        UNION ALL SELECT 418.55,'Travel',837       UNION ALL SELECT 34.60,'Transit',69
        UNION ALL SELECT 9.99,'Shopping',20        UNION ALL SELECT 267.31,'Home',535
        UNION ALL SELECT 18.45,'Dining',37         UNION ALL SELECT 142.00,'Utilities',284
        UNION ALL SELECT 342.78,'Groceries',686    UNION ALL SELECT 11.99,'Entertainment',24
        UNION ALL SELECT 289.20,'Travel',578       UNION ALL SELECT 28.74,'Dining',57
        UNION ALL SELECT 156.42,'Shopping',313     UNION ALL SELECT 214.66,'Utilities',429
        UNION ALL SELECT 389.10,'Shopping',778     UNION ALL SELECT 246.98,'Travel',494
        UNION ALL SELECT 98.34,'Groceries',197     UNION ALL SELECT 26.15,'Transit',52
        UNION ALL SELECT 44.00,'Fitness',88
    )
)
SELECT CAST(line_order AS NUMBER) AS "Line Order",
       CAST(metric AS VARCHAR)    AS "Metric",
       CAST(value AS VARCHAR)     AS "Value"
FROM (
    SELECT 1 AS line_order, 'Purchases'          AS metric, '$' || TO_VARCHAR(total_spend, '9,999.00')      AS value FROM act
    UNION ALL SELECT 2, 'Transactions',   TO_VARCHAR(txn_count)                                              FROM act
    UNION ALL SELECT 3, 'Categories',     TO_VARCHAR(category_count)                                         FROM act
    UNION ALL SELECT 4, 'Average purchase', '$' || TO_VARCHAR(ROUND(avg_txn, 2), '999.00')                   FROM act
    UNION ALL SELECT 5, 'Points earned',  TO_VARCHAR(points_earned, '99,999')                                FROM act
    UNION ALL SELECT 6, 'Credit line',    '$12,000.00'                                                       FROM act
)
