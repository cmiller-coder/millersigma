import json,sys,base64,urllib.request,urllib.error,xml.dom.minidom as _MD
BASE,TOKEN,CONN,FOLDER=sys.argv[1:5]
H={"Authorization":"Bearer "+TOKEN,"Content-Type":"application/json"}
def b64(s): return base64.b64encode(s.encode()).decode()
INK="#141414"; BLUE="#1B5FBF"; CARD={"backgroundColor":"#FFFFFF","borderColor":"#E5E7EB","borderWidth":1,"borderRadius":"round"}
TINT={"backgroundColor":"#EEF3FC","borderColor":"#CFE0F5","borderWidth":1,"borderRadius":"round"}
CUR={"kind":"number","formatString":"$.3~s","currencySymbol":"$","decimalSymbol":".","digitGroupingSymbol":",","digitGroupingSize":[3]}
NUM={"kind":"number","formatString":",.3~s"}

title={"id":"title","kind":"text","body":"# Cohort Builder — Proof of Concept","verticalAlign":"middle","style":{"color":INK}}
subtitle={"id":"subtitle","kind":"text","body":("Demo of the agent-driven cohort pattern (reverse-engineered from demeng's Marketing Control Center). "
 "Swap the base table's columns for any population you segment — customers for marketing, patients for healthcare, "
 "members, students, accounts. Same mechanic every time: one filter control per dimension, one agent tool per filter, "
 "reactive KPIs, and a Save that inserts a real row (not a UI-only Action Sequence, which can't be authored from code)."),
 "verticalAlign":"middle","style":{"color":"#3A3A3A"}}

# synthetic customer population
SQL="""WITH g AS (SELECT SEQ4() i FROM TABLE(GENERATOR(ROWCOUNT=>2000)))
SELECT 'CUST-'||LPAD(i::string,5,'0') AS CUST_ID,
  GET(ARRAY_CONSTRUCT('18-24','25-34','35-44','45-54','55-64','65+'), MOD(i,6))::string AS AGE_GROUP,
  GET(ARRAY_CONSTRUCT('Northeast','Southeast','Midwest','Southwest','West'), MOD(i*7,5))::string AS REGION,
  GET(ARRAY_CONSTRUCT('New','Growing','Loyal','At-Risk','Churned'), MOD(i*13,5))::string AS SEGMENT,
  GET(ARRAY_CONSTRUCT('Yes','No'), MOD(i*3,2))::string AS LOYALTY_MEMBER,
  GET(ARRAY_CONSTRUCT('Yes','No','No','No'), MOD(i*11,4))::string AS IS_LAPSED,
  50+MOD(i*8191,4950) AS REVENUE
FROM g"""
pop={"id":"population","kind":"table","name":"Customer Population","visibleAsSource":True,
 "source":{"connectionId":CONN,"kind":"sql","statement":SQL},
 "columns":[{"id":"p-id","formula":"[Custom SQL/CUST_ID]","name":"Cust ID"},
   {"id":"p-age","formula":"[Custom SQL/AGE_GROUP]","name":"Age Group"},
   {"id":"p-region","formula":"[Custom SQL/REGION]","name":"Region"},
   {"id":"p-seg","formula":"[Custom SQL/SEGMENT]","name":"Segment"},
   {"id":"p-loyal","formula":"[Custom SQL/LOYALTY_MEMBER]","name":"Loyalty Member"},
   {"id":"p-lapsed","formula":"[Custom SQL/IS_LAPSED]","name":"Is Lapsed"},
   {"id":"p-rev","formula":"[Custom SQL/REVENUE]","name":"Revenue"}],
 "order":["p-id","p-age","p-region","p-seg","p-loyal","p-lapsed","p-rev"]}

# independent BASELINE — same SQL, a SEPARATE element id, deliberately NOT targeted by any filter
# control's `filters` block, so it always reflects the whole population regardless of the live
# cohort filters. This is the "Base Case" equivalent from scenario modeling: a stable reference
# to compare the live-filtered cohort against.
baseline={"id":"population-baseline","kind":"table","name":"Population Baseline","visibleAsSource":True,
 "source":{"connectionId":CONN,"kind":"sql","statement":SQL},
 "columns":[{"id":"pb-id","formula":"[Custom SQL/CUST_ID]","name":"Cust ID"},
   {"id":"pb-rev","formula":"[Custom SQL/REVENUE]","name":"Revenue"}],
 "order":["pb-id","pb-rev"]}

# filter controls, each targets the population table directly (standard filter-control pattern)
def listctrl(cid,ctrlid,name,col):
    return {"kind":"control","controlId":ctrlid,"id":cid,"name":name,"controlType":"list","mode":"include","selectionMode":"multiple",
     "values":[],"filters":[{"source":{"kind":"table","elementId":"population"},"columnId":col}],
     "source":{"kind":"source","source":{"kind":"table","elementId":"population"},"columnId":col}}
ctrl_age=listctrl("ctrl-age","AgeGroup","Age Group","p-age")
ctrl_region=listctrl("ctrl-region","Region","Region","p-region")
ctrl_seg=listctrl("ctrl-seg","Segment","Segment","p-seg")
ctrl_loyal=listctrl("ctrl-loyal","LoyaltyMember","Loyalty Member","p-loyal")
ctrl_lapsed=listctrl("ctrl-lapsed","IsLapsed","Lapsed Only","p-lapsed")
ctrl_revfloor={"kind":"control","controlId":"RevenueFloor","id":"ctrl-revfloor","name":"Revenue Floor","controlType":"number","mode":"=","includeNulls":"when-no-value-is-selected"}
ctrl_name={"kind":"control","controlId":"CohortName","id":"ctrl-name","name":"Cohort Name","controlType":"text","mode":"equals","case":"insensitive","includeNulls":"when-no-value-is-selected","showOperators":False}
ctrl_desc={"kind":"control","controlId":"CohortDesc","id":"ctrl-desc","name":"Cohort Description","controlType":"text-area","mode":"equals","case":"insensitive","includeNulls":"when-no-value-is-selected","showOperators":False}

# comparative cohort KPIs: LIVE (filtered "population") next to an always-on BASELINE
# ("population-baseline", never filtered). Flat, minimal, text-only stat treatment (matching
# demeng's own Cohort Analysis reference page) instead of the earlier solid-color blocks -- a
# thin bordered white card, small grey caps label, big bold value. NO wrapping container (nesting
# a GridContainer inside a Tab is what scrambled an earlier version's layout -- verified
# tabbed-container support only for bare LayoutElement children).
BASELINE_GRAY="#5A6472"; LABEL_GRAY="#8A8F98"
def flat_stat(elid,source_id,formula,label,fmt,color=INK,size=26):
    return {"id":elid,"kind":"kpi-chart","source":{"elementId":source_id,"kind":"table"},
     "columns":[{"id":elid+"v","formula":formula,"name":label,"format":fmt}],
     "value":{"columnId":elid+"v","color":color,"fontSize":size,"fontWeight":"bold"},
     "name":{"text":label,"color":LABEL_GRAY,"fontSize":11,"fontWeight":"bold"},
     "layout":{"anchor":"start"},
     "style":{"backgroundColor":"#FFFFFF","borderColor":"#E9ECF1","borderWidth":1,"borderRadius":"round"}}
def cohort_card(elid,title,live_formula,base_formula,fmt):
    left=flat_stat(elid+"c","population",live_formula,title.upper()+" (COHORT)",fmt,color=BLUE,size=28)
    right=flat_stat(elid+"p","population-baseline",base_formula,"ALL CUSTOMERS (BASELINE)",fmt,color=BASELINE_GRAY,size=22)
    return [left,right]
k1=cohort_card("k-size","Cohort Size","CountDistinct([Customer Population/Cust ID])","CountDistinct([Population Baseline/Cust ID])",NUM)
k2=cohort_card("k-rev","Total Revenue","Sum([Customer Population/Revenue])","Sum([Population Baseline/Revenue])",CUR)
k3=cohort_card("k-avg","Avg Revenue / Customer","Sum([Customer Population/Revenue])/CountDistinct([Customer Population/Cust ID])","Sum([Population Baseline/Revenue])/CountDistinct([Population Baseline/Cust ID])",CUR)

# Revenue Distribution -- a histogram (bucketed bar chart) of the live cohort's per-customer
# revenue, the direct analog of the reference's smooth revenue-distribution curve. Bucket width
# $500 comfortably spans the synthetic $50-$5000 range into ~10 bars.
revenue_dist={"id":"revenue-dist","kind":"bar-chart","source":{"elementId":"population","kind":"table"},
 "columns":[{"id":"rd-bucket","formula":"Floor([Customer Population/Revenue]/500)*500","name":"Revenue Bucket","format":CUR},
            {"id":"rd-cnt","formula":"CountDistinct([Customer Population/Cust ID])","name":"Customers","format":NUM},
            {"id":"rd-bucket2","formula":"Floor([Customer Population/Revenue]/500)*500","name":"Revenue Bucket "}],
 "xAxis":{"columnId":"rd-bucket"},"yAxis":{"columnIds":["rd-cnt"]},
 "color":{"by":"category","column":"rd-bucket2","scheme":[BLUE]},"legend":{"visibility":"hidden"},
 "name":{"text":"Revenue distribution — current cohort","fontWeight":"bold","fontSize":14,"color":INK},"style":dict(CARD)}

age_bar={"id":"age-bar","kind":"bar-chart","source":{"elementId":"population","kind":"table"},
 "columns":[{"id":"ab-age","formula":"[Customer Population/Age Group]","name":"Age Group"},
            {"id":"ab-cnt","formula":"CountDistinct([Customer Population/Cust ID])","name":"Customers","format":NUM},
            {"id":"ab-age2","formula":"[Customer Population/Age Group]","name":"Age Group "}],
 "xAxis":{"columnId":"ab-age"},"yAxis":{"columnIds":["ab-cnt"]},
 "color":{"by":"category","column":"ab-age2","scheme":[BLUE]},"legend":{"visibility":"hidden"},
 "name":{"text":"Age distribution — current cohort","fontWeight":"bold","fontSize":14,"color":INK},"style":dict(CARD)}

# Top Customers -- the "Top Customer Preview" analog. Can't do a repeated-container-of-cards
# from code yet (UI-only), so use a real GROUPED table instead (the verified `groupings` shape,
# NOT the plain-table `sort`/`limit` fields -- those round-trip-tested as silently dropped).
# Grouping by every displayed dim keeps it at the same 1-row-per-customer grain as the raw data
# (each Cust ID is already unique), while `sort` on the Revenue calculation puts the biggest
# spenders first -- a compact card height then reads as "top N" without scrolling.
top_customers={"id":"top-cust","kind":"table","source":{"elementId":"population","kind":"table"},
 "columns":[{"id":"tc-id","formula":"[Customer Population/Cust ID]","name":"Cust ID"},
   {"id":"tc-age","formula":"[Customer Population/Age Group]","name":"Age Group"},
   {"id":"tc-region","formula":"[Customer Population/Region]","name":"Region"},
   {"id":"tc-loyal","formula":"[Customer Population/Loyalty Member]","name":"Loyalty Member"},
   {"id":"tc-rev","formula":"Sum([Customer Population/Revenue])","name":"Revenue","format":CUR}],
 "order":["tc-id","tc-age","tc-region","tc-loyal","tc-rev"],
 "groupings":[{"id":"g-top","groupBy":["tc-id","tc-age","tc-region","tc-loyal"],"calculations":["tc-rev"],
   "sort":[{"columnId":"tc-rev","direction":"descending"}]}],
 "name":{"text":"Top customers — current cohort","fontWeight":"bold","fontSize":14,"color":INK},"style":dict(CARD)}

# the large row-level detail table -- the direct analog of demeng's "Cohort Details" table on
# the Cohort Builder tab. Reactively filtered live by every control above (same population
# source), so it always shows exactly who is currently in the cohort being built.
cohort_detail_table={"id":"cohort-detail","kind":"table","source":{"elementId":"population","kind":"table"},
 "columns":[{"id":"cd-id","formula":"[Customer Population/Cust ID]","name":"Cust ID"},
   {"id":"cd-age","formula":"[Customer Population/Age Group]","name":"Age Group"},
   {"id":"cd-region","formula":"[Customer Population/Region]","name":"Region"},
   {"id":"cd-seg","formula":"[Customer Population/Segment]","name":"Segment"},
   {"id":"cd-loyal","formula":"[Customer Population/Loyalty Member]","name":"Loyalty Member"},
   {"id":"cd-lapsed","formula":"[Customer Population/Is Lapsed]","name":"Is Lapsed"},
   {"id":"cd-rev","formula":"[Customer Population/Revenue]","name":"Revenue","format":CUR}],
 "order":["cd-id","cd-age","cd-region","cd-seg","cd-loyal","cd-lapsed","cd-rev"],
 "name":{"text":"Cohort Details","fontWeight":"bold","fontSize":14,"color":INK},"style":dict(CARD)}

# saved cohorts log (append-only insert-rows -- the fully code-representable persistence path)
AGE_GROUPS=['18-24','25-34','35-44','45-54','55-64','65+']
saved={"id":"saved-cohorts","kind":"input-table","source":{"kind":"empty","connectionId":CONN},"inputMode":"explore","name":"Saved Cohorts",
 "columns":[{"id":"s-name","type":"text","name":"Cohort Name"},{"id":"s-desc","type":"text","name":"Description"},
   {"id":"s-size","type":"number","name":"Size at Save Time"},
   {"id":"s-rev","type":"number","name":"Total Revenue"},{"id":"s-avg","type":"number","name":"Avg Revenue per Customer"},
   {"id":"s-loyalrate","type":"number","name":"Loyalty Rate"},{"id":"s-lapsedrate","type":"number","name":"Lapsed Rate"},
   *[{"id":f"s-age{i}","type":"number","name":f"Age {ag} Count"} for i,ag in enumerate(AGE_GROUPS)]]}
# every Save snapshots the LIVE filtered cohort as a WIDE set of scalar numbers -- size, revenue,
# loyalty/lapsed rate, and a per-age-group count. No need to reconstruct which multi-select
# values were picked (Text() on a multi-select control returns its full OPTION list, not the
# selection -- verified live; only single-select controls stringify their actual selection
# correctly). This wide snapshot is what powers "analyze a saved cohort" below via a small
# cross-join + Switch unpivot, the same idea as a scenario "Book" comparing multiple scenarios.
SAVE_VALUES={
    "s-name":{"type":"control","control":"CohortName"},
    "s-desc":{"type":"control","control":"CohortDesc"},
    "s-size":{"type":"formula","formula":"CountDistinct([Customer Population/Cust ID])"},
    "s-rev":{"type":"formula","formula":"Sum([Customer Population/Revenue])"},
    "s-avg":{"type":"formula","formula":"Sum([Customer Population/Revenue])/CountDistinct([Customer Population/Cust ID])"},
    "s-loyalrate":{"type":"formula","formula":"CountDistinct(If([Customer Population/Loyalty Member]=\"Yes\",[Customer Population/Cust ID],Null))/CountDistinct([Customer Population/Cust ID])"},
    "s-lapsedrate":{"type":"formula","formula":"CountDistinct(If([Customer Population/Is Lapsed]=\"Yes\",[Customer Population/Cust ID],Null))/CountDistinct([Customer Population/Cust ID])"},
    **{f"s-age{i}":{"type":"formula","formula":f'CountDistinct(If([Customer Population/Age Group]="{ag}",[Customer Population/Cust ID],Null))'} for i,ag in enumerate(AGE_GROUPS)}}
btn_save={"id":"btn-save","kind":"button","text":"Save Cohort","appearance":"filled","actions":[{"id":"a-save","trigger":"on-click","effects":[
    {"effect":"insert-rows","table":"saved-cohorts","values":SAVE_VALUES},
    {"effect":"set-control-value","control":"CohortPick","value":{"type":"control","control":"CohortName"}}]}]}
btn_reset={"id":"btn-reset","kind":"button","text":"Reset filters","appearance":"outline","actions":[{"id":"a-reset","trigger":"on-click","effects":[
    {"effect":"clear-control","scope":{"type":"page","page":"pg"},"usePublishedValue":True}]}]}
saved_note={"id":"saved-note","kind":"text","body":"Every Save inserts a real row here (never lost, unlike the demeng original's UI-only Action Sequence).","verticalAlign":"middle","style":{"color":"#3A3A3A"}}

# ---- Agent: one tool per filter dimension, mirroring the demeng pattern exactly ----
def filter_tool(tool_id,name,desc,control,input_desc,selection_mode=None):
    step={"kind":"effect","effect":"set-control-value","control":control,"value":{"type":"agent-input","inputName":input_desc}}
    if selection_mode: step["selectionMode"]=selection_mode
    return {"toolId":tool_id,"kind":"action","name":name,"description":desc,"steps":[step]}
AGENT_TOOLS=[
  filter_tool("t-age","Set age group filter","Filter the cohort to one or more age bands.","AgeGroup","Age band(s) mentioned, e.g. '25-34' or '55-64'","add"),
  filter_tool("t-region","Set region filter","Filter the cohort to one or more regions.","Region","Region(s) mentioned, e.g. 'Northeast'","add"),
  filter_tool("t-seg","Set customer segment filter","Filter the cohort to one or more lifecycle segments.","Segment","Segment(s) mentioned, e.g. 'Loyal' or 'At-Risk'","add"),
  filter_tool("t-loyal","Set loyalty member filter","Filter to loyalty members or non-members.","LoyaltyMember","'Yes' or 'No'"),
  filter_tool("t-lapsed","Filter for lapsed customers only","Restrict the cohort to lapsed (inactive) customers only.","IsLapsed","'Yes' to show only lapsed customers"),
  filter_tool("t-rev","Set revenue floor","Set a minimum lifetime revenue threshold for inclusion.","RevenueFloor","The minimum revenue amount as a number"),
  {"toolId":"t-name","kind":"action","name":"Set cohort name & description",
   "description":"Set the cohort's name and description based on what the user is building.",
   "steps":[{"kind":"effect","effect":"set-control-value","control":"CohortName","value":{"type":"agent-input","inputName":"A short name for this cohort, based on the user's request"}},
            {"kind":"effect","effect":"set-control-value","control":"CohortDesc","value":{"type":"agent-input","inputName":"A one-sentence description of this cohort"}}]},
  {"toolId":"t-save","kind":"action","name":"Save the cohort",
   "description":"When the user asks to save/persist/record the current cohort, insert it into the Saved Cohorts log along with its live size, revenue, and average-revenue snapshot so it can be compared against other saved cohorts.",
   "steps":[{"kind":"effect","effect":"insert-rows","table":"saved-cohorts","values":SAVE_VALUES},
            {"kind":"effect","effect":"set-control-value","control":"CohortPick","value":{"type":"control","control":"CohortName"}}]},
]
agent={"id":"ag-cohort","name":"Cohort Builder Assistant",
 "instructions":("You help a marketer or analyst build a customer cohort by setting filters (age group, region, segment, "
   "loyalty status, lapsed status, revenue floor) based on natural language. Never assume a constraint the user didn't "
   "specify — leave it unset. Confirm the resulting cohort size after each change, and compare it to the total customer "
   "base (the baseline) so the user can see how selective the cohort is. "
   "ALWAYS propose and set a short cohort name and description using the naming tool as soon as the first filter is applied "
   "or changed — keep the name/description in sync with the current filters throughout the conversation. Do this "
   "proactively; don't wait for the user to ask for a name. When asked to save, use the save tool."),
 "dataSources":[{"kind":"table","elementId":"population"},{"kind":"table","elementId":"population-baseline"}],"tools":AGENT_TOOLS}
chat={"id":"chat1","kind":"chat","agentId":"ag-cohort"}
chat_c={"id":"c-chat","kind":"container","style":dict(TINT)}
chat_hd={"id":"chat-hd","kind":"text","body":"**Ask the Cohort Builder Assistant**","verticalAlign":"middle","style":{"color":INK}}

header2={"id":"header2","kind":"text","body":"# Saved Cohorts","verticalAlign":"middle","style":{"color":INK}}
# tabbed container matching demeng's original Cohort Construction App: Tab A = build (table +
# filters + agent), Tab B = visualize (KPIs + charts). Restored per Connor's "these two can be
# tabbed containers" -- reverses the earlier 3-separate-pages split for just these two views;
# "Saved Cohorts" (comparing many named cohorts) stays its own separate page, a different function.
tc_cohort={"id":"tc-cohort","kind":"tabbed-container","tabs":[{"name":"Cohort Builder"},{"name":"Visualize"}],"tabBar":{"alignment":"start"}}
saved_table={"id":"saved-view","kind":"table","source":{"elementId":"saved-cohorts","kind":"table"},
 "columns":[{"id":"sv-name","formula":"[Saved Cohorts/Cohort Name]","name":"Cohort Name"},
   {"id":"sv-desc","formula":"[Saved Cohorts/Description]","name":"Description"},
   {"id":"sv-size","formula":"[Saved Cohorts/Size at Save Time]","name":"Size at Save Time","format":NUM},
   {"id":"sv-rev","formula":"[Saved Cohorts/Total Revenue]","name":"Total Revenue","format":CUR},
   {"id":"sv-avg","formula":"[Saved Cohorts/Avg Revenue per Customer]","name":"Avg Revenue / Customer","format":CUR},
   {"id":"sv-loyal","formula":"[Saved Cohorts/Loyalty Rate]","name":"Loyalty Rate","format":{"kind":"number","formatString":".1%"}},
   {"id":"sv-lapsed","formula":"[Saved Cohorts/Lapsed Rate]","name":"Lapsed Rate","format":{"kind":"number","formatString":".1%"}}],
 "order":["sv-name","sv-desc","sv-size","sv-rev","sv-avg","sv-loyal","sv-lapsed"],"style":dict(CARD)}

# ---- Analyze a saved cohort: pick ONE by name, see its age breakdown as a real bar chart ----
# via a small cross-join (selected cohort x 6 age-group labels) + Switch unpivot -- the exact
# same technique used in every scenario modeler this session (dynamic dimension via Switch).
# deliberately NO `filters` on this control -- it must NOT globally filter "saved-cohorts",
# or the main comparison table/chart above would also collapse to just the selected cohort.
# Instead every downstream element below matches [CohortPick] explicitly via SumIf/If, the
# same proven pattern used for every control-driven formula this session.
ctrl_pick={"kind":"control","controlId":"CohortPick","id":"ctrl-pick","name":"Select a saved cohort to analyze","controlType":"list",
 "mode":"include","selectionMode":"single","values":[],
 "source":{"kind":"source","source":{"kind":"table","elementId":"saved-cohorts"},"columnId":"s-name"}}
# NOTE: a `list` control has no code-representable "default selected value" (tested live --
# neither `defaultValue` nor `value` round-trips; both are silently dropped). Both Save paths
# (button + agent tool) already fire `set-control-value` on CohortPick right after saving, so
# once a real Save happens in the published workbook, the picker auto-selects it AND (per Sigma's
# normal published-control-state behavior) should stay selected for future visits -- the null
# state below only shows up on a freshly-redeployed/never-saved workbook.
pick_hint={"id":"pick-hint","kind":"text","body":"_Save a cohort on the Builder tab and it'll auto-select here — and stay selected next time you open this page._","verticalAlign":"middle","style":{"color":LABEL_GRAY}}
AGE_LABEL_VALS=",".join(f"('{ag}',{i})" for i,ag in enumerate(AGE_GROUPS))
age_labels={"id":"age-labels","kind":"table","name":"Age Labels","visibleAsSource":True,
 "source":{"connectionId":CONN,"kind":"sql","statement":f"SELECT column1 AS LABEL, column2 AS IDX FROM (VALUES {AGE_LABEL_VALS})"},
 "columns":[{"id":"al-label","formula":"[Custom SQL/LABEL]","name":"Label"},{"id":"al-idx","formula":"[Custom SQL/IDX]","name":"Idx"}],
 "order":["al-label","al-idx"]}
cohort_age_cross={"id":"cohort-age-cross","kind":"table","name":"Selected Cohort — Age Breakdown","visibleAsSource":True,
 "source":{"kind":"join","joins":[{"left":{"elementId":"saved-cohorts","kind":"table"},"right":{"elementId":"age-labels","kind":"table"},
   "columns":[{"left":"1","right":"1"}],"joinType":"left-outer"}],"primarySource":{"elementId":"saved-cohorts","kind":"table"}},
 "columns":[{"id":"cac-cohort","formula":"[Saved Cohorts/Cohort Name]","name":"Cohort Name"},
   {"id":"cac-label","formula":"[Age Labels/Label]","name":"Age Group"},
   {"id":"cac-count","formula":("Switch([Age Labels/Label]," + ",".join(f'"{ag}",[Saved Cohorts/Age {ag} Count]' for ag in AGE_GROUPS) + ")"),"name":"Customers","format":NUM},
   {"id":"cac-label2","formula":"[Age Labels/Label]","name":"Age Group "}],
 "order":["cac-cohort","cac-label","cac-count","cac-label2"]}
age_analysis_bar={"id":"age-analysis-bar","kind":"bar-chart","source":{"elementId":"cohort-age-cross","kind":"table"},
 "columns":[{"id":"cac-label","formula":"[Selected Cohort — Age Breakdown/Age Group]","name":"Age Group"},
   {"id":"cac-count","formula":"SumIf([Selected Cohort — Age Breakdown/Customers],[Selected Cohort — Age Breakdown/Cohort Name]=[CohortPick])","name":"Customers","format":NUM},
   {"id":"cac-label2","formula":"[Selected Cohort — Age Breakdown/Age Group]","name":"Age Group "}],
 "xAxis":{"columnId":"cac-label"},"yAxis":{"columnIds":["cac-count"]},
 "color":{"by":"category","column":"cac-label2","scheme":[BLUE]},"legend":{"visibility":"hidden"},
 "dataLabel":{"labels":"shown","anchor":"outside-end","fontSize":12},
 "name":{"text":"Age breakdown — selected saved cohort","fontWeight":"bold","fontSize":14,"color":INK},"style":dict(CARD)}
# Same flat white-card treatment as cohort_card, just with a distinct accent color per metric
# (colored VALUE text, not a solid block -- matches the rest of this restyle).
ANALYSIS_COLORS=["#0B2E5E","#1B5FBF","#2E9B6B","#9A1B2F"]
def analysis_kpi(elid,title,formula,fmt,color):
    return flat_stat(elid,"saved-cohorts",formula,title,fmt,color=color,size=28)
_SEL='[Saved Cohorts/Cohort Name]=[CohortPick]'
# MaxIf, not AvgIf -- AvgIf silently resolved to null at query time (verified live: Size/Revenue
# via SumIf worked fine, Loyalty/Lapsed via AvgIf both came back "null" -- AvgIf isn't a real
# Sigma function). MaxIf is already verified working elsewhere; since exactly one row matches
# a given cohort name, Max of that one value is exactly correct.
ak_size=analysis_kpi("ak-size","SIZE",f"SumIf([Saved Cohorts/Size at Save Time],{_SEL})",NUM,ANALYSIS_COLORS[0])
ak_rev=analysis_kpi("ak-rev","REVENUE",f"SumIf([Saved Cohorts/Total Revenue],{_SEL})",CUR,ANALYSIS_COLORS[1])
ak_loyal=analysis_kpi("ak-loyal","LOYALTY RATE",f"MaxIf([Saved Cohorts/Loyalty Rate],{_SEL})",{"kind":"number","formatString":".1%"},ANALYSIS_COLORS[2])
ak_lapsed=analysis_kpi("ak-lapsed","LAPSED RATE",f"MaxIf([Saved Cohorts/Lapsed Rate],{_SEL})",{"kind":"number","formatString":".1%"},ANALYSIS_COLORS[3])

# comparison chart across saved cohorts -- the direct analog of a scenario "Book" bar chart
saved_bar={"id":"saved-bar","kind":"bar-chart","source":{"elementId":"saved-cohorts","kind":"table"},
 "columns":[{"id":"sb-name","formula":"[Saved Cohorts/Cohort Name]","name":"Cohort Name"},
            {"id":"sb-rev","formula":"Sum([Saved Cohorts/Total Revenue])","name":"Total Revenue","format":CUR},
            {"id":"sb-name2","formula":"[Saved Cohorts/Cohort Name]","name":"Cohort Name "}],
 "xAxis":{"columnId":"sb-name"},"yAxis":{"columnIds":["sb-rev"]},
 "color":{"by":"category","column":"sb-name2","scheme":["#1B5FBF","#5A6472","#2E9B6B","#C9A94B","#B0407A","#9A1B2F"]},
 "legend":{"visibility":"hidden"},"name":{"text":"Saved cohorts compared — total revenue","fontWeight":"bold","fontSize":14,"color":INK},"style":dict(CARD)}

# Page 1 = one Sigma page, containing tc_cohort (2 tabs: build / visualize).
# Page 2 = Saved Cohorts (unchanged, its own page -- a different function: comparing many
# already-saved cohorts against each other, not building or visualizing the current one).
page1_elements=[title,subtitle,tc_cohort,
 ctrl_name,ctrl_desc,ctrl_age,ctrl_region,ctrl_seg,ctrl_loyal,ctrl_lapsed,ctrl_revfloor,
 cohort_detail_table,btn_save,btn_reset,saved_note,chat_c,chat_hd,chat,
 *k1,*k2,*k3,revenue_dist,age_bar,top_customers,
 pick_hint,ctrl_pick,ak_size,ak_rev,ak_loyal,ak_lapsed,age_analysis_bar]
page2_elements=[header2,saved,saved_table,saved_bar]
utils_elements=[pop,baseline,age_labels,cohort_age_cross]

layout1=f"""<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg">
  <LayoutElement elementId="title" gridColumn="1 / 25" gridRow="1 / 3"/>
  <LayoutElement elementId="subtitle" gridColumn="1 / 25" gridRow="3 / 6"/>
  <TabbedContainer elementId="tc-cohort" type="tabbed-container" gridColumn="1 / 25" gridRow="7 / 60">
    <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <LayoutElement elementId="ctrl-name" gridColumn="1 / 10" gridRow="1 / 4"/>
      <LayoutElement elementId="ctrl-desc" gridColumn="10 / 18" gridRow="1 / 4"/>
      <LayoutElement elementId="ctrl-age" gridColumn="1 / 6" gridRow="4 / 7"/>
      <LayoutElement elementId="ctrl-region" gridColumn="6 / 11" gridRow="4 / 7"/>
      <LayoutElement elementId="ctrl-seg" gridColumn="11 / 18" gridRow="4 / 7"/>
      <LayoutElement elementId="ctrl-loyal" gridColumn="1 / 6" gridRow="7 / 10"/>
      <LayoutElement elementId="ctrl-lapsed" gridColumn="6 / 11" gridRow="7 / 10"/>
      <LayoutElement elementId="ctrl-revfloor" gridColumn="11 / 18" gridRow="7 / 10"/>
      <LayoutElement elementId="cohort-detail" gridColumn="1 / 18" gridRow="10 / 45"/>
      <LayoutElement elementId="btn-save" gridColumn="1 / 6" gridRow="46 / 49"/>
      <LayoutElement elementId="btn-reset" gridColumn="6 / 10" gridRow="46 / 49"/>
      <LayoutElement elementId="saved-note" gridColumn="10 / 18" gridRow="46 / 49"/>
      <GridContainer elementId="c-chat" type="grid" gridColumn="18 / 25" gridRow="1 / 49" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
        <LayoutElement elementId="chat-hd" gridColumn="1 / 13" gridRow="1 / 2"/>
        <LayoutElement elementId="chat1" gridColumn="1 / 13" gridRow="2 / 26"/>
      </GridContainer>
    </Tab>
    <Tab gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
      <LayoutElement elementId="k-sizec" gridColumn="1 / 5" gridRow="1 / 7"/>
      <LayoutElement elementId="k-sizep" gridColumn="5 / 9" gridRow="1 / 7"/>
      <LayoutElement elementId="k-revc" gridColumn="9 / 13" gridRow="1 / 7"/>
      <LayoutElement elementId="k-revp" gridColumn="13 / 17" gridRow="1 / 7"/>
      <LayoutElement elementId="k-avgc" gridColumn="17 / 21" gridRow="1 / 7"/>
      <LayoutElement elementId="k-avgp" gridColumn="21 / 25" gridRow="1 / 7"/>
      <LayoutElement elementId="revenue-dist" gridColumn="1 / 25" gridRow="8 / 22"/>
      <LayoutElement elementId="age-bar" gridColumn="1 / 25" gridRow="23 / 37"/>
      <LayoutElement elementId="top-cust" gridColumn="1 / 25" gridRow="38 / 50"/>
      <LayoutElement elementId="pick-hint" gridColumn="1 / 25" gridRow="51 / 53"/>
      <LayoutElement elementId="ctrl-pick" gridColumn="1 / 13" gridRow="53 / 57"/>
      <LayoutElement elementId="ak-size" gridColumn="1 / 7" gridRow="58 / 65"/>
      <LayoutElement elementId="ak-rev" gridColumn="7 / 13" gridRow="58 / 65"/>
      <LayoutElement elementId="ak-loyal" gridColumn="13 / 19" gridRow="58 / 65"/>
      <LayoutElement elementId="ak-lapsed" gridColumn="19 / 25" gridRow="58 / 65"/>
      <LayoutElement elementId="age-analysis-bar" gridColumn="1 / 25" gridRow="66 / 82"/>
    </Tab>
  </TabbedContainer>
</Page>"""

layout2="""<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg-saved">
  <LayoutElement elementId="header2" gridColumn="1 / 25" gridRow="1 / 3"/>
  <LayoutElement elementId="saved-view" gridColumn="1 / 25" gridRow="4 / 19"/>
  <LayoutElement elementId="saved-bar" gridColumn="1 / 25" gridRow="19 / 35"/>
  <LayoutElement elementId="saved-cohorts" gridColumn="1 / 25" gridRow="35 / 50"/>
</Page>"""

layout_utils="""<Page type="grid" gridTemplateColumns="repeat(24,1fr)" gridTemplateRows="auto" id="utils-hidden">
  <LayoutElement elementId="population" gridColumn="1 / 13" gridRow="1 / 20"/>
  <LayoutElement elementId="population-baseline" gridColumn="13 / 25" gridRow="1 / 20"/>
  <LayoutElement elementId="age-labels" gridColumn="1 / 13" gridRow="20 / 30"/>
  <LayoutElement elementId="cohort-age-cross" gridColumn="13 / 25" gridRow="20 / 30"/>
</Page>"""

layout='<?xml version="1.0" encoding="utf-8"?>\n'+layout1+layout2+layout_utils

theme={"colors":{"text":INK,"highlight":BLUE},"colorOverrides":{"backgroundCanvas":"#FFFFFF","canvasBackground":"#F3F5F8"},
 "categoricalScheme":["#1B5FBF","#5A6472","#2E9B6B","#C9A94B","#B0407A"],"fonts":{"textFont":"Inter","dataFont":"Inter"},"pageWidth":"full"}

spec={"name":"Cohort Builder — Proof of Concept","folderId":FOLDER,"schemaVersion":1,
 "pages":[{"id":"pg","name":"Cohort Builder","elements":page1_elements},
          {"id":"pg-saved","name":"Saved Cohorts","elements":page2_elements},
          {"id":"utils-hidden","name":"Utility Data","visibility":"hidden","elements":utils_elements}],
 "layout":layout,"themeOverrides":theme,"agents":[agent]}

def qa(s):
    def _walk(o):
        if isinstance(o,dict):
            for v in o.values(): yield from _walk(v)
        elif isinstance(o,list):
            for v in o: yield from _walk(v)
        elif isinstance(o,str): yield o
    bad=0
    for x in _walk(s):
        if x.startswith("data:image/svg+xml;base64,"):
            try: _MD.parseString(base64.b64decode(x.split(",",1)[1]))
            except Exception as e: bad+=1; print("INVALID SVG:",str(e)[:120])
    return bad
if qa(spec): print("ABORT malformed SVG"); sys.exit(1)
# First run: POST creates a new workbook. On every re-run after that, hardcode the
# returned workbookUrlId into EXISTING_WID below and switch to PUT .../{id}/spec — same
# discipline as every other generator in this repo: create once, then always edit in place
# (re-POSTing creates a duplicate workbook with the same name).
EXISTING_WID = None
if EXISTING_WID:
    r=urllib.request.Request(BASE+f"/v2/workbooks/{EXISTING_WID}/spec",data=json.dumps(spec).encode(),headers=H,method="PUT")
else:
    r=urllib.request.Request(BASE+"/v2/workbooks/spec",data=json.dumps(spec).encode(),headers=H,method="POST")
try:
    resp=urllib.request.urlopen(r,timeout=120).read().decode()
    print(("PUT" if EXISTING_WID else "POST")+":", "ACCEPTED" if "success: true" in resp else resp[:500])
    wid=EXISTING_WID or [l.split()[-1] for l in resp.splitlines() if "workbookId" in l][0]
    url=json.loads(urllib.request.urlopen(urllib.request.Request(BASE+f"/v2/workbooks/{wid}",headers=H),timeout=30).read().decode()).get("url")
    print("URL:", url)
except urllib.error.HTTPError as e:
    raw=e.read().decode()
    try: msg=json.loads(raw).get("message","")
    except Exception: msg=raw
    print("FAILED:", e.code, msg[:500])
