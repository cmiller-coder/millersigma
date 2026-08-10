-- Synthetic member-level population for the Cohort Builder page.
-- 2,600 members, deterministic (HASH-seeded, no RANDOM) so segment counts are
-- stable across runs and safe to quote live in a demo.
WITH seq AS (
    SELECT SEQ4() AS i FROM TABLE(GENERATOR(ROWCOUNT => 2600))
),
base AS (
    SELECT
        i,
        'M-' || LPAD(CAST(i + 100001 AS VARCHAR), 7, '0') AS member_id,
        ABS(HASH(i, 11)) % 100 AS r_prod,
        ABS(HASH(i, 22)) % 100 AS r_age,
        ABS(HASH(i, 33)) % 100 AS r_region,
        ABS(HASH(i, 44)) % 100 AS r_credit,
        ABS(HASH(i, 55)) % 5   AS r_count,
        ABS(HASH(i, 66)) % 132 AS r_tenure,
        ABS(HASH(i, 77)) % 100 AS r_dd,
        ABS(HASH(i, 88)) % 100 AS r_engage,
        ABS(HASH(i, 99)) % 1000 AS r_bal
    FROM seq
),
labelled AS (
    SELECT
        member_id,
        CASE
            WHEN r_prod < 31 THEN 'Personal Loans'
            WHEN r_prod < 44 THEN 'Student Refinancing'
            WHEN r_prod < 51 THEN 'Home Loans'
            WHEN r_prod < 63 THEN 'Credit Card'
            WHEN r_prod < 85 THEN 'SoFi Money'
            ELSE 'SoFi Invest'
        END AS primary_product,
        CASE
            WHEN r_age < 26 THEN '18-27'
            WHEN r_age < 58 THEN '28-37'
            WHEN r_age < 80 THEN '38-47'
            WHEN r_age < 93 THEN '48-57'
            ELSE '58+'
        END AS age_band,
        CASE
            WHEN r_region < 23 THEN 'West'
            WHEN r_region < 43 THEN 'Southwest'
            WHEN r_region < 60 THEN 'Midwest'
            WHEN r_region < 79 THEN 'Southeast'
            ELSE 'Northeast'
        END AS region,
        -- SoFi skews prime / super-prime.
        CASE
            WHEN r_credit < 8  THEN 'Near Prime'
            WHEN r_credit < 34 THEN 'Prime'
            WHEN r_credit < 72 THEN 'Super Prime'
            ELSE 'Exceptional'
        END AS credit_band,
        CASE
            WHEN r_credit < 8  THEN 1
            WHEN r_credit < 34 THEN 2
            WHEN r_credit < 72 THEN 3
            ELSE 4
        END AS credit_order,
        r_count + 1 AS products_held,
        ROUND(r_tenure / 12.0, 1) AS tenure_years,
        CASE WHEN r_dd < 43 THEN 'Yes' ELSE 'No' END AS direct_deposit,
        CASE
            WHEN r_engage < 34 THEN 'Daily'
            WHEN r_engage < 68 THEN 'Weekly'
            WHEN r_engage < 89 THEN 'Monthly'
            ELSE 'Dormant'
        END AS engagement,
        CASE
            WHEN r_engage < 34 THEN 1
            WHEN r_engage < 68 THEN 2
            WHEN r_engage < 89 THEN 3
            ELSE 4
        END AS engagement_order,
        r_count, r_bal, r_credit, r_tenure, r_dd
    FROM base
)
SELECT
    member_id                        AS "Member ID",
    primary_product                  AS "Primary Product",
    age_band                         AS "Age Band",
    region                           AS "Region",
    credit_band                      AS "Credit Band",
    credit_order                     AS "Credit Order",
    products_held                    AS "Products Held",
    tenure_years                     AS "Tenure Years",
    direct_deposit                   AS "Direct Deposit",
    engagement                       AS "Engagement",
    engagement_order                 AS "Engagement Order",
    -- Balances scale with credit quality and product depth.
    ROUND(
        CASE
            WHEN credit_band = 'Near Prime'  THEN 6200
            WHEN credit_band = 'Prime'       THEN 11800
            WHEN credit_band = 'Super Prime' THEN 24500
            ELSE 41000
        END
        * (1 + products_held * 0.16)
        * (0.55 + r_bal / 1000.0 * 0.9)
    , 0)                             AS "Total Balances",
    -- Annual revenue per member, roughly 4-6% of balances plus a fee component.
    ROUND(
        (CASE
            WHEN credit_band = 'Near Prime'  THEN 6200
            WHEN credit_band = 'Prime'       THEN 11800
            WHEN credit_band = 'Super Prime' THEN 24500
            ELSE 41000
         END
         * (1 + products_held * 0.16)
         * (0.55 + r_bal / 1000.0 * 0.9)) * 0.048
        + products_held * 34
    , 0)                             AS "Annual Revenue",
    -- Attrition falls with tenure, products, direct deposit and engagement.
    ROUND(LEAST(0.93, GREATEST(0.01,
        0.36
        - 0.019 * tenure_years
        - 0.041 * products_held
        - CASE WHEN direct_deposit = 'Yes' THEN 0.085 ELSE 0 END
        - CASE engagement WHEN 'Daily' THEN 0.075 WHEN 'Weekly' THEN 0.045
                          WHEN 'Monthly' THEN 0.010 ELSE -0.070 END
        + (r_bal % 100) / 1000.0
    )), 3)                           AS "Attrition Propensity"
FROM labelled
