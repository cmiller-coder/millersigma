#!/usr/bin/env python3
import json, os, base64, pathlib, sys
CONN=os.environ.get("SIGMA_CONNECTION_ID","REPLACE_WITH_YOUR_CONNECTION_ID"); AICONN="SNOWFLAKE.CORTEX.COMPLETE"; FOLDER=sys.argv[1]; BASE="NVIDIA POS"
SP=pathlib.Path(__file__).parent
def b64(s): return base64.b64encode(s.encode()).decode()

SQL="""WITH base AS (
  SELECT ORDER_NUMBER, DATE, STORE_REGION, STORE_STATE, STORE_CITY, CUSTOMER_NAME, QUANTITY, PRICE, COST,
         GET(ARRAY_CONSTRUCT('Data Center','Gaming','Professional Visualization','Automotive','OEM & Other'), MOD(ABS(HASH(PRODUCT_FAMILY)),5))::string AS SEGMENT,
         GET(ARRAY_CONSTRUCT('H100','H200','B200','GB200','DGX','GeForce RTX','RTX PRO','DRIVE Thor','Jetson','Spectrum-X'), MOD(ABS(HASH(PRODUCT_LINE)),10))::string AS PRODUCT,
         QUANTITY*PRICE AS REVENUE, QUANTITY*(PRICE-COST) AS MARGIN, DATE_TRUNC('month',DATE) AS ORDER_MONTH
  FROM SE_DEMO_DB.BIG_BUYS.BIG_BUYS_POS
), m AS (SELECT MAX(ORDER_MONTH) AS MAXM FROM base)
SELECT base.*,
  CASE WHEN ORDER_MONTH=(SELECT MAXM FROM m) THEN 'Current Period'
       WHEN ORDER_MONTH=DATEADD('year',-1,(SELECT MAXM FROM m)) THEN 'Prior Year' ELSE NULL END AS PERIOD_NAME
FROM base"""
COLS=[("col-order","ORDER_NUMBER","Order Number"),("col-date","DATE","Order Date"),
 ("col-month","ORDER_MONTH","Order Month"),("col-period","PERIOD_NAME","Period Name"),
 ("col-segment","SEGMENT","Segment"),("col-product","PRODUCT","Product"),
 ("col-region","STORE_REGION","Region"),("col-state","STORE_STATE","State"),
 ("col-city","STORE_CITY","City"),("col-cust","CUSTOMER_NAME","Customer"),
 ("col-qty","QUANTITY","Units"),("col-price","PRICE","Price"),("col-cost","COST","Cost"),
 ("col-rev","REVENUE","Revenue"),("col-margin","MARGIN","Margin")]
tbl={"id":"tbl","kind":"table","source":{"connectionId":CONN,"statement":SQL,"kind":"sql"},
 "columns":[{"id":c,"formula":f"[Custom SQL/{s}]","name":d} for c,s,d in COLS],
 "name":BASE,"order":[c[0] for c in COLS],"visibleAsSource":True}

# GPU Fleet — synthetic operational data for the heatmap plugin
FLEET_SQL=("SELECT 'DC-'||LPAD(SEQ4()::string,3,'0') AS NODE_ID, 'Rack '||(MOD(SEQ4(),12)+1) AS RACK, "
 "GET(ARRAY_CONSTRUCT('H100','H200','B200','GB200','A100'),MOD(SEQ4(),5))::string AS GPU_MODEL, "
 "GET(ARRAY_CONSTRUCT('US-East','US-West','EU-Central','APAC'),MOD(SEQ4(),4))::string AS DC_REGION, "
 "ROUND(30+65*ABS(SIN(SEQ4()))) AS UTILIZATION, ROUND(45+40*ABS(SIN(SEQ4()*1.3))) AS TEMP_C, "
 "ROUND(300+400*ABS(SIN(SEQ4()*0.7))) AS POWER_W FROM TABLE(GENERATOR(ROWCOUNT=>240))")
fleet={"id":"fleet","kind":"table","source":{"connectionId":CONN,"statement":FLEET_SQL,"kind":"sql"},
 "columns":[{"id":"f-node","formula":"[Custom SQL/NODE_ID]","name":"Node"},{"id":"f-rack","formula":"[Custom SQL/RACK]","name":"Rack"},
            {"id":"f-model","formula":"[Custom SQL/GPU_MODEL]","name":"GPU Model"},{"id":"f-region","formula":"[Custom SQL/DC_REGION]","name":"DC Region"},
            {"id":"f-util","formula":"[Custom SQL/UTILIZATION]","name":"Utilization"},{"id":"f-temp","formula":"[Custom SQL/TEMP_C]","name":"Temp C"},
            {"id":"f-power","formula":"[Custom SQL/POWER_W]","name":"Power W"}],
 "name":"GPU Fleet","order":["f-node","f-rack","f-model","f-region","f-util","f-temp","f-power"]}

TRANS={"backgroundColor":"transparent","color":"#FFFFFF","padding":"none"}
CUR={"kind":"number","formatString":"$.3~s","decimalSymbol":".","digitGroupingSymbol":",","digitGroupingSize":[3],"currencySymbol":"$"}
NUM={"kind":"number","formatString":",.0f","decimalSymbol":".","digitGroupingSymbol":",","digitGroupingSize":[3]}
CARD={"backgroundColor":"#FFFFFF","borderColor":"#E1E6DE","borderWidth":1,"borderRadius":"round"}
def grad(a,b,c):
    return "data:image/svg+xml;base64,"+b64(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 240" preserveAspectRatio="xMidYMid slice"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/><stop offset="0.55" stop-color="{b}"/><stop offset="1" stop-color="{c}"/></linearGradient></defs><rect width="400" height="240" fill="url(#g)"/></svg>')
GRADS=[grad("#0A2A00","#3E7A00","#76B900"),grad("#0E1F0A","#2F6B1E","#A3E635"),grad("#0B0B0D","#243714","#5B8C1E")]
def timg(txt,sz=26,col="#FFFFFF",w=800):
    return "data:image/svg+xml;base64,"+b64(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 44" preserveAspectRatio="xMidYMid meet"><text x="150" y="31" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-weight="{w}" font-size="{sz}" fill="{col}">{txt}</text></svg>')

# ---- 3 composite KPI cards ----
KDEFS=[("REVENUE", f'SumIf([{BASE}/Revenue], [{BASE}/Period Name]="§")', CUR, f'Sum([{BASE}/Revenue])'),
       ("MARGIN",  f'SumIf([{BASE}/Margin], [{BASE}/Period Name]="§")', CUR, f'Sum([{BASE}/Margin])'),
       ("UNITS",   f'SumIf([{BASE}/Units], [{BASE}/Period Name]="§")', NUM, f'Sum([{BASE}/Units])')]
card_elems=[]; card_layout=[]
for i,(title,mf,fmt,trend) in enumerate(KDEFS,1):
    cid=f"c-kpi{i}"
    cont={"id":cid,"kind":"container","style":{"borderRadius":"round"},"backgroundImage":{"url":GRADS[i-1],"style":{"fit":"cover"}}}
    t_title={"id":f"t{i}","kind":"image","url":timg(title),"style":{"fit":"scale-down"}}
    lc={"id":f"lc{i}","kind":"image","url":timg("Current Period",30,"#E8FFE0",700),"style":{"fit":"scale-down"}}
    lp={"id":f"lp{i}","kind":"image","url":timg("Prior Year",30,"#E8FFE0",700),"style":{"fit":"scale-down"}}
    def kpi(sfx,period,fmt=fmt):
        return {"id":f"k{i}{sfx}","kind":"kpi-chart","source":{"elementId":"tbl","kind":"table"},
                "columns":[{"id":f"k{i}{sfx}v","formula":mf.replace("§",period),"name":period,"format":fmt}],
                "value":{"columnId":f"k{i}{sfx}v","color":"#FFFFFF"},"name":{"visibility":"hidden"},
                "layout":{"anchor":"middle"},"style":dict(TRANS)}
    kc=kpi("c","Current Period"); kp=kpi("p","Prior Year")
    line={"id":f"ln{i}","kind":"line-chart","source":{"elementId":"tbl","kind":"table"},
          "columns":[{"id":f"ln{i}m","formula":f"[{BASE}/Order Month]","name":"Month"},{"id":f"ln{i}v","formula":trend,"name":"Trend"}],
          "xAxis":{"columnId":f"ln{i}m","format":{"labels":"hidden","marks":"none"}},
          "yAxis":{"columnIds":[f"ln{i}v"],"format":{"labels":"hidden","marks":"none","scale":{"type":"linear","zero":False,"hideZeroLine":True}}},
          "name":{"visibility":"hidden"},"legend":{"visibility":"hidden"},"lineAreaStyle":{"interpolation":"monotone"},"style":dict(TRANS)}
    card_elems+=[cont,t_title,lc,kc,lp,kp,line]
    x0=1+(i-1)*8; x1=1+i*8
    card_layout.append(f'''  <GridContainer elementId="{cid}" type="grid" gridColumn="{x0} / {x1}" gridRow="8 / 18" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <LayoutElement elementId="t{i}" gridColumn="1 / 13" gridRow="1 / 3"/>
    <LayoutElement elementId="lc{i}" gridColumn="1 / 7" gridRow="3 / 5"/>
    <LayoutElement elementId="lp{i}" gridColumn="7 / 13" gridRow="3 / 5"/>
    <LayoutElement elementId="k{i}c" gridColumn="1 / 7" gridRow="5 / 10"/>
    <LayoutElement elementId="k{i}p" gridColumn="7 / 13" gridRow="5 / 10"/>
    <LayoutElement elementId="ln{i}" gridColumn="1 / 13" gridRow="10 / 13"/>
  </GridContainer>''')

# ---- header (heavily-prompted NVIDIA data-center hero + logo + title) ----
hero="data:image/jpeg;base64,"+base64.b64encode(open(SP/"nvda_hero-sm.jpg","rb").read()).decode()
nvlogo=('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 230 96" preserveAspectRatio="xMinYMid meet">'
 '<text x="6" y="62" font-family="Arial,Helvetica,sans-serif" font-weight="800" font-size="42" fill="#76B900" letter-spacing="1">NVIDIA</text></svg>')
def title_wm(h,s):
    return "data:image/svg+xml;base64,"+b64(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 940 150" preserveAspectRatio="xMinYMid meet"><text x="6" y="70" font-family="Arial,Helvetica,sans-serif" font-weight="800" font-size="48" fill="#FFFFFF">{h}</text><text x="8" y="112" font-family="Arial,Helvetica,sans-serif" font-weight="500" font-size="23" fill="#B7E36B">{s}</text></svg>')
masthead={"id":"c-masthead","kind":"container","style":{"backgroundColor":"#05080A","borderRadius":"round"},"backgroundImage":{"url":hero,"style":{"fit":"cover"}}}
logo={"id":"img-logo","kind":"image","url":"data:image/svg+xml;base64,"+b64(nvlogo),"style":{"fit":"scale-down"}}
title={"id":"txt-title","kind":"image","url":title_wm("Commercial Command Center","Segment performance · reshaped from Big Buys POS"),"style":{"fit":"scale-down"}}

# ---- filters (dark) ----
filters={"id":"c-filters","kind":"container","style":dict(CARD)}
def listc(cid,ctrlid,col): return {"kind":"control","controlId":ctrlid,"id":cid,"filters":[{"source":{"kind":"table","elementId":"tbl"},"columnId":col}],"controlType":"list","mode":"include","selectionMode":"multiple","values":[],"source":{"kind":"source","source":{"kind":"table","elementId":"tbl"},"columnId":col}}
ctrl_date={"kind":"control","controlId":"Date","id":"ctrl-date","filters":[{"source":{"kind":"table","elementId":"tbl"},"columnId":"col-date"}],"controlType":"date-range","mode":"between","includeNulls":"when-no-value-is-selected"}
ctrl_region=listc("ctrl-region","Region","col-region"); ctrl_seg=listc("ctrl-seg","Segment","col-segment")

# ---- CallText AI summary in a tinted green box ----
ai_body=('{{ Replace(CallText("'+AICONN+'", "CLAUDE-4-SONNET", '
 '"You are an NVIDIA business analyst. In two concise sentences summarize performance given Revenue $" '
 '& Text(Round(Sum(['+BASE+'/Revenue])/1000000,0)) & "M, Margin $" '
 '& Text(Round(Sum(['+BASE+'/Margin])/1000000,0)) & "M, Units " '
 '& Text(Sum(['+BASE+'/Units])) & ". Note segment strength and margin health."), \'"\', \'\') }}')
ai_box={"id":"c-ai","kind":"container","style":{"backgroundColor":"#EAF7DD","borderColor":"#8BC34A","borderWidth":1,"borderRadius":"round"}}
ai_sum={"id":"txt-ai","kind":"text","body":"### ✨ AI Insight\n\n"+ai_body,"verticalAlign":"middle"}

# ---- bar (Revenue by Segment, green) ----
PASS=[("Segment","sg"),("Product","pr"),("Region","rg"),("State","st"),("City","ct"),("Customer","cu")]
def passcols(cid): return [{"id":f"{cid}_{s}","formula":f"[{BASE}/{n}]","name":n} for n,s in PASS]
bar={"id":"bar","kind":"bar-chart","source":{"elementId":"tbl","kind":"table"},
 "columns":[{"id":"bard","formula":f"[{BASE}/Segment]","name":"Segment"},
            {"id":"barv","formula":f"Sum([{BASE}/Revenue])","name":"Revenue","format":CUR},
            {"id":"barc","formula":f"[{BASE}/Segment]","name":"Segment "}]+passcols("bar"),
 "xAxis":{"columnId":"bard","sort":{"by":"barv","direction":"descending"}},"yAxis":{"columnIds":["barv"]},
 "color":{"by":"category","column":"barc","scheme":["#76B900"]},"legend":{"visibility":"hidden"},
 "name":{"text":"Revenue by Segment","fontWeight":"bold","fontSize":14},"style":dict(CARD)}

# ---- plugin hero panel (GPU heatmap placeholder) ----
plugc={"id":"c-plug","kind":"container","style":{"backgroundColor":"#EFF4EA","borderColor":"#C4D9A8","borderWidth":1,"borderRadius":"round"}}
plugt={"id":"txt-plug","kind":"text","body":"🟢 **GPU Cluster Utilization** — plugin\n\n_Add the hosted heatmap here (Admin → Plugins → Add), bound to the **GPU Fleet** element:_\n\nscintillating-madeleine-4aceba.netlify.app","verticalAlign":"middle"}

elements=[masthead,logo,filters,ctrl_date,ctrl_region,ctrl_seg]+card_elems+[ai_box,ai_sum,bar,plugc,plugt,tbl,fleet]

layout=f"""<?xml version="1.0" encoding="utf-8"?>
<Page type="grid" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto" id="pg">
  <GridContainer elementId="c-masthead" type="grid" gridColumn="1 / 25" gridRow="1 / 5" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <LayoutElement elementId="img-logo" gridColumn="1 / 6" gridRow="1 / 5"/>
  </GridContainer>
  <GridContainer elementId="c-filters" type="grid" gridColumn="1 / 25" gridRow="5 / 8" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <LayoutElement elementId="ctrl-date" gridColumn="1 / 9" gridRow="1 / 4"/>
    <LayoutElement elementId="ctrl-region" gridColumn="9 / 17" gridRow="1 / 4"/>
    <LayoutElement elementId="ctrl-seg" gridColumn="17 / 25" gridRow="1 / 4"/>
  </GridContainer>
{chr(10).join(card_layout)}
  <GridContainer elementId="c-ai" type="grid" gridColumn="1 / 25" gridRow="18 / 22" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <LayoutElement elementId="txt-ai" gridColumn="1 / 25" gridRow="1 / 4"/>
  </GridContainer>
  <LayoutElement elementId="bar" gridColumn="1 / 13" gridRow="22 / 36"/>
  <GridContainer elementId="c-plug" type="grid" gridColumn="13 / 25" gridRow="22 / 36" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">
    <LayoutElement elementId="txt-plug" gridColumn="1 / 13" gridRow="1 / 13"/>
  </GridContainer>
  <LayoutElement elementId="tbl" gridColumn="1 / 25" gridRow="36 / 54"/>
  <LayoutElement elementId="fleet" gridColumn="1 / 25" gridRow="54 / 70"/>
</Page>
"""
theme={"colors":{"text":"#14231A","highlight":"#76B900","success":"#2E7D32","warning":"#E4B23C","danger":"#D93025","darkMode":"hidden"},
 "colorOverrides":{"backgroundCanvas":"#FFFFFF","canvasBackground":"#EEF1EA"},
 "categoricalScheme":["#FFFFFF","#76B900","#3E7A00","#A3E635","#4B5563","#8E8E93"],
 "fonts":{"textFont":"Inter","dataFont":"Inter"},"pageWidth":"full","tableStyles":{"preset":"presentation","cellSpacing":"small"}}
spec={"name":"NVIDIA — Commercial Command Center","folderId":FOLDER,"schemaVersion":1,"pages":[{"id":"pg","name":"Overview","elements":elements}],"layout":layout,"themeOverrides":theme}
out=SP/"nvda.json"; out.write_text(json.dumps(spec,indent=2)); print("wrote",out,"| elements:",len(elements))
