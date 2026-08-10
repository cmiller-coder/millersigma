-- SoFi loan book & fee businesses: 6 product lines x 24 months.
-- Pure generated SQL (no source tables) so it compiles on any Snowflake
-- connection. Amounts in $MM. Calibrated to SoFi's real scale: ~$3.5-3.9B
-- annual adjusted net revenue, ~$33B average balances, ~14M members.
-- Balance type matters to the economics: only lending products carry an asset
-- yield and a funding cost. SoFi Money holds DEPOSITS -- a funding source, not an
-- earning asset -- so it earns fee/interchange revenue and bears no interest
-- expense of its own; the cheap funding it provides is already reflected in the
-- lending products' low cost of funds. Modelling deposits as a 0%-yield asset
-- would book a large phantom interest expense against them.
WITH product AS (
__PRODUCTS__
),
states AS (
__STATES__
),
months AS (
    -- 24 complete months ending 2026-07
    SELECT DATEADD('month', SEQ4(), DATE '2024-08-01') AS period_month,
           SEQ4() AS month_index
    FROM TABLE(GENERATOR(ROWCOUNT => 24))
),
grid AS (
    SELECT
        p.*,
        g.state,
        g.state_share,
        -- deterministic per-state tilt so each state has its own story
        (MOD(ABS(HASH(g.state || p.product)), 21) - 10) / 100.0 AS state_tilt,
        m.period_month,
        m.month_index,
        POWER(1 + p.annual_growth / 12, m.month_index) AS trend,
        1 + 0.035 * SIN(2 * PI() * (m.month_index / 12.0) + p.phase) AS seasonal,
        -- Home lending is rate-sensitive: originations spike in the spring.
        CASE WHEN p.product = 'Home Loans' AND MONTH(m.period_month) IN (4, 5, 6) THEN 1.180
             WHEN p.product = 'Credit Card' AND MONTH(m.period_month) IN (11, 12) THEN 1.140
             ELSE 1.0 END AS event_factor
    FROM product p CROSS JOIN months m CROSS JOIN states g
),
calc AS (
    SELECT
        product, product_order, balance_type, state, state_tilt, period_month, month_index, delinq_rate,
        yield_rate, funding_rate,
        ROUND(bal_base * state_share * (1 + state_tilt) * trend * seasonal, 0) AS avg_balances,
        ROUND(fee_base * state_share * (1 + state_tilt) * trend * seasonal * event_factor, 2) AS fee_income,
        ROUND(members_base * state_share * POWER(1 + 0.075 / 12, month_index), 0) AS members_k,
        -- Originations run roughly 6% of balances a month for lending products.
        ROUND(bal_base * state_share * 0.060 * trend * seasonal * event_factor, 1) AS originations,
        provision_rate, opex_ratio,
        -- Funding cost eases ~45bps over the two years as rates come down.
        funding_rate - 0.0045 * (month_index / 23.0)            AS funding_eff
    FROM grid
),
fin AS (
    SELECT
        c.*,
        ROUND(avg_balances * yield_rate / 12, 2)                        AS interest_income,
        ROUND(avg_balances * funding_eff / 12, 2)                       AS interest_expense,
        ROUND(avg_balances * provision_rate / 12, 2)                    AS provision
    FROM calc c
)
SELECT
    product                                                    AS "Product",
    product_order                                              AS "Product Order",
    balance_type                                               AS "Balance Type",
    state                                                      AS "State",
    ROUND(1 + state_tilt * 1.6, 3)                             AS "Performance Index",
    period_month                                               AS "Period",
    YEAR(period_month)                                         AS "Year",
    'Q' || QUARTER(period_month)                               AS "Quarter",
    CASE WHEN month_index >= 12 THEN 'Current Period'
         ELSE 'Prior Period' END                               AS "Period Name",
    members_k                                                  AS "Members (K)",
    originations                                               AS "Originations",
    avg_balances                                               AS "Avg Balances",
    interest_income                                            AS "Interest Income",
    interest_expense                                           AS "Interest Expense",
    ROUND(interest_income - interest_expense, 2)               AS "Net Interest Income",
    fee_income                                                 AS "Fee Income",
    ROUND(interest_income - interest_expense + fee_income, 2)  AS "Net Revenue",
    provision                                                  AS "Provision",
    ROUND((interest_income - interest_expense + fee_income) * opex_ratio, 2) AS "Opex",
    ROUND(interest_income - interest_expense + fee_income
          - provision
          - (interest_income - interest_expense + fee_income) * opex_ratio, 2)
                                                               AS "Contribution Profit",
    ROUND(delinq_rate, 4)                                      AS "Delinquency Rate",
    ROUND(yield_rate * 100, 2)                                 AS "Yield Pct",
    ROUND(funding_eff * 100, 2)                                AS "Funding Cost Pct",
    ROUND((yield_rate - funding_eff) * 100, 2)                 AS "Spread Pct"
FROM fin
