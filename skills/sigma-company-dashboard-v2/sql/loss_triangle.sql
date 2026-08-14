-- Actuarial loss development triangle: cumulative loss ratio (%) by accident
-- year and development period (months since accident-year start). Older years
-- are fully developed and plateau; the most recent years only carry as much
-- development as has actually occurred, then hold flat (case-reserve estimate)
-- rather than showing NULLs, so the heatmap plugin never has to handle blanks.
SELECT
    CAST(accident_year AS VARCHAR)     AS "Accident Year",
    CAST(dev_period AS VARCHAR)        AS "Development Period",
    CAST(loss_ratio_pct AS NUMBER(6,1)) AS "Cumulative Loss Ratio Pct"
FROM (
    SELECT '2020' AS accident_year, '12' AS dev_period, 1 AS dev_order, 32 AS loss_ratio_pct
    UNION ALL SELECT '2020', '24', 2, 48
    UNION ALL SELECT '2020', '36', 3, 58
    UNION ALL SELECT '2020', '48', 4, 61
    UNION ALL SELECT '2020', '60', 5, 62
    UNION ALL SELECT '2020', '72', 6, 62
    UNION ALL SELECT '2021', '12', 1, 34
    UNION ALL SELECT '2021', '24', 2, 51
    UNION ALL SELECT '2021', '36', 3, 60
    UNION ALL SELECT '2021', '48', 4, 63
    UNION ALL SELECT '2021', '60', 5, 64
    UNION ALL SELECT '2021', '72', 6, 64
    UNION ALL SELECT '2022', '12', 1, 36
    UNION ALL SELECT '2022', '24', 2, 54
    UNION ALL SELECT '2022', '36', 3, 63
    UNION ALL SELECT '2022', '48', 4, 66
    UNION ALL SELECT '2022', '60', 5, 67
    UNION ALL SELECT '2022', '72', 6, 67
    UNION ALL SELECT '2023', '12', 1, 40
    UNION ALL SELECT '2023', '24', 2, 59
    UNION ALL SELECT '2023', '36', 3, 69
    UNION ALL SELECT '2023', '48', 4, 72
    UNION ALL SELECT '2023', '60', 5, 73
    UNION ALL SELECT '2023', '72', 6, 73
    UNION ALL SELECT '2024', '12', 1, 38
    UNION ALL SELECT '2024', '24', 2, 57
    UNION ALL SELECT '2024', '36', 3, 66
    UNION ALL SELECT '2024', '48', 4, 66
    UNION ALL SELECT '2024', '60', 5, 66
    UNION ALL SELECT '2024', '72', 6, 66
    UNION ALL SELECT '2025', '12', 1, 35
    UNION ALL SELECT '2025', '24', 2, 51
    UNION ALL SELECT '2025', '36', 3, 51
    UNION ALL SELECT '2025', '48', 4, 51
    UNION ALL SELECT '2025', '60', 5, 51
    UNION ALL SELECT '2025', '72', 6, 51
)
ORDER BY accident_year, dev_order
