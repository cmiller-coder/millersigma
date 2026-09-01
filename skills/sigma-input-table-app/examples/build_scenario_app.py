import json,sys,urllib.request
BASE,TOKEN,CONN,FOLDER=sys.argv[1:5]
H={"Authorization":"Bearer "+TOKEN,"Content-Type":"application/json"}
CUR={"kind":"number","formatString":"$.3~s","currencySymbol":"$","decimalSymbol":".","digitGroupingSymbol":",","digitGroupingSize":[3]}
CARD={"backgroundColor":"#FFFFFF","borderColor":"#DfE6EE","borderWidth":1,"borderRadius":"round"}
NAVY="#0A1F3B"; TEAL="#14B8A6"; RED="#EF4444"
weekly={"id":"weekly","kind":"table","name":"Weekly","visibleAsSource":True,
 "source":{"connectionId":CONN,"kind":"sql","statement":"SELECT DATE_TRUNC('week',DATE)::date AS WEEK, SUM(QUANTITY*PRICE) AS ACTUAL, ROUND(SUM(QUANTITY*PRICE)*1.10) AS TARGET, ROUND(SUM(QUANTITY*PRICE)*1.02) AS STAT FROM SE_DEMO_DB.BIG_BUYS.BIG_BUYS_POS WHERE DATE >= DATEADD('year',-1,(SELECT MAX(DATE) FROM SE_DEMO_DB.BIG_BUYS.BIG_BUYS_POS)) GROUP BY 1 ORDER BY 1"},
 "columns":[{"id":"w-week","formula":"[Custom SQL/WEEK]","name":"Week"},{"id":"w-act","formula":"[Custom SQL/ACTUAL]","name":"Actual","format":CUR},{"id":"w-tgt","formula":"[Custom SQL/TARGET]","name":"Target","format":CUR},{"id":"w-stat","formula":"[Custom SQL/STAT]","name":"Stat","format":CUR}],"order":["w-week","w-act","w-tgt","w-stat"]}
scenarios={"id":"scenarios","kind":"input-table","source":{"kind":"empty","connectionId":CONN},"inputMode":"edit","name":"Scenarios",
 "columns":[{"id":"s-name","type":"text","name":"Forecast Name"},{"id":"s-status","type":"text","name":"Status","values":["Draft","Reviewed","Published"],"pills":"color-by-option"}]}
cross={"id":"cross","kind":"table","name":"Cross Join","visibleAsSource":True,
 "source":{"kind":"join","joins":[{"left":{"elementId":"scenarios","kind":"table"},"right":{"elementId":"weekly","kind":"table"},"columns":[{"left":"1","right":"1"}],"joinType":"left-outer"}],"primarySource":{"elementId":"scenarios","kind":"table"}},
 "columns":[{"id":"cj-name","formula":"[Scenarios/Forecast Name]","name":"Forecast Name"},{"id":"cj-week","formula":"[Weekly/Week]","name":"Week"},{"id":"cj-act","formula":"[Weekly/Actual]","name":"Actual","format":CUR},{"id":"cj-tgt","formula":"[Weekly/Target]","name":"Target","format":CUR},{"id":"cj-stat","formula":"[Weekly/Stat]","name":"Stat","format":CUR}],
 "order":["cj-name","cj-week","cj-act","cj-tgt","cj-stat"]}
forecast={"id":"forecast","kind":"input-table","source":{"kind":"linked","from":"cross"},"inputMode":"edit","name":"Forecast",
 "columns":[{"id":"fk-n","key":"cj-name","hidden":True},{"id":"fk-w","key":"cj-week","hidden":True},
            {"id":"f-week","formula":"[Cross Join/Week]","name":"Week"},{"id":"f-tgt","formula":"[Cross Join/Target]","name":"Target","format":CUR},
            {"id":"f-act","formula":"[Cross Join/Actual]","name":"Actual","format":CUR},{"id":"f-stat","formula":"[Cross Join/Stat]","name":"Stat Forecast","format":CUR},
            {"id":"f-adj","type":"number","name":"Adjustment"},{"id":"f-fc","formula":"Coalesce([Adjustment],[Stat Forecast])","name":"Forecast","format":CUR},
            {"id":"f-d","formula":"[Forecast]-[Target]","name":"Δ (Forecast - Target)","format":CUR},{"id":"f-c","type":"text","name":"Comments"}]}
# KPI card helper: white card = title text + big kpi + delta text
def card(i,title,formula,deltaf,x0,x1):
    cid=f"c{i}"; k=f"k{i}"
    cont={"id":cid,"kind":"container","style":dict(CARD)}
    t={"id":f"t{i}","kind":"text","body":f"**{title}**","verticalAlign":"middle"}
    kp={"id":k,"kind":"kpi-chart","source":{"elementId":"forecast","kind":"table"},"columns":[{"id":k+"v","formula":formula,"name":title,"format":CUR}],"value":{"columnId":k+"v","color":NAVY},"name":{"visibility":"hidden"},"layout":{"anchor":"middle"}}
    dl={"id":f"d{i}","kind":"text","body":deltaf,"verticalAlign":"middle"}
    lay=f'<GridContainer elementId="{cid}" type="grid" gridColumn="{x0} / {x1}" gridRow="5 / 15" gridTemplateColumns="repeat(12,1fr)" gridTemplateRows="auto"><LayoutElement elementId="t{i}" gridColumn="1 / 13" gridRow="1 / 3"/><LayoutElement elementId="{k}" gridColumn="1 / 13" gridRow="3 / 9"/><LayoutElement elementId="d{i}" gridColumn="1 / 13" gridRow="9 / 11"/></GridContainer>'
    return [cont,t,kp,dl],lay
delta='{{ "vs Target  " & Text(Round((Sum([Forecast/Forecast])-Sum([Forecast/Target]))/1000000,1)) & "M" }}'
c1,l1=card(1,"Projected Revenue",'Sum([Forecast/Forecast])',delta,1,9)
c2,l2=card(2,"Actuals",'Sum([Forecast/Actual])','{{ "vs Target  " & Text(Round((Sum([Forecast/Actual])-Sum([Forecast/Target]))/1000000,1)) & "M" }}',9,17)
c3,l3=card(3,"Target",'Sum([Forecast/Target])','{{ "annual plan" }}',17,25)
# chart
chart={"id":"chart","kind":"line-chart","source":{"elementId":"forecast","kind":"table"},"style":dict(CARD),
 "columns":[{"id":"ch-w","formula":"[Forecast/Week]","name":"Week"},{"id":"ch-t","formula":"Sum([Forecast/Target])","name":"Target","format":CUR},{"id":"ch-a","formula":"Sum([Forecast/Actual])","name":"Actuals","format":CUR},{"id":"ch-f","formula":"Sum([Forecast/Forecast])","name":"Forecast","format":CUR}],
 "xAxis":{"columnId":"ch-w"},"yAxis":{"columnIds":["ch-t","ch-a","ch-f"]},"name":{"text":"Target · Actuals · Forecast by Week","fontWeight":"bold","fontSize":14}}
# dark toolbar
tb={"id":"tb","kind":"container","style":{"backgroundColor":NAVY,"borderRadius":"round"}}
tblabel={"id":"tblabel","kind":"text","body":'{{ "Scenario Modeler   |   " & CurrentUserEmail() }}',"verticalAlign":"middle"}
newbtn={"id":"newbtn","kind":"button","text":"Create Forecast","appearance":"outline","actions":[{"id":"o1","trigger":"on-click","effects":[{"effect":"clear-control","scope":{"type":"control","controlId":"newScenarioName"}},{"effect":"open-overlay","overlayId":"createModal"}]}]}
selctrl={"kind":"control","controlId":"scenarioSelect","id":"ctrl-sel","name":"Forecast","controlType":"list","selectionMode":"single","mode":"include","filters":[{"source":{"kind":"table","elementId":"cross"},"columnId":"cj-name"}],"source":{"kind":"source","source":{"kind":"table","elementId":"cross"},"columnId":"cj-name"}}
hdr={"id":"hdr","kind":"text","body":"# Demand Planning — Scenario Modeler","verticalAlign":"middle"}
# modal
mtitle={"id":"mtitle","kind":"text","body":"### Create Forecast\nName your scenario, then Create.","verticalAlign":"middle"}
namectrl={"kind":"control","controlId":"newScenarioName","id":"ctrl-name","name":"Forecast Name","controlType":"text","mode":"equals","case":"insensitive","includeNulls":"when-no-value-is-selected","showOperators":False}
createbtn={"id":"createbtn","kind":"button","text":"Create","appearance":"filled","actions":[{"id":"c1","trigger":"on-click","effects":[
    {"effect":"insert-rows","tableElementId":"scenarios","values":{"s-name":{"type":"control","control":"newScenarioName"},"s-status":{"type":"constant","value":{"type":"text","value":"Draft"}}}},
    {"effect":"set-control-value","control":"scenarioSelect","value":{"type":"control","control":"newScenarioName"}},{"effect":"clear-control","scope":{"type":"control","controlId":"newScenarioName"}},{"effect":"close-overlay"}]}]}
cancelbtn={"id":"cancelbtn","kind":"button","text":"Cancel","appearance":"outline","actions":[{"id":"x1","trigger":"on-click","effects":[{"effect":"close-overlay"}]}]}
els=[hdr]+c1+c2+c3+[chart,tb,tblabel,newbtn,selctrl,forecast]
data_page={"id":"data","name":"Data","elements":[weekly,scenarios,cross]}
model_page={"id":"model","name":"Summary","elements":els}
modal={"id":"createModal","name":"Create Forecast","type":"modal","modal":{"width":"small","header":{"title":"Create Forecast","showCloseIcon":"hidden"},"footer":{"primaryCta":{"visible":"hidden"},"secondaryCta":{"visible":"hidden"}}},"elements":[mtitle,namectrl,createbtn,cancelbtn]}
def pg(pid,rows): return f'<Page type="grid" gridTemplateColumns="repeat(24,1fr)" gridTemplateRows="auto" id="{pid}">{rows}</Page>'
ml=pg("model",'<LayoutElement elementId="hdr" gridColumn="1 / 25" gridRow="1 / 5"/>'+l1+l2+l3+
   '<LayoutElement elementId="chart" gridColumn="1 / 25" gridRow="15 / 30"/>'+
   '<GridContainer elementId="tb" type="grid" gridColumn="1 / 25" gridRow="30 / 34" gridTemplateColumns="repeat(24,1fr)" gridTemplateRows="auto"><LayoutElement elementId="tblabel" gridColumn="1 / 12" gridRow="1 / 4"/><LayoutElement elementId="newbtn" gridColumn="18 / 25" gridRow="1 / 4"/></GridContainer>'+
   '<LayoutElement elementId="ctrl-sel" gridColumn="1 / 9" gridRow="34 / 36"/>'+
   '<LayoutElement elementId="forecast" gridColumn="1 / 25" gridRow="36 / 54"/>')
dl=pg("data","".join(f'<LayoutElement elementId="{e["id"]}" gridColumn="1 / 25" gridRow="{1+i*7} / {8+i*7}"/>' for i,e in enumerate(data_page["elements"])))
mo=pg("createModal",'<LayoutElement elementId="mtitle" gridColumn="1 / 25" gridRow="1 / 3"/><LayoutElement elementId="ctrl-name" gridColumn="1 / 25" gridRow="3 / 5"/><LayoutElement elementId="cancelbtn" gridColumn="13 / 19" gridRow="5 / 7"/><LayoutElement elementId="createbtn" gridColumn="19 / 25" gridRow="5 / 7"/>')
spec={"name":"Scenario Modeler — Styled v2","folderId":FOLDER,"schemaVersion":1,"pages":[model_page,data_page,modal],"layout":'<?xml version="1.0" encoding="utf-8"?>\n'+ml+dl+mo,
 # colorOverrides:[] TEMP workaround for a live regression, see schema-2026-08-breaking-changes.md
 "themeOverrides":{"colors":{"text":"#0F2138","highlight":TEAL},"colorOverrides":[],"categoricalScheme":["#0A1F3B","#14B8A6","#EF4444","#64748B"],"fonts":{"textFont":"Inter","dataFont":"Inter"},"pageWidth":"full"}}
r=urllib.request.Request(BASE+"/v2/workbooks/spec",data=json.dumps(spec).encode(),headers=H,method="POST")
try:
    resp=urllib.request.urlopen(r,timeout=90).read().decode()
    print("POST:", "ACCEPTED" if "success: true" in resp else resp[:400])
    wid=[l.split()[-1] for l in resp.splitlines() if "workbookId" in l]
    if wid: print("URL:", json.loads(urllib.request.urlopen(urllib.request.Request(BASE+f"/v2/workbooks/{wid[0]}",headers=H),timeout=30).read().decode()).get("url"))
except urllib.error.HTTPError as e:
    print("HTTP",e.code,":",json.loads(e.read().decode()).get("message","")[:400])
