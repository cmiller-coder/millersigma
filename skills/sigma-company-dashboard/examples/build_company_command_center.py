"""
Company Command Center - CANONICAL generator (current standard). Worked example: DoorDash.
Clone and swap the marked pieces for any prospect.

PRODUCES 2 pages: (1) Command Center - brand-gradient header + REAL white company logo +
4 COMPARATIVE KPI cards (Current value + native Delta-vs-Prior + Prior value + sparkline),
AI insight (CallText), Color-By/filter bar, a metric bar chart, a BESPOKE registered plugin
full-width, two side-by-side pivots + an agent rail. (2) Scenario Modeler - linked input-table
drivers -> projected KPIs + create/submit/approve, a second agent with an insert-rows tool.

RE-SKIN (swap only these): brand palette (RED/DARK/ORANGE, KG gradients, HDRBG); logo via
scripts/fetch_logo.py then recolor WHITE by filling every <path>/<polygon> (NOT the <svg> root,
else Sigma renders it black) -> company_white.svg (or set LOGO_SVG); data reshape SQL + KDEFS
(the 4 KPIs); a genuinely non-native plugin, registered (scripts/register_plugin.py), set PLUGIN_ID.

Run: PLUGIN_ID=<id> LOGO_SVG=company_white.svg python3 build_company_command_center.py <BASE> <TOKEN> <CONN> <FOLDER>

KPI STANDARD (do not regress): each card kpi-chart has a value column AND a comparison column
(comparisonColumn + comparison display delta); the metric title is the kpi NATIVE name, color white.
Never bake KPI titles as SVG images.
"""
import json,sys,os,base64,urllib.request,urllib.error,xml.dom.minidom as _MD
BASE,TOKEN,CONN,FOLDER=sys.argv[1:5]
AICONN="SNOWFLAKE.CORTEX.COMPLETE"; CLOCK=os.environ.get("PLUGIN_ID","REPLACE_WITH_YOUR_PLUGIN_ID")
H={"Authorization":"Bearer "+TOKEN,"Content-Type":"application/json"}
def b64(s): return base64.b64encode(s.encode()).decode()
CUR={"kind":"number","formatString":"$.3~s","currencySymbol":"$","decimalSymbol":".","digitGroupingSymbol":",","digitGroupingSize":[3]}
NUM={"kind":"number","formatString":",.3~s"}; PCT2={"kind":"number","formatString":"+,.1%"}; PCT1={"kind":"number","formatString":".1%"}
INK="#191919"; SLATE="#8A8F94"; RED="#EB1700"; DARK="#191919"; ORANGE="#F0872E"; W="#FFFFFF"
CARD={"backgroundColor":"#FFFFFF","borderColor":"#ECEDEF","borderWidth":1,"borderRadius":"round"}
TINT={"backgroundColor":"#FCEEEA","borderColor":"#F6D9CF","borderWidth":1,"borderRadius":"round"}
def grad(a,b):
    return "data:image/svg+xml;base64,"+b64(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 240" preserveAspectRatio="xMidYMid slice"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient></defs><rect width="400" height="240" fill="url(#g)"/></svg>')
KG=[grad("#8A0F1E","#EB1700"),grad("#6E0C18","#C0453A"),grad("#B4571C","#F0872E"),grad("#241318","#5B2340")]
def esc(s): return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def timg(text,size=34,color="#FFFFFF",weight=800,anchor="start"):
    t=esc(text); W_=int(len(text)*size*0.60)+24; Hh=int(size*1.7)
    x=3 if anchor=="start" else (W_//2 if anchor=="middle" else W_-3)
    svg=(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W_} {Hh}" preserveAspectRatio="xMinYMid meet">'
     f'<text x="{x}" y="{int(Hh*0.70)}" text-anchor="{anchor}" font-family="Inter,Arial,sans-serif" font-weight="{weight}" font-size="{size}" fill="{color}">{t}</text></svg>')
    return "data:image/svg+xml;base64,"+b64(svg)
# REAL official DoorDash wordmark, fetched & recolored white
logo_uri="data:image/svg+xml;base64,"+b64(open(os.environ.get("LOGO_SVG","company_white.svg")).read())
HDRBG=('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 210" preserveAspectRatio="xMidYMid slice">'
  '<defs>'
  '<linearGradient id="hg" x1="0" y1="0" x2="1" y2="0.35"><stop offset="0" stop-color="#7A0E1F"/><stop offset="0.5" stop-color="#C0121F"/><stop offset="1" stop-color="#EB1700"/></linearGradient>'
  '<radialGradient id="glow" cx="0.84" cy="0.16" r="0.55"><stop offset="0" stop-color="#FFFFFF" stop-opacity="0.16"/><stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></radialGradient>'
  '</defs>'
  '<rect width="1600" height="210" fill="url(#hg)"/><rect width="1600" height="210" fill="url(#glow)"/>'
  '<g fill="none" stroke="#FFD9CF" stroke-opacity="0.22" stroke-width="1.4" transform="translate(1380,90)"><circle r="42"/><circle r="78"/><circle r="114"/><line x1="-140" y1="0" x2="140" y2="0"/><line x1="0" y1="-140" x2="0" y2="140"/></g>'
  '</svg>')
HDRBG_URI="data:image/svg+xml;base64,"+b64(HDRBG)
def header(sfx,title,subtitle):
    c={"id":f"c-hdr{sfx}","kind":"container","style":{"borderRadius":"round"},"backgroundImage":{"url":HDRBG_URI,"style":{"fit":"cover"}}}
    lg={"id":f"logo{sfx}","kind":"image","url":logo_uri,"style":{"fit":"scale-down"}}
    tt={"id":f"ttl{sfx}","kind":"image","url":timg(title,34,"#FFFFFF",800,"middle"),"style":{"fit":"scale-down"}}
    sb={"id":f"sub{sfx}","kind":"image","url":timg(subtitle,17,"#FFE1D8",500,"middle"),"style":{"fit":"scale-down"}}
    lay=(f'  <GridContainer elementId="c-hdr{sfx}" type="grid" gridColumn="1 / 25" gridRow="1 / 5" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="repeat(6,1fr)">\n'
         f'    <LayoutElement elementId="logo{sfx}" gridColumn="1 / 8" gridRow="2 / 6"/>\n'
         f'    <LayoutElement elementId="ttl{sfx}" gridColumn="8 / 21" gridRow="2 / 4"/>\n'
         f'    <LayoutElement elementId="sub{sfx}" gridColumn="8 / 21" gridRow="4 / 6"/>\n  </GridContainer>')
    return [c,lg,tt,sb],lay
def _spark(elid,src,trend):
    return {"id":f"ln-{elid}","kind":"line-chart","source":{"elementId":src,"kind":"table"},
        "columns":[{"id":f"ln-{elid}m","formula":f"[{MF}/Month]","name":"Month"},{"id":f"ln-{elid}v","formula":trend,"name":"Trend"}],
        "xAxis":{"columnId":f"ln-{elid}m","format":{"marks":"none","labels":"hidden"}},
        "yAxis":{"columnIds":[f"ln-{elid}v"],"format":{"labels":"hidden","marks":"none","scale":{"type":"linear","zero":False,"hideZeroLine":True}}},
        "name":{"visibility":"hidden"},"legend":{"visibility":"hidden"},"lineAreaStyle":{"interpolation":"monotone"},"style":{"backgroundColor":"transparent","padding":"none"}}
def card(elid,src,title,v1f,v2f,v2lab,fmt,g,trend=None,rowband="5 / 13"):
    # Current value (native white title) + native COMPARISON delta vs prior + Prior value shown side-by-side.
    cid=f"c-{elid}"
    cont={"id":cid,"kind":"container","style":{"borderRadius":"round"},"backgroundImage":{"url":g,"style":{"fit":"cover"}}}
    els=[cont]; inner=""
    if v2f:
        left={"id":f"k-{elid}c","kind":"kpi-chart","source":{"elementId":src,"kind":"table"},
          "columns":[{"id":f"k-{elid}cv","formula":v1f,"name":title,"format":fmt},
                     {"id":f"k-{elid}cc","formula":v2f,"name":"vs "+v2lab,"format":fmt}],
          "value":{"columnId":f"k-{elid}cv","color":W,"fontSize":32},
          "comparisonColumn":{"columnId":f"k-{elid}cc"},
          "comparison":{"display":"delta","colorGood":"#CDEBB8","colorBad":"#FFCFC7","fontSize":13},
          "name":{"text":title,"color":W,"fontSize":15},"layout":{"anchor":"middle"},"style":{"backgroundColor":"transparent","padding":"none"}}
        right={"id":f"k-{elid}p","kind":"kpi-chart","source":{"elementId":src,"kind":"table"},
          "columns":[{"id":f"k-{elid}pv","formula":v2f,"name":v2lab,"format":fmt}],
          "value":{"columnId":f"k-{elid}pv","color":W,"fontSize":28},
          "name":{"text":v2lab,"color":W,"fontSize":13},"layout":{"anchor":"middle"},"style":{"backgroundColor":"transparent","padding":"none"}}
        els+=[left,right]
        inner+=(f'    <LayoutElement elementId="k-{elid}c" gridColumn="1 / 7" gridRow="1 / 9"/>\n'
                f'    <LayoutElement elementId="k-{elid}p" gridColumn="7 / 13" gridRow="1 / 9"/>\n')
    else:
        left={"id":f"k-{elid}c","kind":"kpi-chart","source":{"elementId":src,"kind":"table"},
          "columns":[{"id":f"k-{elid}cv","formula":v1f,"name":title,"format":fmt}],
          "value":{"columnId":f"k-{elid}cv","color":W,"fontSize":40},
          "name":{"text":title,"color":W,"fontSize":16},"layout":{"anchor":"middle"},"style":{"backgroundColor":"transparent","padding":"none"}}
        els.append(left); inner+=f'    <LayoutElement elementId="k-{elid}c" gridColumn="1 / 13" gridRow="1 / 9"/>\n'
    if trend:
        els.append(_spark(elid,src,trend)); inner+=f'    <LayoutElement elementId="ln-{elid}" gridColumn="1 / 13" gridRow="9 / 12"/>\n'
    lay=(f'  <GridContainer elementId="{cid}" type="grid" gridColumn="{{col}}" gridRow="{rowband}" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="repeat(12,1fr)">\n'+inner+'  </GridContainer>')
    return els,lay

# ============ PAGE 1 DATA (food-delivery reshape) ============
MF="DoorDash"
CATS=['Restaurants','Grocery','Convenience','Alcohol','Retail','DashMart']
SUBS=['American','Pizza & Italian','Asian','Mexican','Grocery & essentials','Snacks & sweets']
REG=['Northeast','Southeast','Midwest','Southwest','West','Pacific']
TAKE=[0.15,0.08,0.18,0.20,0.12,0.22]
def arr(xs): return "ARRAY_CONSTRUCT("+",".join("'"+str(x).replace("'","''")+"'" for x in xs)+")"
CATARR=arr(CATS); SUBARR=arr(SUBS); REGARR=arr(REG); TAKEARR="ARRAY_CONSTRUCT("+",".join(str(x) for x in TAKE)+")"
SQL=f"""WITH b0 AS (
  SELECT *, MOD(ABS(HASH(PRODUCT_FAMILY)),6) AS IDX, DATE_TRUNC('month',DATE) AS USE_MONTH FROM SE_DEMO_DB.BIG_BUYS.BIG_BUYS_POS
  WHERE PRODUCT_FAMILY IS NOT NULL AND PRODUCT_LINE IS NOT NULL AND STORE_STATE IS NOT NULL AND ORDER_NUMBER IS NOT NULL
), base AS (
  SELECT ORDER_NUMBER, DATE, USE_MONTH,
    GET({CATARR}, IDX)::string AS CATEGORY,
    GET({SUBARR}, MOD(ABS(HASH(PRODUCT_LINE)),6))::string AS SUBCATEGORY,
    GET({REGARR}, MOD(ABS(HASH(STORE_STATE)),6))::string AS REGION,
    MOD(ABS(HASH(CUSTOMER_NAME)),5000000) AS CONSUMER,
    QUANTITY*PRICE*8.0 AS GOV, QUANTITY*PRICE*8.0*GET({TAKEARR}, IDX) AS REVENUE
  FROM b0
), m AS (SELECT MAX(USE_MONTH) MAXM FROM base)
SELECT base.*, CASE WHEN USE_MONTH>DATEADD('month',-12,(SELECT MAXM FROM m)) THEN 'Current Period'
  WHEN USE_MONTH>DATEADD('month',-24,(SELECT MAXM FROM m)) THEN 'Prior Year' ELSE NULL END AS PERIOD_NAME
FROM base"""
COLS=[("c-date","DATE","Date"),("c-month","USE_MONTH","Month"),("c-period","PERIOD_NAME","Period Name"),
 ("c-cat","CATEGORY","Category"),("c-sub","SUBCATEGORY","Subcategory"),("c-reg","REGION","Region"),
 ("c-order","ORDER_NUMBER","Order"),("c-cons","CONSUMER","Consumer"),("c-gov","GOV","GOV"),("c-rev","REVENUE","Revenue")]
tbl={"id":"tbl","kind":"table","source":{"connectionId":CONN,"statement":SQL,"kind":"sql"},
 "columns":[{"id":c,"formula":f"[Custom SQL/{s}]","name":d} for c,s,d in COLS],"name":MF,"order":[c[0] for c in COLS],"visibleAsSource":True}
# demand-clock source: synthetic 24-hour order profile
PROFILE=[3,2,1,1,1,2,5,9,11,9,10,22,26,18,11,10,13,20,30,33,27,17,9,5]
PROFARR="ARRAY_CONSTRUCT("+",".join(str(x) for x in PROFILE)+")"
DEMSQL=f"""WITH g AS (SELECT SEQ4() h FROM TABLE(GENERATOR(ROWCOUNT=>24)))
SELECT h AS HOUR, ROUND(GET({PROFARR}, h)*25000) AS ORDERS FROM g"""
demand={"id":"demand","kind":"table","name":"Hourly Demand","visibleAsSource":True,
 "source":{"connectionId":CONN,"kind":"sql","statement":DEMSQL},
 "columns":[{"id":"dm-hour","formula":"[Custom SQL/HOUR]","name":"Hour"},{"id":"dm-orders","formula":"[Custom SQL/ORDERS]","name":"Orders","format":NUM}],
 "order":["dm-hour","dm-orders"]}

_P='[{0}/Period Name]="§"'.format(MF)
KDEFS=[("gov","MARKETPLACE GOV",f'SumIf([{MF}/GOV],{_P})',CUR,f'Sum([{MF}/GOV])'),
       ("rev","TOTAL REVENUE",f'SumIf([{MF}/Revenue],{_P})',CUR,f'Sum([{MF}/Revenue])'),
       ("ord","TOTAL ORDERS",f'CountDistinct(If({_P},[{MF}/Order],Null))',NUM,f'CountDistinct([{MF}/Order])'),
       ("take","TAKE RATE",f'SumIf([{MF}/Revenue],{_P})/SumIf([{MF}/GOV],{_P})',PCT1,f'Sum([{MF}/Revenue])/Sum([{MF}/GOV])')]
kpis=[]; kpilay=[]
for i,(elid,t,mf,fmt,tr) in enumerate(KDEFS):
    cur=mf.replace("§","Current Period"); pri=mf.replace("§","Prior Year")
    e,l=card(elid,"tbl",t,cur,pri,"Prior Year",fmt,KG[i],trend=tr,rowband="5 / 13"); kpis+=e; kpilay.append(l.replace("{col}",f"{1+i*6} / {1+(i+1)*6}"))

ai_body=('{{ Replace(CallText("'+AICONN+'", "CLAUDE-4-SONNET", '
 '"You are a marketplace analyst at DoorDash (categories: Restaurants, Grocery, Convenience, Alcohol, Retail, DashMart). '
 'In two concise sentences summarize the marketplace given Gross Order Value of $" '
 '& Text(Round(Sum(['+MF+'/GOV])/1000000000,1)) & "B, Revenue of $" '
 '& Text(Round(Sum(['+MF+'/Revenue])/1000000000,1)) & "B, and a blended take rate of " '
 '& Text(Round(Sum(['+MF+'/Revenue])/Sum(['+MF+'/GOV])*100,1)) & "%. Note the leading category and the daypart demand pattern."), \'"\', \'\') }}')
ai_box={"id":"c-ai","kind":"container","style":dict(TINT)}
ai_ic={"id":"ai-ic","kind":"image","url":"data:image/svg+xml;base64,"+b64('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="'+RED+'" stroke="'+RED+'" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>'),"style":{"fit":"contain"}}
ai_hd={"id":"ai-hd","kind":"text","body":"**AI insight**","verticalAlign":"middle","style":{"color":INK}}
ai_sum={"id":"txt-ai","kind":"text","body":ai_body,"verticalAlign":"middle","style":{"color":"#3A2C2C"}}
grain={"kind":"control","controlId":"DateGrain","id":"ctrl-grain","name":"Date Grain","controlType":"segmented","value":"Month","source":{"kind":"manual","valueType":"text","values":["Quarter","Month","Week","Day"]}}
colorby={"kind":"control","controlId":"ColorBy","id":"ctrl-colorby","name":"Color By","controlType":"segmented","value":"Category","source":{"kind":"manual","valueType":"text","values":["Category","Subcategory","Region"]}}
ctrl_cat={"kind":"control","controlId":"CatF","id":"ctrl-catf","name":"Category","controlType":"list","selectionMode":"multiple","mode":"include","values":[],"filters":[{"source":{"kind":"table","elementId":"tbl"},"columnId":"c-cat"}],"source":{"kind":"source","source":{"kind":"table","elementId":"tbl"},"columnId":"c-cat"}}
filt_c={"id":"c-filters","kind":"container","style":dict(CARD)}
sbar={"id":"sbar","kind":"bar-chart","source":{"elementId":"tbl","kind":"table"},
 "columns":[{"id":"sbm","formula":f'Switch([DateGrain],"Quarter",DateTrunc("quarter",[{MF}/Date]),"Week",DateTrunc("week",[{MF}/Date]),"Day",DateTrunc("day",[{MF}/Date]),DateTrunc("month",[{MF}/Date]))',"name":"Period","format":{"kind":"datetime","formatString":"%b %d, %Y"}},
            {"id":"sbv","formula":f"Sum([{MF}/GOV])","name":"GOV","format":CUR},
            {"id":"sbc","formula":f'Switch([ColorBy],"Category",[{MF}/Category],"Subcategory",[{MF}/Subcategory],"Region",[{MF}/Region])',"name":"Series"},
            {"id":"sb-cat","formula":f"[{MF}/Category]","name":"Category"},{"id":"sb-sub","formula":f"[{MF}/Subcategory]","name":"Subcategory"},{"id":"sb-reg","formula":f"[{MF}/Region]","name":"Region"}],
 "xAxis":{"columnId":"sbm"},"yAxis":{"columnIds":["sbv"]},"color":{"by":"category","column":"sbc","scheme":["#EB1700","#B3122E","#F0872E","#C0453A","#5B2340","#8A8F94","#2E6FB0","#0E7C7B"]},"stacking":"stacked",
 "dataLabel":{"labels":"hidden"},"legend":{"visibility":"visible"},"name":{"text":"Gross order value by period & category","fontWeight":"bold","fontSize":15,"color":INK},"style":dict(CARD)}
clock_c={"id":"c-clock","kind":"container","style":dict(CARD)}
clock_hd={"id":"clock-hd","kind":"text","body":"**Order demand by hour of day (daypart)**","verticalAlign":"middle","style":{"color":INK}}
clock_el={"id":"clockviz","kind":"plugin","pluginId":CLOCK,"config":{"source":{"kind":"element","elementId":"demand"},"hour":"dm-hour","value":"dm-orders"}}
heat={"id":"heat","kind":"pivot-table","source":{"elementId":"tbl","kind":"table"},
 "columns":[{"id":"hm","formula":f"[{MF}/Category]","name":"Category"},{"id":"hp","formula":f"[{MF}/Region]","name":"Region"},{"id":"hv","formula":f"Sum([{MF}/GOV])","name":"GOV","format":CUR}],
 "rowsBy":[{"id":"hm"}],"columnsBy":[{"id":"hp"}],"values":["hv"],
 "conditionalFormats":[{"type":"single","columnIds":["hv"],"condition":"IsNotNull","style":{"backgroundColor":"#FCE3DC"}}],
 "name":{"text":"GOV — Category x Region","fontWeight":"bold","fontSize":15,"color":INK},"style":dict(CARD)}
book={"id":"book","kind":"pivot-table","source":{"elementId":"tbl","kind":"table"},
 "columns":[{"id":"bk-cat","formula":f"[{MF}/Category]","name":"Category"},
            {"id":"bk-gov","formula":f"Sum([{MF}/GOV])","name":"GOV","format":CUR},
            {"id":"bk-rev","formula":f"Sum([{MF}/Revenue])","name":"Revenue","format":CUR},
            {"id":"bk-take","formula":f"Sum([{MF}/Revenue])/Sum([{MF}/GOV])","name":"Take rate","format":PCT1}],
 "rowsBy":[{"id":"bk-cat"}],"values":["bk-gov","bk-rev","bk-take"],
 "conditionalFormats":[{"type":"single","columnIds":["bk-gov"],"condition":"IsNotNull","style":{"backgroundColor":"#FCE3DC"}}],
 "name":{"text":"Category mix","fontWeight":"bold","fontSize":15,"color":INK},"style":dict(CARD)}

AG_COPILOT={"id":"ag-copilot","name":"DoorDash Copilot",
 "instructions":("You are a marketplace analyst for DoorDash (categories Restaurants, Grocery, Convenience, Alcohol, Retail, DashMart; six regions). "
   "Answer questions about gross order value (GOV), revenue, take rate by category, regional mix, orders, active consumers, hour-of-day demand patterns, and how order growth or take-rate changes move the marketplace. Be concise and quantitative."),
 "dataSources":[{"kind":"table","elementId":"tbl"},{"kind":"table","elementId":"book2"}]}
SCEN_TOOL={"toolId":"create-scenario","kind":"action","name":"Create scenario","description":"Insert a new named scenario row into the Scenarios table so the user can model it.",
 "steps":[{"kind":"effect","effect":"insert-rows","table":"scenarios","values":{"sc-name":{"type":"agent-input"},"sc-status":{"type":"constant","value":{"type":"text","value":"Draft"}}}}]}
def ag_scenario(with_tool):
    a={"id":"ag-scenario","name":"Scenario Copilot","instructions":("You are a growth & margin scenario copilot for DoorDash. Help model order growth, take-rate changes, and delivery cost by category, and CREATE named scenarios on request using the create-scenario tool."),
       "dataSources":[{"kind":"table","elementId":"book2"}]}
    if with_tool: a["tools"]=[SCEN_TOOL]
    return a
def rail(n,with_agent,rows,agent_id):
    c={"id":f"c-chat{n}","kind":"container","style":dict(CARD)}
    ric={"id":f"chat-ic{n}","kind":"image","url":"data:image/svg+xml;base64,"+b64('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="'+RED+'" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>'),"style":{"fit":"contain"}}
    hdr={"id":f"chat-hdr{n}","kind":"text","body":"**Ask DoorDash AI**","verticalAlign":"middle","style":{"color":INK}}
    if with_agent: inner={"id":f"chat{n}","kind":"chat","agentId":agent_id}
    else: inner={"id":f"chat{n}","kind":"text","verticalAlign":"middle","style":{"color":"#3A2C2C","backgroundColor":"#FCEEEA"},"body":"**Ask AI for Insights**\n\n- Which category drives the most GOV?\n- When does demand peak during the day?\n- What order + take-rate mix hits a revenue target?"}
    lay=(f'  <GridContainer elementId="c-chat{n}" type="grid" gridColumn="18 / 25" gridRow="{rows}" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">\n'
         f'    <LayoutElement elementId="chat-ic{n}" gridColumn="1 / 3" gridRow="1 / 2"/>\n'
         f'    <LayoutElement elementId="chat-hdr{n}" gridColumn="3 / 13" gridRow="1 / 2"/>\n'
         f'    <LayoutElement elementId="chat{n}" gridColumn="1 / 13" gridRow="2 / 26"/>\n  </GridContainer>')
    return [c,ric,hdr,inner],lay
h1e,h1l=header("1","Marketplace Command Center","GOV, revenue, orders & take rate across categories")
def page1(with_agent):
    re,rl=rail(1,with_agent,"20 / 41","ag-copilot")
    elems=[tbl,demand]+h1e+kpis+[ai_box,ai_ic,ai_hd,ai_sum,filt_c,grain,colorby,ctrl_cat,sbar,clock_c,clock_hd,clock_el,heat,book]+re
    lay=f"""<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg">
{h1l}
{chr(10).join(kpilay)}
  <GridContainer elementId="c-ai" type="grid" gridColumn="1 / 25" gridRow="13 / 17" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="repeat(4,1fr)"><LayoutElement elementId="ai-ic" gridColumn="1 / 2" gridRow="1 / 2"/><LayoutElement elementId="ai-hd" gridColumn="2 / 25" gridRow="1 / 2"/><LayoutElement elementId="txt-ai" gridColumn="2 / 25" gridRow="2 / 5"/></GridContainer>
  <GridContainer elementId="c-filters" type="grid" gridColumn="1 / 25" gridRow="17 / 20" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <LayoutElement elementId="ctrl-grain" gridColumn="1 / 9" gridRow="1 / 4"/><LayoutElement elementId="ctrl-colorby" gridColumn="9 / 17" gridRow="1 / 4"/><LayoutElement elementId="ctrl-catf" gridColumn="17 / 25" gridRow="1 / 4"/>
  </GridContainer>
  <LayoutElement elementId="sbar" gridColumn="1 / 18" gridRow="20 / 40"/>
  <GridContainer elementId="c-clock" type="grid" gridColumn="1 / 25" gridRow="42 / 74" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto"><LayoutElement elementId="clock-hd" gridColumn="1 / 25" gridRow="1 / 2"/><LayoutElement elementId="clockviz" gridColumn="1 / 25" gridRow="2 / 32"/></GridContainer>
  <LayoutElement elementId="heat" gridColumn="1 / 13" gridRow="76 / 92"/>
  <LayoutElement elementId="book" gridColumn="13 / 25" gridRow="76 / 92"/>
{rl}
</Page>"""
    return elems,lay

# ============ PAGE 2 — GROWTH & MARGIN SCENARIO MODELER ============
ROWS=[('Restaurants','Prepared',6000000000,0.22),('Grocery','New verticals',1200000000,0.10),
 ('Convenience','New verticals',1300000000,0.25),('Alcohol','New verticals',900000000,0.30),
 ('Retail','New verticals',800000000,0.18),('DashMart','Owned',800000000,0.28)]
VALS=",".join(f"('{p}','{c}',{rev},{m})" for p,c,rev,m in ROWS)
SBASE=f"SELECT column1 AS CATEGORY, column2 AS GRP, column3 AS BASE_REV, column4 AS BASE_MARGIN FROM (VALUES {VALS})"
sbase={"id":"sbase","kind":"table","name":"Category Base","visibleAsSource":True,
 "source":{"connectionId":CONN,"kind":"sql","statement":SBASE},
 "columns":[{"id":"sb-cat2","formula":"[Custom SQL/CATEGORY]","name":"Category"},{"id":"sb-grp","formula":"[Custom SQL/GRP]","name":"Segment"},
            {"id":"sb-rev2","formula":"[Custom SQL/BASE_REV]","name":"Revenue","format":CUR},{"id":"sb-mar","formula":"[Custom SQL/BASE_MARGIN]","name":"Margin","format":PCT1}],
 "order":["sb-cat2","sb-grp","sb-rev2","sb-mar"]}
scenarios={"id":"scenarios","kind":"input-table","source":{"kind":"empty","connectionId":CONN},"inputMode":"edit","name":"Scenarios",
 "columns":[{"id":"sc-name","type":"text","name":"Scenario Name"},{"id":"sc-status","type":"text","name":"Status","values":["Draft","Submitted","Approved"],"pills":"color-by-option"}]}
spivot={"id":"spivot","kind":"pivot-table","name":"Scenario Pivot","visibleAsSource":True,
 "source":{"kind":"join","joins":[{"left":{"elementId":"sbase","kind":"table"},"right":{"elementId":"scenarios","kind":"table"},"columns":[{"left":"1","right":"1"}],"joinType":"left-outer"}],"primarySource":{"elementId":"sbase","kind":"table"}},
 "columns":[{"id":"pv-cat","formula":"[Category Base/Category]","name":"Category"},
            {"id":"pv-grp","formula":"[Category Base/Segment]","name":"Segment"},
            {"id":"pv-scen","formula":'Coalesce([Scenarios/Scenario Name],"Base Case")',"name":"Scenario"},
            {"id":"pv-rev","formula":"Sum([Category Base/Revenue])","name":"Revenue","format":CUR},
            {"id":"pv-mar","formula":"Avg([Category Base/Margin])","name":"Margin","format":PCT1}],
 "rowsBy":[{"id":"pv-cat"},{"id":"pv-grp"}],"values":["pv-rev","pv-mar"]}
assum={"id":"assum","kind":"input-table","source":{"kind":"linked","from":"spivot"},"inputMode":"edit","name":"Assumptions",
 "columns":[{"id":"ia-cat","key":"pv-cat"},{"id":"ia-grp","key":"pv-grp"},{"id":"ia-scen","key":"pv-scen"},{"id":"ia-rev","key":"pv-rev"},{"id":"ia-mar","key":"pv-mar"},
            {"id":"ia-ord","type":"number","name":"Order Growth %"},
            {"id":"ia-take","type":"number","name":"Take Rate Change %"},
            {"id":"ia-cost","type":"number","name":"Delivery Cost %"},
            {"id":"ia-prev","formula":"[Revenue]*(1+Coalesce([Order Growth %],0)/100)","name":"Projected Revenue","format":CUR},
            {"id":"ia-pm","formula":"[Margin]*(1+Coalesce([Take Rate Change %],0)/100)*(1-Coalesce([Delivery Cost %],0)/100)","name":"Projected Margin","format":PCT1},
            {"id":"ia-pc","formula":"[Projected Revenue]*[Projected Margin]","name":"Projected Contribution","format":CUR}],
 "order":["ia-scen","ia-cat","ia-grp","ia-rev","ia-ord","ia-take","ia-cost","ia-prev","ia-pm","ia-pc"]}
book2={"id":"book2","kind":"table","name":"Book","visibleAsSource":True,
 "source":{"elementId":"assum","kind":"table"},
 "columns":[{"id":"bb-scen","formula":"[Assumptions/Scenario]","name":"Scenario"},
            {"id":"bb-cat","formula":"[Assumptions/Category]","name":"Category"},
            {"id":"bb-brev","formula":"[Assumptions/Revenue]","name":"Base Revenue","format":CUR},
            {"id":"bb-bc","formula":"[Assumptions/Revenue]*[Assumptions/Margin]","name":"Base Contribution","format":CUR},
            {"id":"bb-prev","formula":"[Assumptions/Projected Revenue]","name":"Projected Revenue","format":CUR},
            {"id":"bb-pc","formula":"[Assumptions/Projected Contribution]","name":"Projected Contribution","format":CUR}],
 "order":["bb-scen","bb-cat","bb-brev","bb-bc","bb-prev","bb-pc"]}
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
mtitle={"id":"mtitle","kind":"text","body":"### New scenario\nName it, then Create. It clones the current book for every category — edit the assumptions in the grid.","verticalAlign":"middle","style":{"color":INK}}
modal={"id":"createModal","name":"Create Scenario","type":"modal","modal":{"width":"small","header":{"title":"New scenario","showCloseIcon":"hidden"},"footer":{"primaryCta":{"visible":"hidden"},"secondaryCta":{"visible":"hidden"}}},"elements":[mtitle,namectrl,createbtn,cancelbtn]}
BREV='Sum([Book/Base Revenue])'; BC='Sum([Book/Base Contribution])'; PREV='Sum([Book/Projected Revenue])'; PC='Sum([Book/Projected Contribution])'
P2K=[("p1","PROJECTED REVENUE",PREV,CUR,BREV),
     ("p2","PROJECTED CONTRIBUTION",PC,CUR,BC),
     ("p3","BLENDED MARGIN",f"{PC}/{PREV}",PCT1,f"{BC}/{BREV}"),
     ("p4","REVENUE UPLIFT",f"{PREV}/{BREV}-1",PCT2,None)]
C2=[]; C2L=[]
for i,(elid,title,valf,fmt,compf) in enumerate(P2K):
    e,l=card(elid,"book2",title,valf,compf,"Baseline",fmt,KG[i],trend=None,rowband="8 / 16")
    C2+=e; C2L.append(l.replace("{col}",f"{1+i*6} / {1+(i+1)*6}"))
cbar={"id":"cbar","kind":"bar-chart","source":{"elementId":"book2","kind":"table"},
 "columns":[{"id":"cb-cat","formula":"[Book/Category]","name":"Category"},{"id":"cb-cat2","formula":'"Projected revenue"',"name":"Series"},
            {"id":"cb-prev","formula":"Sum([Book/Projected Revenue])","name":"Projected Revenue","format":CUR}],
 "xAxis":{"columnId":"cb-cat","sort":{"by":"cb-prev","direction":"descending"}},"yAxis":{"columnIds":["cb-prev"]},
 "color":{"by":"category","column":"cb-cat2","scheme":["#EB1700"]},
 "legend":{"visibility":"hidden"},"name":{"text":"Projected revenue by category — active scenario","fontWeight":"bold","fontSize":15,"color":INK},"style":dict(CARD)}
instr_c={"id":"c-instr","kind":"container","style":dict(TINT)}
instr_ic={"id":"instr-ic","kind":"image","url":"data:image/svg+xml;base64,"+b64('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="'+RED+'" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>'),"style":{"fit":"contain"}}
instr_hd={"id":"instr-hd","kind":"text","body":"**How the scenario modeler works**","verticalAlign":"middle","style":{"color":INK}}
instr={"id":"instr","kind":"text","body":("**1** — **Create** a named scenario (clones the current book); pick it with **Active scenario**.  **2** — In the grid, type **Order Growth %**, **Take Rate Change %**, **Delivery Cost %** per category.  **3** — Cards, chart & Copilot re-project instantly. **Submit → Approve** to lock a plan. Leave a cell blank to hold a driver flat."),
 "verticalAlign":"middle","style":{"color":"#3A2C2C"}}
tb_c={"id":"c-tb","kind":"container","style":dict(CARD)}
h2e,h2l=header("2","Growth & Margin Scenario Modeler","Model order growth, take rate & delivery cost by category")
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
theme={"colors":{"text":INK,"highlight":RED,"success":"#3B7A3B","warning":ORANGE,"danger":"#EB1700","darkMode":"hidden"},
 "colorOverrides":{"backgroundCanvas":"#FFFFFF","canvasBackground":"#F4F1EF"},
 "categoricalScheme":["#FFFFFF","#EB1700","#B3122E","#F0872E","#C0453A","#5B2340","#8A8F94","#2E6FB0"],
 "fonts":{"textFont":"Inter","dataFont":"Inter"},"pageWidth":"full","tableStyles":{"preset":"presentation","cellSpacing":"small"}}
def build(mode):
    wa=mode!="none"
    p1e,p1l=page1(wa); p2e,p2l=page2(wa)
    s={"name":"DoorDash — Marketplace Command Center","folderId":FOLDER,"schemaVersion":1,
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
