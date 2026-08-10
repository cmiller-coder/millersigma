-- Benchmark rate history, 24 months. Illustrative values anchored to the real
-- rate environment (Treasury 10Y ~4.65%, 30Y ~5.19% as of 2026-08-07) so the
-- charts agree with the live ticker rather than contradicting it.
-- The ticker plugin fetches genuinely live yields; this table is the history
-- behind them and the fallback if the live fetch is unavailable.
WITH benchmark AS (
    SELECT '10Y Treasury' AS benchmark, 1 AS bench_order, 4.65 AS end_rate, -0.55 AS drift, 0.10 AS vol, 0.0 AS phase
    UNION ALL SELECT '2Y Treasury',   2, 4.19, -0.95, 0.12, 0.7
    UNION ALL SELECT 'SOFR',          3, 4.31, -1.10, 0.08, 1.3
    UNION ALL SELECT 'Fed Funds',     4, 4.50, -1.00, 0.05, 1.3
    UNION ALL SELECT '30Y Mortgage',  5, 6.42, -0.70, 0.14, 0.2
    UNION ALL SELECT 'Prime',         6, 7.50, -1.00, 0.05, 1.3
),
months AS (
    SELECT DATEADD('month', SEQ4(), DATE '2024-08-01') AS period_month,
           SEQ4() AS month_index
    FROM TABLE(GENERATOR(ROWCOUNT => 24))
)
SELECT
    b.benchmark                                      AS "Benchmark",
    b.bench_order                                    AS "Benchmark Order",
    m.period_month                                   AS "Period",
    -- Walk backwards from today's real level along the drift, with a small
    -- deterministic wave so the series isn't a straight line.
    ROUND(b.end_rate - b.drift * ((23 - m.month_index) / 23.0)
          + b.vol * SIN(2 * PI() * (m.month_index / 9.0) + b.phase), 3)
                                                     AS "Rate Pct",
    CASE WHEN m.month_index >= 12 THEN 'Current Period'
         ELSE 'Prior Period' END                     AS "Period Name"
FROM benchmark b CROSS JOIN months m
