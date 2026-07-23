# CAVA — restaurant command-center + scenario-modeler generator (workbooks-as-code EXAMPLE).
# Usage: python3 build_cava.py <SIGMA_BASE_URL> <TOKEN> <CONNECTION_ID> <FOLDER_ID>
# Illustrative: reshapes SE_DEMO_DB.BIG_BUYS.BIG_BUYS_POS into a restaurant model.
# DAYPART_PLUGIN is a registered pluginId — register your own (POST /v2/plugins) and replace it.
# Pattern: light surfaces; gradient KPI cards with NATIVE (colorable) titles; comparative deltas;
#   two agents (read-only + insert-rows tool); bespoke day-part plugin in a container BELOW the bar;
#   agent beside the bar only; full-width toolbar buttons; side-by-side pivots below the plugin.
import json,sys,base64,urllib.request,urllib.error,xml.dom.minidom as _MD
BASE,TOKEN,CONN,FOLDER=sys.argv[1:5]
AICONN="SNOWFLAKE.CORTEX.COMPLETE"; DAYPART_PLUGIN="a4e04bd7-3ddb-414b-b528-07d43ea52c5a"
H={"Authorization":"Bearer "+TOKEN,"Content-Type":"application/json"}
def b64(s): return base64.b64encode(s.encode()).decode()
CUR={"kind":"number","formatString":"$.3~s","currencySymbol":"$","decimalSymbol":".","digitGroupingSymbol":",","digitGroupingSize":[3]}
NUM={"kind":"number","formatString":",.3~s"}; PCT2={"kind":"number","formatString":"+,.1%"}; PCT1={"kind":"number","formatString":".1%"}
INK="#2B1D16"; SLATE="#8A6F64"; CORAL="#E5533A"; OLIVE="#6B7A3A"; PLUM="#5A2A4A"; CREAM="#FBEFE6"; W="#FFFFFF"
CARD={"backgroundColor":"#FFFFFF","borderColor":"#ECE0D6","borderWidth":1,"borderRadius":"round"}
TINT={"backgroundColor":"#FBF1E9","borderColor":"#ECE0D6","borderWidth":1,"borderRadius":"round"}
def grad(a,b):
    return "data:image/svg+xml;base64,"+b64(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 240" preserveAspectRatio="xMidYMid slice"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient></defs><rect width="400" height="240" fill="url(#g)"/></svg>')
KG=[grad("#B83D28","#E5674A"),grad("#8E3B2E","#C64A2E"),grad("#5E6B33","#8FA34A"),grad("#5A2A4A","#8E4A6B")]
HEROBG="data:image/svg+xml;base64,"+b64('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 220" preserveAspectRatio="xMidYMid slice"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#FBEBE2"/><stop offset="1" stop-color="#FFFFFF"/></linearGradient></defs><rect width="1600" height="220" fill="url(#g)"/><rect x="0" y="0" width="6" height="220" fill="#E5533A"/></svg>')
def ic(body,col=CORAL,fill="none",sw=2.2):
    return "data:image/svg+xml;base64,"+b64(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{fill}" stroke="{col}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">{body}</svg>')
IC_DOLLAR='<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>'
IC_TREND='<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>'
IC_PIN='<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>'
IC_USERS='<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
IC_ZAP='<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>'
IC_CHAT='<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>'
IC_LIST='<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>'
IC_CLOCK='<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>'
logo_svg=('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 96" preserveAspectRatio="xMinYMid meet">'
 '<text x="4" y="70" font-family="Inter,Arial,sans-serif" font-weight="900" font-size="60" letter-spacing="3" fill="#E5533A">CAVA</text></svg>')
logo_uri="data:image/svg+xml;base64,"+b64(logo_svg)

# ============ PAGE 1 DATA (restaurant reshape) ============
MENU=['Grain Bowls','Pitas','Greens & Grains','Dips & Spreads','Sides','Beverages']
CHAN=['In-Restaurant','Digital','Catering']; MKT=['Northeast','Mid-Atlantic','Southeast','Midwest','Texas','West']
MARR="ARRAY_CONSTRUCT("+",".join("'"+m.replace("'","''")+"'" for m in MENU)+")"
CARR="ARRAY_CONSTRUCT("+",".join("'"+c+"'" for c in CHAN)+")"
KARR="ARRAY_CONSTRUCT("+",".join("'"+m.replace("'","''")+"'" for m in MKT)+")"
SQL=f"""WITH base AS (
  SELECT ORDER_NUMBER, DATE, DATE_TRUNC('month',DATE) AS USE_MONTH,
    GET({MARR}, MOD(ABS(HASH(PRODUCT_FAMILY)),6))::string AS MENU,
    GET({CARR}, MOD(ABS(HASH(PRODUCT_LINE)),3))::string AS CHANNEL,
    GET({KARR}, MOD(ABS(HASH(STORE_STATE)),6))::string AS MARKET,
    MOD(ABS(HASH(CUSTOMER_NAME)),360) AS LOCATION,
    QUANTITY*PRICE*0.087 AS REVENUE, QUANTITY AS GUESTS
  FROM SE_DEMO_DB.BIG_BUYS.BIG_BUYS_POS
), m AS (SELECT MAX(USE_MONTH) MAXM FROM base)
SELECT base.*, CASE WHEN USE_MONTH>DATEADD('month',-12,(SELECT MAXM FROM m)) THEN 'Current Period'
  WHEN USE_MONTH>DATEADD('month',-24,(SELECT MAXM FROM m)) THEN 'Prior Year' ELSE NULL END AS PERIOD_NAME
FROM base"""
MF="CAVA"
COLS=[("c-date","DATE","Date"),("c-month","USE_MONTH","Month"),("c-period","PERIOD_NAME","Period Name"),
 ("c-menu","MENU","Menu category"),("c-chan","CHANNEL","Channel"),("c-mkt","MARKET","Market"),
 ("c-loc","LOCATION","Location"),("c-rev","REVENUE","Revenue"),("c-guests","GUESTS","Guests")]
tbl={"id":"tbl","kind":"table","source":{"connectionId":CONN,"statement":SQL,"kind":"sql"},
 "columns":[{"id":c,"formula":f"[Custom SQL/{s}]","name":d} for c,s,d in COLS],"name":MF,"order":[c[0] for c in COLS],"visibleAsSource":True}
# synthetic day-part source for the bespoke plugin (7 days x 24 hours, lunch+dinner peaks, weekend lift)
DPSQL="""WITH g AS (SELECT SEQ4() s FROM TABLE(GENERATOR(ROWCOUNT=>168))), c AS (SELECT FLOOR(s/24) DOW, MOD(s,24) HR FROM g)
SELECT GET(ARRAY_CONSTRUCT('Mon','Tue','Wed','Thu','Fri','Sat','Sun'),DOW)::string AS DAY, HR AS HOUR,
  CASE WHEN HR<10 OR HR>22 THEN 0 ELSE ROUND((CASE WHEN DOW IN (5,6) THEN 1.30 WHEN DOW=4 THEN 1.12 ELSE 1.0 END)
   *130000*(EXP(-POWER((HR-12.5)/1.6,2))+0.95*EXP(-POWER((HR-18.5)/1.9,2))+0.08)) END AS REVENUE
FROM c"""
daypart={"id":"daypart","kind":"table","name":"Day-part","visibleAsSource":True,
 "source":{"connectionId":CONN,"kind":"sql","statement":DPSQL},
 "columns":[{"id":"dp-day","formula":"[Custom SQL/DAY]","name":"Day"},{"id":"dp-hour","formula":"[Custom SQL/HOUR]","name":"Hour"},{"id":"dp-rev","formula":"[Custom SQL/REVENUE]","name":"Revenue","format":CUR}],
 "order":["dp-day","dp-hour","dp-rev"]}

def header(sfx,title,subtitle):
    c={"id":f"c-hdr{sfx}","kind":"container","style":{"borderRadius":"round","borderColor":"#ECE0D6","borderWidth":1},"backgroundImage":{"url":HEROBG,"style":{"fit":"cover"}}}
    lg={"id":f"logo{sfx}","kind":"image","url":logo_uri,"style":{"fit":"contain"}}
    tt={"id":f"ttl{sfx}","kind":"text","body":f"## {title}","verticalAlign":"middle","style":{"color":INK}}
    sb={"id":f"sub{sfx}","kind":"text","body":subtitle,"verticalAlign":"middle","style":{"color":SLATE}}
    lay=(f'  <GridContainer elementId="c-hdr{sfx}" type="grid" gridColumn="1 / 25" gridRow="1 / 5" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="repeat(6,1fr)">\n'
         f'    <LayoutElement elementId="logo{sfx}" gridColumn="1 / 6" gridRow="2 / 5"/>\n'
         f'    <LayoutElement elementId="ttl{sfx}" gridColumn="7 / 19" gridRow="2 / 4"/>\n'
         f'    <LayoutElement elementId="sub{sfx}" gridColumn="7 / 19" gridRow="4 / 6"/>\n  </GridContainer>')
    return [c,lg,tt,sb],lay

def kpi(elid,src,icon,title,valf,fmt,compf,g,trend=None,rowband="5 / 13"):
    cid=f"c-{elid}"
    cont={"id":cid,"kind":"container","style":{"borderRadius":"round"},"backgroundImage":{"url":g,"style":{"fit":"cover"}}}
    ik={"id":f"i-{elid}","kind":"image","url":icon,"style":{"fit":"contain"}}
    cols=[{"id":f"k-{elid}v","formula":valf,"name":title,"format":fmt}]
    kv={"id":f"k-{elid}","kind":"kpi-chart","source":{"elementId":src,"kind":"table"},
        "value":{"columnId":f"k-{elid}v","color":W,"fontSize":28},
        "name":{"text":title,"fontSize":14,"color":W},"layout":{"anchor":"middle"},"style":{"backgroundColor":"transparent","padding":"none"}}
    if compf:
        cols.append({"id":f"k-{elid}c","formula":compf,"name":"Comparison","format":fmt})
        kv["comparisonColumn"]={"columnId":f"k-{elid}c"}; kv["comparison"]={"display":"delta","colorGood":"#DDF3C6","colorBad":"#FFD1C7","fontSize":14}
    kv["columns"]=cols
    els=[cont,ik,kv]
    if trend:
        ln={"id":f"ln-{elid}","kind":"line-chart","source":{"elementId":src,"kind":"table"},
            "columns":[{"id":f"ln-{elid}m","formula":f"[{MF}/Month]","name":"Month"},{"id":f"ln-{elid}v","formula":trend,"name":"Trend"}],
            "xAxis":{"columnId":f"ln-{elid}m","format":{"marks":"none","labels":"hidden"}},
            "yAxis":{"columnIds":[f"ln-{elid}v"],"format":{"labels":"hidden","marks":"none","scale":{"type":"linear","zero":False,"hideZeroLine":True}}},
            "name":{"visibility":"hidden"},"legend":{"visibility":"hidden"},"lineAreaStyle":{"interpolation":"monotone"},"style":{"backgroundColor":"transparent","padding":"none"}}
        els.append(ln)
        lay=(f'  <GridContainer elementId="{cid}" type="grid" gridColumn="{{col}}" gridRow="{rowband}" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="repeat(12,1fr)">\n'
             f'    <LayoutElement elementId="i-{elid}" gridColumn="1 / 3" gridRow="1 / 3"/>\n'
             f'    <LayoutElement elementId="k-{elid}" gridColumn="1 / 13" gridRow="3 / 9"/>\n'
             f'    <LayoutElement elementId="ln-{elid}" gridColumn="1 / 13" gridRow="9 / 12"/>\n  </GridContainer>')
    else:
        lay=(f'  <GridContainer elementId="{cid}" type="grid" gridColumn="{{col}}" gridRow="{rowband}" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="repeat(12,1fr)">\n'
             f'    <LayoutElement elementId="i-{elid}" gridColumn="1 / 3" gridRow="1 / 3"/>\n'
             f'    <LayoutElement elementId="k-{elid}" gridColumn="1 / 13" gridRow="3 / 11"/>\n  </GridContainer>')
    return els,lay
_P='[{0}/Period Name]="§"'.format(MF)
KDEFS=[("rev","REVENUE",ic(IC_DOLLAR,W),f'SumIf([{MF}/Revenue],{_P})',CUR,f'Sum([{MF}/Revenue])'),
       ("auv","AVG UNIT VOLUME",ic(IC_TREND,W),f'SumIf([{MF}/Revenue],{_P})/CountDistinct(If({_P},[{MF}/Location],Null))',CUR,f'Sum([{MF}/Revenue])/CountDistinct([{MF}/Location])'),
       ("loc","ACTIVE LOCATIONS",ic(IC_PIN,W),f'CountDistinct(If({_P},[{MF}/Location],Null))',NUM,f'CountDistinct([{MF}/Location])'),
       ("guests","GUEST TRANSACTIONS",ic(IC_USERS,W),f'SumIf([{MF}/Guests],{_P})',NUM,f'Sum([{MF}/Guests])')]
kpis=[]; kpilay=[]
for i,(elid,t,icn,mf,fmt,tr) in enumerate(KDEFS):
    cur=mf.replace("§","Current Period"); pri=mf.replace("§","Prior Year")
    e,l=kpi(elid,"tbl",icn,t,cur,fmt,pri,KG[i],trend=tr,rowband="5 / 13"); kpis+=e; kpilay.append(l.replace("{col}",f"{1+i*6} / {1+(i+1)*6}"))

ai_body=('{{ Replace(CallText("'+AICONN+'", "CLAUDE-4-SONNET", '
 '"You are an analyst at CAVA, the Mediterranean fast-casual restaurant brand. In two concise sentences summarize performance given Revenue $" '
 '& Text(Round(Sum(['+MF+'/Revenue])/1000000,0)) & "M across " & Text(CountDistinct(['+MF+'/Location])) & " active locations (AUV about $" '
 '& Text(Round(Sum(['+MF+'/Revenue])/CountDistinct(['+MF+'/Location])/1000000,1)) & "M), and " & Text(Round(Sum(['+MF+'/Guests])/1000000,1)) '
 '& "M guest transactions. Note the top menu category and channel mix."), \'"\', \'\') }}')
ai_box={"id":"c-ai","kind":"container","style":dict(TINT)}
ai_ic={"id":"ai-ic","kind":"image","url":ic(IC_ZAP,CORAL,fill=CORAL),"style":{"fit":"contain"}}
ai_hd={"id":"ai-hd","kind":"text","body":"**AI insight**","verticalAlign":"middle","style":{"color":INK}}
ai_sum={"id":"txt-ai","kind":"text","body":ai_body,"verticalAlign":"middle","style":{"color":"#4A342A"}}
grain={"kind":"control","controlId":"DateGrain","id":"ctrl-grain","name":"Date Grain","controlType":"segmented","value":"Month","source":{"kind":"manual","valueType":"text","values":["Quarter","Month","Week","Day"]}}
colorby={"kind":"control","controlId":"ColorBy","id":"ctrl-colorby","name":"Color By","controlType":"segmented","value":"Menu category","source":{"kind":"manual","valueType":"text","values":["Menu category","Channel","Market"]}}
ctrl_menu={"kind":"control","controlId":"MenuF","id":"ctrl-menuf","name":"Menu category","controlType":"list","selectionMode":"multiple","mode":"include","values":[],"filters":[{"source":{"kind":"table","elementId":"tbl"},"columnId":"c-menu"}],"source":{"kind":"source","source":{"kind":"table","elementId":"tbl"},"columnId":"c-menu"}}
filt_c={"id":"c-filters","kind":"container","style":dict(CARD)}
sbar={"id":"sbar","kind":"bar-chart","source":{"elementId":"tbl","kind":"table"},
 "columns":[{"id":"sbm","formula":f'Switch([DateGrain],"Quarter",DateTrunc("quarter",[{MF}/Date]),"Week",DateTrunc("week",[{MF}/Date]),"Day",DateTrunc("day",[{MF}/Date]),DateTrunc("month",[{MF}/Date]))',"name":"Period","format":{"kind":"datetime","formatString":"%b %d, %Y"}},
            {"id":"sbv","formula":f"Sum([{MF}/Revenue])","name":"Revenue","format":CUR},
            {"id":"sbc","formula":f'Switch([ColorBy],"Menu category",[{MF}/Menu category],"Channel",[{MF}/Channel],"Market",[{MF}/Market])',"name":"Series"},
            {"id":"sb-menu","formula":f"[{MF}/Menu category]","name":"Menu category"},{"id":"sb-chan","formula":f"[{MF}/Channel]","name":"Channel"},{"id":"sb-mkt","formula":f"[{MF}/Market]","name":"Market"},{"id":"sb-loc","formula":f"[{MF}/Location]","name":"Location"},{"id":"sb-g","formula":f"[{MF}/Guests]","name":"Guests","format":NUM}],
 "xAxis":{"columnId":"sbm"},"yAxis":{"columnIds":["sbv"]},"color":{"by":"category","column":"sbc","scheme":["#E5533A","#6B7A3A","#5A2A4A","#C64A2E","#E0A458","#3E7C7B","#8A6F64","#B0407A"]},"stacking":"stacked",
 "dataLabel":{"labels":"hidden"},"legend":{"visibility":"visible"},"name":{"text":"Revenue by period & menu category","fontWeight":"bold","fontSize":15,"color":INK},"style":dict(CARD)}
# bespoke plugin: day-part revenue heatmap, bound to the synthetic day-part source
plug_c={"id":"c-plug","kind":"container","style":dict(CARD)}
plug_hd={"id":"plug-hd","kind":"text","body":"**Day-part revenue — by hour & weekday**","verticalAlign":"middle","style":{"color":INK}}
plug_el={"id":"daypartviz","kind":"plugin","pluginId":DAYPART_PLUGIN,"config":{"source":{"kind":"element","elementId":"daypart"},"day":"dp-day","hour":"dp-hour","value":"dp-rev"}}
heat={"id":"heat","kind":"pivot-table","source":{"elementId":"tbl","kind":"table"},
 "columns":[{"id":"hm","formula":f"[{MF}/Menu category]","name":"Menu"},{"id":"hp","formula":f"[{MF}/Market]","name":"Market"},{"id":"hv","formula":f"Sum([{MF}/Revenue])","name":"Revenue","format":CUR}],
 "rowsBy":[{"id":"hm"}],"columnsBy":[{"id":"hp"}],"values":["hv"],
 "conditionalFormats":[{"type":"single","columnIds":["hv"],"condition":"IsNotNull","style":{"backgroundColor":"#FBEBE2"}}],
 "name":{"text":"Revenue — Menu x Market","fontWeight":"bold","fontSize":15,"color":INK},"style":dict(CARD)}
book={"id":"book","kind":"pivot-table","source":{"elementId":"tbl","kind":"table"},
 "columns":[{"id":"bk-menu","formula":f"[{MF}/Menu category]","name":"Menu category"},
            {"id":"bk-rev","formula":f"Sum([{MF}/Revenue])","name":"Revenue","format":CUR},
            {"id":"bk-g","formula":f"Sum([{MF}/Guests])","name":"Guests","format":NUM},
            {"id":"bk-avg","formula":f"Sum([{MF}/Revenue])/Sum([{MF}/Guests])","name":"Avg check","format":{"kind":"number","formatString":"$,.2f"}}],
 "rowsBy":[{"id":"bk-menu"}],"values":["bk-rev","bk-g","bk-avg"],
 "conditionalFormats":[{"type":"single","columnIds":["bk-rev"],"condition":"IsNotNull","style":{"backgroundColor":"#FBEBE2"}}],
 "name":{"text":"Menu mix","fontWeight":"bold","fontSize":15,"color":INK},"style":dict(CARD)}

# ============ AGENTS + rail ============
AG_COPILOT={"id":"ag-copilot","name":"CAVA Copilot",
 "instructions":("You are a restaurant-performance analyst for CAVA, the Mediterranean fast-casual brand "
   "(menu categories: Grain Bowls, Pitas, Greens & Grains, Dips & Spreads, Sides, Beverages; channels In-Restaurant/Digital/Catering; six markets). "
   "Answer questions about menu-category performance, average check, AUV, channel mix, day-parts, and where price or traffic changes yield the most. Be concise and quantitative."),
 "dataSources":[{"kind":"table","elementId":"tbl"},{"kind":"table","elementId":"book2"}]}
SCEN_TOOL={"toolId":"create-scenario","kind":"action","name":"Create scenario","description":"Insert a new named scenario row into the Scenarios table so the user can model it.",
 "steps":[{"kind":"effect","effect":"insert-rows","table":"scenarios","values":{"sc-name":{"type":"agent-input"},"sc-status":{"type":"constant","value":{"type":"text","value":"Draft"}}}}]}
def ag_scenario(with_tool):
    a={"id":"ag-scenario","name":"Scenario Copilot",
       "instructions":("You are a menu & pricing scenario copilot for CAVA. Help model price, traffic, and attachment scenarios by menu category, and CREATE named scenarios on request using the create-scenario tool."),
       "dataSources":[{"kind":"table","elementId":"book2"}]}
    if with_tool: a["tools"]=[SCEN_TOOL]
    return a
def rail(n,with_agent,rows,agent_id):
    c={"id":f"c-chat{n}","kind":"container","style":dict(CARD)}
    ric={"id":f"chat-ic{n}","kind":"image","url":ic(IC_CHAT,CORAL),"style":{"fit":"contain"}}
    hdr={"id":f"chat-hdr{n}","kind":"text","body":"**Ask CAVA AI**","verticalAlign":"middle","style":{"color":INK}}
    if with_agent: inner={"id":f"chat{n}","kind":"chat","agentId":agent_id}
    else: inner={"id":f"chat{n}","kind":"text","verticalAlign":"middle","style":{"color":"#4A342A","backgroundColor":"#FBF1E9"},"body":"**Ask AI for Insights**\n\n- Which menu categories drive the most revenue per guest?\n- When are our day-part peaks?\n- What price + traffic mix hits a revenue target?\n\n_Agent slot — finish in the UI (Add element → Agent → point at the CAVA / Book tables)._"}
    lay=(f'  <GridContainer elementId="c-chat{n}" type="grid" gridColumn="18 / 25" gridRow="{rows}" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">\n'
         f'    <LayoutElement elementId="chat-ic{n}" gridColumn="1 / 3" gridRow="1 / 2"/>\n'
         f'    <LayoutElement elementId="chat-hdr{n}" gridColumn="3 / 13" gridRow="1 / 2"/>\n'
         f'    <LayoutElement elementId="chat{n}" gridColumn="1 / 13" gridRow="2 / 26"/>\n  </GridContainer>')
    return [c,ric,hdr,inner],lay
h1e,h1l=header("1","Restaurant Performance — Command Center","Revenue, AUV, locations & guests across markets")
def page1(with_agent):
    re,rl=rail(1,with_agent,"20 / 40","ag-copilot")
    elems=[tbl,daypart]+h1e+kpis+[ai_box,ai_ic,ai_hd,ai_sum,filt_c,grain,colorby,ctrl_menu,sbar,plug_c,plug_hd,plug_el,heat,book]+re
    lay=f"""<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg">
{h1l}
{chr(10).join(kpilay)}
  <GridContainer elementId="c-ai" type="grid" gridColumn="1 / 25" gridRow="13 / 17" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="repeat(4,1fr)"><LayoutElement elementId="ai-ic" gridColumn="1 / 2" gridRow="1 / 2"/><LayoutElement elementId="ai-hd" gridColumn="2 / 25" gridRow="1 / 2"/><LayoutElement elementId="txt-ai" gridColumn="2 / 25" gridRow="2 / 5"/></GridContainer>
  <GridContainer elementId="c-filters" type="grid" gridColumn="1 / 25" gridRow="17 / 20" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <LayoutElement elementId="ctrl-grain" gridColumn="1 / 9" gridRow="1 / 4"/><LayoutElement elementId="ctrl-colorby" gridColumn="9 / 17" gridRow="1 / 4"/><LayoutElement elementId="ctrl-menuf" gridColumn="17 / 25" gridRow="1 / 4"/>
  </GridContainer>
  <LayoutElement elementId="sbar" gridColumn="1 / 18" gridRow="20 / 40"/>
  <GridContainer elementId="c-plug" type="grid" gridColumn="1 / 25" gridRow="42 / 66" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto"><LayoutElement elementId="plug-hd" gridColumn="1 / 25" gridRow="1 / 2"/><LayoutElement elementId="daypartviz" gridColumn="1 / 25" gridRow="2 / 24"/></GridContainer>
  <LayoutElement elementId="heat" gridColumn="1 / 13" gridRow="68 / 84"/>
  <LayoutElement elementId="book" gridColumn="13 / 25" gridRow="68 / 84"/>
{rl}
</Page>"""
    return elems,lay

# ============ PAGE 2 — MENU & PRICING SCENARIO MODELER ============
ROWS=[('Grain Bowls','Signature',360000000,0.72),('Pitas','Signature',135000000,0.70),
 ('Greens & Grains','Signature',108000000,0.71),('Dips & Spreads','Add-ons',90000000,0.78),
 ('Sides','Add-ons',117000000,0.68),('Beverages','Add-ons',90000000,0.82)]
VALS=",".join(f"('{p}','{c}',{rev},{m})" for p,c,rev,m in ROWS)
SBASE=f"SELECT column1 AS MENU, column2 AS GRP, column3 AS BASE_REV, column4 AS BASE_MARGIN FROM (VALUES {VALS})"
sbase={"id":"sbase","kind":"table","name":"Menu Base","visibleAsSource":True,
 "source":{"connectionId":CONN,"kind":"sql","statement":SBASE},
 "columns":[{"id":"sb-menu2","formula":"[Custom SQL/MENU]","name":"Menu category"},{"id":"sb-grp","formula":"[Custom SQL/GRP]","name":"Group"},
            {"id":"sb-rev2","formula":"[Custom SQL/BASE_REV]","name":"Revenue","format":CUR},{"id":"sb-mar","formula":"[Custom SQL/BASE_MARGIN]","name":"Margin","format":PCT1}],
 "order":["sb-menu2","sb-grp","sb-rev2","sb-mar"]}
scenarios={"id":"scenarios","kind":"input-table","source":{"kind":"empty","connectionId":CONN},"inputMode":"edit","name":"Scenarios",
 "columns":[{"id":"sc-name","type":"text","name":"Scenario Name"},{"id":"sc-status","type":"text","name":"Status","values":["Draft","Submitted","Approved"],"pills":"color-by-option"}]}
spivot={"id":"spivot","kind":"pivot-table","name":"Scenario Pivot","visibleAsSource":True,
 "source":{"kind":"join","joins":[{"left":{"elementId":"sbase","kind":"table"},"right":{"elementId":"scenarios","kind":"table"},"columns":[{"left":"1","right":"1"}],"joinType":"left-outer"}],"primarySource":{"elementId":"sbase","kind":"table"}},
 "columns":[{"id":"pv-menu","formula":"[Menu Base/Menu category]","name":"Menu category"},
            {"id":"pv-grp","formula":"[Menu Base/Group]","name":"Group"},
            {"id":"pv-scen","formula":'Coalesce([Scenarios/Scenario Name],"Base Case")',"name":"Scenario"},
            {"id":"pv-rev","formula":"Sum([Menu Base/Revenue])","name":"Revenue","format":CUR},
            {"id":"pv-mar","formula":"Avg([Menu Base/Margin])","name":"Margin","format":PCT1}],
 "rowsBy":[{"id":"pv-menu"},{"id":"pv-grp"}],"values":["pv-rev","pv-mar"]}
assum={"id":"assum","kind":"input-table","source":{"kind":"linked","from":"spivot"},"inputMode":"edit","name":"Assumptions",
 "columns":[{"id":"ia-menu","key":"pv-menu"},{"id":"ia-grp","key":"pv-grp"},{"id":"ia-scen","key":"pv-scen"},{"id":"ia-rev","key":"pv-rev"},{"id":"ia-mar","key":"pv-mar"},
            {"id":"ia-price","type":"number","name":"Price Change %"},
            {"id":"ia-traf","type":"number","name":"Traffic Growth %"},
            {"id":"ia-att","type":"number","name":"Attachment %"},
            {"id":"ia-prev","formula":"[Revenue]*(1+Coalesce([Price Change %],0)/100)*(1+Coalesce([Traffic Growth %],0)/100)*(1+Coalesce([Attachment %],0)/100)","name":"Projected Revenue","format":CUR},
            {"id":"ia-pgp","formula":"[Projected Revenue]*[Margin]","name":"Projected Gross Profit","format":CUR}],
 "order":["ia-scen","ia-menu","ia-grp","ia-rev","ia-price","ia-traf","ia-att","ia-prev","ia-pgp"]}
book2={"id":"book2","kind":"table","name":"Book","visibleAsSource":True,
 "source":{"elementId":"assum","kind":"table"},
 "columns":[{"id":"bb-scen","formula":"[Assumptions/Scenario]","name":"Scenario"},
            {"id":"bb-menu","formula":"[Assumptions/Menu category]","name":"Menu category"},
            {"id":"bb-brev","formula":"[Assumptions/Revenue]","name":"Base Revenue","format":CUR},
            {"id":"bb-bgp","formula":"[Assumptions/Revenue]*[Assumptions/Margin]","name":"Base GP","format":CUR},
            {"id":"bb-prev","formula":"[Assumptions/Projected Revenue]","name":"Projected Revenue","format":CUR},
            {"id":"bb-pgp","formula":"[Assumptions/Projected Gross Profit]","name":"Projected GP","format":CUR}],
 "order":["bb-scen","bb-menu","bb-brev","bb-bgp","bb-prev","bb-pgp"]}
subs={"id":"subs","kind":"input-table","source":{"kind":"empty","connectionId":CONN},"inputMode":"edit","name":"Submissions",
 "columns":[{"id":"su-scen","type":"text","name":"Scenario"},{"id":"su-status","type":"text","name":"Status","values":["Submitted","Approved"],"pills":"color-by-option"}]}
selctrl={"kind":"control","controlId":"scenarioSelect","id":"ctrl-sel","name":"Active scenario","controlType":"list","selectionMode":"single","mode":"include","value":"Base Case",
 "filters":[{"source":{"kind":"table","elementId":"book2"},"columnId":"bb-scen"}],
 "source":{"kind":"source","source":{"kind":"table","elementId":"book2"},"columnId":"bb-scen"}}
createbtn_tb={"id":"createbtn_tb","kind":"button","text":"Create scenario","appearance":"filled","actions":[{"id":"o1","trigger":"on-click","effects":[{"effect":"open-overlay","overlayId":"createModal"}]}]}
submitbtn={"id":"submitbtn","kind":"button","text":"Submit","appearance":"outline","actions":[{"id":"s1","trigger":"on-click","effects":[{"effect":"insert-rows","table":"subs","values":{"su-scen":{"type":"control","control":"scenarioSelect"},"su-status":{"type":"constant","value":{"type":"text","value":"Submitted"}}}}]}]}
approvebtn={"id":"approvebtn","kind":"button","text":"Approve","appearance":"outline","actions":[{"id":"a1","trigger":"on-click","effects":[{"effect":"insert-rows","table":"subs","values":{"su-scen":{"type":"control","control":"scenarioSelect"},"su-status":{"type":"constant","value":{"type":"text","value":"Approved"}}}}]}]}
namectrl={"kind":"control","controlId":"newScenarioName","id":"ctrl-name","name":"Scenario name","controlType":"text","mode":"equals","case":"insensitive","includeNulls":"when-no-value-is-selected","showOperators":False}
createbtn={"id":"createbtn","kind":"button","text":"Create scenario","appearance":"filled","actions":[{"id":"c1","trigger":"on-click","effects":[
    {"effect":"insert-rows","table":"scenarios","values":{"sc-name":{"type":"control","control":"newScenarioName"},"sc-status":{"type":"constant","value":{"type":"text","value":"Draft"}}}},
    {"effect":"set-control-value","control":"scenarioSelect","value":{"type":"control","control":"newScenarioName"}},
    {"effect":"clear-control","scope":{"type":"control","control":"newScenarioName"}},
    {"effect":"close-overlay"}]}]}
cancelbtn={"id":"cancelbtn","kind":"button","text":"Cancel","appearance":"outline","actions":[{"id":"x1","trigger":"on-click","effects":[{"effect":"close-overlay"}]}]}
mtitle={"id":"mtitle","kind":"text","body":"### New scenario\nName it, then Create. It clones the current book for every menu category — edit the assumptions in the grid.","verticalAlign":"middle","style":{"color":INK}}
modal={"id":"createModal","name":"Create Scenario","type":"modal","modal":{"width":"small","header":{"title":"New scenario","showCloseIcon":"hidden"},"footer":{"primaryCta":{"visible":"hidden"},"secondaryCta":{"visible":"hidden"}}},"elements":[mtitle,namectrl,createbtn,cancelbtn]}
BREV='Sum([Book/Base Revenue])'; BGP='Sum([Book/Base GP])'; PREV='Sum([Book/Projected Revenue])'; PGP='Sum([Book/Projected GP])'
P2K=[("p1",ic(IC_DOLLAR,W),"PROJECTED REVENUE",PREV,CUR,BREV),
     ("p2",ic(IC_DOLLAR,W),"PROJECTED GROSS PROFIT",PGP,CUR,BGP),
     ("p3",ic(IC_TREND,W),"BLENDED GROSS MARGIN",f"{PGP}/{PREV}",PCT1,f"{BGP}/{BREV}"),
     ("p4",ic(IC_ZAP,W,fill=W),"UPLIFT VS BASELINE",f"{PREV}/{BREV}-1",PCT2,None)]
C2=[]; C2L=[]
for i,(elid,icn,title,valf,fmt,compf) in enumerate(P2K):
    e,l=kpi(elid,"book2",icn,title,valf,fmt,compf,KG[i],trend=None,rowband="8 / 16")
    C2+=e; C2L.append(l.replace("{col}",f"{1+i*6} / {1+(i+1)*6}"))
cbar={"id":"cbar","kind":"bar-chart","source":{"elementId":"book2","kind":"table"},
 "columns":[{"id":"cb-menu","formula":"[Book/Menu category]","name":"Menu category"},
            {"id":"cb-cat","formula":'"Projected revenue"',"name":"Series"},
            {"id":"cb-prev","formula":"Sum([Book/Projected Revenue])","name":"Projected Revenue","format":CUR}],
 "xAxis":{"columnId":"cb-menu","sort":{"by":"cb-prev","direction":"descending"}},"yAxis":{"columnIds":["cb-prev"]},
 "color":{"by":"category","column":"cb-cat","scheme":["#E5533A"]},
 "legend":{"visibility":"hidden"},"name":{"text":"Projected revenue by menu category — active scenario","fontWeight":"bold","fontSize":15,"color":INK},"style":dict(CARD)}
instr_c={"id":"c-instr","kind":"container","style":dict(TINT)}
instr_ic={"id":"instr-ic","kind":"image","url":ic(IC_LIST,CORAL),"style":{"fit":"contain"}}
instr_hd={"id":"instr-hd","kind":"text","body":"**How the scenario modeler works**","verticalAlign":"middle","style":{"color":INK}}
instr={"id":"instr","kind":"text","body":("**1** — **Create** a named scenario (clones the current book); pick it with **Active scenario**.  **2** — In the grid, type **Price Change %**, **Traffic Growth %**, **Attachment %** per menu category.  **3** — Cards, chart & Copilot re-project instantly. **Submit → Approve** to lock a plan. Leave a cell blank to hold a driver flat."),
 "verticalAlign":"middle","style":{"color":"#4A342A"}}
tb_c={"id":"c-tb","kind":"container","style":dict(CARD)}
h2e,h2l=header("2","Menu & Pricing Scenario Modeler","Model price, traffic & attachment by menu category")
def page2(with_agent):
    re,rl=rail(2,with_agent,"21 / 56","ag-scenario")
    elems=[tb_c,sbase,scenarios,spivot,book2,subs]+h2e+[selctrl,createbtn_tb,submitbtn,approvebtn]+C2+[instr_c,instr_ic,instr_hd,instr,cbar,assum]+re
    lay=f"""<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="model">
{h2l}
  <GridContainer elementId="c-tb" type="grid" gridColumn="1 / 25" gridRow="5 / 8" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <LayoutElement elementId="ctrl-sel" gridColumn="1 / 10" gridRow="1 / 4"/>
    <LayoutElement elementId="createbtn_tb" gridColumn="10 / 17" gridRow="1 / 4"/>
    <LayoutElement elementId="submitbtn" gridColumn="17 / 21" gridRow="1 / 4"/>
    <LayoutElement elementId="approvebtn" gridColumn="21 / 25" gridRow="1 / 4"/>
  </GridContainer>
{chr(10).join(C2L)}
  <GridContainer elementId="c-instr" type="grid" gridColumn="1 / 25" gridRow="17 / 21" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="repeat(4,1fr)"><LayoutElement elementId="instr-ic" gridColumn="1 / 2" gridRow="1 / 2"/><LayoutElement elementId="instr-hd" gridColumn="2 / 25" gridRow="1 / 2"/><LayoutElement elementId="instr" gridColumn="2 / 25" gridRow="2 / 5"/></GridContainer>
  <LayoutElement elementId="assum" gridColumn="1 / 18" gridRow="21 / 40"/>
  <LayoutElement elementId="cbar" gridColumn="1 / 18" gridRow="40 / 56"/>
{rl}
</Page>"""
    return elems,lay
modal_lay='<Page type="grid" gridTemplateColumns="repeat(24,1fr)" gridTemplateRows="auto" id="createModal"><LayoutElement elementId="mtitle" gridColumn="1 / 25" gridRow="1 / 3"/><LayoutElement elementId="ctrl-name" gridColumn="1 / 25" gridRow="3 / 5"/><LayoutElement elementId="cancelbtn" gridColumn="13 / 19" gridRow="5 / 7"/><LayoutElement elementId="createbtn" gridColumn="19 / 25" gridRow="5 / 7"/></Page>'
theme={"colors":{"text":INK,"highlight":CORAL,"success":"#4E8A3A","warning":"#E0A458","danger":"#C64A2E","darkMode":"hidden"},
 "colorOverrides":{"backgroundCanvas":"#FFFFFF","canvasBackground":"#F6EEE7"},
 "categoricalScheme":["#FFFFFF","#E5533A","#6B7A3A","#5A2A4A","#C64A2E","#8A6F64","#E0A458","#3E7C7B"],
 "fonts":{"textFont":"Inter","dataFont":"Inter"},"pageWidth":"full","tableStyles":{"preset":"presentation","cellSpacing":"small"}}
def build(mode):
    wa=mode!="none"
    p1e,p1l=page1(wa); p2e,p2l=page2(wa)
    s={"name":"CAVA — Restaurant Performance","folderId":FOLDER,"schemaVersion":1,
     "pages":[{"id":"pg","name":"Command Center","elements":p1e},{"id":"model","name":"Scenario Modeler","elements":p2e},modal],
     "layout":'<?xml version="1.0" encoding="utf-8"?>\n'+p1l+p2l+modal_lay,"themeOverrides":theme}
    if wa: s["agents"]=[AG_COPILOT, ag_scenario(mode=="tool")]
    return s
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
def post(s):
    r=urllib.request.Request(BASE+"/v2/workbooks/spec",data=json.dumps(s).encode(),headers=H,method="POST")
    resp=urllib.request.urlopen(r,timeout=120).read().decode()
    wid=[l.split()[-1] for l in resp.splitlines() if "workbookId" in l]
    url=json.loads(urllib.request.urlopen(urllib.request.Request(BASE+f"/v2/workbooks/{wid[0]}",headers=H),timeout=30).read().decode()).get("url") if wid else None
    return ("success: true" in resp), url, resp
done=False
for mode in ["tool","basic","none"]:
    spec=build(mode)
    if qa(spec): print("ABORT malformed SVG"); sys.exit(1)
    try:
        ok,url,resp=post(spec); print(f"POST (agent mode={mode}):","ACCEPTED" if ok else resp[:300])
        if ok: print("URL:",url); done=True; break
    except urllib.error.HTTPError as e:
        raw=e.read().decode()
        try: msg=json.loads(raw).get("message","")
        except Exception: msg=raw
        print(f"  mode={mode} failed: {e.code} {msg[:220]}")
if not done: print("ALL MODES FAILED")
