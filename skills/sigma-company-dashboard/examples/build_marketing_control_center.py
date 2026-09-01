import json,sys,base64,urllib.request
BASE,TOKEN,CONN,FOLDER=sys.argv[1:5]
AICONN="SNOWFLAKE.CORTEX.COMPLETE"; SANKEY="b4b809c8-8699-42ab-abf6-43775cf863e0"
H={"Authorization":"Bearer "+TOKEN,"Content-Type":"application/json"}
def b64(s): return base64.b64encode(s.encode()).decode()
CUR={"kind":"number","formatString":"$.3~s","currencySymbol":"$","decimalSymbol":".","digitGroupingSymbol":",","digitGroupingSize":[3]}
NUM={"kind":"number","formatString":".3~s"}; ROASF={"kind":"number","formatString":",.2f"}
TRANS={"backgroundColor":"transparent","color":"#FFFFFF","padding":"none"}
CARD={"backgroundColor":"#FFFFFF","borderColor":"#E3E8F0","borderWidth":1,"borderRadius":"round"}
NAVY="#060d1f"; BLU="#2E9BFF"; CYAN="#22D3EE"; TEAL="#14B8A6"; GRN="#22C55E"; INK="#0B1220"; MUTE="#5A6473"
def grad(a,b):
    return "data:image/svg+xml;base64,"+b64(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 240" preserveAspectRatio="xMidYMid slice"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient></defs><rect width="400" height="240" fill="url(#g)"/></svg>')
# bespoke KPI gradient family: blue -> blue/teal -> teal -> green (like the reference row)
KG=[grad("#3F6AD8","#5B8DE0"),grad("#2E8FB0","#22B8C4"),grad("#1FA8A0","#3FD0B8"),grad("#1FA05E","#4FD08A")]
def timg(txt,sz=24,col="#FFFFFF",w=800,anchor="middle",x=200):
    a={"start":"start","middle":"middle"}[anchor]
    return "data:image/svg+xml;base64,"+b64(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 460 44" preserveAspectRatio="xMidYMid meet"><text x="{x}" y="31" text-anchor="{a}" font-family="Inter,Arial,sans-serif" font-weight="{w}" font-size="{sz}" fill="{col}">{txt}</text></svg>')
# bespoke SVG hero (navy + electric particle-network glow) — no external image needed
hero_svg=('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 300" preserveAspectRatio="xMidYMid slice">'
 '<defs><radialGradient id="a" cx="72%" cy="35%" r="60%"><stop offset="0" stop-color="#123a6b"/><stop offset="1" stop-color="#060d1f" stop-opacity="0"/></radialGradient>'
 '<radialGradient id="b" cx="90%" cy="75%" r="55%"><stop offset="0" stop-color="#0e7490"/><stop offset="1" stop-color="#060d1f" stop-opacity="0"/></radialGradient></defs>'
 '<rect width="1600" height="300" fill="#060d1f"/><rect width="1600" height="300" fill="url(#a)"/><rect width="1600" height="300" fill="url(#b)"/>'
 +''.join(f'<circle cx="{(i*97)%1600}" cy="{(i*53)%300}" r="{1.5+(i%3)}" fill="#2E9BFF" opacity="{0.10+0.05*(i%4)}"/>' for i in range(60))
 +''.join(f'<line x1="{(i*97)%1600}" y1="{(i*53)%300}" x2="{((i+1)*97)%1600}" y2="{((i+1)*53)%300}" stroke="#22D3EE" stroke-width="0.5" opacity="0.06"/>' for i in range(40))
 +'<rect width="640" height="300" fill="#060d1f" opacity="0.55"/></svg>')
hero="data:image/svg+xml;base64,"+b64(hero_svg)
logo_uri="data:image/svg+xml;base64,"+b64(open("amp_logo_white.svg").read())

# ============ DATA ============
CATS=['Accessories & Peripherals','Audio & Video','Computing Devices','Gaming & Entertainment','Mobile Devices','Smart Home & IoT','Broadband & Networking','Business & Enterprise IT']
CARR="ARRAY_CONSTRUCT("+",".join("'"+c+"'" for c in CATS)+")"
SQL=f"""WITH base AS (
  SELECT ORDER_NUMBER, DATE, STORE_STATE, CUSTOMER_NAME, QUANTITY, PRICE, COST,
    GET(ARRAY_CONSTRUCT('Paid Search','Paid Social'), MOD(ABS(HASH(ORDER_NUMBER)),2))::string AS ACQ_CHANNEL,
    GET(ARRAY_CONSTRUCT('Google','Bing','Facebook'), MOD(ABS(HASH(CUSTOMER_NAME)),3))::string AS NETWORK,
    GET({CARR}, MOD(ABS(HASH(PRODUCT_FAMILY)),8))::string AS PRODUCT_LINE,
    QUANTITY*PRICE AS REVENUE, QUANTITY*(PRICE-COST) AS GROSS_PROFIT,
    QUANTITY*PRICE*(0.30+0.14*ABS(SIN(ABS(HASH(ORDER_NUMBER))%1000))) AS MARKETING_SPEND,
    DATE_TRUNC('month',DATE) AS USE_MONTH
  FROM SE_DEMO_DB.BIG_BUYS.BIG_BUYS_POS
), m AS (SELECT MAX(USE_MONTH) MAXM FROM base)
SELECT base.*, CASE WHEN USE_MONTH=(SELECT MAXM FROM m) THEN 'Current Period'
  WHEN USE_MONTH=DATEADD('year',-1,(SELECT MAXM FROM m)) THEN 'Prior Year' ELSE NULL END AS PERIOD_NAME
FROM base"""
MF="Marketing"
COLS=[("c-date","DATE","Date"),("c-month","USE_MONTH","Month"),("c-period","PERIOD_NAME","Period Name"),
 ("c-chan","ACQ_CHANNEL","Acquisition Channel"),("c-net","NETWORK","Network"),("c-prod","PRODUCT_LINE","Product Line"),
 ("c-state","STORE_STATE","State"),("c-rev","REVENUE","Revenue"),("c-gp","GROSS_PROFIT","Gross Profit"),("c-spend","MARKETING_SPEND","Marketing Spend")]
tbl={"id":"tbl","kind":"table","source":{"connectionId":CONN,"statement":SQL,"kind":"sql"},
 "columns":[{"id":c,"formula":f"[Custom SQL/{s}]","name":d} for c,s,d in COLS],"name":MF,"order":[c[0] for c in COLS],"visibleAsSource":True}
# journey aggregate for the sankey
JSQL=f"""SELECT ACQ_CHANNEL, NETWORK, PRODUCT_LINE, SUM(REVENUE) REVENUE FROM (
 SELECT GET(ARRAY_CONSTRUCT('Paid Search','Paid Social'), MOD(ABS(HASH(ORDER_NUMBER)),2))::string AS ACQ_CHANNEL,
   GET(ARRAY_CONSTRUCT('Google','Bing','Facebook'), MOD(ABS(HASH(CUSTOMER_NAME)),3))::string AS NETWORK,
   GET({CARR}, MOD(ABS(HASH(PRODUCT_FAMILY)),8))::string AS PRODUCT_LINE, QUANTITY*PRICE AS REVENUE
 FROM SE_DEMO_DB.BIG_BUYS.BIG_BUYS_POS) GROUP BY 1,2,3"""
journey={"id":"journey","kind":"table","source":{"connectionId":CONN,"statement":JSQL,"kind":"sql"},
 "columns":[{"id":"j-chan","formula":"[Custom SQL/ACQ_CHANNEL]","name":"Acquisition Channel"},{"id":"j-net","formula":"[Custom SQL/NETWORK]","name":"Network"},{"id":"j-prod","formula":"[Custom SQL/PRODUCT_LINE]","name":"Product Line"},{"id":"j-rev","formula":"[Custom SQL/REVENUE]","name":"Revenue","format":CUR}],
 "name":"Customer Journey","order":["j-chan","j-net","j-prod","j-rev"],"visibleAsSource":True}

# ============ header (navy hero + white logo + title + tabs) ============
masthead={"id":"c-hdr","kind":"container","style":{"backgroundColor":NAVY,"borderRadius":"round"},"backgroundImage":{"source":{"kind":"url","url":hero},"style":{"fit":"cover"}}}
logo={"id":"img-logo","kind":"image","source":{"kind":"url","url":logo_uri},"style":{"fit":"contain"}}
htitle={"id":"img-htitle","kind":"image","source":{"kind":"url","url":timg("Marketing Performance Analysis",22,"#DCE9FF",600,"start",4)},"style":{"fit":"contain"}}

# ============ KPI cards (gradient + Current/Prior + line chart WITH date axis) ============
def kpi(elid,title,mainf,fmt,trend,g):
    cid=f"c-{elid}"
    cont={"id":cid,"kind":"container","style":{"borderRadius":"round"},"backgroundImage":{"source":{"kind":"url","url":g},"style":{"fit":"cover"}}}
    tt={"id":f"t-{elid}","kind":"image","source":{"kind":"url","url":timg(title,24)},"style":{"fit":"scale-down"}}
    lc={"id":f"lc-{elid}","kind":"image","source":{"kind":"url","url":timg("Current Period",26,"#E6F0FF",600)},"style":{"fit":"scale-down"}}
    lp={"id":f"lp-{elid}","kind":"image","source":{"kind":"url","url":timg("Prior Year",26,"#E6F0FF",600)},"style":{"fit":"scale-down"}}
    def k(sfx,per): return {"id":f"k-{elid}{sfx}","kind":"kpi-chart","source":{"elementId":"tbl","kind":"table"},"columns":[{"id":f"k-{elid}{sfx}v","formula":mainf.replace("§",per),"name":per,"format":fmt}],"value":{"columnId":f"k-{elid}{sfx}v","color":"#FFFFFF","fontSize":30},"name":{"visibility":"hidden"},"layout":{"anchor":"middle"},"style":dict(TRANS)}
    kc=k("c","Current Period"); kp=k("p","Prior Year")
    # line chart WITH visible date x-axis (the differentiator)
    ln={"id":f"ln-{elid}","kind":"line-chart","source":{"elementId":"tbl","kind":"table"},
        "columns":[{"id":f"ln-{elid}m","formula":f"[{MF}/Month]","name":"Month"},{"id":f"ln-{elid}v","formula":trend,"name":"Trend"}],
        "xAxis":{"columnId":f"ln-{elid}m","format":{"marks":"none"}},
        "yAxis":{"columnIds":[f"ln-{elid}v"],"format":{"labels":"hidden","marks":"none","scale":{"type":"linear","zero":False,"hideZeroLine":True}}},
        "name":{"visibility":"hidden"},"legend":{"visibility":"hidden"},"lineAreaStyle":{"interpolation":"monotone"},"style":dict(TRANS)}
    els=[cont,tt,lc,kc,lp,kp,ln]
    lay=(f'  <GridContainer elementId="{cid}" type="grid" gridColumn="{{col}}" gridRow="8 / 19" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">\n'
         f'    <LayoutElement elementId="t-{elid}" gridColumn="1 / 13" gridRow="1 / 3"/>\n'
         f'    <LayoutElement elementId="lc-{elid}" gridColumn="1 / 7" gridRow="3 / 5"/><LayoutElement elementId="lp-{elid}" gridColumn="7 / 13" gridRow="3 / 5"/>\n'
         f'    <LayoutElement elementId="k-{elid}c" gridColumn="1 / 7" gridRow="5 / 9"/><LayoutElement elementId="k-{elid}p" gridColumn="7 / 13" gridRow="5 / 9"/>\n'
         f'    <LayoutElement elementId="ln-{elid}" gridColumn="1 / 13" gridRow="9 / 13"/>\n  </GridContainer>')
    return els,lay
KDEFS=[("rev","REVENUE",f'SumIf([{MF}/Revenue],[{MF}/Period Name]="§")',CUR,f'Sum([{MF}/Revenue])',KG[0]),
       ("gp","GROSS PROFIT",f'SumIf([{MF}/Gross Profit],[{MF}/Period Name]="§")',CUR,f'Sum([{MF}/Gross Profit])',KG[1]),
       ("sp","MARKETING SPEND",f'SumIf([{MF}/Marketing Spend],[{MF}/Period Name]="§")',CUR,f'Sum([{MF}/Marketing Spend])',KG[2]),
       ("roas","ROAS",f'SumIf([{MF}/Revenue],[{MF}/Period Name]="§")/SumIf([{MF}/Marketing Spend],[{MF}/Period Name]="§")',ROASF,f'Sum([{MF}/Revenue])/Sum([{MF}/Marketing Spend])',KG[3])]
kpis=[]; kpilay=[]
for i,(elid,t,mf,fmt,tr,g) in enumerate(KDEFS):
    e,l=kpi(elid,t,mf,fmt,tr,g); kpis+=e; kpilay.append(l.replace("{col}",f"{1+i*6} / {1+(i+1)*6}"))

# AI insight
ai_body=('{{ Replace(CallText("'+AICONN+'", "CLAUDE-4-SONNET", '
 '"You are a performance-marketing analyst at adMarketplace (a search-advertising network). In two concise sentences summarize marketing performance given Revenue $" '
 '& Text(Round(Sum(['+MF+'/Revenue])/1000000,0)) & "M, Marketing Spend $" '
 '& Text(Round(Sum(['+MF+'/Marketing Spend])/1000000,0)) & "M, and ROAS " '
 '& Text(Round(Sum(['+MF+'/Revenue])/Sum(['+MF+'/Marketing Spend]),2)) & "x. Comment on efficiency and the strongest channel."), \'"\', \'\') }}')
ai_box={"id":"c-ai","kind":"container","style":{"backgroundColor":"#EEF4FF","borderColor":BLU,"borderWidth":1,"borderRadius":"round"}}
ai_sum={"id":"txt-ai","kind":"text","body":"**⚡ AI INSIGHT**\n\n"+ai_body,"verticalAlign":"middle","style":{"color":"#0B1B33"}}

# filter buttons (segmented) + selectors
grain={"kind":"control","controlId":"DateGrain","id":"ctrl-grain","name":"Date Grain","controlType":"segmented","value":"Month","source":{"kind":"manual","valueType":"text","values":["Quarter","Month","Week","Day"]}}
colorby={"kind":"control","controlId":"ColorBy","id":"ctrl-colorby","name":"Color By","controlType":"segmented","value":"Product Line","source":{"kind":"manual","valueType":"text","values":["Product Line","Acquisition Channel","Network"]}}
ctrl_chan={"kind":"control","controlId":"Channel","id":"ctrl-chan","name":"Channel","controlType":"list","selectionMode":"multiple","mode":"include","values":[],"filters":[{"source":{"kind":"table","elementId":"tbl"},"columnId":"c-chan"}],"source":{"kind":"source","source":{"kind":"table","elementId":"tbl"},"columnId":"c-chan"}}
filt_c={"id":"c-filters","kind":"container","style":dict(CARD)}

# stacked bar Revenue by Month & Product Line (with value labels)
sbar={"id":"sbar","kind":"bar-chart","source":{"elementId":"tbl","kind":"table"},
 "columns":[{"id":"sbm","formula":f'Switch([DateGrain],"Quarter",DateTrunc("quarter",[{MF}/Date]),"Week",DateTrunc("week",[{MF}/Date]),"Day",DateTrunc("day",[{MF}/Date]),DateTrunc("month",[{MF}/Date]))',"name":"Period","format":{"kind":"datetime","formatString":"%b %d, %Y"}},{"id":"sbv","formula":f"Sum([{MF}/Revenue])","name":"Revenue","format":CUR},{"id":"sbc","formula":f'Switch([ColorBy],"Product Line",[{MF}/Product Line],"Acquisition Channel",[{MF}/Acquisition Channel],"Network",[{MF}/Network])',"name":"Series"}],
 "xAxis":{"columnId":"sbm"},"yAxis":{"columnIds":["sbv"]},"color":{"by":"category","column":"sbc","scheme":["#2E9BFF","#22D3EE","#14B8A6","#22C55E","#8B5CF6","#F59E0B","#EC4899","#64748B"]},"stacking":"stacked",
 "dataLabel":{"labels":"shown","anchor":"middle","fontSize":10},
 "legend":{"visibility":"visible"},"name":{"text":"Total Revenue by Month & Product Line","fontWeight":"bold","fontSize":14,"color":INK},"style":dict(CARD)}
# pivot heatmap: Product Line share by Month
heat={"id":"heat","kind":"pivot-table","source":{"elementId":"tbl","kind":"table"},
 "columns":[{"id":"hm","formula":f"[{MF}/Month]","name":"Month"},{"id":"hp","formula":f"[{MF}/Product Line]","name":"Product Line"},{"id":"hv","formula":f"Sum([{MF}/Revenue])","name":"Revenue","format":CUR}],
 "rowsBy":[{"id":"hm"}],"columnsBy":[{"id":"hp"}],"values":["hv"],
 "conditionalFormats":[{"type":"single","columnIds":["hv"],"condition":"IsNotNull","style":{"backgroundColor":"#E8F1FF"}}],
 "name":{"text":"Revenue Heatmap — Product Line by Month","fontWeight":"bold","fontSize":14,"color":INK},"style":dict(CARD)}
# sankey plugin
sankey_c={"id":"c-sankey","kind":"container","style":dict(CARD)}
sankey_el={"id":"sankey","kind":"plugin","pluginId":SANKEY,"config":{"source":{"kind":"element","elementId":"journey"},"stage1":"j-chan","stage2":"j-net","stage3":"j-prod","value":"j-rev"}}

# ===================== PAGE 2 : SCENARIO MODELER =====================
DCUR={"kind":"number","formatString":"+$.3~s","currencySymbol":"$","decimalSymbol":".","digitGroupingSymbol":",","digitGroupingSize":[3]}
PCT2={"kind":"number","formatString":"+,.1%"}
masthead2={"id":"c-hdr2","kind":"container","style":{"backgroundColor":NAVY,"borderRadius":"round"},"backgroundImage":{"source":{"kind":"url","url":hero},"style":{"fit":"cover"}}}
logo2={"id":"img-logo2","kind":"image","source":{"kind":"url","url":logo_uri},"style":{"fit":"contain"}}
htitle2={"id":"img-htitle2","kind":"image","source":{"kind":"url","url":timg("Scenario Modeler",22,"#DCE9FF",600,"start",4)},"style":{"fit":"contain"}}
mbase={"id":"mbase","kind":"table","name":"Model Base","visibleAsSource":True,"source":{"connectionId":CONN,"kind":"sql","statement":f"SELECT GET({CARR}, MOD(ABS(HASH(PRODUCT_FAMILY)),8))::string AS PRODUCT_LINE, QUANTITY*PRICE AS REVENUE FROM SE_DEMO_DB.BIG_BUYS.BIG_BUYS_POS"},"columns":[{"id":"mb-prod","formula":"[Custom SQL/PRODUCT_LINE]","name":"Product Line"},{"id":"mb-rev","formula":"[Custom SQL/REVENUE]","name":"Revenue","format":CUR}],"order":["mb-prod","mb-rev"]}
scen={"id":"scenarios","kind":"input-table","source":{"kind":"empty","connectionId":CONN},"inputMode":"edit","name":"Scenario Names","columns":[{"id":"sc-name","type":"text","name":"Scenario Name"},{"id":"sc-status","type":"text","name":"Status","values":["Draft","Submitted","Approved"],"pills":"color-by-option"}]}
pivot={"id":"pivot","kind":"pivot-table","name":"Pivot","visibleAsSource":True,"source":{"kind":"join","joins":[{"left":{"elementId":"mbase","kind":"table"},"right":{"elementId":"scenarios","kind":"table"},"columns":[{"left":"1","right":"1"}],"joinType":"left-outer"}],"primarySource":{"elementId":"mbase","kind":"table"}},"columns":[{"id":"pv-prod","formula":"[Model Base/Product Line]","name":"Product Line"},{"id":"pv-scen","formula":"[Scenario Names/Scenario Name]","name":"Scenario"},{"id":"pv-rev","formula":"Sum([Model Base/Revenue])","name":"Revenue","format":CUR}],"rowsBy":[{"id":"pv-prod"}],"values":["pv-rev"]}
forecast={"id":"forecast","kind":"input-table","source":{"kind":"linked","from":"pivot"},"inputMode":"edit","name":"Forecast Entry","columns":[{"id":"lk-prod","key":"pv-prod"},{"id":"lk-scen","key":"pv-scen","hidden":True},{"id":"lk-base","key":"pv-rev"},{"id":"lk-fc","type":"number","name":"Forecasted Revenue","format":CUR}],"order":["lk-prod","lk-scen","lk-base","lk-fc"],"conditionalFormats":[{"type":"single","columnIds":["lk-fc"],"condition":"IsNotNull","style":{"backgroundColor":"#E7F1FB"}}]}
detail={"id":"detail","kind":"table","name":"Detail","visibleAsSource":True,"source":{"elementId":"forecast","kind":"table"},"columns":[{"id":"d-prod","formula":"[Forecast Entry/Product Line]","name":"Product Line"},{"id":"d-scen","formula":"[Forecast Entry/Scenario]","name":"Scenario"}],"order":["d-prod","d-scen"]}
subs={"id":"subs","kind":"input-table","source":{"kind":"empty","connectionId":CONN},"inputMode":"edit","name":"Submissions","columns":[{"id":"su-scen","type":"text","name":"Scenario"},{"id":"su-status","type":"text","name":"Status","values":["Submitted","Approved"],"pills":"color-by-option"}]}
selctrl={"kind":"control","controlId":"scenarioSelect","id":"ctrl-sel","name":"Scenario","controlType":"list","selectionMode":"single","mode":"include","filters":[{"source":{"kind":"table","elementId":"detail"},"columnId":"d-scen"}],"source":{"kind":"source","source":{"kind":"table","elementId":"detail"},"columnId":"d-scen"}}
BASE_M='Sum([Forecast Entry/Revenue])'; FC_M='Sum(Coalesce([Forecast Entry/Forecasted Revenue],[Forecast Entry/Revenue]))'
def gcard(idp,title,mainf,mainfmt,deltaf=None):
    cont={"id":f"c-{idp}","kind":"container","style":{"borderRadius":"round"},"backgroundImage":{"source":{"kind":"url","url":KG[0]},"style":{"fit":"cover"}}}
    t={"id":f"t-{idp}","kind":"image","source":{"kind":"url","url":timg(title.upper(),24)},"style":{"fit":"scale-down"}}
    v={"id":f"v-{idp}","kind":"kpi-chart","source":{"elementId":"forecast","kind":"table"},"columns":[{"id":f"{idp}mv","formula":mainf,"name":title,"format":mainfmt}],"value":{"columnId":f"{idp}mv","fontSize":34,"color":"#FFFFFF"},"name":{"visibility":"hidden"},"layout":{"anchor":"middle"},"style":dict(TRANS)}
    els=[cont,t,v]; rows=[f'<LayoutElement elementId="t-{idp}" gridColumn="1 / 13" gridRow="1 / 3"/>',f'<LayoutElement elementId="v-{idp}" gridColumn="1 / 13" gridRow="3 / 8"/>']
    if deltaf:
        dl={"id":f"dl-{idp}","kind":"image","source":{"kind":"url","url":timg("vs Baseline",18,"#CFE4F7",600)},"style":{"fit":"scale-down"}}
        d={"id":f"d-{idp}","kind":"kpi-chart","source":{"elementId":"forecast","kind":"table"},"columns":[{"id":f"{idp}dv","formula":deltaf,"name":"vs Baseline","format":DCUR}],"value":{"columnId":f"{idp}dv","fontSize":16,"color":"#FFFFFF"},"name":{"visibility":"hidden"},"layout":{"anchor":"middle"},"style":dict(TRANS)}
        els+=[dl,d]; rows+=[f'<LayoutElement elementId="dl-{idp}" gridColumn="1 / 13" gridRow="8 / 9"/>',f'<LayoutElement elementId="d-{idp}" gridColumn="1 / 13" gridRow="9 / 11"/>']
    lay=f'  <GridContainer elementId="c-{idp}" type="grid" gridColumn="{{col}}" gridRow="8 / 17" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">\n    '+"\n    ".join(rows)+"\n  </GridContainer>"
    return els,lay
c1e,c1l=gcard("m1","Projected Revenue",FC_M,CUR,f"{FC_M}-{BASE_M}")
c2e,c2l=gcard("m2","Forecast Uplift",f"({FC_M}-{BASE_M})/{BASE_M}",PCT2)
c3e,c3l=gcard("m3","Baseline Revenue",BASE_M,CUR)
mkpi=c1e+c2e+c3e; mkpilay=c1l.replace("{col}","1 / 9")+"\n"+c2l.replace("{col}","9 / 17")+"\n"+c3l.replace("{col}","17 / 25")
rvf2={"id":"rvf2","kind":"bar-chart","source":{"elementId":"forecast","kind":"table"},"columns":[{"id":"r2d","formula":"[Forecast Entry/Product Line]","name":"Product Line"},{"id":"r2b","formula":"Sum([Forecast Entry/Revenue])","name":"Revenue","format":CUR},{"id":"r2f","formula":"Sum(Coalesce([Forecast Entry/Forecasted Revenue],[Forecast Entry/Revenue]))","name":"Forecasted Revenue","format":CUR}],"xAxis":{"columnId":"r2d","sort":{"by":"r2b","direction":"descending"}},"yAxis":{"columnIds":["r2b","r2f"]},"stacking":"none","legend":{"visibility":"visible"},"name":{"text":"Revenue vs Forecasted Revenue by Product Line","fontWeight":"bold","fontSize":14,"color":INK},"style":dict(CARD)}
create_tb={"id":"create_tb","kind":"button","text":"+ Create","appearance":"filled","actions":[{"id":"o1","trigger":"on-click","effects":[{"effect":"open-overlay","overlayId":"createModal"}]}]}
submit_tb={"id":"submit_tb","kind":"button","text":"Submit","appearance":"outline","actions":[{"id":"s1","trigger":"on-click","effects":[{"effect":"insert-rows","tableElementId":"subs","values":{"su-scen":{"type":"control","control":"scenarioSelect"},"su-status":{"type":"constant","value":{"type":"text","value":"Submitted"}}}}]}]}
mtitle={"id":"mtitle","kind":"text","body":"### New scenario\nName it, then Create — it copies the baseline for every product line.","verticalAlign":"middle"}
namectrl={"kind":"control","controlId":"newScenarioName","id":"ctrl-name","name":"Scenario Name","controlType":"text","mode":"equals","case":"insensitive","includeNulls":"when-no-value-is-selected","showOperators":False}
createbtn={"id":"createbtn","kind":"button","text":"Create","appearance":"filled","actions":[{"id":"c1","trigger":"on-click","effects":[{"effect":"insert-rows","tableElementId":"scenarios","values":{"sc-name":{"type":"control","control":"newScenarioName"},"sc-status":{"type":"constant","value":{"type":"text","value":"Draft"}}}},{"effect":"set-control-value","control":"scenarioSelect","value":{"type":"control","control":"newScenarioName"}},{"effect":"clear-control","scope":{"type":"control","controlId":"newScenarioName"}},{"effect":"close-overlay"}]}]}
cancelbtn={"id":"cancelbtn","kind":"button","text":"Cancel","appearance":"outline","actions":[{"id":"x1","trigger":"on-click","effects":[{"effect":"close-overlay"}]}]}
create_modal={"id":"createModal","name":"Create Scenario","type":"modal","modal":{"width":"small","header":{"title":"New Scenario","showCloseIcon":"hidden"},"footer":{"primaryCta":{"visible":"hidden"},"secondaryCta":{"visible":"hidden"}}},"elements":[mtitle,namectrl,createbtn,cancelbtn]}
p2=[masthead2,logo2,htitle2,create_tb,submit_tb,mbase,scen,pivot,forecast,detail,subs,selctrl]+mkpi+[rvf2]
p2lay=f"""<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="model">
  <GridContainer elementId="c-hdr2" type="grid" gridColumn="1 / 25" gridRow="1 / 5" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <LayoutElement elementId="img-logo2" gridColumn="1 / 5" gridRow="1 / 4"/><LayoutElement elementId="img-htitle2" gridColumn="5 / 15" gridRow="2 / 4"/>
    <LayoutElement elementId="create_tb" gridColumn="17 / 21" gridRow="2 / 4"/><LayoutElement elementId="submit_tb" gridColumn="21 / 24" gridRow="2 / 4"/>
  </GridContainer>
  <LayoutElement elementId="ctrl-sel" gridColumn="1 / 9" gridRow="5 / 8"/>
{mkpilay}
  <LayoutElement elementId="rvf2" gridColumn="1 / 25" gridRow="17 / 31"/>
  <LayoutElement elementId="forecast" gridColumn="1 / 25" gridRow="31 / 49"/>
</Page>"""
molay=f'<Page type="grid" gridTemplateColumns="repeat(24,1fr)" gridTemplateRows="auto" id="createModal"><LayoutElement elementId="mtitle" gridColumn="1 / 25" gridRow="1 / 3"/><LayoutElement elementId="ctrl-name" gridColumn="1 / 25" gridRow="3 / 5"/><LayoutElement elementId="cancelbtn" gridColumn="13 / 19" gridRow="5 / 7"/><LayoutElement elementId="createbtn" gridColumn="19 / 25" gridRow="5 / 7"/></Page>'

elements=[tbl,journey,masthead,logo,htitle]+kpis+[ai_box,ai_sum,filt_c,grain,colorby,ctrl_chan,sbar,heat,sankey_c,sankey_el]
layout=f"""<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg">
  <GridContainer elementId="c-hdr" type="grid" gridColumn="1 / 25" gridRow="1 / 5" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <LayoutElement elementId="img-logo" gridColumn="1 / 5" gridRow="1 / 4"/><LayoutElement elementId="img-htitle" gridColumn="5 / 16" gridRow="2 / 4"/>
  </GridContainer>
{chr(10).join(kpilay)}
  <GridContainer elementId="c-ai" type="grid" gridColumn="1 / 25" gridRow="19 / 23" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto"><LayoutElement elementId="txt-ai" gridColumn="1 / 25" gridRow="1 / 4"/></GridContainer>
  <GridContainer elementId="c-filters" type="grid" gridColumn="1 / 25" gridRow="23 / 26" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <LayoutElement elementId="ctrl-grain" gridColumn="1 / 9" gridRow="1 / 4"/><LayoutElement elementId="ctrl-colorby" gridColumn="9 / 17" gridRow="1 / 4"/><LayoutElement elementId="ctrl-chan" gridColumn="17 / 25" gridRow="1 / 4"/>
  </GridContainer>
  <LayoutElement elementId="sbar" gridColumn="1 / 25" gridRow="26 / 44"/>
  <LayoutElement elementId="heat" gridColumn="1 / 25" gridRow="44 / 58"/>
  <GridContainer elementId="c-sankey" type="grid" gridColumn="1 / 25" gridRow="58 / 78" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto"><LayoutElement elementId="sankey" gridColumn="1 / 25" gridRow="1 / 21"/></GridContainer>
</Page>
{p2lay}
{molay}"""
theme={"colors":{"text":INK,"highlight":BLU,"success":GRN,"warning":"#F59E0B","danger":"#EF4444","darkMode":"hidden"},
 "colorOverrides":[],  # TEMP: live colorOverrides regression, see schema-2026-08-breaking-changes.md
 "categoricalScheme":["#FFFFFF","#22D3EE","#14B8A6","#22C55E","#8B5CF6","#F59E0B","#EC4899","#64748B"],
 "fonts":{"textFont":"Inter","dataFont":"Inter"},"pageWidth":"full","tableStyles":{"preset":"presentation","cellSpacing":"small"}}
spec={"name":"adMarketplace — Marketing Control Center","folderId":FOLDER,"schemaVersion":1,"pages":[{"id":"pg","name":"Marketing Performance Analysis","elements":elements},{"id":"model","name":"Scenario Modeler","elements":p2},create_modal],"layout":layout,"themeOverrides":theme}
open("admp.json","w").write(json.dumps(spec,indent=1))
r=urllib.request.Request(BASE+"/v2/workbooks/spec",data=json.dumps(spec).encode(),headers=H,method="POST")
try:
    resp=urllib.request.urlopen(r,timeout=120).read().decode()
    print("POST:", "ACCEPTED" if "success: true" in resp else resp[:600])
    wid=[l.split()[-1] for l in resp.splitlines() if "workbookId" in l]
    if wid: print("URL:", json.loads(urllib.request.urlopen(urllib.request.Request(BASE+f"/v2/workbooks/{wid[0]}",headers=H),timeout=30).read().decode()).get("url"))
except urllib.error.HTTPError as e:
    print("HTTP",e.code,":",json.loads(e.read().decode()).get("message","")[:600])
