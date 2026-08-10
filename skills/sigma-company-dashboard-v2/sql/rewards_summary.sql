-- Rewards summary lines for the statement, rendered as a banded table so it
-- reads like a real statement block rather than loose text rows.
SELECT
    CAST(line_order AS NUMBER)      AS "Line Order",
    CAST(description AS VARCHAR)    AS "Description",
    CAST(points AS NUMBER(12,0))    AS "Points"
FROM (
    SELECT 1 AS line_order, 'Previous points balance'                        AS description, 18420 AS points
    UNION ALL SELECT 2, '+ 2 points per $1 on travel & dining',               4842
    UNION ALL SELECT 3, '+ 1 point per $1 on all other purchases',            2655
    UNION ALL SELECT 4, '+ Member referral bonus',                            1500
    UNION ALL SELECT 5, '- Points redeemed for statement credit',            -6500
)
