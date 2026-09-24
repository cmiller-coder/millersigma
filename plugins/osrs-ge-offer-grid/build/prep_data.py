#!/usr/bin/env python3
"""Turn live OSRS Grand Exchange API data into a Sigma-ready Snowflake SQL layer."""
import json, math, re, pathlib, datetime

SRC = pathlib.Path("/tmp")
OUT = pathlib.Path("/private/tmp/claude-502/rs")

mapping = json.loads((SRC / "osrs_map.json").read_text())
latest  = json.loads((SRC / "osrs_latest.json").read_text())["data"]
h24     = json.loads((SRC / "osrs_24h.json").read_text())["data"]

# --- real GE tax mechanics: 2% floored, capped 5M, no tax under 100gp, exempt list ---
TAX_EXEMPT = {
    "Old school bond", "Chisel", "Gardening trowel", "Glassblowing pipe", "Hammer",
    "Needle", "Rake", "Saw", "Secateurs", "Seed dibber", "Shears", "Spade",
    "Watering can", "Bucket", "Pestle and mortar", "Knife",
}

def ge_tax(price, name):
    if price < 100 or name in TAX_EXEMPT:
        return 0
    return min(math.floor(price * 0.02), 5_000_000)

# --- category classifier (ordered: first match wins) ---
RULES = [
    ("Bonds",              r"^old school bond$"),
    ("Gems & Jewellery",   r"^(uncut|cut) |\bdiamond\b|\bruby\b|\bemerald\b|\bsapphire\b|\bopal\b|\bjade\b|\btopaz\b|\bdragonstone\b|\bonyx\b|\bzenyte\b|\bamethyst$|amulet|necklace|\bring\b|bracelet|\bpendant\b"),
    ("Runes & Magic",      r"\brunes?$|^(blood|death|soul|nature|law|cosmic|astral|chaos|body|mind|water|earth|fire|air|mist|dust|smoke|steam|lava|wrath) rune|\borb$|tablet\)$|\bether\b|\bessence\b|catalyst|\bcharge\b|\btome\b"),
    ("Potions",            r"\([1-4]\)$|potion|\bbrew\b|antidote|antifire|antipoison|serum|elixir|restore| mix$|\bdose\b"),
    ("Herbs & Secondaries", r"^(grimy|clean) |^(guam|marrentill|tarromin|harralander|ranarr|toadflax|irit|avantoe|kwuarm|snapdragon|cadantine|lantadyme|dwarf weed|torstol)|weed$|eye of newt|limpwurt|white berries|red spiders|snape grass|mort myre|unicorn horn|crushed nest|potato cactus|volcanic ash|dragon scale|wine of zamorak|\bdiabolic worms\b|demon tear|zulrah's scales"),
    ("Ammunition",         r"\bbolts?\b|\barrows?\b|\bdarts?\b|\bjavelin\b|\bknives\b|\bthrownaxe\b|\bcannonball\b|arrowtip|bolt tip|dart tip|\bbolt rack\b|splinters$|\bblowpipe\b"),
    ("Logs & Planks",      r"\blogs?\b|\bplank\b|\bbark\b|\bsaplings?\b"),
    ("Ores, Bars & Coal",  r"\bore\b|\bbars?\b|^coal$|\bingot\b|\bmetal sheet\b|marble block|magic stone|\blimestone\b"),
    ("Seeds",              r"\bseeds?\b|\bspore\b"),
    ("Bones, Ashes & Prayer", r"\bbones?\b|\bashes\b|\bremains\b|ensouled"),
    ("Hunter & Implings",  r"chinchompa|impling|\bjar\b|\bbird nest\b|\bfeather\b"),
    ("Boss & Clue Drops",  r"\bkey\b|emblem$|\btotem\b|\bpage\b|lightbearer|contract of|awakener|\bsack\b|\bcrystal\b|aldarium|amylase"),
    ("Food & Fishing",     r"^raw |^cooked |^(shark|monkfish|lobster|swordfish|tuna|salmon|trout|bass|anglerfish|karambwan|dark crab|manta ray|sea turtle|halibut|marlin|herring|mackerel|cod)|\bpie\b|\bcake\b|\bbread\b|\bstew\b|\bpizza\b|\bcurry\b|\bpotato\b|\bwine\b|\bkebab\b|\bsweets\b|coconut|\bfish\b"),
    ("Weapons",            r"\bsword\b|longsword|scimitar|\bdagger\b|axe\b|\bmace\b|\bspear\b|halberd|\bwhip\b|\bbow\b|longbow|shortbow|crossbow|battlestaff|\bstaff\b|\bwand\b|\bclaws\b|\bhasta\b|rapier|\bmaul\b|godsword|\bblade\b|warhammer|sceptre|\bfang\b|\bhammer\b"),
    ("Armour",             r"platebody|platelegs|plateskirt|chainbody|\bhelm\b|helmet|\bshield\b|defender|\bboots\b|\bgloves\b|vambraces|bracers|\bcoif\b|\bhood\b|\bcape\b|\bcloak\b|\brobe\b| top$|\bbody\b|skirt$|gauntlets|tassets|dragonhide|\bd.hide\b|kiteshield"),
    ("Crafting Supplies",  r"\bthread\b|\bneedle\b|\bmould\b|\bvial\b|\bbucket\b|\bjug\b|molten glass|soft clay|\bclay\b|\bflax\b|bow string|\bleather\b|\bhide\b|cowhide\b|\bwool\b|steel nails|\bnails\b|papyrus|soda ash|seaweed|charcoal|repair kit|\bpot\b|gold leaf"),
]
COMPILED = [(c, re.compile(p, re.I)) for c, p in RULES]

def categorize(name):
    for cat, rx in COMPILED:
        if rx.search(name):
            return cat
    return "Other Goods"

# --- build the universe ---
rows = []
for it in mapping:
    iid = it["id"]
    name = it["name"]
    L = latest.get(str(iid))
    H = h24.get(str(iid))
    if not L or not H:
        continue
    hi, lo = L.get("high"), L.get("low")
    if not hi or not lo or lo < 20:
        continue
    vb = H.get("highPriceVolume") or 0   # units bought at the high price
    vs = H.get("lowPriceVolume") or 0    # units sold at the low price
    vol = vb + vs
    if vol < 1000:
        continue
    limit = it.get("limit") or 0
    if limit <= 0:
        continue                          # no buy limit published -> can't size a trade
    tax = ge_tax(hi, name)
    net = hi - lo - tax
    rows.append(dict(
        item_id=iid, name=name, category=categorize(name),
        members=bool(it.get("members")), limit=limit,
        ge_value=it.get("value") or 0, high_alch=it.get("highalch") or 0,
        insta_buy=hi, insta_sell=lo,
        avg_high=H.get("avgHighPrice") or hi, avg_low=H.get("avgLowPrice") or lo,
        vol_buy=vb, vol_sell=vs, vol=vol,
        tax=tax, net=net,
        traded_value=vol * ((hi + lo) // 2),
    ))

# keep the most economically significant, liquid names
rows.sort(key=lambda r: -r["traded_value"])
rows = rows[:240]
rows.sort(key=lambda r: (r["category"], r["name"]))

def esc(s):
    return s.replace("'", "''")

vals = []
for r in rows:
    vals.append(
        "({id},'{nm}','{cat}',{mem},{lim},{gev},{alch},{ib},{isl},{ah},{al},{vb},{vs})".format(
            id=r["item_id"], nm=esc(r["name"]), cat=r["category"],
            mem="TRUE" if r["members"] else "FALSE", lim=r["limit"],
            gev=r["ge_value"], alch=r["high_alch"],
            ib=r["insta_buy"], isl=r["insta_sell"],
            ah=r["avg_high"], al=r["avg_low"], vb=r["vol_buy"], vs=r["vol_sell"]))

values_block = ",\n".join("    " + v for v in vals)
exempt_sql = ",".join("'%s'" % esc(n) for n in sorted(TAX_EXEMPT))
# the capture time is when the wiki payload was FETCHED, not when this script
# last ran -- otherwise the header timestamp drifts away from the data.
snapshot = datetime.datetime.fromtimestamp(
    (SRC / "osrs_latest.json").stat().st_mtime, datetime.timezone.utc
).strftime("%Y-%m-%d %H:%M UTC")

sql = f"""-- Grand Exchange market layer. Live OSRS wiki prices, captured {snapshot}.
-- GE tax modelled exactly: 2% of sale price, floored, capped 5,000,000 gp,
-- zero under 100 gp and zero on the exempt-item list.
WITH raw AS (
  SELECT * FROM VALUES
{values_block}
  AS t(item_id, item_name, category, members, buy_limit,
       ge_value, high_alch, insta_buy, insta_sell,
       avg_high_24h, avg_low_24h, vol_bought_24h, vol_sold_24h)
),
taxed AS (
  SELECT
    raw.*,
    vol_bought_24h + vol_sold_24h                              AS volume_24h,
    insta_buy - insta_sell                                     AS gross_margin,
    CASE WHEN insta_buy < 100 OR item_name IN ({exempt_sql}) THEN 0
         ELSE LEAST(FLOOR(insta_buy * 0.02), 5000000) END      AS ge_tax
  FROM raw
),
calc AS (
  SELECT
    taxed.*,
    gross_margin - ge_tax                                      AS net_margin,
    (gross_margin - ge_tax) / NULLIF(insta_sell, 0)            AS roi_pct,
    insta_sell * buy_limit                                     AS capital_per_cycle,
    (gross_margin - ge_tax) * buy_limit                         AS profit_per_cycle,
    (gross_margin - ge_tax) * buy_limit * 6                     AS profit_per_day_theoretical,
    LEAST(buy_limit * 6, volume_24h)                            AS fillable_units_24h,
    (gross_margin - ge_tax) * LEAST(buy_limit * 6, volume_24h)  AS profit_per_day_fillable,
    volume_24h * ((insta_buy + insta_sell) / 2)                 AS traded_value_24h,
    ge_tax * vol_bought_24h                                     AS tax_paid_24h,
    high_alch - insta_sell - 180                                AS alch_margin,
    CASE WHEN ge_tax >= gross_margin           THEN 'Tax eats the spread'
         WHEN (gross_margin - ge_tax) <= 0     THEN 'No spread'
         WHEN (gross_margin - ge_tax) / NULLIF(insta_sell,0) >= 0.05 THEN 'High ROI'
         WHEN (gross_margin - ge_tax) / NULLIF(insta_sell,0) >= 0.02 THEN 'Workable'
         ELSE 'Thin' END                                        AS spread_verdict,
    CASE WHEN volume_24h >= 1000000 THEN 'Very liquid'
         WHEN volume_24h >=  100000 THEN 'Liquid'
         WHEN volume_24h >=   10000 THEN 'Moderate'
         ELSE 'Thin book' END                                   AS liquidity_band,
    CASE WHEN insta_sell >= 10000000 THEN 'Green stack (10m+)'
         WHEN insta_sell >=   100000 THEN 'White stack (100k+)'
         ELSE 'Yellow stack' END                                AS stack_tier,
    CASE WHEN members THEN 'Members' ELSE 'Free-to-play' END    AS access_tier,
    CASE WHEN ge_tax >= gross_margin THEN 1 ELSE 0 END          AS tax_killed,
    CASE WHEN gross_margin - ge_tax > 0 THEN 1 ELSE 0 END       AS is_profitable,
    -- Second basis. The live tick is what you can transact on this second and
    -- it is usually crossed; the 24h average spread is what a patient limit
    -- order actually earns. Both are carried so the difference is visible.
    avg_high_24h - avg_low_24h                                  AS avg_gross_margin,
    CASE WHEN avg_high_24h < 100 OR item_name IN ({exempt_sql}) THEN 0
         ELSE LEAST(FLOOR(avg_high_24h * 0.02), 5000000) END    AS avg_ge_tax,
    (avg_high_24h - avg_low_24h)
      - CASE WHEN avg_high_24h < 100 OR item_name IN ({exempt_sql}) THEN 0
             ELSE LEAST(FLOOR(avg_high_24h * 0.02), 5000000) END AS avg_net_margin,
    ((avg_high_24h - avg_low_24h)
      - CASE WHEN avg_high_24h < 100 OR item_name IN ({exempt_sql}) THEN 0
             ELSE LEAST(FLOOR(avg_high_24h * 0.02), 5000000) END)
      / NULLIF(avg_low_24h, 0)                                  AS avg_roi_pct,
    ((avg_high_24h - avg_low_24h)
      - CASE WHEN avg_high_24h < 100 OR item_name IN ({exempt_sql}) THEN 0
             ELSE LEAST(FLOOR(avg_high_24h * 0.02), 5000000) END)
      * buy_limit                                               AS avg_profit_per_cycle
  FROM taxed
)
SELECT
  calc.*,
  CASE WHEN avg_net_margin > 0 THEN 1 ELSE 0 END               AS avg_is_profitable,
  CASE WHEN avg_ge_tax >= avg_gross_margin THEN 'Tax eats the spread'
       WHEN avg_net_margin <= 0                THEN 'No spread'
       WHEN avg_roi_pct >= 0.05                THEN 'High ROI'
       WHEN avg_roi_pct >= 0.02                THEN 'Workable'
       ELSE 'Thin' END                                         AS avg_verdict
FROM calc
"""

(OUT / "market_layer.sql").write_text(sql)

# --- summary for sanity + the plugin snapshot ---
top = sorted(rows, key=lambda r: -(r["net"] * min(r["limit"] * 6, r["vol"])))[:24]
json.dump(top, open(OUT / "top_flips.json", "w"), indent=1)
json.dump({"snapshot": snapshot, "count": len(rows)}, open(OUT / "meta.json", "w"))

print(f"items kept: {len(rows)}   sql bytes: {len(sql)}")
cats = {}
for r in rows:
    cats[r["category"]] = cats.get(r["category"], 0) + 1
for c, n in sorted(cats.items(), key=lambda x: -x[1]):
    print(f"  {n:4d}  {c}")
print("\nTop 8 by fillable daily profit:")
for r in top[:8]:
    fill = min(r["limit"] * 6, r["vol"])
    print(f"  {r['name'][:30]:32s} margin {r['net']:>8,}  limit {r['limit']:>6,}  vol {r['vol']:>9,}  day {r['net']*fill:>12,}")
print("\nTax-eats-spread examples:")
for r in rows:
    if r["tax"] >= (r["insta_buy"] - r["insta_sell"]) and r["insta_buy"] > 1000:
        print(f"  {r['name'][:30]:32s} spread {r['insta_buy']-r['insta_sell']:>7,}  tax {r['tax']:>7,}")
