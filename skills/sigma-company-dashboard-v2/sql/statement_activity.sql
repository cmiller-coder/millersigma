-- Transaction detail for a single member's monthly SoFi Credit Card statement.
-- Feeds the pixel-perfect statement report. Entirely synthetic.
SELECT
    CAST(txn_date AS DATE)              AS "Transaction Date",
    CAST(post_date AS DATE)             AS "Post Date",
    CAST(merchant AS VARCHAR)           AS "Merchant Name or Transaction Description",
    CAST(category AS VARCHAR)           AS "Category",
    CAST(amount AS NUMBER(10,2))        AS "Amount",
    CAST(points AS NUMBER(10,0))        AS "Points Earned"
FROM (
    SELECT DATE '2026-07-03' AS txn_date, DATE '2026-07-04' AS post_date, 'WHOLE FOODS MKT #1042    AUSTIN TX'    AS merchant, 'Groceries' AS category,  184.22 AS amount, 368 AS points
    UNION ALL SELECT DATE '2026-07-04', DATE '2026-07-06', 'DELTA AIR LINES          ATLANTA GA',    'Travel',        612.40, 1225
    UNION ALL SELECT DATE '2026-07-05', DATE '2026-07-07', 'SHELL OIL 57446281       AUSTIN TX',     'Gas',            68.13,  136
    UNION ALL SELECT DATE '2026-07-07', DATE '2026-07-08', 'NETFLIX.COM              LOS GATOS CA',  'Entertainment',  22.99,   46
    UNION ALL SELECT DATE '2026-07-08', DATE '2026-07-09', 'TRADER JOES #714         AUSTIN TX',     'Groceries',     121.87,  244
    UNION ALL SELECT DATE '2026-07-09', DATE '2026-07-11', 'MARRIOTT HOTELS         NASHVILLE TN',   'Travel',        418.55,  837
    UNION ALL SELECT DATE '2026-07-10', DATE '2026-07-11', 'UBER TRIP               SAN FRANCISCO',  'Transit',        34.60,   69
    UNION ALL SELECT DATE '2026-07-11', DATE '2026-07-13', 'APPLE.COM/BILL          CUPERTINO CA',   'Shopping',        9.99,   20
    UNION ALL SELECT DATE '2026-07-12', DATE '2026-07-14', 'HOME DEPOT #6512        AUSTIN TX',      'Home',          267.31,  535
    UNION ALL SELECT DATE '2026-07-14', DATE '2026-07-15', 'STARBUCKS STORE 09912   AUSTIN TX',      'Dining',         18.45,   37
    UNION ALL SELECT DATE '2026-07-15', DATE '2026-07-16', 'AT&T WIRELESS           DALLAS TX',      'Utilities',     142.00,  284
    UNION ALL SELECT DATE '2026-07-16', DATE '2026-07-18', 'COSTCO WHSE #1121       AUSTIN TX',      'Groceries',     342.78,  686
    UNION ALL SELECT DATE '2026-07-18', DATE '2026-07-19', 'SPOTIFY USA             NEW YORK NY',    'Entertainment',  11.99,   24
    UNION ALL SELECT DATE '2026-07-19', DATE '2026-07-21', 'DELTA AIR LINES         ATLANTA GA',     'Travel',        289.20,  578
    UNION ALL SELECT DATE '2026-07-20', DATE '2026-07-21', 'CHIPOTLE 2244           AUSTIN TX',      'Dining',         28.74,   57
    UNION ALL SELECT DATE '2026-07-22', DATE '2026-07-23', 'AMAZON MKTPL US*R42K1   SEATTLE WA',     'Shopping',      156.42,  313
    UNION ALL SELECT DATE '2026-07-23', DATE '2026-07-25', 'AUSTIN ENERGY           AUSTIN TX',      'Utilities',     214.66,  429
    UNION ALL SELECT DATE '2026-07-25', DATE '2026-07-26', 'REI #0087              AUSTIN TX',       'Shopping',      389.10,  778
    UNION ALL SELECT DATE '2026-07-26', DATE '2026-07-28', 'SOUTHWEST AIRLINES      DALLAS TX',      'Travel',        246.98,  494
    UNION ALL SELECT DATE '2026-07-28', DATE '2026-07-29', 'H-E-B #442              AUSTIN TX',      'Groceries',      98.34,  197
    UNION ALL SELECT DATE '2026-07-29', DATE '2026-07-30', 'LYFT RIDE               SAN FRANCISCO',  'Transit',        26.15,   52
    UNION ALL SELECT DATE '2026-07-31', DATE '2026-08-01', 'PELOTON INTERACTIVE     NEW YORK NY',    'Fitness',        44.00,   88
)
