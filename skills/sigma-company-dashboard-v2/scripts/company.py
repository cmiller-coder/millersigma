"""Company configuration — the ONLY file that changes between prospects.

Everything else in this generator (layout, personas, cards, alert rail, modeler,
modal, agent wiring) is company-agnostic. Swapping prospects means writing one
dict here, not editing the build.

The economics are deliberately per-product constants rather than a single
"revenue" number, because the whole demo rests on the P&L being internally
consistent: balances x yield - balances x funding + fees - provision - opex has
to reconcile to the headline KPI, or the first analyst in the room catches it.

    python3 build.py <company> update <workbookId>
    python3 build.py <company> create
"""

# ---------------------------------------------------------------------------
# Field notes for whoever adds the next one:
#
#   unit_noun     what a customer is called ("member", "customer", "account")
#   volume_noun   what the balance sheet number is ("balances", "throughput")
#   products      one row per line of business. bal_base is the stock metric in
#                 $MM; yield/funding only apply to products that carry an asset
#                 yield -- set both to 0 for fee-only or deposit lines.
#   alerts        the operational feed. Keep bodies to one line; they render in a
#                 narrow rail column.
# ---------------------------------------------------------------------------

SOFI = {
    "key": "sofi",
    "name": "SoFi",
    "title": "Member & Lending Command Center",
    "domain": "consumer fintech",
    "unit_noun": "member",
    "volume_noun": "balances",
    "logo_domain": "sofi.com",
    "base_table": "Loan Book",
    "palette": {
        "navy": "#0B2740", "navy_deep": "#06172A",
        "primary": "#0074F5", "secondary": "#00A2C7",
        "accent": "#03AAFF", "mint": "#00C4A7",
    },
    "products": [
        # name, order, balance_type, bal_base, yield, funding, fee_base,
        # provision, delinq, opex_ratio, growth, units_base, phase, tagline,
        # rate_label, goal_pct, status
        ("Personal Loans", 1, "Loans", 17500, .1320, .0410, 22.0, .0360, .0062,
         .380, .052, 3300, 0.0, "Consolidation lending", "Avg APR", .968, "On plan"),
        ("Student Refinancing", 2, "Loans", 9800, .0640, .0410, 6.0, .0090, .0021,
         .340, .028, 1150, 1.1, "Federal & private refi", "Avg APR", .712, "Behind"),
        ("Home Loans", 3, "Loans", 4200, .0680, .0410, 14.0, .0070, .0018,
         .420, .115, 340, 2.2, "Mortgage & HELOC", "Avg APR", 1.118, "Ahead"),
        ("Credit Card", 4, "Loans", 1150, .2150, .0410, 5.0, .0850, .0241,
         .460, .140, 820, 0.6, "Unlimited cash back", "Avg APR", .643, "Behind"),
        ("SoFi Money", 5, "Deposits", 38000, 0.0, 0.0, 45.0, 0.0, 0.0,
         .300, .180, 4600, 1.7, "Checking & savings", "APY", .994, "On plan"),
        ("SoFi Invest", 6, "AUM", 12740, 0.0, 0.0, 18.0, 0.0, 0.0,
         .350, .095, 2000, 2.8, "Brokerage & robo", "Fee", 1.047, "Ahead"),
    ],
    "alerts": [
        ("critical", "Fraud pattern detected",
         "Card-not-present velocity spike on 1,240 Credit Card accounts",
         "18m ago", "Financial Crimes", 1240, "accounts flagged"),
        ("critical", "Funding cost breach",
         "Cost of funds on SoFi Money exceeded the 4.35% plan ceiling",
         "2h ago", "Treasury", 16, "bps over ceiling"),
        ("warning", "Underwriting queue backing up",
         "412 Personal Loan applications past the 24-hour decision SLA",
         "3h ago", "Credit Ops", 412, "apps past SLA"),
        ("warning", "Delinquency drift",
         "Credit Card 30-day DQ up 41 bps week over week",
         "6h ago", "Risk", 41, "bps WoW"),
        ("info", "Rate change published",
         "Savings APY moved 4.20% to 4.35% for all new deposits",
         "1d ago", "Product", 15, "bps APY increase"),
    ],
    "agent": ("You are a fintech analyst covering SoFi's lending and member "
              "businesses. Answer with numbers from the workbook."),
}

BOA = {
    "key": "boa",
    "name": "Bank of America",
    "title": "Client & Balance Sheet Command Center",
    "domain": "universal bank",
    "unit_noun": "client",
    "volume_noun": "balances",
    "logo_domain": "bankofamerica.com",
    "base_table": "Loan Book",
    # BofA red + navy, straight off the corporate mark
    "palette": {
        "navy": "#012169", "navy_deep": "#00102F",
        "primary": "#E31837", "secondary": "#0B4EA2",
        "accent": "#D1122B", "mint": "#00A3A1",
    },
    "products": [
        ("Consumer Banking", 1, "Deposits", 1050000, 0.0, .0185, 1850.0, 0.0, 0.0,
         .520, .031, 69000, 0.0, "Checking, savings, small business",
         "Avg rate paid", .972, "On plan"),
        ("Consumer Lending", 2, "Loans", 312000, .0705, .0185, 240.0, .0125, .0091,
         .410, .044, 12400, 1.1, "Auto, personal, securities-based",
         "Avg APR", .904, "On plan"),
        ("Home Loans", 3, "Loans", 228000, .0615, .0185, 190.0, .0035, .0042,
         .430, .062, 3100, 2.2, "Mortgage & home equity",
         "Avg APR", 1.086, "Ahead"),
        ("Credit Card", 4, "Loans", 98000, .1780, .0185, 620.0, .0410, .0268,
         .440, .028, 24500, 0.6, "Consumer & business card",
         "Avg APR", .661, "Behind"),
        ("Merrill Wealth", 5, "AUM", 1420000, 0.0, 0.0, 3100.0, 0.0, 0.0,
         .620, .088, 3400, 1.7, "Advisory & investment management",
         "Fee rate", 1.041, "Ahead"),
        ("Global Markets", 6, "Trading", 480000, .0410, .0295, 2400.0, .0015, 0.0,
         .580, .019, 1200, 2.8, "Sales, trading & research",
         "Net spread", .738, "Behind"),
    ],
    "alerts": [
        ("critical", "Liquidity coverage watch",
         "LCR on the trading book fell to 118%, inside the 120% internal floor",
         "22m ago", "Treasury", 118, "% LCR"),
        ("critical", "Card fraud cluster",
         "Point-of-sale fraud ring detected across 3,410 consumer card accounts",
         "1h ago", "Financial Crimes", 3410, "accounts flagged"),
        ("warning", "Deposit beta accelerating",
         "Consumer Banking rate paid up 24 bps against a 15 bps plan",
         "4h ago", "ALM", 24, "bps rate paid"),
        ("warning", "Mortgage pipeline aging",
         "1,820 home loan applications past the 30-day close SLA",
         "6h ago", "Lending Ops", 1820, "apps past SLA"),
        ("info", "Fed decision priced",
         "Forward curve now implies one cut by Q4, down from two",
         "1d ago", "Research", 1, "cuts implied"),
    ],
    "agent": ("You are an analyst covering Bank of America's consumer, wealth "
              "and markets segments. Answer with numbers from the workbook."),
}

COMPANIES = {"sofi": SOFI, "boa": BOA}

# The hero plugin does NOT template -- a balance flywheel is a lending metaphor.
# Each industry declares its own, and its own section heading.
PLUGINS = {
    "sofi": {"hero": "55a04ab4-562a-4f14-b8f9-4901742b1fd8",
             "hero_label": "BALANCE FLYWHEEL",
             "ticker": "27050329-90c1-4b79-b32e-08aaa48f7c56"},
    "boa": {"hero": "55a04ab4-562a-4f14-b8f9-4901742b1fd8",
            "hero_label": "BALANCE SHEET FLYWHEEL",
            "ticker": "27050329-90c1-4b79-b32e-08aaa48f7c56"},
    "elevance": {"hero": "6311bbc6-e144-4845-8a4c-819a62cf27ab",
                 "hero_label": "PREMIUM & MEDICAL COST FLOW",
                 # a payer has no reason to watch the Treasury curve; this strip
                 # carries medical, Rx and specialty trend instead
                 "ticker": "2f50c42d-06be-4cd2-ad95-245442623287"},
}


def plugin(cfg, slot):
    return PLUGINS.get(cfg["key"], PLUGINS["sofi"])[slot]


def scale(cfg):
    """Format the headline volume at the company's own magnitude. BofA's
    trillions rendered as `$1,050.00` under a billions format -- the number was
    right and read as nonsense."""
    total = sum(p[3] for p in cfg["products"])          # $MM
    if total >= 1_000_000:                              # >= $1T
        return {"div": 1_000_000, "suffix": "T", "dp": 2}
    if total >= 1_000:                                  # >= $1B
        return {"div": 1_000, "suffix": "B", "dp": 2}
    return {"div": 1, "suffix": "M", "dp": 0}


def products_cte(cfg):
    """The per-product constants block that every generated SQL file shares."""
    rows = []
    for i, p in enumerate(cfg["products"]):
        (name, order, btype, bal, yld, fund, fee, prov, delinq,
         opex, growth, units, phase) = p[:13]
        lead = "SELECT" if i == 0 else "UNION ALL SELECT"
        cols = ("" if i else
                " AS product, %d AS product_order, '%s' AS balance_type,"
                " %d AS bal_base, %s AS yield_rate, %s AS funding_rate,"
                " %s AS fee_base, %s AS provision_rate, %s AS delinq_rate,"
                " %s AS opex_ratio, %s AS annual_growth, %d AS members_base,"
                " %s AS phase")
        if i == 0:
            rows.append("    %s '%s'%s" % (lead, name, cols % (
                order, btype, bal, yld, fund, fee, prov, delinq,
                opex, growth, units, phase)))
        else:
            rows.append("    %s '%s', %d, '%s', %d, %s, %s, %s, %s, %s, %s, %s, %d, %s"
                        % (lead, name, order, btype, bal, yld, fund, fee,
                           prov, delinq, opex, growth, units, phase))
    return "\n".join(rows)


def product_cards_sql(cfg):
    """One row per product for the card grid. Generated, not authored: the card
    values have to agree with the loan-book economics or the grid contradicts
    the KPI band directly above it."""
    rows = []
    for i, p in enumerate(cfg["products"]):
        name, bal = p[0], p[3]
        tagline, rate_label, goal, status = p[13], p[14], p[15], p[16]
        # rate shown on the card is the product's own yield, or the funding rate
        # for deposit lines (what the bank pays, not what it earns)
        rate = p[4] if p[4] else p[5]
        units = p[11]
        lead = "    SELECT" if i == 0 else "    UNION ALL SELECT"
        suffix = ("" if i else
                  " AS product, %d AS product_order, '%s' AS tagline,"
                  " %s AS balances_b, '%s' AS rate_label, '%s' AS rate_value,"
                  " %s AS members_m, %s AS goal_pct, '%s' AS status")
        vals = (p[1], tagline, round(bal / 1000.0, 2), rate_label,
                "%.2f%%" % (rate * 100), round(units / 1000.0, 2), goal, status)
        if i == 0:
            rows.append("%s '%s'%s" % (lead, name, suffix % vals))
        else:
            rows.append("%s '%s', %d, '%s', %s, '%s', '%s', %s, %s, '%s'"
                        % (lead, name, p[1], tagline, round(bal / 1000.0, 2),
                           rate_label, "%.2f%%" % (rate * 100),
                           round(units / 1000.0, 2), goal, status))
    return ("-- Generated from company.py. One row per product for the card grid.\n"
            "SELECT\n"
            "    CAST(product AS VARCHAR)            AS \"Product\",\n"
            "    CAST(product_order AS NUMBER)       AS \"Product Order\",\n"
            "    CAST(tagline AS VARCHAR)            AS \"Tagline\",\n"
            "    CAST(balances_b AS NUMBER(12,2))    AS \"Balances $B\",\n"
            "    CAST(rate_label AS VARCHAR)         AS \"Rate Label\",\n"
            "    CAST(rate_value AS VARCHAR)         AS \"Rate Value\",\n"
            "    CAST(members_m AS NUMBER(12,2))     AS \"Members M\",\n"
            "    CAST(goal_pct AS NUMBER(10,3))      AS \"Goal Pct\",\n"
            "    CAST(status AS VARCHAR)             AS \"Status\"\n"
            "FROM (\n" + "\n".join(rows) + "\n)\n")


def notifications_sql(cfg):
    """The operational alert feed, generated so each prospect gets alerts that
    belong to its own business rather than reskinned fintech copy."""
    rows = []
    for i, a in enumerate(cfg["alerts"]):
        sev, title, body, age, owner, impact, cap = a
        lead = "    SELECT" if i == 0 else "    UNION ALL SELECT"
        esc = lambda t: t.replace("'", "''")
        if i == 0:
            rows.append("%s 'a1' AS alert_key, 1 AS alert_order, '%s' AS severity,"
                        " '%s' AS title, '%s' AS body, '%s' AS age,"
                        " '%s' AS owner, %d AS impact"
                        % (lead, sev, esc(title), esc(body), age, esc(owner), impact))
        else:
            rows.append("%s 'a%d', %d, '%s', '%s', '%s', '%s', '%s', %d"
                        % (lead, i + 1, i + 1, sev, esc(title), esc(body),
                           age, esc(owner), impact))
    return ("-- Generated from company.py. One row per operational alert.\n"
            "SELECT\n"
            "    CAST(alert_key AS VARCHAR)       AS \"Alert Key\",\n"
            "    CAST(alert_order AS NUMBER)      AS \"Alert Order\",\n"
            "    CAST(severity AS VARCHAR)        AS \"Severity\",\n"
            "    CAST(title AS VARCHAR)           AS \"Title\",\n"
            "    CAST(body AS VARCHAR)            AS \"Body\",\n"
            "    CAST(age AS VARCHAR)             AS \"Age\",\n"
            "    CAST(owner AS VARCHAR)           AS \"Owner\",\n"
            "    CAST(impact AS NUMBER(12,0))     AS \"Impact\"\n"
            "FROM (\n" + "\n".join(rows) + "\n)\n")

SOFI["subs"] = {
    "Personal Loans": [("Debt Consolidation", .535, -30, 3.1, "On plan"),
                       ("Home Improvement", .224, 20, 5.4, "Ahead"),
                       ("Major Purchase", .157, 55, 1.2, "On plan"),
                       ("Medical & Dental", .084, 90, -0.8, "Behind")],
    "Student Refinancing": [("Undergraduate Refi", .485, -20, 2.1, "On plan"),
                            ("Graduate Refi", .331, 15, 3.6, "Ahead"),
                            ("Parent PLUS Refi", .123, 40, -1.4, "Behind"),
                            ("In-School Loans", .061, 70, 0.4, "On plan")],
    "Home Loans": [("Purchase Mortgage", .494, -15, 8.2, "Ahead"),
                   ("Refinance", .238, 10, 4.1, "Ahead"),
                   ("HELOC", .186, 55, 6.7, "Ahead"),
                   ("Jumbo", .082, -35, 1.9, "On plan")],
    "Credit Card": [("Unlimited 2% Cash Back", .578, -30, -2.4, "Behind"),
                    ("Everyday Cash", .305, 40, -1.1, "Behind"),
                    ("Secured Starter", .117, 190, 4.3, "Ahead")],
    "SoFi Money": [("Savings", .549, 0, 4.6, "Ahead"),
                   ("Checking", .311, -370, 2.8, "On plan"),
                   ("Vaults", .097, 0, 6.1, "Ahead"),
                   ("Joint Accounts", .043, 0, 1.5, "On plan")],
    "SoFi Invest": [("Active Brokerage", .479, 0, 3.3, "On plan"),
                    ("Robo Portfolios", .239, 25, 5.8, "Ahead"),
                    ("Retirement IRA", .224, 0, 2.2, "On plan"),
                    ("Fractional Shares", .058, 0, -0.6, "Behind")],
}

BOA["subs"] = {
    "Consumer Banking": [("Checking", .462, -120, 1.8, "On plan"),
                         ("Savings & CDs", .331, 95, 3.4, "Ahead"),
                         ("Small Business", .142, 40, 2.1, "On plan"),
                         ("Preferred Rewards", .065, 15, 5.2, "Ahead")],
    "Consumer Lending": [("Auto", .448, -45, 3.1, "On plan"),
                         ("Securities-Based", .287, -80, 6.4, "Ahead"),
                         ("Personal", .174, 210, -1.2, "Behind"),
                         ("Student", .091, 30, 0.6, "On plan")],
    "Home Loans": [("Purchase Mortgage", .512, -20, 7.8, "Ahead"),
                   ("Refinance", .218, 15, 3.2, "On plan"),
                   ("Home Equity", .194, 60, 5.9, "Ahead"),
                   ("Jumbo", .076, -40, 1.4, "On plan")],
    "Credit Card": [("Customized Cash", .404, -35, -1.8, "Behind"),
                    ("Travel Rewards", .296, 20, -2.6, "Behind"),
                    ("Business Card", .211, 55, 2.4, "On plan"),
                    ("Secured", .089, 240, 3.9, "Ahead")],
    "Merrill Wealth": [("Advisory Accounts", .518, 0, 9.1, "Ahead"),
                       ("Merrill Edge", .224, 0, 6.3, "Ahead"),
                       ("Retirement", .187, 0, 4.2, "On plan"),
                       ("Alternatives", .071, 0, 11.4, "Ahead")],
    "Global Markets": [("Fixed Income", .441, -25, -3.2, "Behind"),
                       ("Equities", .312, 30, 2.8, "On plan"),
                       ("Commodities", .148, 65, -5.1, "Behind"),
                       ("FX", .099, -10, 1.7, "On plan")],
}


def product_skus_sql(cfg):
    """Sub-product breakdown for the baseball-card modal. Shares are fractions of
    the parent product's balances, so the modal always reconciles to the card."""
    rows, n = [], 0
    for p in cfg["products"]:
        name, bal, units, base_rate = p[0], p[3], p[11], (p[4] or p[5])
        for order, (sub, share, dbps, qoq, status) in enumerate(cfg["subs"][name], 1):
            n += 1
            lead = "    SELECT" if n == 1 else "    UNION ALL SELECT"
            vals = (name.replace("'", "''"), sub.replace("'", "''"), order,
                    round(bal * share / 1000.0, 2), round(units * share / 1000.0, 1),
                    round((base_rate + dbps / 10000.0) * 100, 2), qoq, status)
            if n == 1:
                rows.append("%s '%s' AS product, '%s' AS sub_product, %d AS sub_order,"
                            " %s AS balances_b, %s AS members_k, %s AS rate_pct,"
                            " %s AS qoq_pct, '%s' AS status" % ((lead,) + vals))
            else:
                rows.append("%s '%s', '%s', %d, %s, %s, %s, %s, '%s'" % ((lead,) + vals))
    return ("-- Generated from company.py. One row per (product, sub-product).\n"
            "SELECT\n"
            "    CAST(product AS VARCHAR)         AS \"Product\",\n"
            "    CAST(sub_product AS VARCHAR)     AS \"Sub-Product\",\n"
            "    CAST(sub_order AS NUMBER)        AS \"Sub-Product Order\",\n"
            "    CAST(balances_b AS NUMBER(12,2)) AS \"Balances $B\",\n"
            "    CAST(members_k AS NUMBER(12,1))  AS \"Members K\",\n"
            "    CAST(rate_pct AS NUMBER(8,2))    AS \"Rate Pct\",\n"
            "    CAST(qoq_pct AS NUMBER(8,2))     AS \"QoQ Growth Pct\",\n"
            "    CAST(status AS VARCHAR)          AS \"Status\"\n"
            "FROM (\n" + "\n".join(rows) + "\n)\n")


# ---------------------------------------------------------------------------
# Healthcare payer. This is the config that proves the template is not secretly
# a banking template, so the mapping is worth spelling out:
#
#   products      -> benefit plans (Commercial, Medicare Advantage, Medicaid...)
#   bal_base      -> member months, the volume the P&L scales with
#   yield_rate    -> premium PMPM yield
#   funding_rate  -> medical cost PMPM (the payer's cost of goods)
#   fee_base      -> admin/ASO fee revenue
#   provision     -> IBNR reserve build
#   delinq        -> prior-auth denial-overturn rate, the quality signal
#   opex_ratio    -> admin expense ratio
#
# The spread between yield and funding IS the medical loss ratio, which is why
# the same cross-join scenario modeler works unchanged: a "rate shock" becomes a
# trend shock to medical cost.
# ---------------------------------------------------------------------------

ELEVANCE = {
    "key": "elevance",
    "name": "Elevance Health",
    "title": "Membership & Medical Cost Command Center",
    "domain": "healthcare payer",
    "unit_noun": "member",
    "volume_noun": "member months",
    "logo_domain": "elevancehealth.com",
    "base_table": "Benefit Ledger",
    "palette": {
        "navy": "#1B365D", "navy_deep": "#0C1D33",
        "primary": "#286CE2", "secondary": "#0F5AA8",
        "accent": "#5B9BF8", "mint": "#00A69C",
    },
    "products": [
        ("Commercial Group", 1, "Fully insured", 41200, .0512, .0428, 62.0, .0090, .0410,
         .118, .031, 3420, 0.0, "Employer-sponsored plans", "Premium PMPM", .981, "On plan"),
        ("Medicare Advantage", 2, "Fully insured", 28600, .1104, .0961, 38.0, .0140, .0362,
         .092, .094, 1180, 1.1, "MA and MAPD plans", "Premium PMPM", 1.062, "Ahead"),
        ("Medicaid Managed", 3, "Fully insured", 33900, .0468, .0421, 21.0, .0120, .0518,
         .081, .046, 2760, 2.2, "State managed care", "Premium PMPM", .694, "Behind"),
        ("ASO Self-funded", 4, "Administrative", 52400, 0.0, 0.0, 148.0, 0.0, .0288,
         .640, .058, 4310, 0.6, "Self-funded employers", "Admin fee PMPM", 1.041, "Ahead"),
        ("Individual Exchange", 5, "Fully insured", 11800, .0596, .0547, 14.0, .0180, .0605,
         .104, .128, 890, 1.7, "ACA marketplace", "Premium PMPM", .648, "Behind"),
        ("Pharmacy Benefit", 6, "Carve-out", 19400, .0342, .0289, 74.0, .0060, .0224,
         .126, .072, 5140, 2.8, "PBM and specialty drug", "Net rebate yield", .972, "On plan"),
    ],
    "alerts": [
        ("critical", "Medical loss ratio breach",
         "Individual Exchange MLR hit 91.8%, above the 88% pricing assumption",
         "31m ago", "Actuarial", 380, "bps over target"),
        ("critical", "High-cost claimant cluster",
         "14 new claimants above $250K attached to Commercial Group this month",
         "2h ago", "Care Management", 14, "claimants over $250K"),
        ("warning", "Prior-auth backlog",
         "2,140 authorizations past the 72-hour turnaround standard",
         "4h ago", "Utilization Mgmt", 2140, "auths past SLA"),
        ("warning", "Star rating exposure",
         "Medicare Advantage CAHPS scores trending toward a 3.5 star cut",
         "7h ago", "Quality", 35, "projected stars x10"),
        ("info", "Risk adjustment submitted",
         "Q3 RAPS/EDPS files accepted with a 0.04 coding intensity lift",
         "1d ago", "Risk Adjustment", 4, "bps RAF lift"),
    ],
    "agent": ("You are an analyst covering Elevance Health's benefit plans, "
              "membership and medical cost trend."),
}

ELEVANCE["subs"] = {
    "Commercial Group": [("Large Group PPO", .441, -40, 2.1, "On plan"),
                         ("Large Group HMO", .262, 25, 1.4, "On plan"),
                         ("Small Group", .188, 110, -2.8, "Behind"),
                         ("Level-funded", .109, -60, 8.6, "Ahead")],
    "Medicare Advantage": [("MAPD HMO", .512, -30, 9.2, "Ahead"),
                           ("MAPD PPO", .284, 45, 6.8, "Ahead"),
                           ("D-SNP", .142, 120, 12.4, "Ahead"),
                           ("MA-only", .062, -20, -1.1, "Behind")],
    "Medicaid Managed": [("TANF", .468, -15, 1.2, "On plan"),
                         ("Expansion", .291, 30, -3.4, "Behind"),
                         ("LTSS", .164, 95, 4.1, "Ahead"),
                         ("CHIP", .077, -25, 0.6, "On plan")],
    "ASO Self-funded": [("National Accounts", .524, 0, 7.2, "Ahead"),
                        ("Regional Employers", .276, 0, 3.8, "On plan"),
                        ("Taft-Hartley", .128, 0, 1.1, "On plan"),
                        ("Stop-loss attach", .072, 0, 9.4, "Ahead")],
    "Individual Exchange": [("Silver On-Exchange", .548, -25, -4.2, "Behind"),
                            ("Bronze", .241, 60, -2.1, "Behind"),
                            ("Gold", .142, -40, 1.8, "On plan"),
                            ("Catastrophic", .069, 140, 0.4, "On plan")],
    "Pharmacy Benefit": [("Specialty", .462, 55, 11.8, "Ahead"),
                         ("Retail generic", .288, -30, 1.2, "On plan"),
                         ("Retail brand", .174, 40, -2.6, "Behind"),
                         ("Mail order", .076, -15, 3.4, "On plan")],
}

COMPANIES["elevance"] = ELEVANCE


# ---------------------------------------------------------------------------
# Domain language. The layout is universal; the WORDS are not. A payer does not
# have a "Finance" tab or "Avg balances" -- it has actuarial trend and member
# months. Anything a human reads comes from here.
# ---------------------------------------------------------------------------
LABELS = {
    "sofi": {
        "col_volume": "Baseline Balances",
        "col_growth": "Balance Growth %",
        "col_yield": "Yield \u0394 bps",
        "col_cost": "Funding \u0394 bps",
        "personas": ["Executive", "Analyst"],
        "seg_product": "Primary Product", "seg_credit": "Credit Band",
        "seg_dd": "Direct Deposit", "seg_engage": "Engagement",
        "seg_held": "Products held", "cohort_name": "Cohort name",
        "kpi_cohort_size": "Members in Cohort",
        "kpi_cohort_vol": "Cohort Balances", "kpi_cohort_rev": "Revenue per Member",
        "kpi_cohort_risk": "Avg Attrition Risk",
        "modeler_page": "Finance", "cohort_page": "Cohort Builder",
        "modeler_title": "Rate & Growth Scenario Modeler",
        "shock_label": "Parallel rate shock (bps)",
        "kpi_revenue": "Net revenue ($M)", "kpi_margin": "Contribution ($M)",
        "kpi_volume": "Avg balances ($M)", "kpi_units": "Members (K)",
        "driver_nim": "Net interest margin", "driver_risk": "30-day delinquency",
        "driver_cost": "Cost of funds", "driver_eff": "Efficiency ratio",
        # the third Color-by option / the Balance Type dimension
        "seg_type": "Balance type",
        # cohort filter for CohortAge -- was hardcoded "Age Band" in
        # build_sofi.py for every company until Veraset's build (B2B
        # enterprise accounts have no natural "age," found via QA render).
        # Parameterized instead of patched per-company.
        "seg_age": "Age Band",
    },
    "boa": {
        "personas": ["Executive", "Analyst"],
        "seg_product": "Primary Product", "seg_credit": "Credit Band",
        "seg_dd": "Direct Deposit", "seg_engage": "Engagement",
        "seg_held": "Products held", "cohort_name": "Cohort name",
        "kpi_cohort_size": "Members in Cohort",
        "kpi_cohort_vol": "Cohort Balances", "kpi_cohort_rev": "Revenue per Member",
        "kpi_cohort_risk": "Avg Attrition Risk",
        "modeler_page": "Finance", "cohort_page": "Client Segments",
        "modeler_title": "Rate & Balance Sheet Scenario Modeler",
        "shock_label": "Parallel rate shock (bps)",
        "kpi_revenue": "Net revenue ($M)", "kpi_margin": "Contribution ($M)",
        "kpi_volume": "Avg balances ($M)", "kpi_units": "Clients (K)",
        "driver_nim": "Net interest margin", "driver_risk": "30-day delinquency",
        "driver_cost": "Cost of funds", "driver_eff": "Efficiency ratio",
    },
    "elevance": {
        "personas": ["Executive", "Actuarial"],
        "seg_product": "Primary plan", "seg_credit": "Risk band",
        "seg_dd": "PCP assigned", "seg_engage": "Utilization",
        "seg_held": "Chronic conditions", "cohort_name": "Population name",
        "kpi_cohort_size": "Members in population",
        "kpi_cohort_vol": "Annual medical cost", "kpi_cohort_rev": "Premium per member",
        "kpi_cohort_risk": "Avg churn risk",
        "modeler_page": "Trend & Pricing", "cohort_page": "Population Builder",
        "modeler_title": "Medical Cost Trend & Pricing Modeler",
        "shock_label": "Medical cost trend shock (bps)",
        "kpi_revenue": "Premium revenue ($M)", "kpi_margin": "Underwriting margin ($M)",
        "kpi_volume": "Member months (K)", "kpi_units": "Members (K)",
        "driver_nim": "Underwriting margin %", "driver_risk": "Denial overturn rate",
        "driver_cost": "Medical cost PMPM", "driver_eff": "Admin expense ratio",
    },
}


def lab(cfg, key):
    """Domain label lookup, falling back to the SoFi wording."""
    return LABELS.get(cfg["key"], LABELS["sofi"]).get(key, LABELS["sofi"][key])


# ---------------------------------------------------------------------------
# Geography. The Cold Provisions overview works because you scan a map for the
# one region that is the wrong colour, then click into it. That needs a state
# dimension, which is a per-company footprint: a payer's licensed states, a
# bank's branch footprint, a chain's store states.
# ---------------------------------------------------------------------------
FOOTPRINTS = {
    "sofi": [("CA", .148), ("TX", .112), ("NY", .094), ("FL", .088), ("IL", .058),
             ("PA", .051), ("OH", .046), ("GA", .044), ("NC", .041), ("WA", .038),
             ("MA", .036), ("AZ", .034), ("NJ", .033), ("VA", .031), ("CO", .029)],
    "boa":  [("CA", .171), ("TX", .124), ("FL", .102), ("NY", .091), ("NC", .068),
             ("NJ", .048), ("MA", .045), ("WA", .041), ("GA", .039), ("VA", .036),
             ("AZ", .033), ("PA", .031), ("MD", .029), ("IL", .027), ("CT", .024)],
    # Elevance's real Blue-plan footprint
    "elevance": [("CA", .218), ("NY", .131), ("OH", .094), ("IN", .081), ("GA", .069),
                 ("VA", .062), ("KY", .048), ("MO", .046), ("WI", .041), ("CT", .038),
                 ("CO", .034), ("NV", .031), ("ME", .022), ("NH", .021), ("TX", .019)],
}


def states_cte(cfg):
    """The footprint block injected into the ONE base table."""
    rows = []
    for i, (st, share) in enumerate(FOOTPRINTS.get(cfg["key"], FOOTPRINTS["sofi"])):
        lead = "    SELECT" if i == 0 else "    UNION ALL SELECT"
        if i == 0:
            rows.append("%s '%s' AS state, %s AS state_share" % (lead, st, share))
        else:
            rows.append("%s '%s', %s" % (lead, st, share))
    return "\n".join(rows)


def geo_sql(cfg):
    """State x product performance. Deterministic variance from a hash so each
    state has its own story without needing a random seed."""
    rows, n = [], 0
    states = FOOTPRINTS.get(cfg["key"], FOOTPRINTS["sofi"])
    for st, share in states:
        for p in cfg["products"]:
            n += 1
            name, vol, yld, cost = p[0], p[3], p[4], p[5]
            # spread the footprint share across products, then tilt per state
            tilt = ((sum(ord(c) for c in st + name) % 21) - 10) / 100.0
            v = round(vol * share * (1 + tilt), 1)
            perf = round(1.0 + tilt * 1.6, 3)
            spread = round(((yld - cost) * 100) * (1 + tilt), 3)
            lead = "    SELECT" if n == 1 else "    UNION ALL SELECT"
            if n == 1:
                rows.append("%s '%s' AS state, '%s' AS product, %s AS volume,"
                            " %s AS perf_index, %s AS spread_pct"
                            % (lead, st, name.replace("'", "''"), v, perf, spread))
            else:
                rows.append("%s '%s', '%s', %s, %s, %s"
                            % (lead, st, name.replace("'", "''"), v, perf, spread))
    return ("-- Generated from company.py. State x product footprint.\n"
            "SELECT\n"
            "    CAST(state AS VARCHAR)          AS \"State\",\n"
            "    CAST(product AS VARCHAR)        AS \"Product\",\n"
            "    CAST(volume AS NUMBER(14,1))    AS \"Volume\",\n"
            "    CAST(perf_index AS NUMBER(8,3)) AS \"Performance Index\",\n"
            "    CAST(spread_pct AS NUMBER(8,3)) AS \"Spread Pct\"\n"
            "FROM (\n" + "\n".join(rows) + "\n)\n")


# Population segmentation. The SCHEMA is universal -- every business segments
# its people by a risk-ish band, an engagement-ish band, a yes/no flag and a
# count of things held. Only the vocabulary changes, so substitute the literals
# rather than rewriting the SQL.
SEGMENTS = {
    "sofi": {},   # the SQL is authored in SoFi's vocabulary already
    "boa": {"Near Prime": "Mass Market", "Prime": "Preferred",
            "Super Prime": "Platinum", "Exceptional": "Private Bank"},
    "elevance": {"Near Prime": "High Risk", "Prime": "Rising Risk",
                 "Super Prime": "Stable", "Exceptional": "Healthy",
                 "Daily": "High", "Weekly": "Moderate",
                 "Monthly": "Low", "Dormant": "None"},
}


# Per-unit economics for the population table, by band, in DOLLARS. The
# defaults are retail-banking balances; a company whose unit economics live at a
# different order of magnitude must override, or the cohort KPIs read as
# nonsense (a dental patient with an $1,825 lifetime value).
POP = {
    "_default": {"bases": (6200, 11800, 24500, 41000), "rev_rate": 0.048,
                 "fee_per_product": 34},
    "nuvia": {"bases": (9500, 21000, 34000, 46000), "rev_rate": 0.92,
              "fee_per_product": 620},
}


def population_sql(cfg, raw):
    """Swap the segment vocabulary AND the per-unit economics. Every band
    literal appears in both the assignment CASE and the downstream economics
    CASEs, so a global replace is what keeps them consistent -- editing one site
    orphans the others."""
    for old, new in SEGMENTS.get(cfg["key"], {}).items():
        raw = raw.replace("'%s'" % old, "'%s'" % new)
    pop = POP.get(cfg["key"], POP["_default"])
    d = POP["_default"]
    if pop is not d:
        # bases appear twice (balances + revenue); replace both occurrences
        for i, (a, b) in enumerate(zip(d["bases"], pop["bases"])):
            # the top band is an ELSE branch, not a THEN -- it has no literal
            kw = "ELSE" if i == len(d["bases"]) - 1 else "THEN"
            raw = raw.replace("%s %d" % (kw, a), "%s %d" % (kw, b))
        raw = raw.replace("* 0.048", "* %s" % pop["rev_rate"])
        raw = raw.replace("products_held * 34", "products_held * %d"
                          % pop["fee_per_product"])
    return raw


# Agent vocabulary. The instruction body -- not just the product list -- has to
# speak the domain, or a payer's copilot offers to explain credit-card
# delinquency. `econ` explains the spread; `metrics` are what to cite; `bands`
# are the valid segment values for the cohort agent.
VOCAB = {
    "sofi": {
        "econ": "Lending products carry an asset yield and a funding cost; deposit "
                "and AUM lines earn fee and interchange revenue instead.",
        "metrics": "net revenue, contribution profit, provision and delinquency",
        "bands": "Credit bands: Near Prime (640-679), Prime (680-719), Super Prime "
                 "(720-779), Exceptional (780+). Engagement: Daily, Weekly, Monthly, "
                 "Dormant.",
        "cohort_report": "cohort size, balances and average attrition risk",
    },
    "boa": {
        "econ": "Lending and deposit lines carry an asset yield and a cost of funds; "
                "wealth and markets lines earn fee and spread revenue instead.",
        "metrics": "net revenue, contribution profit, provision and delinquency",
        "bands": "Client tiers: Mass Market, Preferred, Platinum, Private Bank. "
                 "Engagement: Daily, Weekly, Monthly, Dormant.",
        "cohort_report": "segment size, balances and average attrition risk",
    },
    "elevance": {
        "econ": "Fully insured plans earn premium PMPM against medical cost PMPM -- "
                "the spread between them is the medical loss ratio. ASO lines earn an "
                "administrative fee and carry no medical risk.",
        "metrics": "premium revenue, underwriting margin, IBNR reserve build and "
                   "medical loss ratio",
        "bands": "Risk bands: High Risk, Rising Risk, Stable, Healthy. Utilization: "
                 "High, Moderate, Low, None.",
        "cohort_report": "population size, annual medical cost and average churn risk",
    },
}


def vocab(cfg, key):
    return VOCAB.get(cfg["key"], VOCAB["sofi"])[key]


# ---------------------------------------------------------------------------
# COLD-RUN TEST: derived from the company name alone, no hand-holding.
# McDonald's stresses the template because franchise economics are not lending
# economics: the "volume" is system-wide sales it does not book as revenue, and
# the "yield" is the royalty + rent rate it takes off the top.
#
#   volume  -> system-wide sales ($MM)
#   yield   -> royalty + rent rate taken by the franchisor
#   cost    -> company-operated restaurant operating cost
#   fee     -> initial franchise fees
#   risk    -> restaurants below plan (the operational quality signal)
# ---------------------------------------------------------------------------
MCD = {
    "key": "mcd",
    "name": "McDonald's",
    "title": "Market & Restaurant Performance Command Center",
    "domain": "quick-service restaurant franchisor",
    "unit_noun": "guest",
    "volume_noun": "system-wide sales",
    "logo_domain": "mcdonalds.com",
    "base_table": "Market Performance",
    "palette": {
        "navy": "#27251F", "navy_deep": "#141210",
        "primary": "#DA291C", "secondary": "#FFC72C",
        "accent": "#FF8C1A", "mint": "#2E8B57",
    },
    "products": [
        ("US", 1, "Franchised", 53800, .1340, .0812, 210.0, .0040, .0180,
         .118, .046, 26400, 0.0, "Largest market, 95% franchised",
         "Royalty + rent", .982, "On plan"),
        ("France", 2, "Franchised", 7900, .1420, .0904, 34.0, .0035, .0165,
         .126, .038, 3100, 1.1, "Strong franchise base", "Royalty + rent", 1.058, "Ahead"),
        ("United Kingdom", 3, "Franchised", 8600, .1385, .0868, 38.0, .0030, .0142,
         .121, .052, 3400, 2.2, "Delivery-led growth", "Royalty + rent", 1.041, "Ahead"),
        ("Germany", 4, "Franchised", 6400, .1360, .0921, 27.0, .0045, .0205,
         .133, .021, 2600, 0.6, "Mature, traffic-pressured",
         "Royalty + rent", .914, "Behind"),
        ("Australia", 5, "Franchised", 4100, .1310, .0886, 18.0, .0038, .0158,
         .128, .034, 1700, 1.7, "High average check", "Royalty + rent", .968, "On plan"),
        ("China (IDL)", 6, "Developmental", 11200, .0305, 0.0, 12.0, .0010, .0126,
         .092, .118, 5900, 2.8, "Licensed, royalty-only",
         "Royalty rate", 1.086, "Ahead"),
    ],
    "alerts": [
        ("critical", "Beef cost spike",
         "Ground beef up 11.4% month over month against a 4% plan assumption",
         "26m ago", "Supply Chain", 1140, "bps over plan"),
        ("critical", "Drive-thru service times",
         "412 US restaurants above the 4-minute drive-thru standard",
         "1h ago", "Operations", 412, "restaurants over SLA"),
        ("warning", "Germany traffic decline",
         "Guest counts down 3.8% year over year, third consecutive month",
         "5h ago", "Market Ops", 380, "bps traffic decline"),
        ("warning", "Franchisee cash flow",
         "68 franchisees below the 12% cash-flow-margin covenant",
         "6h ago", "Franchising", 68, "franchisees at risk"),
        ("info", "Delivery mix milestone",
         "Delivery reached 22% of system-wide sales in top-six markets",
         "1d ago", "Digital", 22, "% delivery mix"),
    ],
    "agent": ("You are an analyst covering McDonald's markets, franchisee "
              "economics and restaurant operations."),
}

MCD["subs"] = {
    "US": [("Breakfast", .224, -40, 1.2, "On plan"), ("Lunch", .358, 0, 2.4, "On plan"),
           ("Dinner", .291, 15, 3.1, "Ahead"), ("Late night", .127, 60, -2.8, "Behind")],
    "France": [("Lunch", .392, 0, 3.4, "Ahead"), ("Dinner", .318, 20, 4.1, "Ahead"),
               ("Breakfast", .186, -30, 1.1, "On plan"), ("Snack", .104, 45, 2.2, "On plan")],
    "United Kingdom": [("Lunch", .341, 0, 4.2, "Ahead"), ("Dinner", .302, 25, 5.6, "Ahead"),
                       ("Breakfast", .214, -25, 2.1, "On plan"), ("Late night", .143, 70, 3.8, "Ahead")],
    "Germany": [("Lunch", .368, 0, -2.1, "Behind"), ("Dinner", .296, 20, -3.4, "Behind"),
                ("Breakfast", .201, -35, -1.2, "Behind"), ("Snack", .135, 50, 1.4, "On plan")],
    "Australia": [("Lunch", .334, 0, 2.8, "On plan"), ("Dinner", .287, 20, 3.2, "Ahead"),
                  ("Breakfast", .246, -30, 1.6, "On plan"), ("Late night", .133, 65, -0.8, "Behind")],
    "China (IDL)": [("Lunch", .352, 0, 12.4, "Ahead"), ("Dinner", .311, 15, 13.8, "Ahead"),
                    ("Breakfast", .189, -20, 8.2, "Ahead"), ("Delivery", .148, 40, 21.6, "Ahead")],
}

FOOTPRINTS["mcd"] = [("CA", .118), ("TX", .102), ("FL", .088), ("NY", .062),
                     ("IL", .054), ("OH", .048), ("PA", .046), ("MI", .042),
                     ("GA", .040), ("NC", .038), ("NJ", .034), ("VA", .032),
                     ("AZ", .030), ("WA", .028), ("MA", .026)]

LABELS["mcd"] = {
    "personas": ["Executive", "Operations"],
    "modeler_page": "Planning", "cohort_page": "Guest Segments",
    "modeler_title": "Commodity & Traffic Scenario Modeler",
    "shock_label": "Food & paper cost shock (bps)",
    "kpi_revenue": "Franchisor revenue ($M)", "kpi_margin": "Segment margin ($M)",
    "kpi_volume": "System-wide sales ($M)", "kpi_units": "Guests (K)",
    "driver_nim": "Franchise margin %", "driver_risk": "Restaurants below plan",
    "driver_cost": "Food & paper cost %", "driver_eff": "G&A ratio",
    "seg_product": "Market", "seg_credit": "Restaurant tier",
    "seg_dd": "Drive-thru", "seg_engage": "Visit frequency",
    "seg_held": "Dayparts visited", "cohort_name": "Segment name",
    "kpi_cohort_size": "Guests in segment", "kpi_cohort_vol": "Annual spend",
    "kpi_cohort_rev": "Spend per guest", "kpi_cohort_risk": "Avg churn risk",
}

SEGMENTS["mcd"] = {"Near Prime": "Value", "Prime": "Core",
                   "Super Prime": "Frequent", "Exceptional": "Loyalty app",
                   "Daily": "Daily", "Weekly": "Weekly",
                   "Monthly": "Monthly", "Dormant": "Lapsed"}

VOCAB["mcd"] = {
    "econ": "Franchised markets earn a royalty and rent off system-wide sales the "
            "franchisor does not book as revenue; developmental licensed markets "
            "earn a royalty only and carry no restaurant operating cost.",
    "metrics": "franchisor revenue, segment margin, system-wide sales and guest counts",
    "bands": "Restaurant tiers: Value, Core, Frequent, Loyalty app. Visit frequency: "
             "Daily, Weekly, Monthly, Lapsed.",
    "cohort_report": "segment size, annual spend and average churn risk",
}

# A Treasury curve on a burger chain is nonsense, and a "balance flywheel" is a
# lending metaphor. Day-part sales and a food-and-paper commodity basket are what
# a QSR operator actually watches.
PLUGINS["mcd"] = {"hero": "ff626565-e857-4921-b01d-a39f570dec44",
                  "hero_label": "DAY-PART SALES HEATMAP",
                  "ticker": "2e4dd24a-7be2-4bcb-aaf8-8f7ebe88088e"}

COMPANIES["mcd"] = MCD


# ---------------------------------------------------------------------------
# Abry Partners — middle-market PE, built for Chad Morris' call.
# Sectors are ABRY'S OWN taxonomy, lifted from the icon set on abry.com:
# Business Services, Communications, Data Center, Government, Healthcare,
# Human Capital, Insurance, Media, Outsourced Services. Using their real
# sectors instead of generic "portfolio companies" is the credibility lever.
#
#   product -> portfolio sector
#   volume  -> invested capital ($MM)
#   yield   -> portfolio company EBITDA margin
#   cost    -> blended cost of debt on the LBO structure
#   spread  -> the value-creation spread the fund earns
#   fee     -> management + monitoring fees
#   risk    -> companies tripping covenant thresholds
# ---------------------------------------------------------------------------
ABRY = {
    "key": "abry",
    "name": "Abry Partners",
    "title": "Portfolio Performance & Value Creation Command Center",
    "domain": "middle-market private equity",
    "unit_noun": "portfolio company",
    "volume_noun": "invested capital",
    "logo_domain": "abry.com",
    "base_table": "Portfolio Ledger",
    # deep navy + Boston-brick accent, off their site's palette
    "palette": {
        "navy": "#0E2A47", "navy_deep": "#07182A",
        "primary": "#1F6FB2", "secondary": "#8C6239",
        "accent": "#4A97D2", "mint": "#2E9E7E",
    },
    "products": [
        ("Communications", 1, "Control buyout", 1840, .2410, .0865, 22.0, .0180, .0420,
         .140, .086, 14, 0.0, "Fiber, wireless infrastructure",
         "EBITDA margin", 1.062, "Ahead"),
        ("Business Services", 2, "Control buyout", 1420, .2180, .0910, 18.0, .0150, .0380,
         .132, .094, 19, 1.1, "Tech-enabled B2B services",
         "EBITDA margin", 1.041, "Ahead"),
        ("Insurance Services", 3, "Control buyout", 1160, .2650, .0885, 15.0, .0120, .0290,
         .128, .112, 11, 2.2, "Brokerage, MGA platforms",
         "EBITDA margin", 1.084, "Ahead"),
        ("Media & Information", 4, "Control buyout", 980, .1920, .0940, 12.0, .0240, .0610,
         .146, .034, 9, 0.6, "Data, subscription information",
         "EBITDA margin", .872, "Behind"),
        ("Healthcare Services", 5, "Control buyout", 760, .2050, .0925, 9.0, .0210, .0530,
         .138, .058, 8, 1.7, "Provider platforms, rev-cycle",
         "EBITDA margin", .941, "On plan"),
        ("Data Center & Digital", 6, "Growth equity", 640, .3120, .0805, 7.0, .0090, .0210,
         .118, .148, 5, 2.8, "Colocation, edge compute",
         "EBITDA margin", 1.118, "Ahead"),
    ],
    "alerts": [
        ("critical", "Covenant headroom breach",
         "Two Media & Information companies inside 0.25x of the leverage covenant",
         "34m ago", "Portfolio Ops", 2, "companies at covenant"),
        ("critical", "Refinancing wall",
         "$418M of portfolio debt matures inside 18 months at above-market spreads",
         "2h ago", "Capital Markets", 418, "$M maturing"),
        ("warning", "Value creation plan slippage",
         "Six companies behind on VCP milestones for two consecutive quarters",
         "5h ago", "Operating Partners", 6, "companies behind VCP"),
        ("warning", "Add-on pipeline stalling",
         "Nine signed LOIs past the 90-day close target across three platforms",
         "7h ago", "Deal Team", 9, "LOIs past target"),
        ("info", "Exit readiness",
         "Insurance Services platform cleared the 3.0x MOIC readiness threshold",
         "1d ago", "Investment Committee", 30, "MOIC x10"),
    ],
    "agent": ("You are an analyst covering Abry Partners' portfolio companies, "
              "value creation plans and capital structure."),
}

ABRY["subs"] = {
    "Communications": [("Fiber infrastructure", .412, -40, 8.2, "Ahead"),
                       ("Wireless towers", .284, 20, 6.4, "Ahead"),
                       ("Managed connectivity", .186, 60, 3.1, "On plan"),
                       ("Rural broadband", .118, 110, -1.4, "Behind")],
    "Business Services": [("Tech-enabled BPO", .368, 0, 9.1, "Ahead"),
                          ("Compliance services", .276, -30, 5.8, "Ahead"),
                          ("Facilities services", .204, 45, 2.2, "On plan"),
                          ("Logistics services", .152, 80, -2.1, "Behind")],
    "Insurance Services": [("Retail brokerage", .441, -25, 11.2, "Ahead"),
                           ("MGA platforms", .312, 15, 9.4, "Ahead"),
                           ("Claims services", .156, 50, 4.1, "On plan"),
                           ("Benefits admin", .091, 90, 1.2, "On plan")],
    "Media & Information": [("Subscription data", .384, 0, 2.1, "On plan"),
                            ("B2B publishing", .291, 40, -4.8, "Behind"),
                            ("Events", .208, 75, -6.2, "Behind"),
                            ("Ad-supported", .117, 120, -8.4, "Behind")],
    "Healthcare Services": [("Provider platforms", .402, -20, 4.2, "On plan"),
                            ("Revenue cycle", .298, 25, 6.8, "Ahead"),
                            ("Behavioral health", .184, 55, 1.1, "On plan"),
                            ("Dental platforms", .116, 95, -3.2, "Behind")],
    "Data Center & Digital": [("Colocation", .458, -35, 16.4, "Ahead"),
                              ("Edge compute", .282, 10, 21.2, "Ahead"),
                              ("Interconnection", .164, 45, 12.8, "Ahead"),
                              ("Managed cloud", .096, 85, 7.4, "Ahead")],
}

FOOTPRINTS["abry"] = [("MA", .142), ("NY", .118), ("TX", .094), ("CA", .086),
                      ("FL", .072), ("IL", .062), ("GA", .058), ("NC", .052),
                      ("PA", .048), ("OH", .044), ("CO", .040), ("VA", .038),
                      ("TN", .034), ("AZ", .030), ("WA", .028)]

LABELS["abry"] = {
    "personas": ["Investment Committee", "Deal Team"],
    "modeler_page": "Value Creation", "cohort_page": "Portfolio Screening",
    "modeler_title": "Value Creation & Exit Scenario Modeler",
    "shock_label": "EBITDA growth shock (bps)",
    "kpi_revenue": "Portfolio EBITDA ($M)", "kpi_margin": "Value creation ($M)",
    "kpi_volume": "Invested capital ($M)", "kpi_units": "Companies",
    "driver_nim": "Avg EBITDA margin", "driver_risk": "Companies at covenant",
    "driver_cost": "Blended cost of debt", "driver_eff": "Management fee ratio",
    "seg_product": "Sector", "seg_credit": "Hold period",
    "seg_dd": "Board seat", "seg_engage": "VCP status",
    "seg_held": "Add-ons completed", "cohort_name": "Screen name",
    "kpi_cohort_size": "Companies in screen", "kpi_cohort_vol": "Invested capital",
    "kpi_cohort_rev": "EBITDA per company", "kpi_cohort_risk": "Avg downside risk",
}

SEGMENTS["abry"] = {"Near Prime": "0-2 years", "Prime": "2-4 years",
                    "Super Prime": "4-6 years", "Exceptional": "6+ years",
                    "Daily": "On track", "Weekly": "Minor slippage",
                    "Monthly": "At risk", "Dormant": "Stalled"}

VOCAB["abry"] = {
    "econ": "Control buyouts earn an EBITDA margin against a blended cost of debt on "
            "the LBO structure; the spread between them is the value creation the fund "
            "captures. Growth equity positions carry lower leverage and higher margins.",
    "metrics": "portfolio EBITDA, value creation, invested capital and covenant headroom",
    "bands": "Hold periods: 0-2 years, 2-4 years, 4-6 years, 6+ years. VCP status: "
             "On track, Minor slippage, At risk, Stalled.",
    "cohort_report": "companies in the screen, invested capital and average downside risk",
}

# Plugin-free for Chad: nothing to host, works for anyone who opens it.
PLUGINS["abry"] = {"hero": None, "hero_label": None, "ticker": None}

COMPANIES["abry"] = ABRY


# ---------------------------------------------------------------------------
# Nuvia Dental Implant Center — full-arch dental implant clinics.
# Treatment lines, not "products": full-arch is the business, and the
# same-day provisional is the thing they actually market.
#
#   product -> treatment line
#   volume  -> case production ($MM)
#   yield   -> net collection rate
#   cost    -> implant, lab and surgical cost
#   spread  -> center contribution margin
#   fee     -> ancillary revenue (CBCT, extractions, warranty plans)
#   risk    -> revision / lab remake rate
#   units   -> arches placed
#   shock   -> implant & lab cost shock
# ---------------------------------------------------------------------------
NUVIA = {
    "key": "nuvia",
    "name": "Nuvia Dental Implant Center",
    "title": "Center Performance & Case Production Command Center",
    "domain": "full-arch dental implant centers",
    "unit_noun": "patient",
    "volume_noun": "case value in treatment",
    "logo_domain": "nuviasmiles.com",
    "base_table": "Center Performance",
    # #00346D is sampled from their own logo — the single real hex. Everything
    # else is a derived tint of it rather than a guess at their palette.
    "palette": {
        "navy": "#00346D", "navy_deep": "#001E42",
        "primary": "#1E6FBF", "secondary": "#7FB2E0",
        "accent": "#E1A32D", "mint": "#2E9E7B",
    },
    "products": [
        ("Full arch — dual", 1, "Full arch", 96, .9350, .3720, 1.3, .0180, .0210,
         .268, .092, 45600, 0.0, "Both arches, same-day provisional",
         "Contribution margin", 1.043, "Ahead"),
        ("Full arch — single", 2, "Full arch", 52, .9280, .3580, 0.8, .0165, .0195,
         .262, .068, 20300, 1.1, "Single arch restoration",
         "Contribution margin", 1.012, "On plan"),
        ("Zirconia premium", 3, "Upgrade", 21, .9520, .4240, 0.35, .0120, .0480,
         .240, .134, 8400, 2.2, "Premium material upgrade",
         "Contribution margin", .946, "Behind"),
        ("Single & multi-tooth", 4, "Implant", 12, .9180, .3410, 0.45, .0210, .0160,
         .284, .046, 29200, 0.6, "One to four implant sites",
         "Contribution margin", .982, "On plan"),
        ("Bone graft & sinus lift", 5, "Adjunct", 8, .9060, .3180, 0.30, .0195, .0140,
         .296, .038, 18100, 1.7, "Augmentation before placement",
         "Contribution margin", 1.021, "Ahead"),
        ("Restorative & maintenance", 6, "Recurring", 4, .9440, .2260, 0.40, .0090, .0085,
         .312, .112, 49900, 1.3, "Follow-up, repairs, hygiene",
         "Contribution margin", 1.068, "Ahead"),
    ],
    "subs": {
        "Full arch — dual": [("Zirconia", .42, 30, 6.2, "Ahead"),
                             ("Titanium bar", .34, 0, 3.1, "On plan"),
                             ("Hybrid acrylic", .24, -25, -1.4, "Behind")],
        "Full arch — single": [("Upper only", .58, 15, 4.2, "Ahead"),
                               ("Lower only", .42, -10, 1.1, "On plan")],
        "Zirconia premium": [("Full zirconia", .66, -40, -2.8, "Behind"),
                             ("Layered zirconia", .34, -15, 0.6, "On plan")],
        "Single & multi-tooth": [("Single site", .54, 10, 3.4, "On plan"),
                                 ("Two to four sites", .46, 20, 5.1, "Ahead")],
        "Bone graft & sinus lift": [("Socket preservation", .61, 5, 2.2, "On plan"),
                                    ("Sinus augmentation", .39, 25, 4.8, "Ahead")],
        "Restorative & maintenance": [("Repairs & relines", .48, 20, 5.6, "Ahead"),
                                      ("Hygiene & recall", .52, 10, 3.9, "On plan")],
    },
    "alerts": [
        ("critical", "Case acceptance below plan",
         "Three centers converting under 38% of full-arch consults against a 46% plan",
         "18m ago", "Clinical Ops", 380, "bps below plan"),
        ("critical", "Same-day surgical capacity",
         "64 scheduled arches exceed available surgeon chair hours next week",
         "52m ago", "Scheduling", 64, "arches over capacity"),
        ("warning", "Zirconia remake rate",
         "Lab remakes on premium zirconia at 4.8% against a 2.5% standard",
         "2h ago", "Clinical Quality", 230, "bps over standard"),
        ("warning", "Financing declines rising",
         "212 patients declined third-party financing this month, up 31%",
         "3h ago", "Patient Finance", 212, "patients declined"),
        ("info", "Consult no-shows",
         "1,140 booked consults did not attend across the network this month",
         "5h ago", "Marketing", 1140, "no-shows"),
    ],
    "agent": ("You are an analyst covering Nuvia Dental Implant Center's treatment "
              "lines, center economics and clinical operations."),
}

FOOTPRINTS["nuvia"] = [("TX", .128), ("UT", .095), ("AZ", .082), ("CA", .076),
                       ("FL", .072), ("CO", .062), ("NV", .048), ("GA", .046),
                       ("NC", .042), ("TN", .038), ("OH", .036), ("MO", .034),
                       ("WA", .032), ("OK", .028), ("VA", .026)]

LABELS["nuvia"] = {
    "personas": ["Executive", "Clinical Operations"],
    "modeler_page": "Capacity Planning",
    "cohort_page": "Patient Segments",
    "modeler_title": "Case Mix & Capacity Scenario Modeler",
    "shock_label": "Implant & lab cost shock (bps)",
    "kpi_revenue": "Net patient revenue ($M)",
    "kpi_margin": "Center contribution ($M)",
    "kpi_volume": "Case value in treatment ($M)",
    "kpi_units": "Arches placed",
    "driver_nim": "Contribution margin %",
    "driver_risk": "Cases needing revision",
    "driver_cost": "Implant & lab cost %",
    "driver_eff": "Center overhead ratio",
    "col_volume": "Baseline case value",
    "col_growth": "Volume growth %",
    "col_yield": "Collection \u0394 bps",
    "col_cost": "Cost \u0394 bps",
    "seg_product": "Treatment line",
    "seg_credit": "Financing tier",
    "seg_dd": "Same-day case",
    "seg_engage": "Consult stage",
    "seg_held": "Arches treated",
    "cohort_name": "Segment name",
    "kpi_cohort_size": "Patients in segment",
    "kpi_cohort_vol": "Case value",
    "kpi_cohort_rev": "Value per patient",
    "kpi_cohort_risk": "Avg no-show risk",
}

SEGMENTS["nuvia"] = {"Near Prime": "Declined", "Prime": "Partial approval",
                     "Super Prime": "Full approval", "Exceptional": "Self-pay",
                     "Daily": "Treatment started", "Weekly": "Scheduled",
                     "Monthly": "Consulted", "Dormant": "Lapsed lead"}

VOCAB["nuvia"] = {
    "econ": ("Centers produce case value from full-arch consults; the contribution "
             "spread is net collections less implant, lab and surgical cost. "
             "Financed cases carry a chargeback risk that self-pay cases do not."),
    "metrics": ("net patient revenue, center contribution, case production and "
                "arches placed"),
    "bands": ("Financing tiers: Declined, Partial approval, Full approval, "
              "Self-pay. Consult stage: Treatment started, Scheduled, Consulted, "
              "Lapsed lead."),
    "cohort_report": "segment size, case value and average no-show risk",
}

PLUGINS["nuvia"] = {"hero": "ae7bf513-6314-4f17-a798-a6cb15cc6d8c",
                    "hero_label": "ARCH PLACEMENT MAP",
                    "ticker": None}

COMPANIES["nuvia"] = NUVIA


# ---------------------------------------------------------------------------
# Delta Air Lines — network carrier. The economics ARE unit economics, so this
# is the cleanest mapping in the file: capacity x RASM less capacity x CASM.
#
#   product -> cabin product (the premiumisation story)
#   volume  -> capacity, available seat miles (ASMs, millions)
#   yield   -> RASM, revenue per available seat mile
#   cost    -> CASM, cost per available seat mile
#   spread  -> unit margin
#   fee     -> ancillary (bags, paid upgrades)
#   risk    -> cancellation rate
#   units   -> passengers
#   shock   -> jet fuel price
# ---------------------------------------------------------------------------
DELTA = {
    "key": "delta",
    "name": "Delta Air Lines",
    "title": "Network & Revenue Performance Command Center",
    "domain": "network airline",
    "unit_noun": "SkyMiles member",
    "volume_noun": "capacity",
    "logo_domain": "delta.com",
    "base_table": "Network Performance",
    # every hex sampled from their own wordmark SVG, not guessed
    "palette": {
        "navy": "#003D79", "navy_deep": "#00224A",
        "primary": "#E31837", "secondary": "#2E6DB4",
        "accent": "#98002E", "mint": "#1F9D7A",
    },
    "products": [
        ("Main Cabin", 1, "Core", 208000, .1520, .1478, 78.0, .0020, .0125,
         .104, .028, 930, 0.0, "Largest cabin by capacity",
         "RASM", .994, "On plan"),
        ("Basic Economy", 2, "Core", 52000, .1180, .1172, 30.0, .0026, .0140,
         .112, .015, 280, 1.1, "Price-led, no changes",
         "RASM", .952, "Behind"),
        ("Delta Comfort", 3, "Premium", 46000, .2180, .2010, 22.0, .0015, .0105,
         .096, .092, 222, 2.2, "Extra legroom, premiumising fast",
         "RASM", 1.061, "Ahead"),
        ("First Class", 4, "Premium", 34000, .3240, .2985, 14.0, .0012, .0095,
         .092, .078, 136, 0.6, "Domestic premium cabin",
         "RASM", 1.048, "Ahead"),
        ("Delta One", 5, "Premium", 14000, .5860, .5310, 6.0, .0010, .0085,
         .088, .112, 43, 1.7, "Long-haul flagship",
         "RASM", 1.084, "Ahead"),
        ("Loyalty & partner", 6, "Loyalty", 16000, .4100, .3620, 10.0, .0008, .0060,
         .074, .095, 54, 1.3, "Amex remuneration, partner miles",
         "Yield", 1.072, "Ahead"),
    ],
    "subs": {
        "Main Cabin": [("Domestic", .612, -15, 1.8, "On plan"),
                       ("Atlantic", .208, 20, 4.2, "Ahead"),
                       ("Latin America", .112, -30, -1.2, "Behind"),
                       ("Pacific", .068, 35, 6.4, "Ahead")],
        "Basic Economy": [("Domestic", .824, -25, 0.9, "Behind"),
                          ("Latin America", .176, -10, 2.1, "On plan")],
        "Delta Comfort": [("Domestic", .548, 25, 7.8, "Ahead"),
                          ("Atlantic", .284, 30, 11.2, "Ahead"),
                          ("Pacific", .168, 15, 8.6, "Ahead")],
        "First Class": [("Domestic", .782, 20, 6.9, "Ahead"),
                        ("Latin America", .218, 5, 3.4, "On plan")],
        "Delta One": [("Atlantic", .462, 40, 13.8, "Ahead"),
                      ("Pacific", .308, 25, 10.4, "Ahead"),
                      ("Transcon", .230, 10, 6.2, "On plan")],
        "Loyalty & partner": [("Amex remuneration", .706, 20, 9.8, "Ahead"),
                              ("Partner & other", .294, 10, 7.2, "Ahead")],
    },
    "alerts": [
        ("critical", "ATL bank compression",
         "Afternoon bank running 14 minutes tight; 1,180 connections under the "
         "45-minute minimum", "12m ago", "Network Ops", 1180, "tight connections"),
        ("critical", "Jet fuel above plan",
         "Gulf Coast jet fuel at $2.71 a gallon against a $2.44 plan assumption",
         "38m ago", "Fuel", 1100, "bps over plan"),
        ("warning", "Mishandled baggage",
         "MSP and DTW above the 4.2 per thousand standard for a third day",
         "1h ago", "Airport Ops", 640, "bags over standard"),
        ("warning", "Widebody delivery slip",
         "Two A330neo deliveries pushed a quarter, 1.8 billion ASMs at risk on "
         "Atlantic", "3h ago", "Fleet", 1800, "ASMs (M) at risk"),
        ("info", "Award redemption spike",
         "SkyMiles redemptions up 18% week over week on transatlantic premium",
         "5h ago", "Loyalty", 1800, "bps above trend"),
    ],
    "agent": ("You are an analyst covering Delta Air Lines' cabin products, "
              "network unit economics and airport operations."),
}

FOOTPRINTS["delta"] = [("GA", .186), ("MN", .092), ("MI", .078), ("UT", .072),
                       ("CA", .068), ("NY", .064), ("WA", .048), ("MA", .038),
                       ("TX", .036), ("FL", .034), ("NC", .030), ("TN", .026),
                       ("AZ", .022), ("CO", .020), ("IL", .018)]

LABELS["delta"] = {
    "personas": ["Executive", "Network Operations"],
    "modeler_page": "Network Planning",
    "cohort_page": "SkyMiles Segments",
    "modeler_title": "Capacity & Fare Scenario Modeler",
    "shock_label": "Jet fuel price shock (bps)",
    "kpi_revenue": "Operating income ($M)",
    "kpi_margin": "Contribution ($M)",
    "kpi_volume": "Capacity — ASMs (M)",
    "kpi_units": "Passengers (M)",
    "driver_nim": "Unit margin, RASM less CASM",
    "driver_risk": "Flights cancelled",
    "driver_cost": "CASM",
    "driver_eff": "Overhead ratio",
    "seg_product": "Cabin product",
    "seg_credit": "Medallion tier",
    "seg_dd": "Amex cardholder",
    "seg_engage": "Flight frequency",
    "seg_held": "Segments flown",
    "cohort_name": "Segment name",
    "kpi_cohort_size": "Members in segment",
    "kpi_cohort_vol": "Lifetime spend",
    "kpi_cohort_rev": "Spend per member",
    "kpi_cohort_risk": "Avg attrition risk",
    "col_volume": "Baseline capacity",
    "col_growth": "Capacity growth %",
    "col_yield": "RASM Δ bps",
    "col_cost": "CASM Δ bps",
}

SEGMENTS["delta"] = {"Near Prime": "Silver", "Prime": "Gold",
                     "Super Prime": "Platinum", "Exceptional": "Diamond",
                     "Daily": "Weekly flyer", "Weekly": "Monthly flyer",
                     "Monthly": "Occasional", "Dormant": "Lapsed"}

VOCAB["delta"] = {
    "econ": ("Revenue is capacity times RASM; cost is capacity times CASM, so the "
             "unit margin is the spread between them. Premium cabins carry a far "
             "higher RASM per seat mile than Main Cabin, which is why cabin mix "
             "moves margin more than traffic does."),
    "metrics": ("operating revenue, unit contribution, capacity in ASMs and "
                "passengers carried"),
    "bands": ("Medallion tiers: Silver, Gold, Platinum, Diamond. Flight "
              "frequency: Weekly flyer, Monthly flyer, Occasional, Lapsed."),
    "cohort_report": "segment size, lifetime spend and average attrition risk",
}

POP["delta"] = {"bases": (2400, 6800, 15400, 31000), "rev_rate": 0.19,
                "fee_per_product": 210}

PLUGINS["delta"] = {
    "hero": "786a148f-7d2b-45f3-a0aa-65af5960c841",
    "hero_label": "ATL CONNECTION BANKS",
    "ticker": None,
    # The hero plugin needs hour-of-day data, not the product cards, so it
    # brings its own source table. See hub_banks_sql().
    "hero_table": {"name": "Hub Banks", "file": "hub_banks.sql", "prefix": "h",
                   "cols": ["Hour", "Direction", "Flights", "Seats",
                            "Connections"]},
    "hero_config": {"hour": "h0", "direction": "h1", "flights": "h2",
                    "seats": "h3", "connections": "h4"},
}

COMPANIES["delta"] = DELTA


# ---------------------------------------------------------------------------
# BayPort Credit Union — member-owned credit union, Newport News VA
# (Virginia Peninsula & Southside / Hampton Roads). Real public figures:
# ~$2.7B in assets, 156,000+ members, 29 branches, founded 1928.
#
#   product -> loan/deposit line, using BayPort's own site product names
#   volume  -> avg balances ($MM) -- loans AND shares both carry a balance
#   yield   -> loan APR (asset side) / 0 for share (deposit) lines
#   funding -> cost of funds -- for share lines this IS the dividend paid
#   spread  -> net interest margin, same shape as every other bank/CU built
#   fee     -> interchange, service charges, ancillary (MONTHLY, $MM)
#   risk    -> delinquency
#   shock   -> parallel rate shock (bps), same modeler as sofi/boa unchanged
# A member-owned CU pays "dividends," not "interest," on deposits -- VOCAB
# below carries that word choice into the agent so it doesn't read as a bank.
# ---------------------------------------------------------------------------
BAYPORT = {
    "key": "bayport",
    "name": "BayPort Credit Union",
    "title": "Member & Lending Command Center",
    "domain": "member-owned credit union",
    "unit_noun": "member",
    "volume_noun": "balances",
    "logo_domain": "bayportcu.org",
    "base_table": "Member Ledger",
    # navy + green sampled from BayPort's own wordmark (bayport-logo.png)
    "palette": {
        "navy": "#0A2B57", "navy_deep": "#051A38",
        "primary": "#1E7F4D", "secondary": "#0D6E9C",
        "accent": "#2FA766", "mint": "#17A793",
    },
    "products": [
        ("Checking & Savings", 1, "Deposits", 1550, 0.0, .0140, 2.6, 0.0, 0.0,
         .460, .024, 225, 0.0, "Free rewards checking & regular shares",
         "APY", .978, "On plan"),
        ("Share Certificates", 2, "Deposits", 800, 0.0, .0410, 0.3, 0.0, 0.0,
         .180, .086, 39, 1.7, "12-60 month share & IRA certificates",
         "APY", 1.092, "Ahead"),
        ("Vehicle Loans", 3, "Loans", 600, .0680, .0300, 0.9, .0075, .0068,
         .300, .041, 55, 1.1, "New, used & refinance auto lending",
         "Avg APR", 1.028, "Ahead"),
        ("Mortgages & Home Equity", 4, "Loans", 1030, .0615, .0300, 1.4, .0018, .0032,
         .240, .026, 16, 2.2, "Fixed, balloon/hybrid & home equity",
         "Avg APR", .946, "Behind"),
        ("Personal Loans", 5, "Loans", 175, .1120, .0300, 0.25, .0180, .0145,
         .360, .052, 34, 0.6, "Signature & Take-Back® lending",
         "Avg APR", 1.014, "On plan"),
        ("Credit Cards", 6, "Loans", 135, .1780, .0300, 0.6, .0420, .0225,
         .420, .037, 67, 2.8, "Visa Platinum & Rewards card programs",
         "Avg APR", .881, "Behind"),
    ],
    "alerts": [
        ("critical", "Straw-purchase indicators flagged",
         "Fraud pattern detected across 86 recently funded Vehicle Loans",
         "24m ago", "Financial Crimes", 86, "loans flagged"),
        ("critical", "Certificate maturity wall",
         "$42M of Share Certificates mature within 30 days at risk of non-renewal",
         "1h ago", "Treasury", 42, "$M maturing at risk"),
        ("warning", "Mortgage pipeline aging",
         "218 mortgage applications past the 21-day underwriting SLA",
         "3h ago", "Lending Ops", 218, "apps past SLA"),
        ("warning", "Credit card delinquency drift",
         "Visa Platinum 30-day delinquency up 34 bps quarter over quarter",
         "6h ago", "Risk", 34, "bps QoQ"),
        ("info", "Dividend rate change published",
         "Regular Shares dividend moved 1.25% to 1.40% APY for all members",
         "1d ago", "Product", 15, "bps APY increase"),
    ],
    "agent": ("You are an analyst covering BayPort Credit Union's lending, "
              "deposit and member business. Answer with numbers from the workbook."),
}

BAYPORT["subs"] = {
    "Checking & Savings": [("Free Rewards Checking", .42, -15, 2.4, "Ahead"),
                           ("Regular Shares (Savings)", .34, 5, 1.1, "On plan"),
                           ("Money Market", .16, 20, 3.6, "Ahead"),
                           ("Youth & Student Accounts", .08, -20, 0.8, "On plan")],
    "Share Certificates": [("12-Month Certificate", .38, 10, 8.4, "Ahead"),
                           ("24-Month Certificate", .27, 15, 6.9, "Ahead"),
                           ("36-60 Month Certificate", .22, -10, 4.2, "On plan"),
                           ("IRA Certificate", .13, 5, 5.1, "Ahead")],
    "Vehicle Loans": [("New Auto", .46, -20, 4.8, "Ahead"),
                      ("Used Auto", .38, 10, 3.1, "On plan"),
                      ("Auto Refinance", .11, -30, 6.2, "Ahead"),
                      ("Boat & RV", .05, 40, -1.2, "Behind")],
    "Mortgages & Home Equity": [("Fixed-Rate Purchase", .44, 15, -2.1, "Behind"),
                                ("Refinance", .21, -25, -4.6, "Behind"),
                                ("Home Equity Line", .24, 20, 3.8, "Ahead"),
                                ("Balloon & Hybrid", .11, 30, -0.6, "On plan")],
    "Personal Loans": [("Debt Consolidation", .52, -10, 3.4, "Ahead"),
                       ("Take-Back® Loan", .27, 0, 5.6, "Ahead"),
                       ("Signature/Unsecured", .21, 25, -1.8, "Behind")],
    "Credit Cards": [("Visa Platinum Rewards", .58, 20, -2.4, "Behind"),
                     ("Visa Platinum Low Rate", .29, -15, 1.2, "On plan"),
                     ("Secured Builder Card", .13, 60, 4.8, "Ahead")],
}

# Field-of-membership footprint: heavily Virginia Peninsula & Southside
# (Hampton Roads), plus a national tail from members who relocated -- Hampton
# Roads is a major Navy homeport, so PCS moves scatter former members
# nationwide the way no ordinary regional bank's footprint would.
FOOTPRINTS["bayport"] = [("VA", .580), ("NC", .062), ("MD", .048), ("FL", .042),
                         ("TX", .034), ("GA", .028), ("SC", .026), ("CA", .024),
                         ("PA", .022), ("TN", .020), ("OH", .018), ("NY", .016),
                         ("WA", .014), ("AZ", .012), ("CO", .010)]

LABELS["bayport"] = {
    "personas": ["Executive", "Member Experience"],
    "seg_product": "Primary Product", "seg_credit": "Credit Band",
    "seg_dd": "Direct Deposit", "seg_engage": "Engagement",
    "seg_held": "Products held", "cohort_name": "Cohort name",
    "kpi_cohort_size": "Members in Cohort",
    "kpi_cohort_vol": "Cohort Balances", "kpi_cohort_rev": "Revenue per Member",
    "kpi_cohort_risk": "Avg Attrition Risk",
    "modeler_page": "Rate Planning", "cohort_page": "Member Segments",
    "modeler_title": "Dividend & Loan Rate Scenario Modeler",
    "shock_label": "Parallel rate shock (bps)",
    "kpi_revenue": "Net revenue ($M)", "kpi_margin": "Contribution ($M)",
    "kpi_volume": "Avg balances ($M)", "kpi_units": "Members (K)",
    "driver_nim": "Net interest margin", "driver_risk": "30-day delinquency",
    "driver_cost": "Cost of funds", "driver_eff": "Efficiency ratio",
}

SEGMENTS["bayport"] = {"Near Prime": "Building Credit", "Prime": "Established",
                       "Super Prime": "Preferred Member", "Exceptional": "Elite Member",
                       "Daily": "Highly Engaged", "Weekly": "Active",
                       "Monthly": "Occasional", "Dormant": "Inactive"}

VOCAB["bayport"] = {
    "econ": ("Vehicle, mortgage, personal and card loans carry an asset yield "
             "against a blended cost of funds; checking, savings and certificate "
             "lines pay a member dividend and earn fee income instead."),
    "metrics": "net revenue, contribution profit, provision and delinquency",
    "bands": ("Credit bands: Building Credit (640-679), Established (680-719), "
              "Preferred Member (720-779), Elite Member (780+). Engagement: "
              "Highly Engaged, Active, Occasional, Inactive."),
    "cohort_report": "cohort size, balances and average attrition risk",
}

# _default POP (retail-banking dollar bases) fits a credit union as-is -- no
# override needed, unlike Nuvia (dental) or Delta (airline lifetime spend).

PLUGINS["bayport"] = {
    "hero": "2a077d2f-1519-4514-81e3-cc4e71fee9b8",
    "hero_label": "HAMPTON ROADS BRANCH PERFORMANCE",
    "ticker": None,
    # Real Virginia locality shapes, not the product-card table -- see
    # branch_performance_sql() and plugins/bayport-branch-map.
    "hero_table": {"name": "Branch Performance", "file": "branch_performance.sql",
                   "prefix": "h", "cols": ["Locality", "Branches", "Balances",
                                           "Member Growth Pct", "Status"]},
    "hero_config": {"locality": "h0", "branches": "h1", "balances": "h2",
                    "growth": "h3", "status": "h4"},
}

COMPANIES["bayport"] = BAYPORT


def hub_banks_sql(cfg):
    """Arrival/departure banks at the primary hub, by hour. Explicit UNION ALL
    rather than a generator so it stays portable across warehouses."""
    # ATL runs roughly ten banks a day: arrivals land, then departures push.
    arr = [0, 0, 0, 0, 0, 6, 34, 52, 28, 44, 61, 33, 48, 66, 37, 51,
           69, 41, 55, 72, 38, 24, 11, 3]
    dep = [0, 0, 0, 0, 2, 18, 58, 31, 49, 67, 35, 52, 70, 39, 54, 73,
           42, 58, 76, 44, 29, 14, 5, 1]
    rows = []
    for h in range(24):
        for label, flights in (("Arrival", arr[h]), ("Departure", dep[h])):
            seats = flights * 148
            # connections only make sense where an arrival bank feeds a push
            conn = int(flights * (11.4 if label == "Arrival" else 9.8))
            lead = "SELECT" if not rows else "UNION ALL SELECT"
            cols = ("" if rows else
                    ' AS "Hour", %s AS "Direction", %d AS "Flights",'
                    ' %d AS "Seats", %d AS "Connections"')
            if not rows:
                rows.append("    %s %d%s" % (lead, h, cols % (
                    "'%s'" % label, flights, seats, conn)))
            else:
                rows.append("    %s %d, '%s', %d, %d, %d"
                            % (lead, h, label, flights, seats, conn))
    return "SELECT * FROM (\n" + "\n".join(rows) + "\n) AS hub_banks"


# BayPort's hero plugin needs Hampton Roads / Peninsula-Southside locality
# data, not the product-card table -- same pattern as Delta's hub_banks_sql.
# Branch counts sum to the real public figure (29 branches). Locality names
# are the exact labels baked into the plugin's Virginia county-shape paths
# (see plugins/bayport-branch-map) -- renaming one here without renaming it
# there is the display-label trap from HANDOFF.md section 8.
_BAYPORT_LOCALITIES = [
    ("Newport News", 5, 640, 4.2, "Ahead"),
    ("Hampton", 4, 480, 2.1, "On plan"),
    ("York County", 3, 310, 5.8, "Ahead"),
    ("Poquoson", 1, 85, 1.4, "On plan"),
    ("Williamsburg", 2, 260, 6.4, "Ahead"),
    ("James City County", 2, 240, 3.9, "On plan"),
    ("Gloucester", 1, 78, -1.2, "Behind"),
    ("Mathews", 0, 22, -3.4, "Behind"),
    ("Isle of Wight", 1, 96, 2.8, "On plan"),
    ("Suffolk", 2, 210, 7.1, "Ahead"),
    ("Portsmouth", 2, 175, -2.6, "Behind"),
    ("Norfolk", 2, 205, 1.9, "On plan"),
    ("Chesapeake", 2, 230, 5.2, "Ahead"),
    ("Virginia Beach", 2, 260, 4.6, "Ahead"),
    ("Southampton", 0, 38, -0.8, "On plan"),
    ("Franklin", 0, 26, -4.1, "Behind"),
]


def branch_performance_sql(cfg):
    rows = []
    for i, (name, branches, bal, growth, status) in enumerate(_BAYPORT_LOCALITIES):
        lead = "SELECT" if i == 0 else "UNION ALL SELECT"
        cols = ("" if i else
                " AS \"Locality\", %d AS \"Branches\", %d AS \"Balances\","
                " %s AS \"Member Growth Pct\", '%s' AS \"Status\"")
        if i == 0:
            rows.append("    %s '%s'%s" % (lead, name, cols % (
                branches, bal, growth, status)))
        else:
            rows.append("    %s '%s', %d, %d, %s, '%s'"
                        % (lead, name, branches, bal, growth, status))
    return "SELECT * FROM (\n" + "\n".join(rows) + "\n) AS branch_performance"


# ---------------------------------------------------------------------------
# Pixel-perfect statement, per company. The report's LAYOUT is universal (a
# dense two-column statement); everything a human reads comes from here, and the
# three data sources are generated so the numbers reconcile with the copy.
#
# Column contracts are fixed: activity is (Transaction Date, Post Date,
# Description, Category, Amount, Points Earned); rewards is (Line Order,
# Description, Points); summary is (Line Order, Metric, Value).
# ---------------------------------------------------------------------------
STATEMENTS = {
    "sofi": {
        "spec_name": "SoFi — Member Statement (July 2026)",
        "page_name": "Statement Summary",
        "manage_url": "www.sofi.com/account",
        "service_label": "Member Services",
        "service_phone": "1-855-456-7634",
        "period": "07/01 – 07/31/2026",
        "sect_rewards": "SOFI REWARDS SUMMARY",
        "sect_summary": "ACCOUNT SUMMARY",
        "sect_category": "SPEND BY CATEGORY",
        "sect_activity": "TRANSACTIONS",
        "sect_messages": "YOUR ACCOUNT MESSAGES",
        "headline": [("New Balance", None), ("Minimum Payment Due", None),
                     ("Payment Due Date", "08/25/2026")],
        "button_label": "Member statement ↗",
        "rewards_total": "Total points available",
        "h_formulas": [("src", 'Sum([Statement Activity/Amount])', "MONEY"),
                       ("src", 'Round(Sum([Statement Activity/Amount]) * 0.02, 2)',
                        "MONEY")],
        "msg_body": ("Starting 09/01/2026, SoFi Rewards points earned on travel "
                     "and dining purchases increase from 2x to 3x per $1 spent, "
                     "with no cap. Points continue to be redeemable for statement "
                     "credit, deposits into a SoFi Money or Invest account, or "
                     "loan principal payments. No action is required to keep "
                     "earning at the new rate."),
        "warn1": ("**Late Payment Warning:** If we do not receive your minimum "
                  "payment by the date listed above, you may have to pay a late "
                  "fee of up to $29.00 and your APRs may be subject to increase "
                  "to the Penalty APR of 29.99%."),
        "warn2": ("**Minimum Payment Warning:** Paying only the minimum payment "
                  "will increase the interest you pay and the time it takes to "
                  "repay your balance. Enroll in AutoPay at sofi.com/account to "
                  "avoid missing a payment."),
        "footer": ("SoFi Credit Card is issued by The Bank of Missouri. "
                   "Illustrative statement generated from a Sigma report "
                   "specification — synthetic data, not a real account."),
    },
    "delta": {
        "spec_name": "Delta Air Lines — SkyMiles Statement (July 2026)",
        "page_name": "SkyMiles Statement",
        "manage_url": "delta.com/skymiles",
        "service_label": "SkyMiles Service",
        "service_phone": "1-800-323-2323",
        "period": "07/01 – 07/31/2026",
        "sect_rewards": "SKYMILES ACTIVITY",
        "sect_summary": "MEDALLION QUALIFICATION",
        "sect_category": "MILES BY EARN SOURCE",
        "sect_activity": "FLIGHT ACTIVITY",
        "sect_messages": "YOUR SKYMILES MESSAGES",
        "headline": [("Miles Balance", None), ("MQDs This Year", None),
                     ("Status Valid Through", "01/31/2028")],
        "button_label": "SkyMiles statement ↗",
        "rewards_total": "Total miles available",
        "h_formulas": [("src-rw", 'Sum([Rewards Summary/Points])', "NUM0"),
                       ("src", 'SumIf([Statement Activity/Amount], '
                        '[Statement Activity/Category] = "Flights")', "MONEY0")],
        "msg_body": ("Beginning 01/01/2027, Medallion Qualification Dollars earned "
                     "on Delta-marketed flights operated by joint venture partners "
                     "will credit at 100% of the fare paid, up from 80%. Rollover "
                     "MQDs above your tier threshold carry into the next "
                     "qualification year automatically. No action is required."),
        "warn1": ("**Award travel:** Miles do not expire while your SkyMiles "
                  "account remains open. Award seats are capacity controlled and "
                  "pricing is dynamic, so the miles required for a given itinerary "
                  "may change until the booking is ticketed."),
        "warn2": ("**Medallion qualification:** Only MQDs from Delta-marketed "
                  "flights, eligible partner flights and qualifying American "
                  "Express spend count toward tier status. Award tickets earn MQDs "
                  "on the cash portion of the fare only."),
        "footer": ("SkyMiles Medallion status is determined by Medallion "
                   "Qualification Dollars. Illustrative statement generated "
                   "from a Sigma report specification — synthetic data, not a "
                   "real account."),
    },
    "sigma_motors": {
        "spec_name": "Sigma Motors — Reservation Statement (July 2026)",
        "page_name": "Reservation Statement",
        "page2_title": "# Reservation & service activity",
        "manage_url": "sigmamotors.com/account",
        "service_label": "Reservation Support",
        "service_phone": "1-888-EV-SIGMA",
        "period": "07/01 – 07/31/2026",
        "sect_rewards": "SIGMA REWARDS SUMMARY",
        "sect_summary": "RESERVATION SUMMARY",
        "sect_category": "ACTIVITY BY CATEGORY",
        "sect_activity": "RESERVATION & SERVICE ACTIVITY",
        "sect_messages": "YOUR SIGMA MOTORS MESSAGES",
        "headline": [("Sigma Rewards Points", None),
                     ("Reservation Activity This Period", None),
                     ("Estimated Delivery Window", "Q1 2027")],
        "button_label": "Reservation statement ↗",
        "rewards_total": "Total Sigma Rewards points available",
        "h_formulas": [("src-rw", 'Sum([Rewards Summary/Points])', "NUM0"),
                       ("src", 'Sum([Statement Activity/Amount])', "MONEY0")],
        "msg_body": ("Beginning September 2026, Sigma Motors is expanding EV "
                     "production capacity in the West and Southwest regions to "
                     "reduce reservation wait times. Reservation holders in "
                     "affected regions may see their estimated delivery window "
                     "move earlier automatically. No action is required to "
                     "receive an updated estimate."),
        "warn1": ("**Delivery Estimate Notice:** Delivery windows may shift as "
                  "capacity is reallocated across regions. Your deposit remains "
                  "fully refundable prior to build confirmation."),
        "warn2": ("**Sigma Rewards Terms:** Points are earned on reservations, "
                  "upgrades, and referrals, and do not expire while your "
                  "reservation is active. Redeem for merchandise or service "
                  "credit."),
        "footer": ("Sigma Motors is a fictional EV/Hybrid automaker. "
                   "Illustrative statement generated from a Sigma report "
                   "specification — synthetic data, not a real account."),
    },
    "veraset": {
        "spec_name": "Veraset — Data License Invoice (July 2026)",
        "page_name": "Invoice Summary",
        "manage_url": "www.veraset.com/portal",
        "service_label": "Account Support",
        "service_phone": "support@veraset.com",
        "period": "07/01 – 07/31/2026",
        "sect_rewards": "USAGE SUMMARY",
        "sect_summary": "CONTRACT SUMMARY",
        "sect_category": "LICENSED VOLUME BY PRODUCT",
        "sect_activity": "USAGE DETAIL",
        "sect_messages": "YOUR ACCOUNT MESSAGES",
        "headline": [("Invoice Total", None), ("Overage Charges", None),
                     ("Payment Due Date", "08/30/2026")],
        "button_label": "Data license invoice ↗",
        "rewards_total": "Total records delivered",
        "h_formulas": [("src", 'Sum([Statement Activity/Amount])', "MONEY"),
                       ("src", 'Round(Sum([Statement Activity/Amount]) * 0.08, 2)',
                        "MONEY")],
        "msg_body": ("Beginning 09/01/2026, overage rates for Movement and Visits "
                     "volume above committed minimums decrease 10% after this "
                     "quarter's 6-country panel expansion. No action is required."),
        "warn1": ("**Late Payment Notice:** If payment is not received within 30 "
                  "days of the invoice date, a 1.5% monthly late fee may apply "
                  "and data delivery may be suspended until the account is "
                  "brought current."),
        "warn2": ("**Usage Overage Notice:** Charges beyond your committed "
                  "volume are billed monthly in arrears at the current overage "
                  "rate. Contact your account team to adjust committed volume "
                  "and avoid overage charges."),
        "footer": ("Veraset licenses anonymized, privacy-compliant location data "
                   "under a data processing agreement with each customer. "
                   "Illustrative invoice generated from a Sigma report "
                   "specification — synthetic data, not a real account."),
    },
    "bayport": {
        "spec_name": "BayPort Credit Union — Free Rewards Checking Statement (July 2026)",
        "page_name": "Member Statement",
        "manage_url": "www.bayportcu.org/account",
        "service_label": "Member Services",
        "service_phone": "1-757-928-8850",
        "period": "07/01 – 07/31/2026",
        "sect_rewards": "BAYPORT REWARDS SUMMARY",
        "sect_summary": "ACCOUNT SUMMARY",
        "sect_category": "SPEND BY CATEGORY",
        "sect_activity": "TRANSACTIONS",
        "sect_messages": "YOUR ACCOUNT MESSAGES",
        "headline": [("New Balance", None), ("Dividends Earned YTD", None),
                     ("Statement Closing Date", "07/31/2026")],
        "button_label": "Member statement ↗",
        "rewards_total": "Total BayPort Rewards points available",
        "h_formulas": [("src", 'Sum([Statement Activity/Amount])', "MONEY"),
                       ("src", 'Round(Sum([Statement Activity/Amount]) * 0.015, 2)',
                        "MONEY")],
        "msg_body": ("Starting 09/01/2026, BayPort Rewards points earned on debit "
                     "card purchases increase from 1 point per $2 spent to 1 point "
                     "per $1 spent on groceries and fuel, with no cap. Points "
                     "continue to be redeemable for statement credit, a deposit "
                     "into any BayPort share account, or loan principal payments. "
                     "No action is required to keep earning at the new rate."),
        "warn1": ("**Overdraft Notice:** If your Free Rewards Checking balance "
                  "goes negative, an overdraft fee of up to $29.00 per item may "
                  "apply. Enroll in Courtesy Pay for free automatic overdraft "
                  "transfer from savings."),
        "warn2": ("**Dividend Rate Notice:** Dividend rates on regular shares and "
                  "money market accounts are set by the Board and may change at "
                  "any time. Current rates are posted at bayportcu.org."),
        "footer": ("BayPort Credit Union is federally insured by NCUA. "
                   "Illustrative statement generated from a Sigma report "
                   "specification — synthetic data, not a real account."),
    },
    "clickhouse": {
        "spec_name": "ClickHouse Cloud — Usage Invoice (July 2026)",
        "page_name": "Usage Invoice",
        "manage_url": "clickhouse.cloud/billing",
        "service_label": "Cloud Support",
        "service_phone": "support@clickhouse.com",
        "period": "07/01 – 07/31/2026",
        "sect_rewards": "USAGE SUMMARY",
        "sect_summary": "ACCOUNT SUMMARY",
        "sect_category": "SPEND BY CATEGORY",
        "sect_activity": "USAGE DETAIL",
        "sect_messages": "YOUR ACCOUNT MESSAGES",
        "headline": [("Invoice Total", None), ("Overage Charges", None),
                     ("Payment Due Date", "08/15/2026")],
        "button_label": "Usage invoice ↗",
        "rewards_total": "Total CHU-hours consumed",
        "h_formulas": [("src", 'Sum([Statement Activity/Amount])', "MONEY"),
                       ("src", 'Round(Sum([Statement Activity/Amount]) * 0.08, 2)',
                        "MONEY")],
        "msg_body": ("Beginning 09/01/2026, ClickHouse Cloud is expanding "
                     "committed-use credit tiers so customers exceeding 500 "
                     "CHU-hours per month qualify for an additional 10% discount "
                     "on overage compute. No action is required to receive the "
                     "new rate."),
        "warn1": ("**Late Payment Notice:** If payment is not received within 15 "
                  "days of the invoice date, a 1.5% monthly late fee may apply "
                  "and compute may be throttled until the account is brought "
                  "current."),
        "warn2": ("**Overage Notice:** Compute consumed beyond your committed "
                  "CHU-hours is billed monthly in arrears at the current "
                  "on-demand rate. Contact your account team to adjust your "
                  "committed tier and avoid overage charges."),
        "footer": ("ClickHouse Cloud is billed based on compute (ClickHouse "
                   "Units) and storage consumed. Illustrative invoice generated "
                   "from a Sigma report specification — synthetic data, not a "
                   "real account."),
    },
}


def statement(cfg, key):
    return STATEMENTS.get(cfg["key"], STATEMENTS["sofi"])[key]


def has_statement(cfg):
    return cfg["key"] in STATEMENTS


def _union(rows, cols):
    """UNION ALL block where only the first SELECT carries column aliases."""
    out = []
    for i, vals in enumerate(rows):
        if i == 0:
            out.append("    SELECT " + ", ".join(
                "%s AS \"%s\"" % (v, c) for v, c in zip(vals, cols)))
        else:
            out.append("    UNION ALL SELECT " + ", ".join(vals))
    return "SELECT * FROM (\n" + "\n".join(out) + "\n) AS t"


# --- Delta: flight activity, miles activity, Medallion qualification ---------

_DL_FLIGHTS = [
    ("07/02", "07/03", "DL 1247  ATL–LAX  Delta One", "Flights", 1946.00, 9730),
    ("07/02", "07/03", "Miles Booster  ATL–LAX", "Flights", 149.00, 745),
    ("07/06", "07/07", "DL 0088  LAX–NRT  Delta One", "Flights", 4312.00, 21560),
    ("07/09", "07/10", "DL 0089  NRT–LAX  Delta One", "Flights", 4312.00, 21560),
    ("07/11", "07/12", "Amex Platinum  monthly spend", "Card", 4820.00, 9640),
    ("07/14", "07/15", "DL 2231  LAX–SLC  First Class", "Flights", 612.00, 3060),
    ("07/14", "07/15", "Delta Sky Club  annual", "Ancillary", 695.00, 1390),
    ("07/16", "07/17", "DL 1108  SLC–ATL  First Class", "Flights", 588.00, 2940),
    ("07/18", "07/19", "Hertz  Gold Plus Rewards", "Partner", 342.00, 1026),
    ("07/21", "07/22", "DL 0264  ATL–LHR  Delta One", "Flights", 3860.00, 19300),
    ("07/22", "07/23", "Marriott Bonvoy  4 nights", "Partner", 1284.00, 2568),
    ("07/25", "07/26", "DL 0265  LHR–ATL  Delta One", "Flights", 3860.00, 19300),
    ("07/26", "07/27", "Paid upgrade  ATL–BOS  Comfort", "Ancillary", 129.00, 645),
    ("07/28", "07/29", "DL 1442  ATL–BOS  Delta Comfort", "Flights", 428.00, 2140),
    ("07/29", "07/30", "Amex Delta Reserve  spend", "Card", 2140.00, 4280),
    ("07/30", "07/31", "DL 1443  BOS–ATL  Delta Comfort", "Flights", 428.00, 2140),
]

_DL_MILES = [
    (1, "Miles earned from flights", 101_730),
    (2, "Miles earned from American Express", 13_920),
    (3, "Miles earned from partners", 3_594),
    (4, "Miles earned from ancillary purchases", 2_035),
    (5, "Miles redeemed for award travel", -85_000),
    (6, "Miles transferred to a family member", -10_000),
    (7, "Balance carried forward", 214_806),
]

_DL_MEDALLION = [
    (1, "Current Medallion tier", "Platinum"),
    (2, "MQDs earned", "20,495 of 28,000"),
    (3, "MQDs to Diamond Medallion", "7,505"),
    (4, "Rollover MQDs from prior year", "2,140"),
    (5, "Choice Benefits selected", "2 of 2"),
    (6, "Companion certificates available", "1"),
    (7, "Status valid through", "01/31/2028"),
    (8, "SkyMiles member since", "2011"),
]

# --- Veraset: one enterprise customer's monthly data-license invoice --------
# Report template is shaped like a credit-card statement (fixed columns:
# Merchant Name or Transaction Description, Points Earned). Reframed as an
# invoice rather than extending the builder -- "Points" here holds records
# delivered (thousands), not loyalty points; "Merchant Name" holds a
# delivery line-item description. Represents ONE customer's monthly
# activity, not Veraset's whole-company revenue (same scale as Delta's
# report being one flyer's SkyMiles statement, not Delta's revenue).
_VR_ACTIVITY = [
    ("07/01", "07/02", "Movement — Daily GPS Ping Delivery (US Panel)", "Movement", 8200.00, 420),
    ("07/01", "07/02", "Visits — POI Attribution Batch", "Visits", 5400.00, 180),
    ("07/08", "07/09", "Movement — Daily GPS Ping Delivery (US Panel)", "Movement", 8350.00, 428),
    ("07/08", "07/09", "Trade Area — Site Selection Scoring Refresh", "Trade Area & Site Selection", 3100.00, 60),
    ("07/15", "07/16", "Movement — Daily GPS Ping Delivery (US Panel)", "Movement", 8180.00, 419),
    ("07/15", "07/16", "Visits — POI Attribution Batch", "Visits", 5550.00, 185),
    ("07/18", "07/19", "Visits — Cannibalization Overlay Add-on", "Visits", 2200.00, 40),
    ("07/22", "07/23", "Movement — Daily GPS Ping Delivery (US Panel)", "Movement", 8290.00, 424),
    ("07/22", "07/23", "Trade Area — Site Selection Scoring Refresh", "Trade Area & Site Selection", 3050.00, 58),
    ("07/29", "07/30", "Movement — Daily GPS Ping Delivery (US Panel)", "Movement", 8410.00, 431),
    ("07/29", "07/30", "Visits — Overage Records Beyond Committed Volume", "Visits", 4600.00, 95),
]

_VR_USAGE = [
    (1, "Committed monthly volume", 2_400_000),
    (2, "+ Movement records delivered", 1_702_000),
    (3, "+ Visits records delivered", 500_000),
    (4, "+ Trade Area records delivered", 118_000),
    (5, "Overage records this cycle", 95_000),
    (6, "Carryover from prior cycle", 40_000),
    (7, "Balance carried forward", 2_855_000),
]

_VR_CONTRACT = [
    (1, "Contract ID", "VRS-2026-04417"),
    (2, "Data products licensed", "3 of 6"),
    (3, "Committed monthly volume", "2.4M records"),
    (4, "Contract renewal date", "03/01/2027"),
    (5, "Account manager", "J. Alvarez"),
    (6, "Billing cycle", "Monthly, net-30"),
    (7, "Overage rate", "$0.0035 / record"),
]


# --- Sigma Motors: one reservation holder's monthly account activity -------
# Same reframe as Veraset -- this is ONE customer's reservation/service/rewards
# activity, not the company's whole-fleet EV waitlist numbers from the command
# center workbook (those are aggregate/regional, a different persona entirely).
# "Points Earned" here is Sigma Rewards loyalty points (1pt/$1 plus referral
# bonuses), "Merchant Name" holds the activity description.
_SM_ACTIVITY = [
    ("07/02", "07/03", "Reserve — Meridian EV Sedan (West Region)", "Reservation", 500.00, 500),
    ("07/05", "07/06", "Configurator — Extended Range Battery Pack upgrade", "Reservation", 3200.00, 3200),
    ("07/09", "07/10", "Referral bonus — J. Alvarez reservation confirmed", "Referral", 0.00, 1000),
    ("07/12", "07/13", "Service — 12-month software update & inspection", "Service", 149.00, 149),
    ("07/15", "07/16", "Sigma Charging Network — 500 kWh prepaid credit", "Charging", 175.00, 350),
    ("07/19", "07/20", "Merchandise — Sigma Motors apparel bundle", "Merchandise", 86.00, 86),
    ("07/22", "07/23", "Configurator — Performance wheel package upgrade", "Reservation", 1450.00, 1450),
    ("07/25", "07/26", "Priority Build Slot — queue advancement fee", "Reservation", 250.00, 250),
    ("07/29", "07/30", "Sigma Charging Network — 500 kWh prepaid credit", "Charging", 175.00, 350),
]

_SM_REWARDS = [
    (1, "Points earned from reservation & configuration", 5400),
    (2, "Points earned from referrals", 1000),
    (3, "Points earned from charging network purchases", 700),
    (4, "Points earned from service & merchandise", 235),
    (5, "Points redeemed for Priority Build Slot upgrade", -250),
    (6, "Points redeemed for merchandise bundle", -86),
    (7, "Balance carried forward", 22_340),
]

_SM_SUMMARY = [
    (1, "Reservation ID", "SM-RES-88214"),
    (2, "Vehicle configuration", "Meridian EV Sedan, Ext. Range"),
    (3, "Region", "West"),
    (4, "Queue position", "1,120 of 4,120 (West Region)"),
    (5, "Estimated delivery window", "Q1 2027"),
    (6, "Deposit status", "Fully refundable, on file"),
    (7, "Sigma Rewards tier", "Gold"),
    (8, "Reservation holder since", "2025"),
]


# --- BayPort: one member's Free Rewards Checking monthly statement ---------
# "Points Earned" is BayPort Rewards points (1pt/$2 debit spend); "Merchant
# Name" holds the transaction description. Represents ONE member's checking
# activity, not the credit union's whole balance sheet from the command
# center workbook (same reframe as Veraset/Sigma Motors above).
_BP_ACTIVITY = [
    ("07/01", "07/02", "Payroll Deposit — Huntington Ingalls Industries", "Deposit", 2840.00, 0),
    ("07/02", "07/03", "Kroger #4417 Newport News VA", "Groceries", -96.42, 48),
    ("07/03", "07/03", "Wawa Fuel #0231 Hampton VA", "Fuel", -52.10, 26),
    ("07/05", "07/06", "BayPort Mobile Deposit — Check #1042", "Deposit", 640.00, 0),
    ("07/07", "07/08", "Amazon.com Purchase", "Shopping", -128.77, 64),
    ("07/08", "07/09", "Dominion Energy Virginia — Auto Pay", "Utilities", -184.33, 0),
    ("07/10", "07/11", "Chick-fil-A Oyster Point", "Dining", -14.86, 7),
    ("07/11", "07/12", "Vehicle Loan Payment — Auto", "Loan Payment", -412.60, 0),
    ("07/12", "07/13", "Food Lion #0219 Williamsburg VA", "Groceries", -88.15, 44),
    ("07/15", "07/16", "Payroll Deposit — Huntington Ingalls Industries", "Deposit", 2840.00, 0),
    ("07/16", "07/17", "Transfer to Share Certificate", "Transfer", -500.00, 0),
    ("07/18", "07/19", "Cox Communications", "Utilities", -142.99, 0),
    ("07/20", "07/21", "Target T-2281 Hampton VA", "Shopping", -76.24, 38),
    ("07/22", "07/23", "BJ's Wholesale Fuel", "Fuel", -61.30, 30),
    ("07/25", "07/26", "ATM Withdrawal — BayPort Way Branch", "Cash", -100.00, 0),
    ("07/29", "07/30", "Dividend Paid — Regular Shares", "Dividend", 4.62, 0),
]

_BP_REWARDS = [
    (1, "Points earned from debit card purchases", 257),
    (2, "Points earned from mobile & bill pay activity", 40),
    (3, "Points earned from referral bonus", 250),
    (4, "Points redeemed for statement credit", -200),
    (5, "Points redeemed for merchandise", -75),
    (6, "Balance carried forward", 6840),
]

_BP_SUMMARY = [
    (1, "Membership Number", "BP-441207"),
    (2, "Account Type", "Free Rewards Checking"),
    (3, "Current Dividend Rate (Regular Shares)", "1.40% APY"),
    (4, "Direct Deposit Status", "Active — Huntington Ingalls Industries"),
    (5, "Share Certificates on File", "2 (12-mo, 24-mo)"),
    (6, "Vehicle Loan Balance", "$18,240.55"),
    (7, "Member Since", "2014"),
    (8, "Branch of Record", "One BayPort Way, Newport News"),
]

# --- ClickHouse: one Cloud customer's monthly usage invoice -----------------
# Same reframe as Veraset -- this is ONE mid-market ClickHouse Cloud account's
# monthly bill (compute/storage/transfer/support), not the company-wide ARR
# numbers on the command-center workbook (those are aggregate, a different
# persona entirely).
_CH_ACTIVITY = [
    ("07/01", "07/02", "Compute -- Scale tier (142 CHU-hours)", "Compute", 3245.00, 142),
    ("07/01", "07/02", "Storage -- Primary + replicas (8.2 TB)", "Storage", 1890.00, 0),
    ("07/08", "07/09", "Compute -- Scale tier (156 CHU-hours)", "Compute", 3564.00, 156),
    ("07/08", "07/09", "Data Transfer -- Egress (1.1 TB)", "Data Transfer", 220.00, 0),
    ("07/12", "07/13", "Support -- Enterprise SLA (monthly)", "Support", 1500.00, 0),
    ("07/15", "07/16", "Compute -- Scale tier (148 CHU-hours)", "Compute", 3382.00, 148),
    ("07/15", "07/16", "Storage -- Primary + replicas (8.6 TB)", "Storage", 1978.00, 0),
    ("07/18", "07/19", "Data Transfer -- Egress (0.9 TB)", "Data Transfer", 180.00, 0),
    ("07/22", "07/23", "Compute -- Scale tier (161 CHU-hours)", "Compute", 3679.00, 161),
    ("07/26", "07/27", "Committed-use credit applied", "Compute", -850.00, 0),
    ("07/29", "07/30", "Compute -- Scale tier (139 CHU-hours)", "Compute", 3176.00, 139),
]
_CH_USAGE = [
    (1, "Committed monthly compute (CHU-hours)", 500),
    (2, "+ Compute consumed this cycle", 746),
    (3, "+ Storage consumed (TB-months)", 25),
    (4, "Overage compute hours this cycle", 246),
    (5, "Committed-use credits applied", 85),
    (6, "Carryover credits from prior cycle", 40),
    (7, "Credit balance carried forward", 526),
]
_CH_CONTRACT = [
    (1, "Account ID", "CH-2026-08821"),
    (2, "Plan tier", "Scale"),
    (3, "Committed monthly spend", "$18,000"),
    (4, "Contract renewal date", "02/01/2027"),
    (5, "Account manager", "T. Nakamura"),
    (6, "Primary region", "us-west-2 (AWS)"),
    (7, "Support plan", "Enterprise SLA"),
]


def statement_activity_sql(cfg):
    if cfg["key"] == "bayport":
        cols = ["Transaction Date", "Post Date",
                "Merchant Name or Transaction Description", "Category", "Amount",
                "Points Earned"]
        rows = [("'%s/2026'" % t, "'%s/2026'" % pd, "'%s'" % d.replace("'", "''"),
                 "'%s'" % c, "%.2f" % amt, str(pts))
                for t, pd, d, c, amt, pts in _BP_ACTIVITY]
        return _union(rows, cols)
    if cfg["key"] == "sigma_motors":
        cols = ["Transaction Date", "Post Date",
                "Merchant Name or Transaction Description", "Category", "Amount",
                "Points Earned"]
        rows = [("'%s/2026'" % t, "'%s/2026'" % pd, "'%s'" % d.replace("'", "''"),
                 "'%s'" % c, "%.2f" % amt, str(pts))
                for t, pd, d, c, amt, pts in _SM_ACTIVITY]
        return _union(rows, cols)
    if cfg["key"] == "veraset":
        cols = ["Transaction Date", "Post Date",
                "Merchant Name or Transaction Description", "Category", "Amount",
                "Points Earned"]
        rows = [("'%s/2026'" % t, "'%s/2026'" % pd, "'%s'" % d.replace("'", "''"),
                 "'%s'" % c, "%.2f" % amt, str(pts))
                for t, pd, d, c, amt, pts in _VR_ACTIVITY]
        return _union(rows, cols)
    if cfg["key"] == "clickhouse":
        cols = ["Transaction Date", "Post Date",
                "Merchant Name or Transaction Description", "Category", "Amount",
                "Points Earned"]
        rows = [("'%s/2026'" % t, "'%s/2026'" % pd, "'%s'" % d.replace("'", "''"),
                 "'%s'" % c, "%.2f" % amt, str(pts))
                for t, pd, d, c, amt, pts in _CH_ACTIVITY]
        return _union(rows, cols)
    if cfg["key"] == "foxmedia":
        cols = ["Transaction Date", "Post Date",
                "Merchant Name or Transaction Description", "Category", "Amount",
                "Points Earned"]
        rows = [("'%s/2026'" % t, "'%s/2026'" % pd, "'%s'" % d.replace("'", "''"),
                 "'%s'" % c, "%.2f" % amt, str(pts))
                for t, pd, d, c, amt, pts in _FM_ACTIVITY]
        return _union(rows, cols)
    if cfg["key"] != "delta":
        return None
    cols = ["Transaction Date", "Post Date",
            "Merchant Name or Transaction Description", "Category", "Amount",
            "Points Earned"]
    rows = [("'%s/2026'" % t, "'%s/2026'" % pd, "'%s'" % d.replace("'", "''"),
             "'%s'" % c, "%.2f" % amt, str(pts))
            for t, pd, d, c, amt, pts in _DL_FLIGHTS]
    return _union(rows, cols)


def rewards_summary_sql(cfg):
    if cfg["key"] == "bayport":
        rows = [(str(o), "'%s'" % d, str(p)) for o, d, p in _BP_REWARDS]
        return _union(rows, ["Line Order", "Description", "Points"])
    if cfg["key"] == "sigma_motors":
        rows = [(str(o), "'%s'" % d, str(p)) for o, d, p in _SM_REWARDS]
        return _union(rows, ["Line Order", "Description", "Points"])
    if cfg["key"] == "veraset":
        rows = [(str(o), "'%s'" % d, str(p)) for o, d, p in _VR_USAGE]
        return _union(rows, ["Line Order", "Description", "Points"])
    if cfg["key"] == "clickhouse":
        rows = [(str(o), "'%s'" % d, str(p)) for o, d, p in _CH_USAGE]
        return _union(rows, ["Line Order", "Description", "Points"])
    if cfg["key"] == "foxmedia":
        rows = [(str(o), "'%s'" % d, str(p)) for o, d, p in _FM_ADUNITS]
        return _union(rows, ["Line Order", "Description", "Points"])
    if cfg["key"] != "delta":
        return None
    rows = [(str(o), "'%s'" % d, str(p)) for o, d, p in _DL_MILES]
    return _union(rows, ["Line Order", "Description", "Points"])


def account_summary_sql(cfg):
    if cfg["key"] == "bayport":
        rows = [(str(o), "'%s'" % m, "'%s'" % v) for o, m, v in _BP_SUMMARY]
        return _union(rows, ["Line Order", "Metric", "Value"])
    if cfg["key"] == "sigma_motors":
        rows = [(str(o), "'%s'" % m, "'%s'" % v) for o, m, v in _SM_SUMMARY]
        return _union(rows, ["Line Order", "Metric", "Value"])
    if cfg["key"] == "veraset":
        rows = [(str(o), "'%s'" % m, "'%s'" % v) for o, m, v in _VR_CONTRACT]
        return _union(rows, ["Line Order", "Metric", "Value"])
    if cfg["key"] == "clickhouse":
        rows = [(str(o), "'%s'" % m, "'%s'" % v) for o, m, v in _CH_CONTRACT]
        return _union(rows, ["Line Order", "Metric", "Value"])
    if cfg["key"] == "foxmedia":
        rows = [(str(o), "'%s'" % m, "'%s'" % v) for o, m, v in _FM_SUMMARY]
        return _union(rows, ["Line Order", "Metric", "Value"])
    if cfg["key"] != "delta":
        return None
    rows = [(str(o), "'%s'" % m, "'%s'" % v) for o, m, v in _DL_MEDALLION]
    return _union(rows, ["Line Order", "Metric", "Value"])


# ---------------------------------------------------------------------------
# Marriott International — asset-light lodging. Marriott does not own the
# hotels; it manages and franchises them, so the P&L it runs on is a FEE P&L
# layered on top of the system's room revenue. That maps onto this template
# almost literally:
#
#   product -> brand tier (Luxury / Premium / Select / Longer Stays / Midscale)
#   volume  -> system-wide room revenue, annualised, $MM
#   yield   -> the fee rate Marriott books on that room revenue
#              (base management + incentive + franchise fees, ~5-8%)
#   cost    -> Marriott's own direct cost rate against that fee stream
#   spread  -> fee margin
#   fee     -> other revenue: branded residential, licensing (MONTHLY $MM)
#   risk    -> share of properties running below RevPAR plan
#   units   -> rooms
#   shock   -> RevPAR shock
#
# Calibration against the real 10-K: ~1.6M rooms, ~9,300 properties,
# ~$75-80B of system-wide room revenue, ~$5.2B of gross fee revenues.
# ---------------------------------------------------------------------------
MARRIOTT = {
    "key": "marriott",
    "name": "Marriott International",
    "title": "Brand Portfolio & Fee Revenue Command Center",
    "domain": "global lodging",
    # the page-1 copilot writes its greeting from the base table's NAME, so a
    # table called "Loan Book" makes a lodging copilot talk about loan portfolios
    "base_table": "Brand Portfolio",
    "unit_noun": "Bonvoy member",
    "volume_noun": "room revenue",
    "logo_domain": "marriott.com",
    # #A11D2B is sampled from Marriott's own brand SVG on Commons (the wordmark
    # itself is monochrome); the deep wine and the burgundy are darkenings of it,
    # and the gold is the luxury-portfolio accent.
    "palette": {
        "navy": "#3D1119", "navy_deep": "#1C0A0E",
        "primary": "#A11D2B", "secondary": "#B08D57",
        "accent": "#C8455A", "mint": "#1F7A6B",
    },
    "products": [
        # bal_base = annualised system-wide room revenue, $MM.
        # units_base is a room count carried at the generator's own scale -- the
        # units KPI reads the largest single (brand tier x state) row, so the
        # input is ~14x the tier's rooms in thousands to land the headline on
        # Marriott's real ~1.6M rooms.
        ("Luxury", 1, "Managed", 11000, .0700, .0240, 6.0, .0008, .082,
         .180, .052, 1260, 0.0, "Ritz-Carlton, St. Regis",
         "Fee rate", 1.048, "Ahead"),
        ("Premium", 2, "Franchised", 35000, .0600, .0200, 9.0, .0008, .104,
         .165, .034, 8960, 1.1, "Marriott, Sheraton, Westin",
         "Fee rate", .982, "On plan"),
        ("Select", 3, "Franchised", 19000, .0530, .0170, 4.0, .0009, .126,
         .175, .028, 6020, 2.2, "Courtyard, Four Points",
         "Fee rate", .938, "Behind"),
        ("Longer Stays", 4, "Franchised", 8500, .0510, .0160, 2.0, .0008, .098,
         .170, .036, 2940, 0.6, "Residence Inn, TownePlace",
         "Fee rate", 1.026, "Ahead"),
        ("Midscale", 5, "Franchised", 4500, .0460, .0140, 1.0, .0010, .152,
         .190, .062, 2940, 1.7, "Fairfield, StudioRes",
         "Fee rate", .906, "Behind"),
        # Co-brand card fees and licensing are not room revenue, so this line's
        # volume is qualifying Bonvoy card spend -- and it carries a much higher
        # take rate than any hotel fee.
        ("Co-brand & fees", 6, "Licensed", 12000, .0820, .0260, 4.0, .0004, .045,
         .120, .088, 280, 1.3, "Bonvoy cards, licensing",
         "Fee rate", 1.072, "Ahead"),
    ],
    "subs": {
        "Luxury": [("The Ritz-Carlton", .420, 30, 7.4, "Ahead"),
                   ("W Hotels", .220, 15, 4.1, "On plan"),
                   ("St. Regis", .180, 25, 6.8, "Ahead"),
                   ("The Luxury Collection", .180, 10, 3.2, "On plan")],
        "Premium": [("Marriott Hotels", .380, 10, 2.8, "On plan"),
                    ("Sheraton", .240, -20, -1.4, "Behind"),
                    ("Westin", .200, 15, 3.6, "Ahead"),
                    ("Renaissance", .100, -5, 0.9, "On plan"),
                    ("Autograph Collection", .080, 35, 8.2, "Ahead")],
        "Select": [("Courtyard", .580, 5, 1.6, "On plan"),
                   ("Four Points", .180, -25, -2.2, "Behind"),
                   ("SpringHill Suites", .140, 10, 2.4, "On plan"),
                   ("AC Hotels", .100, 20, 6.1, "Ahead")],
        "Longer Stays": [("Residence Inn", .620, 15, 4.2, "Ahead"),
                         ("TownePlace Suites", .280, 5, 2.6, "On plan"),
                         ("Element", .100, 20, 5.8, "Ahead")],
        "Midscale": [("Fairfield by Marriott", .860, -10, 1.1, "Behind"),
                     ("StudioRes", .140, 25, 9.4, "Ahead")],
        "Co-brand & fees": [("Bonvoy co-brand cards", .740, 20, 9.6, "Ahead"),
                            ("Licensing & residential", .260, 10, 5.4, "Ahead")],
    },
    "alerts": [
        ("critical", "Orlando cluster missing RevPAR plan",
         "38 Select-brand hotels ran RevPAR 6.2% under plan through the holiday "
         "week", "14m ago", "Revenue Management", 620, "bps under plan"),
        ("critical", "Group block attrition downtown",
         "1,240 room nights released inside the 30-day cutoff at three city-centre "
         "Sheratons", "41m ago", "Group Sales", 1240, "room nights released"),
        ("warning", "Bonvoy redemption cost above trend",
         "Award redemption on transatlantic peak dates running 14% over the "
         "loyalty reserve assumption", "2h ago", "Loyalty Finance", 1400,
         "bps over reserve"),
        ("warning", "Franchise fee remittance aging",
         "92 franchised properties past the 45-day fee remittance SLA, mostly "
         "Midscale", "4h ago", "Owner & Franchise Services", 92,
         "properties past SLA"),
        ("info", "Luxury ADR holding",
         "Ritz-Carlton and St. Regis ADR up 310 bps year over year on Caribbean "
         "and Middle East demand", "6h ago", "Brand Management", 310,
         "bps ADR growth"),
    ],
    "agent": ("You are an analyst covering Marriott International's brand "
              "portfolio, management and franchise fee revenue, RevPAR "
              "performance and the Bonvoy loyalty programme."),
}

# US states weighted for Marriott's own room footprint -- Florida, California,
# Texas and the Southeast carry the count.
FOOTPRINTS["marriott"] = [("FL", .152), ("CA", .128), ("TX", .112), ("NY", .078),
                          ("GA", .062), ("NC", .048), ("VA", .046), ("IL", .042),
                          ("AZ", .038), ("TN", .034), ("NV", .032), ("MD", .030),
                          ("PA", .028), ("CO", .026), ("WA", .024)]

LABELS["marriott"] = {
    "personas": ["Executive", "Operations"],
    "modeler_page": "Portfolio Planning",
    "cohort_page": "Bonvoy Segments",
    "modeler_title": "RevPAR & Fee Scenario Modeler",
    "shock_label": "RevPAR shock (bps)",
    "kpi_revenue": "Net fee revenue ($M)",
    "kpi_margin": "Contribution ($M)",
    "kpi_volume": "Room revenue ($M)",
    "kpi_units": "Rooms (K)",
    "driver_nim": "Fee margin, fee rate less direct cost",
    "driver_risk": "Properties below RevPAR plan",
    "driver_cost": "Direct cost rate",
    "driver_eff": "Overhead ratio",
    "seg_product": "Brand tier",
    "seg_credit": "Bonvoy tier",
    "seg_dd": "Bonvoy card holder",
    "seg_engage": "Stay frequency",
    "seg_type": "Ownership",
    "seg_held": "Brands stayed",
    "cohort_name": "Segment name",
    "kpi_cohort_size": "Members in segment",
    "kpi_cohort_vol": "Lifetime spend",
    "kpi_cohort_rev": "Fee revenue per member",
    "kpi_cohort_risk": "Avg attrition risk",
    "col_volume": "Baseline room revenue",
    "col_growth": "RevPAR growth %",
    "col_yield": "Fee rate Δ bps",
    "col_cost": "Direct cost Δ bps",
}

SEGMENTS["marriott"] = {"Near Prime": "Silver", "Prime": "Gold",
                        "Super Prime": "Platinum", "Exceptional": "Titanium",
                        "Daily": "Frequent stayer", "Weekly": "Regular stayer",
                        "Monthly": "Occasional", "Dormant": "Lapsed"}

VOCAB["marriott"] = {
    "econ": ("Marriott is asset-light: it does not own the hotels, so revenue is "
             "system-wide room revenue times the fee rate it books on that room "
             "revenue -- base management, incentive and franchise fees -- less its "
             "own direct cost of servicing those hotels. The spread between them "
             "is the fee margin. Luxury and Premium tiers carry higher fee rates "
             "per dollar of room revenue than Midscale, and the Bonvoy co-brand "
             "card line carries the highest take rate of all, which is why brand "
             "mix moves fee revenue more than room growth does."),
    "metrics": ("net fee revenue, contribution, system-wide room revenue, rooms "
                "and the share of properties running below RevPAR plan"),
    "bands": ("Bonvoy tiers: Silver, Gold, Platinum, Titanium. Stay frequency: "
              "Frequent stayer, Regular stayer, Occasional, Lapsed."),
    "cohort_report": ("segment size, lifetime spend and average attrition risk"),
}

# Bonvoy per-member economics, in DOLLARS. A member's LIFETIME spend with
# Marriott runs in the low thousands for Silver and the low tens of thousands for
# Titanium -- an order of magnitude below a retail-banking balance, which is what
# the default carries. rev_rate is the fee revenue Marriott books per dollar of
# member spend (fee rate plus the co-brand contribution); fee_per_product is the
# incremental fee value of each additional brand the member stays with.
POP["marriott"] = {"bases": (1200, 2800, 5600, 11000), "rev_rate": 0.09,
                   "fee_per_product": 45}

# No bespoke plugin on this build, and no ticker -- a lodging company has no
# obvious public index worth streaming across the top of the page.
PLUGINS["marriott"] = {"hero": None, "hero_label": None, "ticker": None}

COMPANIES["marriott"] = MARRIOTT


# ---------------------------------------------------------------------------
# Activision Blizzard — interactive entertainment, FY2022 full-year.
# Three reporting segments from the 10-K: Activision (Call of Duty-led premium
# + live ops), Blizzard (Warcraft/Overwatch subscription + digital), King
# (Candy Crush mobile IAP). Acquired by Microsoft in Oct 2023; this build
# uses the last full standalone fiscal year.
#
# Mapping into the template:
#   product       -> reporting segment
#   volume        -> net revenues ($MM) — the P&L line the segment is judged on
#   yield         -> effective net revenue rate on gross bookings (~0.86-0.91)
#                    i.e. after platform/channel fees and deferred-revenue haircut
#   funding_rate  -> cost rate: platform fees + royalties + server COGS as % of
#                    net revenues. Gaming COGS are platform pass-through (30% for
#                    console/mobile storefronts) PLUS hosting/bandwidth; the rate
#                    is calculated against segment NET revenues.
#   fee_base      -> ancillary/licensing revenue beyond game sales, MONTHLY $MM.
#                    Advertising, hardware accessories, content licensing.
#   provision     -> refund and chargeback provision rate
#   delinq_rate   -> content underperformance / games-below-plan rate
#   opex_ratio    -> R&D + SG&A overhead as fraction of segment net revenues.
#                    Gaming is R&D-heavy (esp. Blizzard); 0.40-0.65 range.
#   units_base    -> MAUs in thousands. Activision ~100M, Blizzard ~35M, King ~238M.
#   shock         -> in-game net revenue trend shock
#
# FY2022 10-K calibration:
#   Activision: net revenues $2,313M, net bookings $2,282M, MAUs ~100M
#   Blizzard:   net revenues $1,632M, net bookings $1,537M, MAUs ~35M
#   King:       net revenues $2,688M, net bookings $2,630M, MAUs ~238M
#   Total segment net revenues: ~$6,633M (per-segment, ex Distribution)
# ---------------------------------------------------------------------------

BLIZZARD = {
    "key": "blizzard",
    "name": "Activision Blizzard",
    "title": "Franchise Performance & Live Operations Command Center",
    "domain": "interactive entertainment",
    "unit_noun": "player",
    "volume_noun": "net revenues",
    "logo_domain": "activisionblizzard.com",
    "base_table": "Revenue Book",
    # Palette sampled from the Activision Blizzard corporate site:
    # navy from the dark header; primary from the electric-blue accent on the
    # Activision brand; secondary from the Blizzard cobalt; King orange-gold
    # as the warm accent. mint stays teal for the positive-trend indicator.
    "palette": {
        "navy": "#0A0E1A", "navy_deep": "#05070F",
        "primary": "#1DA1F2", "secondary": "#148ECF",
        "accent": "#F5A623", "mint": "#00C4A7",
    },
    "products": [
        # name, order, balance_type, bal_base, yield, funding, fee_base,
        # provision, delinq, opex_ratio, growth, units_base, phase, tagline,
        # rate_label, goal_pct, status
        #
        # Activision segment: ~$2,313M FY2022 net revenues.
        # Platform fees (console/PC storefronts) ~28% of gross; net revenue rate
        # against gross bookings ~0.88. COGS (royalties + online hosting) ~22%
        # of net revenues. fee_base = licensing/advertising MONTHLY $MM: ~$4M/mo.
        # MAUs ~100M -> units_base 100000 (thousands).
        # Activision grew YoY on Warzone + MW2 launch; ~+3.5% net revenues vs FY21.
        ("Activision", 1, "Premium + live ops", 2313, .8800, .2200, 4.0, .0120, .0580,
         .4200, .035, 100000, 0.0,
         "Call of Duty franchise, live service",
         "Net bookings yield", .982, "On plan"),

        # Blizzard segment: ~$1,632M FY2022 net revenues.
        # Subscription-heavy (WoW) + digital sales (Diablo Immortal launched Jun 2022).
        # Net revenue yield vs gross bookings ~0.87 (subscription deferred).
        # COGS include server/hosting for WoW classic + live + Overwatch 2 relaunch;
        # higher cost ratio ~26% from heavy server load on OW2 F2P migration.
        # fee_base = BlizzCon licensing + esports broadcast MONTHLY $MM: ~$3M/mo.
        # MAUs ~35M (Overwatch 2 F2P relaunch Nov 2022 boosted back end of year).
        # Blizzard was slightly behind plan; OW2 launch disruption.
        ("Blizzard", 2, "Subscription + digital", 1632, .8700, .2600, 3.0, .0100, .0760,
         .5800, -.018, 35000, 1.1,
         "World of Warcraft, Overwatch, Diablo",
         "Net bookings yield", .912, "Behind"),

        # King segment: ~$2,688M FY2022 net revenues.
        # Mobile-only; platform fees higher (~30% Apple/Google cut) but volume huge.
        # Net revenue yield vs gross bookings ~0.89.
        # COGS ~23% (server + UA amortised COGS). fee_base = in-app advertising
        # revenue MONTHLY $MM: King has meaningful ad revenue ~$9-10M/mo.
        # MAUs ~238M across Candy Crush franchise (Saga, Soda, Friends, All-Stars).
        # King grew ~+3% in FY2022 driven by Candy Crush Saga resilience.
        ("King", 3, "Mobile IAP", 2688, .8900, .2300, 9.5, .0090, .0420,
         .3800, .032, 238000, 2.2,
         "Candy Crush franchise, mobile-first",
         "Net bookings yield", 1.024, "Ahead"),
    ],
    "alerts": [
        ("critical", "Call of Duty live-ops event underperforming",
         "Season 02 battle pass attach rate 31% below the 48% plan assumption",
         "22m ago", "Franchise Ops — Activision", 1700, "bps below plan"),
        ("critical", "Overwatch 2 server capacity",
         "1,840 concurrent peak sessions breached the provisioned cap; "
         "latency SLA missed across EU and NA",
         "1h ago", "Platform Reliability", 1840, "sessions over capacity"),
        ("warning", "Candy Crush day-7 retention drift",
         "New-install day-7 retention down 2.8pp month over month across Saga",
         "3h ago", "King Growth — UA", 280, "bps retention decline"),
        ("warning", "Microsoft deal regulatory timeline",
         "FTC second request extends closing estimate; 38 licensing deals in "
         "flight pending close certainty",
         "4h ago", "Corp Dev", 38, "deals pending close"),
        ("info", "Diablo Immortal in-app revenue milestone",
         "Mobile segment crossed $150M cumulative in-app revenue in under 12 months",
         "6h ago", "Blizzard Mobile", 150, "$M cumulative IAP"),
    ],
    "agent": ("You are an analyst covering Activision Blizzard's three reporting "
              "segments: Activision (Call of Duty + live ops), Blizzard (WoW, "
              "Overwatch, Diablo) and King (Candy Crush mobile). "
              "Answer with numbers from the Revenue Book."),
}

BLIZZARD["subs"] = {
    "Activision": [
        ("Call of Duty: Modern Warfare II", .582, 20, 4.8, "Ahead"),
        ("Warzone & Call of Duty: Mobile", .298, -15, 1.2, "On plan"),
        ("Crash, Spyro & other", .120, -40, -2.6, "Behind"),
    ],
    "Blizzard": [
        ("World of Warcraft", .481, -25, -3.4, "Behind"),
        ("Overwatch 2", .314, 80, 8.6, "Ahead"),
        ("Diablo Immortal", .205, 140, 22.1, "Ahead"),
    ],
    "King": [
        ("Candy Crush Saga", .642, 10, 2.4, "Ahead"),
        ("Candy Crush Soda Saga", .218, -20, 0.8, "On plan"),
        ("Other King titles", .140, -35, -1.4, "Behind"),
    ],
}

FOOTPRINTS["blizzard"] = [
    ("CA", .182), ("TX", .094), ("WA", .088), ("NY", .072), ("FL", .064),
    ("IL", .048), ("MA", .041), ("GA", .036), ("CO", .034), ("OR", .030),
    ("PA", .028), ("AZ", .026), ("NC", .024), ("VA", .022), ("OH", .020),
]

LABELS["blizzard"] = {
    "personas": ["Executive", "Franchise Analytics"],
    "modeler_page": "Live Ops Planning",
    "cohort_page": "Player Segments",
    "modeler_title": "Franchise Revenue & Live-Ops Scenario Modeler",
    "shock_label": "In-game net revenue trend shock (bps)",
    "kpi_revenue": "Net revenues ($M)",
    "kpi_margin": "Segment operating income ($M)",
    "kpi_volume": "Net revenues ($M)",
    "kpi_units": "MAUs (K)",
    "driver_nim": "Net bookings yield",
    "driver_risk": "Franchises below plan",
    "driver_cost": "Platform fee + COGS rate",
    "driver_eff": "R&D + SG&A overhead ratio",
    "col_volume": "Baseline net revenues",
    "col_growth": "Revenue growth %",
    "col_yield": "Bookings yield Δ bps",
    "col_cost": "Platform cost Δ bps",
    "seg_product": "Franchise segment",
    "seg_credit": "Monetisation tier",
    "seg_dd": "Live-ops participant",
    "seg_engage": "Play frequency",
    "seg_held": "Franchises played",
    "cohort_name": "Cohort name",
    "kpi_cohort_size": "Players in cohort",
    "kpi_cohort_vol": "Cohort net revenues",
    "kpi_cohort_rev": "Revenue per player",
    "kpi_cohort_risk": "Avg churn risk",
    # the Balance Type colour-by dimension
    "seg_type": "Revenue model",
}

SEGMENTS["blizzard"] = {
    # credit/engagement band translations
    "Near Prime": "F2P", "Prime": "Casual payer",
    "Super Prime": "Recurring payer", "Exceptional": "Whale",
    "Daily": "Daily", "Weekly": "Weekly",
    "Monthly": "Monthly", "Dormant": "Churned",
    # product name translations — member_population.sql has 6 SoFi product names
    # hardcoded; map them to the three Blizzard reporting segments so the cohort
    # "Franchise segment" control shows real names, not lending products.
    # Resulting distribution: Activision ~43%, Blizzard ~28%, King ~29%.
    "Personal Loans": "Activision",       # 31% of rows -> Activision
    "Credit Card": "Activision",          # 12% of rows -> Activision
    "SoFi Money": "King",                 # 22% of rows -> King
    "Home Loans": "King",                 # 7%  of rows -> King
    "Student Refinancing": "Blizzard",    # 13% of rows -> Blizzard
    "SoFi Invest": "Blizzard",            # 15% of rows -> Blizzard
}

VOCAB["blizzard"] = {
    "econ": ("Activision and Blizzard segments sell premium games and live-ops "
             "content; net revenues differ from net bookings because of deferred "
             "recognition on multi-element arrangements. King earns purely from "
             "mobile in-app purchases and advertising. The effective spread is "
             "net revenues less platform fees (up to 30% for iOS/Android) and "
             "hosting/server COGS."),
    "metrics": ("net revenues, net bookings, segment operating income and "
                "monthly active users"),
    "bands": ("Monetisation tiers: F2P (free-to-play, no spend), Casual payer "
              "(under $10/mo), Recurring payer ($10-50/mo), Whale (over $50/mo). "
              "Play frequency: Daily, Weekly, Monthly, Churned."),
    "cohort_report": "cohort size, net revenues per player and average churn risk",
}

# Per-player economics in DOLLARS.
# A Casual payer spends ~$5/mo ($60/yr); Recurring ~$25/mo ($300/yr);
# Whale ~$120/mo ($1,440/yr). Lifetime value is capped by churn, so the
# band bases are annual revenue, not lifetime balance.
POP["blizzard"] = {"bases": (0, 60, 300, 1440), "rev_rate": 1.00,
                   "fee_per_product": 18}

# No bespoke plugin on this build per the task spec.
PLUGINS["blizzard"] = {"hero": None, "hero_label": None, "ticker": None}

COMPANIES["blizzard"] = BLIZZARD


# ---------------------------------------------------------------------------
NVIDIA = {
    "key": "nvidia",
    "name": "NVIDIA",
    "title": "Platform & Data Center Command Center",
    "domain": "accelerated computing",
    # the page-1 copilot reads the base table's NAME for its greeting
    "base_table": "Platform Shipments",
    "unit_noun": "developer",
    "volume_noun": "shipments",
    "logo_domain": "nvidia.com",
    # navy/black sampled as a deep neutral to carry the header; the wordmark's
    # own colour is black-on-white, so the header instead keys off NVIDIA's
    # signature eye-mark green (#76B900, sampled directly from the Wikimedia
    # Commons NVIDIA_logo.svg path fill) as the brand accent throughout.
    # navy is `TEXT_DARK` for the ENTIRE workbook (brand.py: TEXT_DARK =
    # pal["navy"]) as well as the header gradient's midtone -- not primarily
    # a chart colour, even though it also happens to land in the
    # categorical-scheme's 3rd slot (here: Gaming). Three earlier passes on
    # this build tried to lighten navy specifically so that slot's chart
    # legend swatch would look less like black -- but every existing company
    # (sofi #0B2740, boa #012169, elevance #1B365D, mcd #27251F, abry
    # #0E2A47, nuvia #00346D, delta #003D79, marriott #3D1119) keeps navy at
    # HLS lightness 0.14-0.24, i.e. dark-as-text, and each one has this exact
    # same dark-swatch cosmetic on whichever category alphabetically lands in
    # slot 3. This is shared, standing generator behaviour, not a
    # company-specific defect -- so reverted to a dark, readable navy
    # in-band with every other company, matching the standing rule not to
    # patch around shared-code behaviour from a single company's config.
    "palette": {
        "navy": "#0B2412", "navy_deep": "#06140A",
        "primary": "#76B900", "secondary": "#4A8A00",
        "accent": "#9AE000", "mint": "#00C4A7",
    },
    "products": [
        # name, order, balance_type, bal_base, yield(gross margin), funding
        # (cost of revenue), fee_base (MONTHLY $MM), provision(supply-risk
        # reserve rate), delinq(allocation-risk rate), opex_ratio, growth,
        # units_base, phase, tagline, rate_label, goal_pct, status
        #
        # IMPORTANT: the generator's "Net Revenue" is a SPREAD --
        # bal_base*(yield_rate - funding_rate) + fee_base*12 -- exactly the
        # trap documented in HANDOFF section 8 for Delta ("the column called
        # 'Net Revenue' is income - cost + fees, i.e. a SPREAD"). The first
        # pass here set funding_rate to a separate cost-of-revenue rate
        # (yield=margin, funding=1-margin), which made the spread compute as
        # margin MINUS (1-margin) -- roughly half the real gross margin, and
        # went NEGATIVE for OEM & Other where cost-of-revenue rate (0.70)
        # exceeded margin (0.30). Fixed by setting funding_rate=0 (same
        # pattern as SoFi Money, a fee-only/no-funding-cost line) so
        # yield_rate alone IS the spread, and it equals the segment's real
        # gross margin directly. bal_base is calibrated so
        # bal_base*yield_rate + fee_base*12 reconciles to each segment's real
        # FY2025 revenue.
        #
        # units_base is scaled at the generator's own headline-KPI scale, not
        # a literal unit count: the KPI reads the largest single
        # (product x state) row as max(units_base) * max(state_share) * 1.157
        # (empirical constant, see HANDOFF section 20). Gaming ships the most
        # discrete boards by far, so it carries the max and is calibrated to
        # land the "GPUs shipped (M)" headline around ~45-50M; the other
        # lines are scaled down from it in proportion to their real relative
        # unit volumes (Data Center ships far fewer, much more expensive
        # boards; Automotive/ProViz/OEM fewer still).
        # bal_base is back-solved (not the naive segment-revenue/margin figure)
        # to account for the loan_book.sql mechanics: the KPI card sums
        # SumIf(Net Revenue, "Current Period") across months 12-23 AND across
        # every FOOTPRINTS state, where each month's balance is
        # bal_base*state_share*(1+growth/12)^month_index*seasonal. Growth
        # compounding alone inflates the 12-23 month window ~1.01x-1.36x
        # above the month-0 base depending on each segment's annual_growth,
        # and the ~15-state FOOTPRINTS share_sum (~0.876 here) scales it back
        # down again -- so the naive bal_base = revenue/margin figure
        # overshoots real revenue once rendered. Solved numerically against
        # the actual query shape instead of guessed.
        ("Data Center", 1, "Compute", 127376, .7800, 0.0, 640.0, .0040, .028,
         .140, .142, 24, 0.0, "Hopper, Blackwell, NVLink, networking",
         "Gross margin", 1.086, "Ahead"),
        ("Gaming", 2, "Compute", 19424, .6000, 0.0, 55.0, .0060, .046,
         .180, .038, 267, 1.1, "GeForce RTX desktop & laptop GPUs",
         "Gross margin", .958, "On plan"),
        ("Professional Visualization", 3, "Compute", 2927, .6500, 0.0, 9.0, .0035, .020,
         .160, .052, 12, 2.2, "RTX workstation & Omniverse",
         "Gross margin", 1.024, "Ahead"),
        ("Automotive & Robotics", 4, "Compute", 2515, .5500, 0.0, 4.0, .0050, .034,
         .190, .210, 4, 0.6, "DRIVE, Jetson, physical AI",
         "Gross margin", .912, "Behind"),
        ("OEM & Other", 5, "Compute", 1085, .3000, 0.0, 1.0, .0020, .015,
         .120, .010, 6, 1.7, "Legacy & channel",
         "Gross margin", .968, "On plan"),
    ],
    "subs": {
        "Data Center": [("Hopper", .420, -60, 9.4, "Behind"),
                        ("Blackwell", .380, 180, 24.8, "Ahead"),
                        ("Networking (NVLink/InfiniBand)", .140, 40, 12.2, "Ahead"),
                        ("DGX Cloud & software", .060, 90, 18.6, "Ahead")],
        "Gaming": [("GeForce RTX desktop", .560, -15, 4.2, "On plan"),
                  ("GeForce RTX laptop", .310, 10, 5.8, "Ahead"),
                  ("Gaming consoles & other", .130, -25, -1.4, "Behind")],
        "Professional Visualization": [("RTX workstation GPUs", .680, 5, 6.4, "On plan"),
                                       ("Omniverse & software", .320, 45, 14.2, "Ahead")],
        "Automotive & Robotics": [("DRIVE platform", .560, -40, -3.2, "Behind"),
                                  ("Jetson & robotics", .440, 60, 8.6, "Ahead")],
        "OEM & Other": [("Legacy GPUs", .620, -20, -4.8, "Behind"),
                        ("Channel & other", .380, 15, 2.1, "On plan")],
    },
    "alerts": [
        ("critical", "Blackwell allocation shortfall",
         "Hyperscaler demand outstrips CoWoS packaging capacity; 14 top accounts "
         "under-allocated against committed forecast", "24m ago",
         "Supply Chain", 14, "accounts under-allocated"),
        ("critical", "HBM3e cost spike",
         "High-bandwidth memory input cost up 340 bps against the quarter's "
         "standard-cost assumption", "51m ago", "Procurement", 340,
         "bps over plan"),
        ("warning", "Export control exposure",
         "Compliance flagged 6 data-center SKUs pending re-classification for "
         "restricted-region shipment", "2h ago", "Trade Compliance", 6,
         "SKUs under review"),
        ("warning", "Foundry lead-time drift",
         "Advanced-node wafer lead times extended 3 weeks against the capacity "
         "plan", "5h ago", "Manufacturing", 3, "weeks extended"),
        ("info", "Developer ecosystem growth",
         "CUDA developer registrations up 22% year over year, led by robotics "
         "and agentic-AI toolkits", "1d ago", "Developer Relations", 22,
         "pct YoY growth"),
    ],
    "agent": ("You are an analyst covering NVIDIA's Data Center, Gaming, "
              "Professional Visualization and Automotive & Robotics segments, "
              "gross margin trends and supply allocation risk. Answer with "
              "numbers from the workbook."),
}

# US states weighted toward NVIDIA's own design, HQ and hyperscaler-adjacent
# footprint -- Santa Clara plus the major hyperscaler build-out states.
FOOTPRINTS["nvidia"] = [("CA", .152), ("TX", .118), ("VA", .096), ("WA", .078),
                        ("GA", .064), ("OH", .058), ("AZ", .052), ("IL", .046),
                        ("OR", .042), ("NY", .038), ("NC", .034), ("IN", .030),
                        ("CO", .026), ("UT", .022), ("MA", .020)]

LABELS["nvidia"] = {
    "personas": ["Executive", "Supply Chain"],
    "modeler_page": "Capacity Planning",
    "cohort_page": "Customer Segments",
    "modeler_title": "Wafer & Packaging Capacity Scenario Modeler",
    "shock_label": "HBM / wafer cost shock (bps)",
    "kpi_revenue": "Revenue ($M)",
    "kpi_margin": "Gross profit ($M)",
    "kpi_volume": "Shipment volume ($M)",
    "kpi_units": "GPUs shipped (M)",
    "driver_nim": "Gross margin",
    "driver_risk": "Allocation shortfall rate",
    "driver_cost": "Cost of revenue rate",
    "driver_eff": "Opex ratio",
    "seg_product": "Segment",
    "seg_credit": "Customer tier",
    "seg_type": "Compute type",
    "seg_dd": "Direct hyperscaler account",
    "seg_engage": "Order cadence",
    "seg_held": "Platforms adopted",
    "cohort_name": "Segment name",
    "kpi_cohort_size": "Accounts in segment",
    "kpi_cohort_vol": "Annual spend",
    "kpi_cohort_rev": "Spend per account",
    "kpi_cohort_risk": "Avg allocation risk",
    "col_volume": "Baseline shipment volume",
    "col_growth": "Shipment growth %",
    "col_yield": "Gross margin Δ bps",
    "col_cost": "Cost of revenue Δ bps",
}

SEGMENTS["nvidia"] = {"Near Prime": "Emerging", "Prime": "Growth",
                      "Super Prime": "Enterprise", "Exceptional": "Hyperscale",
                      "Daily": "Active", "Weekly": "Recurring",
                      "Monthly": "Occasional", "Dormant": "Lapsed"}

VOCAB["nvidia"] = {
    "econ": "Each platform earns a gross margin against its cost of revenue "
            "(wafer, packaging and memory input costs); the spread between "
            "them is the gross profit the segment contributes before opex.",
    "metrics": "revenue, gross profit, shipment volume and allocation "
               "shortfall risk",
    "bands": "Customer tiers: Emerging, Growth, Enterprise, Hyperscale. Order "
             "cadence: Active, Recurring, Occasional, Lapsed.",
    "cohort_report": "accounts in the segment, annual spend and average "
                     "allocation risk",
}

# Per-unit economics for the cohort page, in DOLLARS. A hyperscale account's
# annual platform spend is nothing like a retail-banking balance, so this must
# override the default or the cohort KPIs read as nonsense.
POP["nvidia"] = {"bases": (85000, 420000, 2100000, 9800000), "rev_rate": 0.78,
                 "fee_per_product": 640000}

# Plugin-free for this build -- no bespoke plugin authored this session, and
# no obvious public index (unlike Treasury yields or commodity indices) to
# stream as a ticker without a metaphor stretch.
PLUGINS["nvidia"] = {"hero": None, "hero_label": None, "ticker": None}

COMPANIES["nvidia"] = NVIDIA


# ---------------------------------------------------------------------------
# ClickHouse Inc. -- real-time OLAP database company. Privately held (no
# 10-K), so calibrated against the real publicly-reported figures instead:
# $250M ARR (May 2026, TechCrunch, "tripled" YoY), Series D Jan 2026 ($400M
# at ~$15B valuation), 4,000 customers (May 2026, up from ~3,000 Jan 2026).
# Segment split (Cloud/Enterprise/Services) and the exact revenue-per-segment
# numbers are NOT disclosed by the company -- the 65/25/10 split and margins
# below are a reasonable estimate, not a confirmed figure, same caveat as
# every other company here whose card/alert numbers are illustrative dressing
# on a real total. bal_base values are back-solved (not naive) against the
# actual 24-month growth+seasonal grid so month 12-23 sums hit the target ARR
# exactly -- same method as NVIDIA's units_base, see HANDOFF section 20.
#
# NOTE: this company has NO Snowflake-dialect SQL file wired up (there is no
# clickhouse_book.sql -- porting loan_book.sql's SEQ4()/DATEADD()/HASH() to
# ClickHouse SQL is real work, not a config-only change). This entry is
# consumed by examples/build_clickhouse_v2_command_center.py, a standalone
# script that reuses company.py's config + the portable literal-value
# generators (products_cte, product_cards_sql, notifications_sql,
# product_skus_sql -- CAST(...AS VARCHAR/NUMBER) shimmed to ClickHouse's
# String/Decimal) but computes the product x state x month grid in pure
# Python and emits it as literal SELECT/UNION ALL rows, so no vendor-specific
# SQL function is needed at all. NOT build_sofi.py-compatible as-is.
CLICKHOUSE = {
    "key": "clickhouse",
    "name": "ClickHouse",
    "title": "Revenue & Customer Command Center",
    "domain": "real-time OLAP analytics",
    "unit_noun": "customer",
    "volume_noun": "ARR",
    "logo_domain": "clickhouse.com",
    "base_table": "Revenue Book",
    "palette": {
        "navy": "#161616", "navy_deep": "#0B0B0B",
        "primary": "#FCFF74", "secondary": "#D9B400",
        "accent": "#FFE873", "mint": "#00C48C",
    },
    "products": [
        # name, order, balance_type, bal_base($MM/mo, back-solved), yield
        # (gross margin, funding=0 same as NVIDIA -- no cost-of-funds concept
        # for a software business), funding, fee_base(unused, 0), provision
        # (unused, 0), delinq(unused, 0), opex_ratio, annual_growth,
        # units_base(customers), phase, tagline, rate_label, goal_pct, status
        ("ClickHouse Cloud", 1, "Cloud", 1.057, .6500, 0.0, 0.0, 0.0, 0.0,
         .5500, 1.80, 2600, 0.0, "Managed real-time analytics, usage-based",
         "Gross margin", 1.08, "Ahead"),
        ("Enterprise & Support", 2, "License", 2.3535, .7800, 0.0, 0.0, 0.0, 0.0,
         .3500, 0.55, 1000, 1.1, "On-prem licensing & dedicated support",
         "Gross margin", 1.04, "Ahead"),
        ("Training & Services", 3, "Services", 1.2525, .5500, 0.0, 0.0, 0.0, 0.0,
         .4200, 0.35, 400, 2.2, "Certification, training & professional services",
         "Gross margin", 0.92, "Behind"),
    ],
    "alerts": [
        ("critical", "Cloud infrastructure margin compression",
         "ClickHouse Cloud gross margin sits at 65%, the thinnest of the three "
         "lines, as usage growth outpaces compute/storage cost optimization",
         "31m ago", "Cloud Platform", 65, "pct gross margin"),
        ("critical", "Hyperscaler account concentration",
         "A small number of hyperscaler accounts (OpenAI, Anthropic, Meta-scale "
         "workloads) represent an outsized share of Enterprise & Support revenue",
         "1h ago", "Enterprise Sales", 3, "top accounts flagged"),
        ("warning", "Training & Services margin lag",
         "Training & Services gross margin is 55%, the only line behind its "
         "own target and the thinnest of the three overall",
         "4h ago", "Professional Services", 55, "pct gross margin"),
        ("warning", "Headcount scaling risk",
         "Headcount grew roughly 72% year over year; onboarding and support "
         "coverage are at risk of lagging revenue growth",
         "6h ago", "People Ops", 72, "pct YoY headcount growth"),
        ("info", "Series D milestone",
         "Closed a $400M Series D at a ~$15B valuation as ARR tripled "
         "year over year to $250M and the customer base passed 4,000",
         "1d ago", "Finance", 250, "$M ARR"),
    ],
    "agent": ("You are an analyst covering ClickHouse Inc.'s business across "
              "ClickHouse Cloud, Enterprise & Support, and Training & Services. "
              "Answer with numbers from the workbook."),
}

# US states weighted toward ClickHouse's real footprint: SF Bay Area /
# Portland heritage, remote-first team, and a customer base concentrated in
# the same AI/tech hubs as its named hyperscaler customers (OpenAI, Anthropic,
# Meta, Tesla).
FOOTPRINTS["clickhouse"] = [("CA", .25), ("NY", .13), ("WA", .10), ("TX", .09),
                            ("MA", .07), ("IL", .05), ("GA", .05), ("CO", .04),
                            ("VA", .04), ("OR", .03), ("NC", .03), ("FL", .03),
                            ("PA", .03), ("OH", .03), ("AZ", .03)]

PLUGINS["clickhouse"] = {"hero": None, "hero_label": None, "ticker": None}

COMPANIES["clickhouse"] = CLICKHOUSE

# ---------------------------------------------------------------------------
# SynergenRx -- independent specialty pharmacy (Doraville, GA) serving rare &
# complex therapies (oncology, orphan/rare disease, autoimmune/rheumatology)
# via manufacturer hub services, prior-auth support and adherence programs.
# LIGHTWEIGHT build: single dashboard page, no map/plugin/scenario-modeler --
# see build_synergenrx_command_center.py.
# ---------------------------------------------------------------------------
SYNERGENRX = {
    "key": "synergenrx",
    "name": "SynergenRx",
    "title": "Patient Access & Therapy Performance Command Center",
    "domain": "independent specialty pharmacy — rare & complex therapies",
    "unit_noun": "patient",
    "volume_noun": "scripts filled",
    "logo_domain": "synergenrx.com",
    "base_table": "Dispensing Book",
    # Real brand colors, pulled from the company's own logo SVG
    # (synergenrx.com/wp-content/uploads/Synergen_logo.svg): navy-blue
    # #00518E is the wordmark fill, #289500 is the leaf/vitality accent.
    "palette": {
        "navy": "#0B2F4A", "navy_deep": "#061A2C",
        "primary": "#00518E", "secondary": "#289500",
        "accent": "#4FA8D8", "mint": "#289500",
    },
    "products": [
        # name, order, balance_type, bal_base(monthly compounding seed,
        # back-solved against _ANNUAL_TARGETS in the build script -- same
        # technique as ClickHouse), gross margin, funding(unused,0),
        # fee_base(unused,0), provision(unused,0), delinq(unused,0),
        # opex_ratio, annual_growth, units_base(active patients), phase,
        # tagline, rate_label, goal_pct, status
        ("Oncology & Hematology", 1, "Therapy", 0.924437, .2200, 0.0, 0.0, 0.0, 0.0,
         .6800, 0.18, 500, 0.0, "Oral & infused oncology, complex hematology support",
         "Gross margin", 1.05, "Ahead"),
        ("Rare & Orphan Disease", 2, "Therapy", 0.481688, .2600, 0.0, 0.0, 0.0, 0.0,
         .6300, 0.35, 250, 1.4, "High-touch hub services for ultra-rare, high-cost therapies",
         "Gross margin", 1.12, "Ahead"),
        ("Autoimmune & Rheumatology", 3, "Therapy", 0.593141, .2400, 0.0, 0.0, 0.0, 0.0,
         .6500, 0.08, 350, 2.6, "Biologics adherence & injection-training support",
         "Gross margin", 0.91, "Behind"),
    ],
    "alerts": [
        ("critical", "Prior authorization turnaround rising",
         "Average prior-authorization turnaround climbed to 6.2 days across "
         "rare-disease referrals, above the 3-day target and risking treatment "
         "delays for new patient starts.",
         "45m ago", "Patient Access Team", 6, "avg PA days"),
        ("warning", "Autoimmune & Rheumatology margin behind plan",
         "Autoimmune & Rheumatology gross margin is 24%, trailing Oncology and "
         "Rare Disease as payer rebate pressure increases on biologics.",
         "2h ago", "Payer Contracting", 24, "pct gross margin"),
        ("info", "Rare & Orphan Disease enrollment accelerating",
         "New patient starts in Rare & Orphan Disease are up 35% year over "
         "year, the fastest-growing therapy line and the primary driver of "
         "company growth.",
         "3h ago", "Clinical Intake", 35, "pct YoY growth"),
    ],
    "agent": ("You are an analyst covering SynergenRx's specialty pharmacy "
              "business across Oncology & Hematology, Rare & Orphan Disease, "
              "and Autoimmune & Rheumatology. Answer with numbers from the "
              "workbook."),
}

COMPANIES["synergenrx"] = SYNERGENRX


# ---------------------------------------------------------------------------
# Alnylam Pharmaceuticals -- RNAi/siRNA therapeutics, FY2025 full-year. The
# first biotech/pharma build for this generator, so the mapping is worth
# spelling out (this is NOT a lending template with new labels):
#
#   products      -> real franchise / product lines from the 10-K:
#                    TTR Franchise (AMVUTTRA, ONPATTRO), Rare Disease
#                    Franchise (GIVLAARI, OXLUMO), plus a 5th administrative
#                    line for collaboration & royalty revenue (Roche,
#                    Regeneron, Novartis LEQVIO royalty) -- fee-only, no
#                    product volume of its own, same shape as Elevance's
#                    "ASO Self-funded" line.
#   bal_base      -> patients-on-therapy-weighted net product revenue base,
#                    $MM (back-solved, see note below -- NOT literally
#                    revenue/margin)
#   yield_rate    -> gross margin on net product revenue. RNAi biologics run
#                    materially higher gross margin than a bank's asset
#                    yield or an airline's RASM -- 80-86% here, matching
#                    Alnylam's real COGS profile (COGS ~14-20% of net
#                    product revenue).
#   funding_rate  -> set to 0 for every product. This is the exact trap
#                    documented in HANDOFF section 8 (Delta's RASM/CASM,
#                    then NVIDIA's gross-margin business): the generator's
#                    "Net Revenue" column is a SPREAD
#                    (income - cost + fees), not a revenue line. A biotech's
#                    real economics ARE that spread -- funding_rate=0 lets
#                    yield_rate alone equal the true gross margin, the same
#                    pattern already used for SoFi Money and every NVIDIA
#                    segment.
#   fee_base      -> MONTHLY $MM (x12 in the SQL -- the Nuvia trap). Used for
#                    Collaborations & Royalties, which has no bal_base/yield
#                    of its own; its entire revenue is fee_base x 12.
#   provision_rate -> set near 0; there is no credit/refund provision
#                    analogous to a bank's -- rare-disease payer contracts
#                    carry negligible bad debt relative to list price.
#   delinq_rate   -> repurposed as a "patient discontinuation / non-adherence
#                    rate" -- the risk metric that actually matters for a
#                    chronic-therapy rare-disease franchise.
#   opex_ratio    -> R&D + SG&A load against gross profit (Alnylam's R&D and
#                    SG&A together run close to net product revenue as the
#                    company approaches durable profitability).
#   units_base    -> patients on therapy, at the generator's own KPI scale
#                    (see note below) -- NOT US population, NOT a mass-market
#                    unit count. This is an ultra-rare-disease population.
#
# bal_base back-solve: the KPI compounds bal_base through
# (1+annual_growth/12)**month_index over months 12-23, summed across every
# FOOTPRINTS state share (share_sum ~0.924 here), which inflates or deflates
# the naive bal_base = revenue/margin figure. Solved numerically against a
# standalone reproduction of loan_book.sql's math (script discarded after
# use); the four product bal_base values below render within +0.55%/-3.21%
# of the real FY2025 net product revenue figures, and total revenue across
# all five lines (incl. Collaborations & Royalties) renders within -0.55% of
# the real $3,713.9M FY2025 total revenue.
#
# AMVUTTRA's real FY2025 YoY growth was +138%, off an unusual pent-up-demand
# base the year of its ATTR-CM approval -- not a sustainable forward run
# rate. annual_growth=.85 here instead approximates the growth implied by
# FY2026 guidance (TTR franchise net product revenue of $4,400-4,700M against
# a 2025 AMVUTTRA+ONPATTRO base of ~$2,486.6M is roughly +77-89% blended,
# and ONPATTRO is declining, so AMVUTTRA alone must grow faster than the
# blended franchise number).
# ---------------------------------------------------------------------------

ALNYLAM = {
    "key": "alnylam",
    "name": "Alnylam Pharmaceuticals",
    "title": "Franchise & Patient Access Command Center",
    "domain": "RNAi therapeutics",
    "unit_noun": "patient",
    "volume_noun": "net product revenue",
    "logo_domain": "alnylam.com",
    "base_table": "Patient Therapy Ledger",
    # navy + primary sampled directly from Alnylam's own logo.svg (the
    # double-helix mark): #0F9BD7 is the helix's cyan-blue arc, #1A3967 is
    # the helix tail + wordmark navy, #ACD5F1 is the small accent dot.
    "palette": {
        "navy": "#1A3967", "navy_deep": "#0C1B33",
        "primary": "#0F9BD7", "secondary": "#1774B0",
        "accent": "#4DC0EA", "mint": "#00B3A4",
    },
    "products": [
        # name, order, balance_type, bal_base, yield(gross margin), funding,
        # fee_base (MONTHLY $MM), provision, delinq(discontinuation rate),
        # opex_ratio, growth, units_base, phase, tagline, rate_label,
        # goal_pct, status
        ("AMVUTTRA", 1, "TTR Franchise", 851.6, .8600, 0.0, 0.0, .0025, .048,
         .560, .85, 46.84, 0.0,
         "Vutrisiran for hATTR polyneuropathy and ATTR cardiomyopathy",
         "Gross margin", 1.086, "Ahead"),
        ("ONPATTRO", 2, "TTR Franchise", 361.2, .8000, 0.0, 0.0, .0030, .092,
         .520, -.30, 3.51, 1.1,
         "Patisiran, the first-generation TTR therapy, being cannibalised by AMVUTTRA",
         "Gross margin", .694, "Behind"),
        ("GIVLAARI", 3, "Rare Disease Franchise", 299.5, .8300, 0.0, 0.0, .0022, .038,
         .480, .21, 24.59, 2.2,
         "Givosiran for acute hepatic porphyria",
         "Gross margin", 1.041, "Ahead"),
        ("OXLUMO", 4, "Rare Disease Franchise", 199.8, .8300, 0.0, 0.0, .0020, .034,
         .480, .15, 8.78, 0.6,
         "Lumasiran for primary hyperoxaluria type 1",
         "Gross margin", 1.024, "Ahead"),
        # Fee-only administrative line -- same shape as Elevance's ASO
        # Self-funded: bal_base/yield/funding are 0, all revenue is
        # fee_base x 12. No patient population of its own (units_base=0).
        ("Collaborations & Royalties", 5, "Administrative", 0.0, 0.0, 0.0, 65.60,
         0.0, .0, .180, .10, 0.0, 1.7,
         "Roche and Regeneron collaboration revenue plus the Novartis LEQVIO royalty",
         "Royalty rate", .968, "On plan"),
    ],
    "subs": {
        "AMVUTTRA": [("hATTR polyneuropathy", .420, -25, 6.8, "Ahead"),
                     ("ATTR cardiomyopathy", .580, 210, 42.4, "Ahead")],
        "ONPATTRO": [("Continuing therapy", .680, -40, -18.2, "Behind"),
                     ("New starts", .320, -90, -52.6, "Behind")],
        "GIVLAARI": [("US", .580, 15, 8.4, "Ahead"),
                     ("Ex-US", .420, -10, 4.1, "On plan")],
        "OXLUMO": [("US", .540, 20, 6.2, "Ahead"),
                   ("Ex-US", .460, -15, 3.8, "On plan")],
        "Collaborations & Royalties": [("Novartis LEQVIO royalty", .239, 40, 9.0, "Ahead"),
                                       ("Roche collaboration", .543, 130, 23.0, "Ahead"),
                                       ("Regeneron collaboration", .157, -180, -6.2, "Behind"),
                                       ("Other collaborations", .061, 260, 44.5, "Ahead")],
    },
    "alerts": [
        ("critical", "AMVUTTRA cardiomyopathy demand outstripping supply plan",
         "Fill-finish capacity running 12% behind the ATTR-CM launch ramp forecast",
         "38m ago", "Supply Chain", 12, "pct behind ramp plan"),
        ("critical", "ONPATTRO conversion accelerating",
         "212 patients switched from ONPATTRO to AMVUTTRA this month, ahead of the "
         "cannibalisation model", "1h ago", "Commercial Analytics", 212,
         "patients converted"),
        ("warning", "GIVLAARI prior-authorization delays",
         "184 payer prior-auth requests past the 10-business-day standard in AHP "
         "referral centers", "3h ago", "Patient Access", 184, "auths past SLA"),
        ("warning", "OXLUMO newborn-screening referrals lagging",
         "PH1 genetic-testing referrals from 6 pediatric nephrology centers down "
         "9% quarter over quarter", "5h ago", "Medical Affairs", 9,
         "pct QoQ decline"),
        ("info", "Roche collaboration milestone recognized",
         "A $45M development milestone was recognized this quarter under the "
         "Roche collaboration agreement", "1d ago", "Business Development", 45,
         "$M milestone recognized"),
    ],
    "agent": ("You are an analyst covering Alnylam Pharmaceuticals' TTR and "
              "Rare Disease franchises -- AMVUTTRA, ONPATTRO, GIVLAARI, "
              "OXLUMO -- plus collaboration and royalty revenue from Roche, "
              "Regeneron and the Novartis LEQVIO royalty. Answer with numbers "
              "from the Patient Therapy Ledger."),
}

# US states weighted toward rare-disease referral and treatment-center
# concentration -- HQ (MA) plus the major academic medical center states
# where ATTR amyloidosis, AHP and PH1 patients are actually diagnosed and
# infused/dosed.
FOOTPRINTS["alnylam"] = [
    ("MA", .148), ("CA", .132), ("NY", .108), ("TX", .072), ("PA", .066),
    ("OH", .058), ("IL", .052), ("NC", .046), ("FL", .044), ("MI", .038),
    ("MN", .036), ("CO", .034), ("WA", .032), ("GA", .030), ("VA", .028),
]

LABELS["alnylam"] = {
    "personas": ["Executive", "Medical Affairs"],
    "modeler_page": "Commercial Planning",
    "cohort_page": "Patient Population",
    "modeler_title": "Gross-to-Net & Manufacturing Cost Scenario Modeler",
    "shock_label": "Gross-to-net rebate shock (bps)",
    "kpi_revenue": "Net product revenue ($M)",
    "kpi_margin": "Gross profit ($M)",
    "kpi_volume": "Net product revenue ($M)",
    "kpi_units": "Patients on therapy (K)",
    "driver_nim": "Gross margin",
    "driver_risk": "Discontinuation rate",
    "driver_cost": "Cost of goods rate",
    "driver_eff": "R&D + SG&A ratio",
    "seg_product": "Franchise / product",
    "seg_credit": "Therapy tenure",
    "seg_dd": "Site-of-care infusion",
    "seg_engage": "Dosing adherence",
    "seg_held": "Indications treated",
    "seg_type": "Franchise",
    "cohort_name": "Population name",
    "kpi_cohort_size": "Patients in population",
    "kpi_cohort_vol": "Annual therapy spend",
    "kpi_cohort_rev": "Revenue per patient",
    "kpi_cohort_risk": "Avg discontinuation risk",
    "col_volume": "Baseline net product revenue",
    "col_growth": "Revenue growth %",
    "col_yield": "Gross margin Δ bps",
    "col_cost": "Cost of goods Δ bps",
}

SEGMENTS["alnylam"] = {
    # tenure/adherence band translations
    "Near Prime": "New start", "Prime": "Established",
    "Super Prime": "Long-term adherent", "Exceptional": "Legacy (10yr+)",
    "Daily": "On-schedule", "Weekly": "Recently dosed",
    "Monthly": "Due for dose", "Dormant": "Discontinued",
    # product-name translations -- member_population.sql hardcodes 6 SoFi
    # product names; Alnylam has 5 real lines, so AMVUTTRA (the dominant,
    # fastest-growing franchise) legitimately covers two of the six slots,
    # the same pattern used for Blizzard's Activision segment.
    # Resulting distribution: AMVUTTRA ~53%, GIVLAARI ~12%, ONPATTRO ~13%,
    # OXLUMO ~7%, Collaborations & Royalties ~15%.
    "Personal Loans": "AMVUTTRA",              # 31% of rows -> AMVUTTRA
    "SoFi Money": "AMVUTTRA",                  # 22% of rows -> AMVUTTRA
    "Student Refinancing": "ONPATTRO",         # 13% of rows -> ONPATTRO
    "Credit Card": "GIVLAARI",                 # 12% of rows -> GIVLAARI
    "Home Loans": "OXLUMO",                    # 7%  of rows -> OXLUMO
    "SoFi Invest": "Collaborations & Royalties",  # 15% of rows -> Collab & Royalties
}

VOCAB["alnylam"] = {
    "econ": ("Each product earns a gross margin against its cost of goods "
             "sold -- manufacturing, drug substance and drug product costs "
             "for the RNAi therapy itself; the spread between net product "
             "revenue and COGS is the gross profit the franchise contributes "
             "before R&D and SG&A. Collaborations & Royalties carries no "
             "product cost of its own -- it is fee revenue recognized under "
             "the Roche and Regeneron collaboration agreements and the "
             "Novartis LEQVIO royalty."),
    "metrics": ("net product revenue, gross profit, patients on therapy and "
                "the discontinuation rate"),
    "bands": ("Therapy tenure: New start, Established, Long-term adherent, "
              "Legacy (10yr+). Dosing adherence: On-schedule, Recently dosed, "
              "Due for dose, Discontinued."),
    "cohort_report": ("population size, annual therapy spend and average "
                      "discontinuation risk"),
}

# Per-patient economics for the cohort page, in DOLLARS. These are chronic,
# ultra-high-cost specialty RNAi therapies -- annual list price runs
# ~$450K-$575K per patient per year (GIVLAARI, AMVUTTRA), nothing like a
# retail-banking balance. bases are lifetime therapy spend at increasing
# tenure (New start ~1yr, Established ~3yr, Long-term adherent ~6yr, Legacy
# ~10yr) and MUST override the default or the cohort KPIs read as nonsense
# (the Nuvia "$1,825 lifetime value" mistake).
POP["alnylam"] = {"bases": (480000, 1440000, 2880000, 4800000), "rev_rate": 0.84,
                  "fee_per_product": 465000}

# Bespoke plugin: an animated RNAi/siRNA gene-silencing pathway visual. mRNA
# strands travel from each product node inward to a central RISC hub and are
# "silenced" -- the actual RNAi mechanism, not decoration. Node size = net
# product revenue (tbl-pc "Balances $B" / p3); pulse rate keys off plan
# attainment (tbl-pc "Goal Pct" / p7) as a growth-like signal. Registered via
# POST /v2/plugins from ~/Library/Application Support/millersigma-plugins/
# alnylam-rnai-pathway/, served by the existing com.millersigma.plugins
# launchd agent on localhost:8080 -- no new hosting step required.
PLUGINS["alnylam"] = {"hero": "8c93a664-6c23-4f05-9672-8b5dec130ee6",
                      "hero_label": "RNAi SILENCING PATHWAY", "ticker": None,
                      "hero_config": {"product": "p0", "revenue": "p3", "pulse": "p7"}}

COMPANIES["alnylam"] = ALNYLAM

# ================================================================== VERASET
# Private company -- no disclosed financials. Scale modeled from Veraset's
# own stated coverage (10B+ anonymized GPS pings/day, ~300M devices, 200+
# countries) and typical DaaS/alt-data pricing, not real reported numbers.
# funding_rate=0 throughout (fee-only/margin-only pattern, same as NVIDIA's
# compute segments and SoFi Money) -- a data-licensing business has no
# "cost of funds," yield_rate alone IS the gross margin.
VERASET = {
    "key": "veraset",
    "name": "Veraset",
    "title": "Data Licensing Command Center",
    "domain": "location data intelligence",
    "base_table": "Data License Book",
    "unit_noun": "account",
    "volume_noun": "licensed volume",
    "logo_domain": "veraset.com",
    # sampled directly from veraset.com's page CSS, not guessed: #011627 (dark
    # navy, near-black -- the site's actual header/background) and #23D6C7
    # (a saturated teal/cyan, the one vivid accent against an otherwise
    # muted/monochrome palette -- used sparingly on their own site, same
    # restraint applied here).
    "palette": {
        "navy": "#011627", "navy_deep": "#010B14",
        "primary": "#23D6C7", "secondary": "#698A9F",
        "accent": "#ED793B", "mint": "#23D6C7",
    },
    "products": [
        # name, order, balance_type, bal_base, yield(gross margin), funding
        # (0 -- fee-only), fee_base (MONTHLY $MM), provision(delivery-risk
        # reserve), delinq(churn/non-renewal rate), opex_ratio, growth,
        # units_base, phase, tagline, rate_label, goal_pct, status
        ("Movement", 1, "Usage-Based", 62, .60, 0.0, 1.2, .0030, .020,
         .16, .14, 850, 0.2, "Global anonymized GPS ping pipeline, 10B+ signals/day",
         "Gross margin", .98, "On plan"),
        ("Visits", 2, "Usage-Based", 34, .72, 0.0, 0.9, .0025, .022,
         .18, .20, 420, 1.0, "ML-modeled foot-traffic & POI visitation",
         "Gross margin", 1.04, "Ahead"),
        ("Trade Area & Site Selection", 3, "Subscription", 16, .75, 0.0, 0.4, .0020, .026,
         .20, .17, 140, 1.6, "Retail & real estate expansion analytics",
         "Gross margin", .96, "On plan"),
        ("Advertising & Media Measurement", 4, "Usage-Based", 26, .46, 0.0, 0.7, .0040, .034,
         .24, .10, 310, 0.6, "Ad-tech attribution & audience measurement feed",
         "Gross margin", .90, "Behind"),
        ("Financial & Alt-Data", 5, "Subscription", 9, .82, 0.0, 0.35, .0015, .012,
         .13, .26, 45, 2.0, "Alt-data feeds for hedge funds & equity research",
         "Gross margin", 1.12, "Ahead"),
        ("Government & Urban Planning", 6, "Subscription", 10, .55, 0.0, 0.25, .0020, .016,
         .17, .07, 60, 1.3, "Public-sector mobility & census-adjacent analytics",
         "Gross margin", .99, "On plan"),
    ],
    "subs": {
        "Movement": [("Core ping feed", .620, 10, 22.4, "On plan"),
                     ("Historical archive", .240, -20, 8.2, "Behind"),
                     ("Real-time streaming add-on", .140, 60, 12.6, "Ahead")],
        "Visits": [("POI visit attribution", .680, 15, 18.4, "Ahead"),
                   ("Trade-area overlays", .320, -10, 6.2, "On plan")],
        "Trade Area & Site Selection": [("Site selection scoring", .580, 20, 8.6, "Ahead"),
                                        ("Cannibalization modeling", .420, -15, 4.4, "On plan")],
        "Advertising & Media Measurement": [("Attribution feed", .640, -25, -2.4, "Behind"),
                                            ("Audience segments", .360, 30, 6.8, "On plan")],
        "Financial & Alt-Data": [("Hedge fund feeds", .700, 45, 12.2, "Ahead"),
                                 ("Equity research add-on", .300, 20, 4.6, "On plan")],
        "Government & Urban Planning": [("Census-adjacent studies", .560, 5, 4.8, "On plan"),
                                        ("Transportation planning", .440, -10, 2.2, "Behind")],
    },
    "alerts": [
        ("critical", "Largest device panel partner renewal at risk",
         "Top SDK-partner contract representing 18% of device panel coverage "
         "up for renewal with a competing bidder", "31m ago",
         "Partnerships", 18, "pct of panel coverage"),
        ("warning", "iOS ATT opt-in rate drift",
         "App Tracking Transparency opt-in rate down 260 bps against plan, "
         "thinning device panel density in 4 top metro markets", "2h ago",
         "Data Operations", 260, "bps below plan"),
        ("warning", "Ad-tech pricing compression",
         "Two hyperscaler resellers renegotiated per-record pricing down "
         "12% at last renewal", "5h ago", "Advertising & Media Measurement",
         12, "pct price compression"),
        ("info", "Alt-data demand surge",
         "Inbound hedge-fund and equity-research pipeline up 34% quarter over "
         "quarter", "1d ago", "Financial & Alt-Data", 34, "pct QoQ growth"),
        ("info", "New country coverage live",
         "Device panel coverage extended to 6 additional countries in "
         "Southeast Asia", "2d ago", "Data Operations", 6, "new countries"),
    ],
    "agent": ("You are an analyst covering Veraset's Movement, Visits, Trade Area, "
              "Advertising, Financial Alt-Data and Government data products, gross "
              "margin trends and device-panel/churn risk. Answer with numbers from "
              "the workbook."),
}

# HQ in San Francisco; footprint weighted toward enterprise-customer
# concentration (finance, adtech, retail hubs) rather than device coverage,
# since the base table's geography represents customer/contract location.
FOOTPRINTS["veraset"] = [("CA", .180), ("NY", .142), ("TX", .086), ("IL", .068),
                         ("MA", .062), ("WA", .058), ("FL", .052), ("GA", .046),
                         ("VA", .042), ("CO", .038), ("NJ", .034), ("PA", .030),
                         ("OH", .026), ("NC", .022), ("AZ", .018)]

LABELS["veraset"] = {
    "personas": ["Executive", "Partner Success"],
    "modeler_page": "Contract Renewal Planning",
    "cohort_page": "Customer Segments",
    "modeler_title": "Data License Renewal & Pricing Scenario Modeler",
    "shock_label": "Per-record pricing shock (bps)",
    "kpi_revenue": "Revenue ($M)",
    "kpi_margin": "Gross profit ($M)",
    "kpi_volume": "Licensed volume ($M)",
    "kpi_units": "Devices covered (M)",
    "driver_nim": "Gross margin",
    "driver_risk": "Churn / non-renewal rate",
    "driver_cost": "Cost to deliver rate",
    "driver_eff": "Opex ratio",
    "seg_product": "Data product",
    "seg_credit": "Customer tier",
    "seg_type": "Contract type",
    "seg_dd": "Direct enterprise account",
    "seg_engage": "Renewal cadence",
    "seg_held": "Data products licensed",
    "seg_age": "Contract age",
    "cohort_name": "Segment name",
    "kpi_cohort_size": "Accounts in segment",
    "kpi_cohort_vol": "Annual contract value",
    "kpi_cohort_rev": "ACV per account",
    "kpi_cohort_risk": "Avg churn risk",
    "col_volume": "Baseline licensed volume",
    "col_growth": "Volume growth %",
    "col_yield": "Gross margin Δ bps",
    "col_cost": "Cost to deliver Δ bps",
}

SEGMENTS["veraset"] = {"Near Prime": "Emerging", "Prime": "Growth",
                       "Super Prime": "Enterprise", "Exceptional": "Strategic",
                       "Daily": "Active", "Weekly": "Recurring",
                       "Monthly": "Occasional", "Dormant": "Churned"}

VOCAB["veraset"] = {
    "econ": ("Veraset licenses anonymized location data as a subscription or "
             "usage-based feed; each data product earns a gross margin against "
             "its cost to source, cleanse and deliver the underlying device "
             "signal. The spread between licensing revenue and delivery cost "
             "is the gross profit the product contributes before opex."),
    "metrics": ("revenue, gross profit, licensed data volume and churn/"
                "non-renewal risk"),
    "bands": ("Customer tiers: Emerging, Growth, Enterprise, Strategic. "
              "Renewal cadence: Active, Recurring, Occasional, Churned."),
    "cohort_report": ("accounts in the segment, annual contract value and "
                      "average churn risk"),
}

# Per-account annual contract value, in DOLLARS -- an enterprise data-license
# customer runs from a small startup feed to a strategic hyperscale account,
# nothing like a retail-banking balance, so this must override the default.
POP["veraset"] = {"bases": (18000, 85000, 420000, 1850000), "rev_rate": 0.62,
                  "fee_per_product": 22000}

# Plugin-free for this build per explicit request (quick build, cohort-only
# surfaces) -- no bespoke plugin authored this session.
PLUGINS["veraset"] = {"hero": None, "hero_label": None, "ticker": None}

COMPANIES["veraset"] = VERASET


# ---------------------------------------------------------------------------
# P&C mutual insurer. Command-center-only build (no scenario modeler, no
# cohort builder) plus a bespoke plugin and a bolt-on Underwriting Approval
# Workflow page (see patch_enumclaw_approvals.py) instead. The mapping:
#
#   products      -> lines of business (Homeowners, Auto, Farm & Ranch...)
#   bal_base      -> earned premium base ($MM) -- unlike a payer, premium
#                    itself IS the volume, so yield_rate is pinned to 1.00
#                    for every line (premium = exposure at par)
#   funding_rate  -> loss ratio (the line's "cost of goods")
#   opex_ratio    -> expense ratio (acquisition + G&A)
#   spread + opex -> combined ratio = funding_rate + opex_ratio, target ~96%
#   delinq/"risk" -> claim frequency
#   fee_base      -> policy & endorsement fees (MONTHLY $MM)
#
# Real anchors (2024 report, web-verified): ~$467M gross premium, ~96-100%
# combined ratio, ~66% loss ratio, 5-state footprint WA/OR/ID/UT/AZ. bal_base
# sums to 468 by construction to land on the real premium figure directly.
# ---------------------------------------------------------------------------
ENUMCLAW = {
    "key": "enumclaw",
    "name": "Mutual of Enumclaw",
    "title": "Book of Business & Underwriting Command Center",
    "domain": "P&C mutual insurance",
    "unit_noun": "policyholder",
    "volume_noun": "earned premium",
    "logo_domain": "mutualofenumclaw.com",
    "base_table": "Policy Book",
    # real evergreen off mutualofenumclaw.com, deepened for a dark header
    "palette": {
        "navy": "#0C2118", "navy_deep": "#061109",
        "primary": "#005424", "secondary": "#1F7A44",
        "accent": "#4CA771", "mint": "#00A69C",
    },
    "products": [
        # name, order, balance_type, bal_base($MM premium), yield(=1.00, premium
        # at par), funding(loss ratio + expense ratio combined -- the shared
        # loan_book.sql computes Opex as a % of the SPREAD, not of premium, so
        # folding the expense ratio into funding_rate directly against a yield
        # of 1.00 is what makes funding_rate == combined ratio and the spread
        # == underwriting margin, matching real P&C reporting), fee_base
        # (MONTHLY $MM), provision(LAE/reserve rate), delinq(claim frequency),
        # opex_ratio(0 -- already folded into funding above), growth,
        # units_base(policies in force, K), phase, tagline, rate_label,
        # goal_pct, status
        ("Homeowners", 1, "Property", 159, 1.00, .94, 1.2, .05, .06,
         0.0, .045, 62, 0.0, "Owner-occupied dwelling & property",
         "Avg Premium/Policy", .96, "On plan"),
        ("Personal Auto", 2, "Auto", 131, 1.00, 1.00, 0.9, .04, .09,
         0.0, .028, 74, 1.1, "Liability, collision & comprehensive",
         "Avg Premium/Policy", .91, "Behind"),
        ("Farm & Ranch", 3, "Property", 75, 1.00, .90, 0.5, .06, .05,
         0.0, .052, 18, 2.2, "Farm dwelling, equipment & liability",
         "Avg Premium/Policy", 1.04, "Ahead"),
        ("Commercial Multi-Peril", 4, "Commercial", 65, 1.00, .98, 0.6, .07, .04,
         0.0, .061, 9, 0.6, "Small & mid-market business package",
         "Avg Premium/Policy", .98, "On plan"),
        ("Umbrella", 5, "Excess Liability", 19, 1.00, .77, 0.15, .03, .02,
         0.0, .038, 22, 1.7, "Personal excess liability",
         "Avg Premium/Policy", 1.06, "Ahead"),
        ("Specialty Lines", 6, "Specialty", 19, 1.00, .84, 0.15, .04, .03,
         0.0, .034, 11, 2.8, "Watercraft, RV & scheduled valuables",
         "Avg Premium/Policy", 1.01, "On plan"),
    ],
    "alerts": [
        ("critical", "Combined ratio breach",
         "Personal Auto combined ratio hit 101.4%, above the 98% pricing plan",
         "24m ago", "Actuarial", 140, "bps over plan"),
        ("critical", "Catastrophe claim cluster",
         "68 new wind/hail claims filed across Eastern Washington in the last 48 hours",
         "3h ago", "Claims", 68, "claims filed"),
        ("warning", "Renewal retention drift",
         "Homeowners retention fell to 84.2%, below the 88% target",
         "5h ago", "Underwriting", 84, "% retention"),
        ("warning", "Rate filing pending",
         "Idaho Personal Auto rate filing (+6.8%) awaiting DOI approval",
         "1d ago", "Product", 7, "% filed increase"),
        ("info", "Reinsurance renewal bound",
         "2026 property cat-XL treaty renewed at expiring terms, $5M retention",
         "2d ago", "Reinsurance", 5, "$M retention"),
    ],
    "agent": ("You are an underwriting analyst covering Mutual of Enumclaw's "
              "Homeowners, Personal Auto, Farm & Ranch, Commercial, Umbrella "
              "and Specialty lines across Washington, Oregon, Idaho, Utah and "
              "Arizona. Answer with numbers from the workbook."),
}

ENUMCLAW["subs"] = {
    "Homeowners": [("HO-3 Special Form", .58, 20, 4.1, "On plan"),
                   ("HO-4 Renters", .14, -30, 8.2, "Ahead"),
                   ("HO-6 Condo", .16, 10, 2.4, "On plan"),
                   ("DP-3 Dwelling Fire", .12, -20, -1.8, "Behind")],
    "Personal Auto": [("Liability", .42, 30, -2.1, "Behind"),
                      ("Collision", .28, -15, 3.2, "On plan"),
                      ("Comprehensive", .18, 10, 5.6, "Ahead"),
                      ("UM/UIM", .12, -25, 1.1, "On plan")],
    "Farm & Ranch": [("Farm Dwelling", .38, -10, 2.2, "On plan"),
                     ("Farm Liability", .24, 15, 6.4, "Ahead"),
                     ("Farm Equipment", .22, -20, -3.1, "Behind"),
                     ("Livestock", .16, 25, 4.8, "Ahead")],
    "Commercial Multi-Peril": [("Property", .34, 10, 1.6, "On plan"),
                               ("General Liability", .30, -15, -2.4, "Behind"),
                               ("BOP", .22, 20, 5.2, "Ahead"),
                               ("Inland Marine", .14, -10, 3.0, "On plan")],
    "Umbrella": [("Personal Umbrella", .72, 15, 7.8, "Ahead"),
                ("Excess Liability", .28, -20, 2.4, "On plan")],
    "Specialty Lines": [("Watercraft", .42, 10, 3.6, "On plan"),
                        ("Recreational Vehicle", .34, -15, 5.2, "Ahead"),
                        ("Scheduled Valuables", .24, 20, -1.4, "Behind")],
}

FOOTPRINTS["enumclaw"] = [("WA", .58), ("OR", .16), ("ID", .12),
                          ("UT", .09), ("AZ", .05)]

LABELS["enumclaw"] = {
    "personas": ["Executive", "Underwriting"],
    "modeler_page": "Underwriting",
    "cohort_page": "Book Segments",
    "modeler_title": "Rate & Underwriting Scenario Modeler",
    "shock_label": "Rate change shock (%)",
    # kpi_revenue is ALWAYS bound to the shared "Net Revenue" column
    # (income - expense + fees, i.e. the SPREAD), and kpi_volume is ALWAYS
    # bound to "Avg Balances" (the raw bal_base, i.e. actual premium) --
    # see build_sofi.py's kpi_card() call sites. For a lender that spread IS
    # the headline number, but for an insurer with yield_rate pinned to 1.00
    # (premium at par), "Net Revenue" is premium-minus-losses-plus-fees, not
    # gross premium -- the same "Net Revenue is a spread, not income" trap
    # HANDOFF.md documents for Delta/NVIDIA. Labelled honestly instead of
    # relabelling the wrong number "Earned Premium".
    "kpi_revenue": "Net Underwriting Revenue ($M)",
    "kpi_margin": "Underwriting Margin ($M)",
    "kpi_volume": "Earned Premium ($M)",
    "kpi_units": "Policies in Force (K)",
    "driver_nim": "Underwriting Margin %",
    "driver_risk": "Claim Frequency",
    "driver_cost": "Combined Ratio",
    "driver_eff": "Expense Ratio",
    "seg_product": "Line of Business",
    "seg_credit": "Territory Risk Tier",
    "seg_type": "Coverage Type",
    "seg_dd": "Independent Agency",
    "seg_engage": "Policy Tenure",
    "seg_held": "Policies per Household",
    "seg_age": "Policy Age Band",
    "cohort_name": "Book segment name",
    "kpi_cohort_size": "Policies in segment",
    "kpi_cohort_vol": "Written premium",
    "kpi_cohort_rev": "Premium per policy",
    "kpi_cohort_risk": "Avg claim frequency",
    "col_volume": "Written Premium",
    "col_growth": "Premium Growth %",
    "col_yield": "Rate Δ bps",
    "col_cost": "Combined Ratio Δ bps",
}

SEGMENTS["enumclaw"] = {"Near Prime": "Standard", "Prime": "Preferred",
                        "Super Prime": "Select", "Exceptional": "Elite",
                        "Daily": "Frequent Claimant", "Weekly": "Occasional Claimant",
                        "Monthly": "Rare Claimant", "Dormant": "Claim-Free"}

VOCAB["enumclaw"] = {
    "econ": ("Each line of business earns premium against a loss rate and an "
             "expense ratio -- the spread between premium and losses plus "
             "expenses is the underwriting margin, and losses plus expenses "
             "over premium is the combined ratio."),
    "metrics": "earned premium, underwriting margin, loss ratio and combined ratio",
    "bands": ("Territory risk tiers: Standard, Preferred, Select, Elite. Claim "
              "frequency: Frequent Claimant, Occasional Claimant, Rare Claimant, "
              "Claim-Free."),
    "cohort_report": "book segment size, written premium and average claim frequency",
}

# Registered 2026-08-14 on papercranestaging via POST /v2/plugins, GitHub
# Pages host (cmiller-coder.github.io/millersigma/plugins/enumclaw-loss-triangle/).
PLUGINS["enumclaw"] = {"hero": "ae977e73-2d97-4fec-a505-a0eaaf7ba628",
                       "hero_label": "LOSS DEVELOPMENT TRIANGLE",
                       "ticker": None,
                       "hero_table": {"name": "Loss Triangle", "file": "loss_triangle.sql",
                                      "prefix": "h",
                                      "cols": ["Accident Year", "Development Period",
                                               "Cumulative Loss Ratio Pct"]},
                       "hero_config": {"accidentYear": "h0", "devPeriod": "h1",
                                       "lossRatio": "h2"}}

COMPANIES["enumclaw"] = ENUMCLAW


# ---------------------------------------------------------------------------
# Smart home fragrance / DTC subscription hardware. Cold-run test #2 for the
# funding_rate=0 "margin-only" pattern (same family as Veraset/NVIDIA/SoFi
# Money) -- deliberately chosen to dodge the "Net Revenue is a spread, not
# income" trap hit on Mutual of Enumclaw: with funding_rate pinned to 0,
# "Net Revenue" (income - expense + fee) collapses to bal_base*yield_rate,
# i.e. a genuine gross profit number, and "Avg Balances" (bal_base) is
# genuine revenue -- both KPI bindings are honest without any relabeling.
#
#   products      -> product lines (Fragrance Subscriptions, Home
#                    Diffusers, Car, Pura Air, Brand Marketplace, B2B)
#   bal_base      -> annual revenue for the line, in $MM (sums to the real
#                    ~$500M 2026 projected total)
#   yield_rate    -> gross margin % (funding_rate always 0 -- no COGS-as-a-
#                    rate-on-a-separate-exposure-base concept for a DTC
#                    subscription/hardware business)
#   provision     -> return/refund reserve rate (30-day risk-free trial)
#   delinq/"risk" -> churn / return rate
#   opex_ratio    -> variable opex (marketing, fulfillment) against gross
#                    profit -> Contribution Profit is a real DTC unit-
#                    economics number, not company-wide net income
# ---------------------------------------------------------------------------
PURA = {
    "key": "pura",
    "name": "Pura",
    "title": "Subscription & Device Performance Command Center",
    "domain": "smart home fragrance / DTC subscription hardware",
    "unit_noun": "household",
    "volume_noun": "revenue",
    "logo_domain": "pura.com",
    "base_table": "Subscription & Device Ledger",
    # sampled from pura.com's own page CSS: ink #1D1B1B, warm gold #CFA363/
    # #A6824F, deep brown #725A3E -- a warm minimal palette, not tech-navy
    "palette": {
        "navy": "#1D1B1B", "navy_deep": "#0F0E0E",
        "primary": "#CFA363", "secondary": "#A6824F",
        "accent": "#725A3E", "mint": "#8FA68E",
    },
    "products": [
        # name, order, balance_type, bal_base($MM revenue), yield(gross
        # margin %), funding(0 -- no separate exposure base), fee_base
        # (MONTHLY $MM, 0), provision(return/refund rate), delinq(churn/
        # return rate), opex_ratio(variable opex vs gross profit), growth,
        # units_base(subscribers/units/partners, K), phase, tagline,
        # rate_label, goal_pct, status
        ("Fragrance Subscriptions", 1, "Subscription", 325, .72, 0.0, 0.0, .02, .055,
         .38, .14, 1900, 0.0, "Recurring vial & refill subscriptions across the installed base",
         "Gross Margin", .97, "On plan"),
        ("Home Diffusers", 2, "Hardware", 80, .32, 0.0, 0.0, .03, .08,
         .30, .08, 850, 1.1, "Home, Home Mini & Home Plus smart diffusers",
         "Gross Margin", .93, "Behind"),
        ("Car Diffusers", 3, "Hardware", 25, .38, 0.0, 0.0, .025, .07,
         .28, .18, 300, 2.2, "Smart diffusers for vehicles",
         "Gross Margin", 1.05, "Ahead"),
        ("Pura Air", 4, "Hardware", 20, .40, 0.0, 0.0, .02, .05,
         .34, .65, 180, 0.6, "HEPA-like filtration + fragrance, launched 2026",
         "Gross Margin", 1.18, "Ahead"),
        ("Brand Marketplace", 5, "Marketplace", 35, .42, 0.0, 0.0, .015, .04,
         .26, .20, 410, 1.7, "300+ fragrances from NEST, Capri Blue, Disney, Anthropologie & 100+ brand partners",
         "Gross Margin", 1.02, "On plan"),
        ("B2B Licensing", 6, "Licensing", 15, .62, 0.0, 0.0, .01, .03,
         .22, .35, 45, 2.8, "White-label smart-diffuser tech licensing to hospitality & other brands",
         "Gross Margin", 1.09, "Ahead"),
    ],
    "alerts": [
        ("critical", "Home Diffuser margin compression",
         "Home hardware gross margin fell to 29.4%, below the 32% pricing plan amid component cost inflation",
         "26m ago", "Supply Chain", 260, "bps under plan"),
        ("warning", "Subscription churn drift",
         "Fragrance Subscriptions churn ticked up to 6.1%, above the 5.5% target after the Q2 price adjustment",
         "3h ago", "Retention", 60, "bps over target"),
        ("warning", "Pura Air fulfillment backlog",
         "2,400 Pura Air pre-orders past the 2-week ship SLA amid HEPA filter supply constraints",
         "5h ago", "Operations", 2400, "orders past SLA"),
        ("info", "New brand partner signed",
         "Otherland joins the Marketplace, Pura's 100th+ active fragrance brand partnership",
         "1d ago", "Partnerships", 100, "active brand partners"),
        ("info", "Retail distribution expansion",
         "Target expanded Pura's shelf placement to 380 additional stores this quarter",
         "2d ago", "Retail", 380, "new stores"),
    ],
    "agent": ("You are a DTC/subscription analyst covering Pura's smart fragrance "
              "diffusers, subscription vial economics, and brand-partner marketplace "
              "across Home, Car, and Pura Air product lines. Answer with numbers from "
              "the workbook."),
}

PURA["subs"] = {
    "Fragrance Subscriptions": [("Monthly Vial Plan", .58, 20, 8.2, "Ahead"),
                                ("Bi-Monthly Plan", .24, -15, 3.4, "On plan"),
                                ("Gifting & One-Time", .12, 30, -4.2, "Behind"),
                                ("Car Refill Add-on", .06, -10, 6.8, "On plan")],
    "Home Diffusers": [("Home (Medium Room)", .48, 10, 2.2, "On plan"),
                       ("Home Mini", .30, -20, 5.6, "Ahead"),
                       ("Home Plus (Large Room)", .22, 15, -3.1, "Behind")],
    "Car Diffusers": [("Car Standard", .68, -10, 4.4, "On plan"),
                      ("Car Vent Clip", .32, 20, 8.1, "Ahead")],
    "Pura Air": [("Pura Air Standard", .70, 25, 12.4, "Ahead"),
                ("Pura Air Filter Refills", .30, -15, 18.6, "Ahead")],
    "Brand Marketplace": [("NEST New York", .18, 10, 4.2, "On plan"),
                          ("Capri Blue", .16, -10, 3.8, "On plan"),
                          ("Disney Collection", .14, 30, 9.6, "Ahead"),
                          ("Anthropologie", .12, -15, -2.4, "Behind"),
                          ("Other 100+ Partners", .40, 5, 6.1, "On plan")],
    "B2B Licensing": [("Hospitality Licensing", .55, 20, 14.2, "Ahead"),
                      ("White-Label OEM", .45, -10, 8.4, "On plan")],
}

FOOTPRINTS["pura"] = [("CA", .142), ("TX", .098), ("FL", .086), ("NY", .071),
                      ("IL", .052), ("TN", .048), ("UT", .045), ("GA", .041),
                      ("AZ", .038), ("CO", .036), ("NC", .033), ("WA", .031),
                      ("OH", .028), ("NJ", .024), ("MA", .021)]

LABELS["pura"] = {
    "personas": ["Executive", "Brand & Growth"],
    "modeler_page": "Pricing & Growth",
    "cohort_page": "Household Segments",
    "modeler_title": "Pricing & Subscriber Growth Scenario Modeler",
    "shock_label": "Subscription price change (%)",
    "kpi_revenue": "Gross Profit ($M)",
    "kpi_margin": "Contribution Profit ($M)",
    "kpi_volume": "Revenue ($M)",
    "kpi_units": "Active Subscribers (K)",
    "driver_nim": "Contribution Margin %",
    "driver_risk": "Churn / Return Rate",
    "driver_cost": "Variable Opex Ratio",
    "driver_eff": "Fulfillment Efficiency",
    "seg_product": "Product Line",
    "seg_credit": "Subscriber Tier",
    "seg_type": "Fragrance Category",
    "seg_dd": "Auto-Refill Enabled",
    "seg_engage": "Usage Frequency",
    "seg_held": "Devices per Household",
    "seg_age": "Subscriber Tenure",
    "cohort_name": "Household segment name",
    "kpi_cohort_size": "Households in segment",
    "kpi_cohort_vol": "Annual fragrance spend",
    "kpi_cohort_rev": "Revenue per household",
    "kpi_cohort_risk": "Avg churn risk",
    "col_volume": "Revenue",
    "col_growth": "Revenue Growth %",
    "col_yield": "Margin Δ bps",
    "col_cost": "Opex Δ bps",
}

SEGMENTS["pura"] = {"Near Prime": "New Subscriber", "Prime": "Growing Household",
                    "Super Prime": "Loyal Multi-Room", "Exceptional": "VIP Whole-Home",
                    "Daily": "Daily Use", "Weekly": "Weekly Use",
                    "Monthly": "Monthly Use", "Dormant": "Inactive"}

VOCAB["pura"] = {
    "econ": ("Fragrance Subscriptions and Brand Marketplace vials earn a high gross "
             "margin against modest fulfillment cost; Home, Car and Pura Air hardware "
             "earn a thinner margin since devices are often priced near cost to drive "
             "subscription attach. B2B Licensing earns the richest margin at the "
             "lowest volume."),
    "metrics": "revenue, gross profit, contribution profit and churn/return rate",
    "bands": ("Subscriber tiers: New Subscriber, Growing Household, Loyal Multi-Room, "
              "VIP Whole-Home. Usage frequency: Daily Use, Weekly Use, Monthly Use, Inactive."),
    "cohort_report": "households in segment, annual fragrance spend and average churn risk",
}

POP["pura"] = {"bases": (80, 180, 350, 750), "rev_rate": 0.65, "fee_per_product": 25}

# No bespoke plugin this build (explicit ask) -- native fallback wheel renders instead.
PLUGINS["pura"] = {"hero": None, "hero_label": None, "ticker": None}

COMPANIES["pura"] = PURA

# --- Sigma Motors -- statement-only entry (no workbook build via this skill) -
# The Sigma Motors command center (EV/Hybrid demand, backlog, scenario modeler)
# already exists as its own hand-built workbook, not one generated by this
# skill's build_sofi.py. This entry exists ONLY so build_statement.py can
# produce a companion pixel-perfect PDF -- palette pulled directly from that
# live workbook's own brand colors (navy header, blue accent, green "good"),
# not invented fresh. logo_domain is unused (Sigma Motors is fictional, no
# real site to fetch from) -- assets/sigma_motors_logo_{navy,white}.datauri.txt
# were extracted from the live workbook's own header image via Playwright.
SIGMA_MOTORS = {
    "key": "sigma_motors",
    "name": "Sigma Motors",
    "logo_domain": "sigmamotors.example.com",
    "palette": {
        "navy": "#0B1B3A", "navy_deep": "#071022",
        "primary": "#1B4FD6", "secondary": "#0F9F6E",
        "accent": "#7FA3E8", "mint": "#0F9F6E",
    },
}
COMPANIES["sigma_motors"] = SIGMA_MOTORS

# ---------------------------------------------------------------------------
# Fox Corporation (FOXA) -- broadcast & cable media conglomerate. Real 10-K
# segment structure: Cable Network Programming (FOX News Media, FS1/FS2, the
# Big Ten Network) and Television (the FOX broadcast network, owned & operated
# stations, Tubi AVOD). "Products" here are the real properties within each
# segment, not the two statutory segments themselves -- same choice BofA made
# (six lines of business inside two segments) so the persona tabs and product
# cards have something to differentiate.
#
#   product -> network / property (tagged with its real 10-K segment)
#   volume  -> a notional distribution & advertising base ($MM) -- there is no
#              single public "system-wide sales" analog for media the way
#              there is for a franchisor, so this plays that role
#   yield   -> blended monetization rate (affiliate + retrans + advertising)
#   cost    -> programming & content cost rate against that same base
#   spread  -> segment operating income -- a real, disclosed media metric,
#              NOT total revenue (see the Delta/NVIDIA spread trap in
#              HANDOFF.md sec 8 -- this is the same shape, mapped correctly
#              up front instead of getting caught by render)
#   fee     -> small ancillary revenue: digital licensing & syndication
#              (MONTHLY, $MM -- the ×12 trap that hit Nuvia)
#   risk    -> affiliate subscriber erosion / cord-cutting (delinq_rate)
#   shock   -> ad market / upfront pricing shock (bps), same cross-join
#              modeler as every other company, unchanged
#
# Tubi is fee-only in spirit (ad-supported, no affiliate/retrans fee) but is
# NOT modeled as yield=funding=0 the way SoFi Money is -- its ad revenue has
# real content-acquisition and ad-tech cost against it, so it gets a genuine
# (thin) yield/funding spread instead, the same as every other property.
#
# Scale sanity check against the real FY2024 10-K (fiscal Q1-Q4 revenues of
# $3.21B + $4.23B + $3.45B + $3.09B = ~$14.0B; Cable Network Programming ~43-45%
# of revenue, Television ~55-57%; quarterly adjusted EBITDA of $869M + $350M +
# $891M + $773M = ~$2.9B, ~21% margin) -- see the products list below for the
# per-property revenue and margin build-up.
# ---------------------------------------------------------------------------
FOXMEDIA = {
    "key": "foxmedia",
    "name": "Fox Corporation",
    "title": "Network Portfolio & Distribution Command Center",
    "domain": "broadcast & cable media conglomerate",
    "unit_noun": "viewer",
    "volume_noun": "distribution & advertising base",
    "logo_domain": "foxnewsmedia.com",
    # Fox News Media's real mark is a two-tone blue/red block with white
    # wordmark baked in -- recolouring it solid white (the default treatment)
    # makes the wordmark unreadable. Keep it in its real colours on a white
    # chip instead, the same exception already established for eBay (see
    # HANDOFF.md sec 17).
    "logo_chip": True,
    "base_table": "Programming Ledger",
    # sampled from foxcorporation.com's own site CSS, not guessed: #001D3D navy
    # and #BD232F red are the two most-repeated hexes on the page; #004C97 and
    # #00B9EA are the secondary/accent blues actually in use there too.
    "palette": {
        "navy": "#001D3D", "navy_deep": "#000F1F",
        "primary": "#BD232F", "secondary": "#004C97",
        "accent": "#00B9EA", "mint": "#0EA394",
    },
    "products": [
        # name, order, balance_type, bal_base, yield, funding, fee_base,
        # provision, delinq, opex_ratio, growth, units_base, phase, tagline,
        # rate_label, goal_pct, status
        ("FOX News Media", 1, "Cable Network Programming", 7000, .600, .330, 15.0,
         .005, .014, .09, .022, 210, 0.0,
         "FOX News, FOX Business & digital news properties",
         "Monetization rate", 1.028, "Ahead"),
        ("FS1/FS2", 2, "Cable Network Programming", 2180, .550, .4125, 8.0,
         .008, .022, .12, .015, 95, 1.1,
         "National & regional sports cable networks",
         "Monetization rate", .968, "On plan"),
        ("Big Ten Network", 3, "Cable Network Programming", 700, .500, .400, 3.0,
         .010, .028, .14, .008, 40, 2.2,
         "Big Ten Conference football & Olympic sports",
         "Monetization rate", .914, "Behind"),
        ("FOX Network", 4, "Television", 11700, .350, .308, 10.0,
         .006, .042, .08, .006, 480, 0.6,
         "Broadcast network — NFL, MLB, college football, primetime",
         "Monetization rate", .952, "On plan"),
        ("Owned Television Stations", 5, "Television", 6000, .450, .2925, 12.0,
         .007, .031, .10, .028, 260, 1.7,
         "29 owned-and-operated stations in major U.S. markets",
         "Monetization rate", 1.041, "Ahead"),
        ("Tubi", 6, "Television", 4000, .400, .360, 5.0,
         .004, .009, .19, .145, 690, 2.8,
         "Free ad-supported streaming (AVOD), fastest-growing property",
         "Monetization rate", 1.128, "Ahead"),
    ],
    "alerts": [
        ("critical", "Big Ten Network carriage lapse",
         "Two regional MVPDs let BTN carriage lapse ahead of the September "
         "kickoff window", "22m ago", "Affiliate Relations", 2, "MVPDs uncarried"),
        ("critical", "National upfront pricing miss",
         "Cable Network Programming upfront CPMs closed 6.2% below the spring "
         "pricing guide", "48m ago", "Ad Sales", 620, "bps below guide"),
        ("warning", "Tubi header-bidding latency",
         "CTV auction latency above the 250ms SLA on 8.4% of Tubi ad impressions",
         "2h ago", "AdTech Ops", 8.4, "% impressions over SLA"),
        ("warning", "Owned-station political pacing",
         "3 owned stations tracking below plan on election-cycle local ad pacing",
         "5h ago", "Station Group", 3, "stations below pacing"),
        ("info", "Retransmission renewal signed",
         "A top-10 MVPD renewed Television retransmission consent at a step-up "
         "rate", "1d ago", "Affiliate Relations", 1, "MVPD renewed"),
    ],
    "agent": ("You are an analyst covering Fox Corporation's Cable Network "
              "Programming and Television segments — affiliate and subscription "
              "fees, advertising revenue and retransmission consent economics "
              "across FOX News Media, FS1/FS2, the Big Ten Network, the FOX "
              "broadcast network, owned stations and Tubi."),
}

FOXMEDIA["subs"] = {
    "FOX News Media": [("FOX News Channel", .58, -20, 4.2, "Ahead"),
                       ("FOX Business", .14, 10, 1.8, "On plan"),
                       ("Digital & FOX Nation", .16, 30, 12.4, "Ahead"),
                       ("FOX Weather", .12, 50, 8.6, "On plan")],
    "FS1/FS2": [("FS1 national windows", .62, -10, 3.1, "On plan"),
               ("FS2 regional", .24, 20, -1.4, "Behind"),
               ("MLB/NASCAR windows", .14, 40, 6.8, "Ahead")],
    "Big Ten Network": [("Football Saturdays", .48, -15, -2.2, "Behind"),
                        ("Basketball", .28, 15, 1.4, "On plan"),
                        ("Olympic sports", .16, 35, 0.8, "On plan"),
                        ("BTN2Go digital", .08, 55, 9.6, "Ahead")],
    "FOX Network": [("NFL Sunday/Thursday", .42, -20, 2.4, "Ahead"),
                    ("MLB postseason", .12, 10, -3.1, "Behind"),
                    ("Primetime entertainment", .28, 25, -5.4, "Behind"),
                    ("College football", .18, 40, 4.8, "Ahead")],
    "Owned Television Stations": [("Local news", .38, -10, 1.6, "On plan"),
                                  ("Retransmission consent", .34, 0, 5.2, "Ahead"),
                                  ("Syndicated programming", .18, 30, -2.8, "Behind"),
                                  ("Local political & spot", .10, 45, 14.2, "Ahead")],
    "Tubi": [("Connected TV (CTV)", .64, -15, 22.4, "Ahead"),
            ("Mobile app", .22, 10, 9.8, "On plan"),
            ("Web", .09, 35, -1.2, "Behind"),
            ("FAST channels", .05, 55, 18.6, "Ahead")],
}

# Real Fox owned-station / major-DMA footprint, weighted toward the biggest
# markets Fox actually operates stations in.
FOOTPRINTS["foxmedia"] = [("CA", .150), ("NY", .118), ("TX", .096), ("IL", .072),
                          ("PA", .058), ("GA", .052), ("AZ", .046), ("MI", .042),
                          ("MN", .038), ("FL", .036), ("WA", .032), ("MO", .028),
                          ("WI", .024), ("UT", .020), ("NC", .018)]

LABELS["foxmedia"] = {
    "personas": ["Executive", "Content & Distribution"],
    "modeler_page": "Ad Market Planning",
    "cohort_page": "Audience Segments",
    "modeler_title": "Ad Market & Affiliate Rate Scenario Modeler",
    "shock_label": "Ad market / upfront pricing shock (bps)",
    "kpi_revenue": "Segment operating income ($M)",
    "kpi_margin": "Contribution ($M)",
    "kpi_volume": "Distribution & ad base ($M)",
    "kpi_units": "Avg monthly viewers (M)",
    "driver_nim": "Content margin, revenue less programming cost",
    "driver_risk": "Affiliate subscriber erosion",
    "driver_cost": "Programming & content cost rate",
    "driver_eff": "SG&A ratio",
    "seg_product": "Network / Segment",
    "seg_credit": "Viewer tier",
    "seg_dd": "TV Everywhere authenticated",
    "seg_engage": "Viewing frequency",
    "seg_held": "Networks watched",
    "cohort_name": "Audience segment name",
    "kpi_cohort_size": "Viewers in segment",
    "kpi_cohort_vol": "Attributable annual value ($)",
    "kpi_cohort_rev": "Value per viewer ($)",
    "kpi_cohort_risk": "Avg churn risk",
    "col_volume": "Baseline distribution base",
    "col_growth": "Distribution base growth %",
    "col_yield": "Monetization rate Δ bps",
    "col_cost": "Programming cost Δ bps",
}

SEGMENTS["foxmedia"] = {"Near Prime": "Casual Viewer", "Prime": "Regular Viewer",
                        "Super Prime": "Core Viewer", "Exceptional": "Superfan",
                        "Daily": "Daily Viewer", "Weekly": "Weekly Viewer",
                        "Monthly": "Monthly Viewer", "Dormant": "Lapsed Viewer"}

VOCAB["foxmedia"] = {
    "econ": ("Cable Network Programming and Television both earn affiliate and "
             "retransmission consent fees against a programming and content cost "
             "base, plus advertising revenue sold on a CPM basis; Tubi earns "
             "advertising revenue only, with no affiliate or retransmission fee."),
    "metrics": ("segment operating income, contribution, distribution & ad base "
                "and average monthly viewers"),
    "bands": ("Viewer tiers: Casual Viewer, Regular Viewer, Core Viewer, "
              "Superfan. Viewing frequency: Daily Viewer, Weekly Viewer, "
              "Monthly Viewer, Lapsed Viewer."),
    "cohort_report": "segment size, attributable annual value and average churn risk",
}

POP["foxmedia"] = {"bases": (8, 35, 85, 180), "rev_rate": 0.24, "fee_per_product": 5}

# Media has no existing plugin in this generator's industry table -- a ratings
# heatmap by network x daypart is the domain-specific hero, not a reskinned
# flywheel/ticker from another industry. Bound to its own source table (needs
# daypart granularity the product-card table doesn't carry) -- same pattern as
# Delta's hub_banks_sql. hero/pluginId is filled in once the plugin is pushed
# to GitHub Pages and registered via POST /v2/plugins (see HANDOFF.md sec 9).
PLUGINS["foxmedia"] = {
    "hero": None,  # TODO: set once registered -- see build notes
    "hero_label": "NETWORK x DAYPART RATINGS",
    "ticker": None,
    "hero_table": {"name": "Daypart Ratings", "file": "daypart_ratings.sql",
                   "prefix": "h", "cols": ["Network", "Daypart", "RatingIndex",
                                           "SellThroughPct", "Status"]},
    "hero_config": {"network": "h0", "daypart": "h1", "rating": "h2",
                    "sellthrough": "h3", "status": "h4"},
}

COMPANIES["foxmedia"] = FOXMEDIA


def daypart_ratings_sql(cfg):
    """Network x daypart ratings-index and ad sell-through, for the bespoke
    hero plugin. Explicit UNION ALL, pure config (no __PRODUCTS__/__STATES__
    substitution) -- same shape as hub_banks_sql / branch_performance_sql."""
    dayparts = ["Early Morning", "Daytime", "Early Fringe", "Primetime", "Late Night"]
    data = {
        "FOX News Media": [(128.4, 92.1, "Ahead"), (104.2, 86.4, "On plan"),
                           (111.6, 89.7, "Ahead"), (142.8, 96.3, "Ahead"),
                           (96.4, 81.2, "On plan")],
        "FS1/FS2": [(82.6, 74.8, "Behind"), (91.3, 79.5, "On plan"),
                   (118.7, 90.2, "Ahead"), (124.5, 93.6, "Ahead"),
                   (88.9, 77.3, "Behind")],
        "Big Ten Network": [(71.2, 68.4, "Behind"), (84.6, 75.1, "Behind"),
                            (96.8, 82.9, "On plan"), (118.3, 88.6, "Ahead"),
                            (79.4, 70.2, "Behind")],
        "FOX Network": [(89.7, 80.3, "On plan"), (93.5, 81.9, "On plan"),
                        (121.4, 91.8, "Ahead"), (156.2, 98.4, "Ahead"),
                        (97.8, 85.6, "On plan")],
        "Owned Television Stations": [(108.6, 87.2, "Ahead"), (95.3, 83.1, "On plan"),
                                      (132.7, 94.5, "Ahead"), (119.4, 90.8, "Ahead"),
                                      (102.1, 85.9, "On plan")],
        "Tubi": [(68.4, 71.2, "Behind"), (86.7, 79.8, "On plan"),
                (97.5, 84.3, "On plan"), (112.8, 89.1, "Ahead"),
                (106.3, 86.7, "Ahead")],
    }
    rows = []
    for net, vals in data.items():
        for dp, (rating, sellthrough, status) in zip(dayparts, vals):
            lead = "SELECT" if not rows else "UNION ALL SELECT"
            cols = ("" if rows else
                    ' AS "Network", %s AS "Daypart", %s AS "RatingIndex",'
                    ' %s AS "SellThroughPct", %s AS "Status"')
            if not rows:
                rows.append("    %s '%s'%s" % (lead, net, cols % (
                    "'%s'" % dp, rating, sellthrough, "'%s'" % status)))
            else:
                rows.append("    %s '%s', '%s', %s, %s, '%s'"
                            % (lead, net, dp, rating, sellthrough, status))
    return "SELECT * FROM (\n" + "\n".join(rows) + "\n) AS daypart_ratings"


STATEMENTS["foxmedia"] = {
    "spec_name": "Fox Corporation — Affiliate & Distribution Statement (July 2026)",
    "page_name": "Distribution Statement",
    "manage_url": "foxcorporation.com/affiliates",
    "service_label": "Affiliate Relations",
    "service_phone": "1-844-369-3467",
    "period": "07/01 – 07/31/2026",
    "sect_rewards": "AD INVENTORY SUMMARY",
    "sect_summary": "CARRIAGE SUMMARY",
    "sect_category": "REVENUE BY CATEGORY",
    "sect_activity": "BILLING ACTIVITY",
    "sect_messages": "YOUR DISTRIBUTION MESSAGES",
    "headline": [("Amount Due", None), ("Retransmission Fees", None),
                 ("Agreement Renewal Date", "12/31/2026")],
    "button_label": "Distribution statement ↗",
    "rewards_total": "Total ad impressions delivered",
    "h_formulas": [("src", 'Sum([Statement Activity/Amount])', "MONEY"),
                   ("src", 'SumIf([Statement Activity/Amount], '
                    '[Statement Activity/Category] = "Retransmission Consent")',
                    "MONEY0")],
    "msg_body": ("Beginning 01/01/2027, the Cable Network Programming affiliate "
                 "rate for FOX News Media and FS1/FS2 increases under the terms "
                 "of the renewed carriage agreement, with the Big Ten Network "
                 "moving to a per-subscriber step-up tied to conference football "
                 "season. Retransmission consent rates for the Television "
                 "segment's owned stations increase on the same schedule. No "
                 "action is required; the new rates apply automatically to your "
                 "next billing cycle."),
    "warn1": ("**Carriage Renewal Notice:** This agreement is subject to renewal "
              "terms filed with the FCC. Failure to renew before the expiration "
              "date listed above may result in a service interruption (a "
              "\"blackout\") of Cable Network Programming and Television signals "
              "carried under this agreement."),
    "warn2": ("**Advertising Avail Notice:** National and local advertising "
              "avails are sold subject to sellout and audience-delivery "
              "guarantees. Make-good impressions are issued automatically when "
              "guaranteed delivery is not met and do not carry forward beyond "
              "two billing cycles."),
    "footer": ("Fox Corporation content is distributed under affiliate and "
               "retransmission consent agreements with pay-TV and streaming "
               "distributors. Illustrative distribution statement generated "
               "from a Sigma report specification — synthetic data, not a "
               "real account."),
}

_FM_ACTIVITY = [
    ("07/01", "07/02", "Cable Network Programming — Affiliate Fee (FOX News Media)",
     "Affiliate Fees", 428000.00, 0),
    ("07/01", "07/02", "Cable Network Programming — Affiliate Fee (FS1/FS2)",
     "Affiliate Fees", 186000.00, 0),
    ("07/05", "07/06", "Television — Retransmission Consent (Owned Stations)",
     "Retransmission Consent", 512000.00, 0),
    ("07/08", "07/09", "National Advertising — NFL on FOX Sunday Window",
     "National Advertising", 940000.00, 18200),
    ("07/12", "07/13", "Digital Advertising — Tubi AVOD Campaign (CPG)",
     "Digital Advertising", 214000.00, 42600),
    ("07/15", "07/16", "Local Spot Advertising — Owned Stations Group",
     "Local Advertising", 168000.00, 9100),
    ("07/19", "07/20", "Cable Network Programming — Affiliate Fee (Big Ten Network)",
     "Affiliate Fees", 96000.00, 0),
    ("07/22", "07/23", "National Advertising — FOX News Prime Time",
     "National Advertising", 356000.00, 7400),
    ("07/26", "07/27", "Television — Retransmission True-Up Adjustment",
     "Retransmission Consent", 34000.00, 0),
    ("07/29", "07/30", "Digital Advertising — Tubi Connected TV Upfront Draw",
     "Digital Advertising", 128000.00, 25800),
]

_FM_ADUNITS = [
    (1, "Impressions delivered — National advertising", 18_200_000),
    (2, "Impressions delivered — Local/Spot advertising", 9_100_000),
    (3, "Impressions delivered — Tubi digital (AVOD/CTV)", 42_600_000),
    (4, "Make-good impressions issued this period", -1_250_000),
    (5, "Bonus impressions — upfront overdelivery credit", 3_400_000),
    (6, "Impressions rolled over from prior period", 6_800_000),
    # No trailing "total" row: the report's Sum([Rewards Summary/Points]) adds
    # every row in this table, so a running-total row here would double count
    # (caught live -- first render showed 157.7M, exactly 2x the correct 78.85M).
]

_FM_SUMMARY = [
    (1, "Distributor", "Regional Cable & Fiber Co-op (MVPD)"),
    (2, "Carriage Agreement Status", "Renewed — 3-Year Term"),
    (3, "Total Subscribers Under Agreement", "1,240,000"),
    (4, "Affiliate Fee Rate — Cable Network Programming", "$1.86 / sub / month"),
    (5, "Retransmission Consent Rate — Television", "$3.10 / sub / month"),
    (6, "Ad Avail Utilization (Sellout Rate)", "94.2%"),
    (7, "Agreement Renewal Date", "12/31/2026"),
    (8, "Account Standing", "Current"),
]
