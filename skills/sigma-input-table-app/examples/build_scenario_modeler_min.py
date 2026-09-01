import json,sys,base64,urllib.request
BASE,TOKEN,CONN,FOLDER=sys.argv[1:5]
H={"Authorization":"Bearer "+TOKEN,"Content-Type":"application/json"}
def b64(s): return base64.b64encode(s.encode()).decode()
CUR={"kind":"number","formatString":"$.3~s","currencySymbol":"$","decimalSymbol":".","digitGroupingSymbol":",","digitGroupingSize":[3]}
CARD={"backgroundColor":"#FFFFFF","borderColor":"#E3E8EF","borderWidth":1,"borderRadius":"round"}
GOOD="#0D9488"; BAD="#DC2626"
def timg(txt,sz=24,col="#FFFFFF",w=800,anchor="middle",x=160):
    a={"start":"start","middle":"middle"}[anchor]
    return "data:image/svg+xml;base64,"+b64(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 44" preserveAspectRatio="xMidYMid meet"><text x="{x}" y="31" text-anchor="{a}" font-family="Arial,Helvetica,sans-serif" font-weight="{w}" font-size="{sz}" fill="{col}">{txt}</text></svg>')

# ---------- VERIFIED v4 foundation ----------
base={"id":"base","kind":"table","name":"Custom SQL Base","visibleAsSource":True,
 "source":{"connectionId":CONN,"kind":"sql","statement":"SELECT PRODUCT_FAMILY, QUANTITY*PRICE AS REVENUE FROM SE_DEMO_DB.BIG_BUYS.BIG_BUYS_POS"},
 "columns":[{"id":"b-fam","formula":"[Custom SQL/PRODUCT_FAMILY]","name":"Product Family"},{"id":"b-rev","formula":"[Custom SQL/REVENUE]","name":"Revenue","format":CUR}],"order":["b-fam","b-rev"]}
scen={"id":"scenarios","kind":"input-table","source":{"kind":"empty","connectionId":CONN},"inputMode":"edit","name":"Scenario Names",
 "columns":[{"id":"sc-name","type":"text","name":"Scenario Name"},
            {"id":"sc-status","type":"text","name":"Status","values":["Draft","Submitted","Approved"],"pills":"color-by-option"}]}
pivot={"id":"pivot","kind":"pivot-table","name":"Pivot","visibleAsSource":True,
 "source":{"kind":"join","joins":[{"left":{"elementId":"base","kind":"table"},"right":{"elementId":"scenarios","kind":"table"},"columns":[{"left":"1","right":"1"}],"joinType":"left-outer"}],"primarySource":{"elementId":"base","kind":"table"}},
 "columns":[{"id":"pv-fam","formula":"[Custom SQL Base/Product Family]","name":"Product Family"},
            {"id":"pv-scen","formula":"[Scenario Names/Scenario Name]","name":"Scenario"},
            {"id":"pv-rev","formula":"Sum([Custom SQL Base/Revenue])","name":"Revenue","format":CUR}],
 "rowsBy":[{"id":"pv-fam"}],"values":["pv-rev"]}
# linked input table: keys + pulled baseline + editable forecast + row-level Δ + comments
forecast={"id":"forecast","kind":"input-table","source":{"kind":"linked","from":"pivot"},"inputMode":"edit","name":"Forecast Entry",
 "columns":[{"id":"lk-fam","key":"pv-fam"},
            {"id":"lk-scen","key":"pv-scen"},
            {"id":"lk-base","key":"pv-rev"},
            {"id":"lk-fc","type":"number","name":"Forecast Revenue","format":CUR},
            {"id":"lk-var","formula":"[Forecast Revenue]-[Revenue]","name":"Δ (Forecast − Baseline)","format":CUR},
            {"id":"lk-com","type":"text","name":"Comments"}],
 "order":["lk-fam","lk-scen","lk-base","lk-fc","lk-var","lk-com"]}
EFF='Coalesce([Forecast Entry/Forecast Revenue],[Forecast Entry/Revenue])'
# derived NORMAL table -> controls can filter this (not the input table)
detail={"id":"detail","kind":"table","name":"Detail","visibleAsSource":True,
 "source":{"elementId":"forecast","kind":"table"},
 "columns":[{"id":"d-fam","formula":"[Forecast Entry/Product Family]","name":"Product Family"},
            {"id":"d-scen","formula":"[Forecast Entry/Scenario]","name":"Scenario"},
            {"id":"d-base","formula":"[Forecast Entry/Revenue]","name":"Baseline","format":CUR},
            {"id":"d-eff","formula":EFF,"name":"Forecast","format":CUR}],
 "order":["d-fam","d-scen","d-base","d-eff"]}
# submissions log (append-only; Submit inserts here)
subs={"id":"subs","kind":"input-table","source":{"kind":"empty","connectionId":CONN},"inputMode":"edit","name":"Submissions",
 "columns":[{"id":"su-scen","type":"text","name":"Scenario"},{"id":"su-status","type":"text","name":"Status","values":["Submitted","Approved","Change Request"],"pills":"color-by-option"}]}

# ---------- controls ----------
selctrl={"kind":"control","controlId":"scenarioSelect","id":"ctrl-sel","name":"Forecast","controlType":"list","selectionMode":"single","mode":"include",
 "filters":[{"source":{"kind":"table","elementId":"detail"},"columnId":"d-scen"}],
 "source":{"kind":"source","source":{"kind":"table","elementId":"detail"},"columnId":"d-scen"}}

# ---------- comparative KPI cards (composite: title + big value + colored delta) ----------
PCT={"kind":"number","formatString":"+,.1%"}
DPCT={"kind":"number","formatString":"+,.1%"}
DCUR={"kind":"number","formatString":"+$.3~s","currencySymbol":"$","decimalSymbol":".","digitGroupingSymbol":",","digitGroupingSize":[3]}
BASELINE='Sum([Detail/Baseline])'; FCAST='Sum([Detail/Forecast])'
def card(idp,title,mainf,mainfmt,deltaf=None,deltafmt=DCUR,deltalabel="vs Baseline"):
    cont={"id":f"c-{idp}","kind":"container","style":dict(CARD)}
    t={"id":f"t-{idp}","kind":"text","body":f"**{title}**","verticalAlign":"middle","style":{"color":"#5B6B7B"}}
    v={"id":f"v-{idp}","kind":"kpi-chart","source":{"elementId":"detail","kind":"table"},
       "columns":[{"id":f"{idp}mv","formula":mainf,"name":title,"format":mainfmt}],
       "value":{"columnId":f"{idp}mv","fontSize":34},"name":{"visibility":"hidden"},"layout":{"anchor":"middle"},"style":{"backgroundColor":"transparent","padding":"none"}}
    els=[cont,t,v]; rows=[f'<LayoutElement elementId="t-{idp}" gridColumn="1 / 13" gridRow="1 / 3"/>',
                          f'<LayoutElement elementId="v-{idp}" gridColumn="1 / 13" gridRow="3 / 7"/>']
    if deltaf:
        d={"id":f"d-{idp}","kind":"kpi-chart","source":{"elementId":"detail","kind":"table"},
           "columns":[{"id":f"{idp}dv","formula":deltaf,"name":deltalabel,"format":deltafmt}],
           "value":{"columnId":f"{idp}dv","fontSize":15,"color":GOOD},"name":{"text":deltalabel,"fontSize":12},"layout":{"anchor":"middle"},"style":{"backgroundColor":"transparent","padding":"none"}}
        els.append(d); rows.append(f'<LayoutElement elementId="d-{idp}" gridColumn="1 / 13" gridRow="7 / 9"/>')
    lay=f'  <GridContainer elementId="c-{idp}" type="grid" gridColumn="{{col}}" gridRow="4 / 13" gridTemplateColumns="repeat(12, 1fr)" gridTemplateRows="auto">\n    '+"\n    ".join(rows)+"\n  </GridContainer>"
    return els,lay
c1e,c1l=card("k1","Projected Revenue",FCAST,CUR,f"{FCAST}-{BASELINE}",DCUR,"vs Baseline")
c2e,c2l=card("k2","Forecast Uplift",f"({FCAST}-{BASELINE})/{BASELINE}",PCT)
c3e,c3l=card("k3","Baseline Revenue",BASELINE,CUR)
kpi_elems=c1e+c2e+c3e
kpi_layout=c1l.replace("{col}","1 / 9")+"\n"+c2l.replace("{col}","9 / 17")+"\n"+c3l.replace("{col}","17 / 25")

# ---------- toolbar ----------
bar_c={"id":"c-bar","kind":"container","style":{"backgroundColor":"#0B2440","borderRadius":"round"}}
bar_title={"id":"bar-title","kind":"image","source":{"kind":"url","url":timg("Scenario Modeler  |  cmiller@sigmacomputing.com",22,"#E6EEF6",600,"start",8)},"style":{"fit":"scale-down"}}
createbtn_tb={"id":"createbtn_tb","kind":"button","text":"Create Forecast","appearance":"filled","actions":[{"id":"o1","trigger":"on-click","effects":[{"effect":"open-overlay","overlayId":"createModal"}]}]}
submitbtn={"id":"submitbtn","kind":"button","text":"Submit Forecast","appearance":"outline","actions":[{"id":"s1","trigger":"on-click","effects":[
    {"effect":"insert-rows","tableElementId":"subs","values":{"su-scen":{"type":"control","control":"scenarioSelect"},"su-status":{"type":"constant","value":{"type":"text","value":"Submitted"}}}}]}]}

# ---------- baseline vs forecast bar ----------
barchart={"id":"bar","kind":"bar-chart","source":{"elementId":"detail","kind":"table"},
 "columns":[{"id":"bd","formula":"[Detail/Product Family]","name":"Product Family"},
            {"id":"bb","formula":"Sum([Detail/Baseline])","name":"Baseline","format":CUR},
            {"id":"bf","formula":"Sum([Detail/Forecast])","name":"Forecast","format":CUR}],
 "xAxis":{"columnId":"bd","sort":{"by":"bb","direction":"descending"}},"yAxis":{"columnIds":["bb","bf"]},
 "legend":{"visibility":"visible"},"name":{"text":"Baseline vs Forecast by Product Family","fontWeight":"bold","fontSize":14},"style":dict(CARD)}

# ---------- create modal ----------
mtitle={"id":"mtitle","kind":"text","body":"### New forecast scenario\nName it, then Create — it copies the baseline for every product family.","verticalAlign":"middle"}
namectrl={"kind":"control","controlId":"newScenarioName","id":"ctrl-name","name":"Scenario Name","controlType":"text","mode":"equals","case":"insensitive","includeNulls":"when-no-value-is-selected","showOperators":False}
createbtn={"id":"createbtn","kind":"button","text":"Create","appearance":"filled","actions":[{"id":"c1","trigger":"on-click","effects":[
    {"effect":"insert-rows","tableElementId":"scenarios","values":{"sc-name":{"type":"control","control":"newScenarioName"},"sc-status":{"type":"constant","value":{"type":"text","value":"Draft"}}}},
    {"effect":"set-control-value","control":"scenarioSelect","value":{"type":"control","control":"newScenarioName"}},
    {"effect":"clear-control","scope":{"type":"control","controlId":"newScenarioName"}},
    {"effect":"close-overlay"}]}]}
cancelbtn={"id":"cancelbtn","kind":"button","text":"Cancel","appearance":"outline","actions":[{"id":"x1","trigger":"on-click","effects":[{"effect":"close-overlay"}]}]}
modal={"id":"createModal","name":"Create Scenario","type":"modal","modal":{"width":"small","header":{"title":"New Forecast","showCloseIcon":"hidden"},"footer":{"primaryCta":{"visible":"hidden"},"secondaryCta":{"visible":"hidden"}}},"elements":[mtitle,namectrl,createbtn,cancelbtn]}

model_page={"id":"model","name":"Modeler","elements":[bar_c,bar_title,createbtn_tb,submitbtn,selctrl]+kpi_elems+[barchart,forecast]}
data_page={"id":"data","name":"Data","elements":[base,scen,pivot,detail,subs]}
def pg(pid,rows): return f'<Page type="grid" gridTemplateColumns="repeat(24,1fr)" gridTemplateRows="auto" id="{pid}">{rows}</Page>'
ml=pg("model",f'''  <GridContainer elementId="c-bar" type="grid" gridColumn="1 / 25" gridRow="1 / 4" gridTemplateColumns="repeat(24, 1fr)" gridTemplateRows="auto">
    <LayoutElement elementId="bar-title" gridColumn="1 / 13" gridRow="1 / 4"/>
    <LayoutElement elementId="createbtn_tb" gridColumn="15 / 20" gridRow="1 / 4"/>
    <LayoutElement elementId="submitbtn" gridColumn="20 / 24" gridRow="1 / 4"/>
  </GridContainer>
{kpi_layout}
  <LayoutElement elementId="ctrl-sel" gridColumn="1 / 9" gridRow="13 / 16"/>
  <LayoutElement elementId="bar" gridColumn="1 / 25" gridRow="16 / 31"/>
  <LayoutElement elementId="forecast" gridColumn="1 / 25" gridRow="31 / 52"/>''')
dl=pg("data","".join(f'<LayoutElement elementId="{e["id"]}" gridColumn="1 / 25" gridRow="{1+i*7} / {8+i*7}"/>' for i,e in enumerate(data_page["elements"])))
mo=pg("createModal",'<LayoutElement elementId="mtitle" gridColumn="1 / 25" gridRow="1 / 3"/><LayoutElement elementId="ctrl-name" gridColumn="1 / 25" gridRow="3 / 5"/><LayoutElement elementId="cancelbtn" gridColumn="13 / 19" gridRow="5 / 7"/><LayoutElement elementId="createbtn" gridColumn="19 / 25" gridRow="5 / 7"/>')
theme={"colors":{"text":"#0F2138","highlight":"#0D9488","success":GOOD,"warning":"#F59E0B","danger":BAD,"darkMode":"hidden"},
 "colorOverrides":[],  # TEMP: live colorOverrides regression, see schema-2026-08-breaking-changes.md
 "categoricalScheme":["#1E3A8A","#0D9488","#7C3AED","#F59E0B","#3B82F6","#64748B"],
 "fonts":{"textFont":"Inter","dataFont":"Inter"},"pageWidth":"full","tableStyles":{"preset":"presentation","cellSpacing":"small"}}
spec={"name":"Scenario Modeler — Demand Planning (v2)","folderId":FOLDER,"schemaVersion":1,"pages":[model_page,data_page,modal],
 "layout":'<?xml version="1.0" encoding="utf-8"?>\n'+ml+dl+mo,"themeOverrides":theme}
r=urllib.request.Request(BASE+"/v2/workbooks/spec",data=json.dumps(spec).encode(),headers=H,method="POST")
try:
    resp=urllib.request.urlopen(r,timeout=90).read().decode()
    print("POST:", "ACCEPTED" if "success: true" in resp else resp[:500])
    wid=[l.split()[-1] for l in resp.splitlines() if "workbookId" in l]
    if wid: print("URL:", json.loads(urllib.request.urlopen(urllib.request.Request(BASE+f"/v2/workbooks/{wid[0]}",headers=H),timeout=30).read().decode()).get("url"))
except urllib.error.HTTPError as e:
    print("HTTP",e.code,":",json.loads(e.read().decode()).get("message","")[:500])
