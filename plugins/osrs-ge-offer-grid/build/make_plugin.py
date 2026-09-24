#!/usr/bin/env python3
"""Generate the OSRS Grand Exchange offer-grid plugin with real sprites embedded."""
import json, pathlib

RS = pathlib.Path("/private/tmp/claude-502/rs")
DEST = pathlib.Path("/Users/cmiller/Desktop/millersigma/plugins/osrs-ge-offer-grid/index.html")

sprites = json.load(open(RS / "sprites.json"))
top = json.load(open(RS / "top_flips.json"))
meta = json.load(open(RS / "meta.json"))

# Static fallback = the real top flips, so an unbound preview still reads as real data.
snap = [[r["name"], r["insta_buy"], r["insta_sell"], r["net"],
         round(r["net"] / r["insta_sell"], 5), r["limit"], r["vol"], r["tax"]] for r in top]

HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Grand Exchange — Offer Grid</title>
<script src="https://unpkg.com/react@18/umd/react.production.min.js" crossorigin></script>
<script src="https://unpkg.com/@sigmacomputing/plugin"></script>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  html,body{height:100%;background:transparent;overflow:hidden}
  body{font:13px/1.35 "Helvetica Neue",Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}

  /* --- the OSRS interface frame: dark outer, lit inner bevel --- */
  #frame{
    position:absolute;inset:0;display:flex;flex-direction:column;
    background:#3E3529;
    border:2px solid #1B1712;
    box-shadow:inset 0 0 0 1px #6F634E, inset 0 0 0 2px #2B2620, inset 0 2px 0 2px #564C3B;
  }
  /* faint leather noise, exactly like the in-game panels */
  #frame::before{
    content:"";position:absolute;inset:0;pointer-events:none;opacity:.055;
    background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3'/></filter><rect width='120' height='120' filter='url(%23n)'/></svg>");
  }

  header{
    flex:0 0 auto;display:flex;align-items:baseline;gap:9px;
    padding:7px 11px 6px;border-bottom:2px solid #1B1712;
    background:linear-gradient(#4A4133,#3A3227);position:relative;z-index:1;
  }
  h1{
    font-size:12.5px;font-weight:700;letter-spacing:.9px;text-transform:uppercase;
    color:#FF981F;text-shadow:1px 1px 0 #000;
  }
  #sub{font-size:10.5px;color:#C9BCA0;text-shadow:1px 1px 0 #000;letter-spacing:.2px}

  #grid{
    flex:1 1 auto;overflow-y:auto;overflow-x:hidden;padding:9px;position:relative;z-index:1;
    display:grid;grid-template-columns:repeat(auto-fill,minmax(74px,1fr));
    gap:5px;align-content:start;
  }
  #grid::-webkit-scrollbar{width:9px}
  #grid::-webkit-scrollbar-track{background:#2B2620}
  #grid::-webkit-scrollbar-thumb{background:#6F634E;border:1px solid #1B1712}

  /* --- an inventory slot --- */
  .slot{
    position:relative;height:72px;cursor:pointer;
    background:#332C22;
    box-shadow:inset 1px 1px 0 #1B1712, inset -1px -1px 0 #574C3C;
    display:flex;align-items:center;justify-content:center;
  }
  .slot:hover{background:#413828;box-shadow:inset 0 0 0 1px #FF981F}
  .slot img{
    width:34px;height:34px;object-fit:contain;image-rendering:pixelated;
    margin-top:-6px;filter:drop-shadow(1px 1px 0 rgba(0,0,0,.55));
  }
  /* stack count, top-left, in the real RS quantity colours */
  .qty{
    position:absolute;top:2px;left:3px;font-size:10px;font-weight:700;
    text-shadow:1px 1px 0 #000;letter-spacing:.2px;pointer-events:none;
  }
  .q-y{color:#FFFF00}   /* under 100k  */
  .q-w{color:#FFFFFF}   /* 100k - 10m  */
  .q-g{color:#00FF80}   /* 10m and up  */

  /* net margin badge along the bottom of the slot */
  .mg{
    position:absolute;left:0;right:0;bottom:0;text-align:center;
    font-size:9.5px;font-weight:700;padding:1px 0 2px;
    text-shadow:1px 1px 0 #000;background:rgba(0,0,0,.34);
    white-space:nowrap;overflow:hidden;
  }
  .up{color:#4BE04B}.dn{color:#FF5B4A}.flat{color:#B9AC92}

  /* a thin left edge marks where GE tax has eaten the whole spread */
  .taxed::after{
    content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:#C4241A;
  }

  footer{
    flex:0 0 auto;display:flex;justify-content:space-between;align-items:center;gap:10px;
    padding:5px 11px 6px;border-top:2px solid #1B1712;
    background:linear-gradient(#3A3227,#332C22);position:relative;z-index:1;
    font-size:10px;color:#9C9078;text-shadow:1px 1px 0 #000;
  }
  footer b{color:#FFC65B;font-weight:700}

  /* --- RS tooltip: black box, yellow title --- */
  #tip{
    position:fixed;z-index:9;pointer-events:none;opacity:0;transition:opacity .07s;
    background:#000;border:1px solid #6F634E;padding:5px 8px 6px;
    font-size:11px;line-height:1.5;color:#fff;white-space:nowrap;
    box-shadow:2px 2px 0 rgba(0,0,0,.5);
  }
  #tip .t{color:#FFFF00;font-weight:700;margin-bottom:2px}
  #tip .r{display:flex;justify-content:space-between;gap:16px}
  #tip .k{color:#A79B82}
  #tip .warn{color:#FF7A6B;margin-top:3px}
  #empty{
    grid-column:1/-1;padding:26px 10px;text-align:center;
    color:#9C9078;font-size:11px;text-shadow:1px 1px 0 #000;
  }
</style>
</head>
<body>
<div id="frame">
  <header><h1>Grand Exchange &mdash; Offer Grid</h1><span id="sub"></span></header>
  <div id="grid"></div>
  <footer><span id="fl"></span><span id="fr"></span></footer>
</div>
<div id="tip"></div>

<script>
(function(){
  "use strict";
  var SPRITES = __SPRITES__;
  var SNAPSHOT = __SNAPSHOT__;
  var CAPTURED = "__CAPTURED__";

  var client = (window.SigmaPlugin && window.SigmaPlugin.client) || null;

  client && client.config.configureEditorPanel([
    {name:'source',    type:'element'},
    {name:'itemName',  type:'column', source:'source', label:'Item name'},
    {name:'instaBuy',  type:'column', source:'source', allowedTypes:['number','integer'], label:'Insta-buy price'},
    {name:'instaSell', type:'column', source:'source', allowedTypes:['number','integer'], label:'Insta-sell price'},
    {name:'netMargin', type:'column', source:'source', allowedTypes:['number','integer'], label:'Net margin (after tax)'},
    {name:'roiPct',    type:'column', source:'source', allowedTypes:['number'],           label:'ROI %'},
    {name:'buyLimit',  type:'column', source:'source', allowedTypes:['number','integer'], label:'4h buy limit'},
    {name:'volume',    type:'column', source:'source', allowedTypes:['number','integer'], label:'24h volume'},
    {name:'geTax',     type:'column', source:'source', allowedTypes:['number','integer'], label:'GE tax'},
    {name:'maxSlots',  type:'text',   label:'Max slots (default 40)'}
  ]);

  var tip  = document.getElementById('tip');
  var grid = document.getElementById('grid');

  function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  // RuneScape's own quantity shorthand: 100000 -> "100K", 10000000 -> "10M"
  function rsQty(n){
    n = Math.round(Number(n)||0);
    if (n >= 10000000) return Math.floor(n/1000000) + 'M';
    if (n >= 100000)   return Math.floor(n/1000) + 'K';
    return String(n);
  }
  function qtyClass(n){
    n = Number(n)||0;
    return n >= 10000000 ? 'q-g' : (n >= 100000 ? 'q-w' : 'q-y');
  }
  function gp(n){
    n = Math.round(Number(n)||0);
    var s = Math.abs(n).toLocaleString('en-US');
    return (n<0?'-':'') + s;
  }
  function shortGp(n){
    var a = Math.abs(Number(n)||0), sg = n<0?'-':'';
    if (a >= 1000000) return sg + (a/1000000).toFixed(a>=10000000?0:1) + 'm';
    if (a >= 1000)    return sg + (a/1000).toFixed(a>=10000?0:1) + 'k';
    return sg + Math.round(a);
  }
  function spriteFor(name){
    return 'data:image/png;base64,' + (SPRITES[name] || SPRITES['__fallback__']);
  }

  function showTip(e, d){
    var taxKilled = d.geTax != null && d.gross != null && d.geTax >= d.gross;
    var html =
      '<div class="t">' + esc(d.name) + '</div>' +
      row('Insta-buy',  gp(d.instaBuy)  + ' gp') +
      row('Insta-sell', gp(d.instaSell) + ' gp') +
      (d.geTax != null ? row('GE tax (2%)', '-' + gp(d.geTax) + ' gp') : '') +
      row('Net margin', (d.netMargin>0?'+':'') + gp(d.netMargin) + ' gp') +
      (d.roiPct != null ? row('ROI', (d.roiPct*100).toFixed(2) + '%') : '') +
      (d.buyLimit ? row('4h buy limit', gp(d.buyLimit) + ' ea') : '') +
      (d.buyLimit && d.instaSell ? row('Capital to fill', shortGp(d.instaSell*d.buyLimit) + ' gp') : '') +
      (d.volume   ? row('24h volume',   gp(d.volume)   + ' traded') : '') +
      (d.buyLimit && d.netMargin ? row('Per 4h cycle', (d.netMargin*d.buyLimit>0?'+':'') + shortGp(d.netMargin*d.buyLimit) + ' gp') : '') +
      (taxKilled ? '<div class="warn">Tax exceeds the spread &mdash; unprofitable</div>' : '');
    tip.innerHTML = html;
    tip.style.opacity = 1;
    var w = tip.offsetWidth, h = tip.offsetHeight;
    var x = e.clientX + 14, y = e.clientY + 12;
    if (x + w > window.innerWidth  - 4) x = e.clientX - w - 10;
    if (y + h > window.innerHeight - 4) y = e.clientY - h - 8;
    tip.style.left = Math.max(2, x) + 'px';
    tip.style.top  = Math.max(2, y) + 'px';
  }
  function row(k, v){ return '<div class="r"><span class="k">' + k + '</span><span>' + v + '</span></div>'; }

  var painted = false;
  function render(rows, bound){
    painted = true;
    grid.innerHTML = '';
    if (!rows.length){
      grid.innerHTML = '<div id="empty">No tradeable offers in the current selection.</div>';
      document.getElementById('sub').textContent = '';
      document.getElementById('fl').textContent  = '';
      document.getElementById('fr').textContent  = '';
      return;
    }
    // biggest realisable profit first -- the order a merchant actually cares about
    rows = rows.slice().sort(function(a,b){
      return (b.netMargin*(b.buyLimit||1)) - (a.netMargin*(a.buyLimit||1));
    });

    var cap = 40;
    if (window.__maxSlots__) { var m = parseInt(window.__maxSlots__,10); if (m>0) cap = m; }
    rows = rows.slice(0, cap);

    var totalCycle = 0, taxedOut = 0;
    rows.forEach(function(d){
      totalCycle += (d.netMargin||0) * (d.buyLimit||0);
      if (d.geTax != null && d.gross != null && d.geTax >= d.gross) taxedOut++;

      var slot = document.createElement('div');
      slot.className = 'slot' + ((d.geTax!=null && d.gross!=null && d.geTax>=d.gross) ? ' taxed' : '');

      var capital = (Number(d.instaSell)||0) * (Number(d.buyLimit)||0);
      var q = document.createElement('div');
      q.className = 'qty ' + qtyClass(capital);
      q.textContent = rsQty(capital);

      var img = document.createElement('img');
      img.src = spriteFor(d.name);
      img.alt = d.name;

      var mg = document.createElement('div');
      var v = Number(d.netMargin) || 0;
      mg.className = 'mg ' + (v>0 ? 'up' : (v<0 ? 'dn' : 'flat'));
      mg.textContent = (v>0?'\\u25B2 ':(v<0?'\\u25BC ':'')) + shortGp(v);

      slot.appendChild(q); slot.appendChild(img); slot.appendChild(mg);
      slot.addEventListener('mousemove', function(e){ showTip(e, d); });
      slot.addEventListener('mouseleave', function(){ tip.style.opacity = 0; });
      grid.appendChild(slot);
    });

    document.getElementById('sub').textContent =
      rows.length + ' offers' + (bound ? '' : ' \\u00b7 snapshot ' + CAPTURED);
    document.getElementById('fl').innerHTML =
      'Stack = gold to fill the offer \\u00b7 <b>' + taxedOut + '</b> where tax exceeds the spread';
    document.getElementById('fr').innerHTML =
      'Profit per full cycle <b>' + shortGp(totalCycle) + ' gp</b>';
  }

  function fromSnapshot(){
    return SNAPSHOT.map(function(r){
      return { name:r[0], instaBuy:r[1], instaSell:r[2], netMargin:r[3],
               roiPct:r[4], buyLimit:r[5], volume:r[6], geTax:r[7],
               gross:r[1]-r[2] };
    });
  }

  var unsub = null;
  function bind(cfg){
    if (unsub){ unsub(); unsub = null; }
    window.__maxSlots__ = cfg && cfg.maxSlots;
    if (!client || !cfg || !cfg.source || !cfg.itemName){ render(fromSnapshot(), false); return; }
    unsub = client.elements.subscribeToElementData(cfg.source, function(ed){
      if (!ed || !ed[cfg.itemName]){ render(fromSnapshot(), false); return; }
      var names = ed[cfg.itemName], n = names.length, rows = [];
      function col(key, i){ return (cfg[key] && ed[cfg[key]]) ? Number(ed[cfg[key]][i]) : null; }
      for (var i=0; i<n; i++){
        var ib = col('instaBuy', i), is = col('instaSell', i);
        rows.push({
          name: names[i],
          instaBuy: ib, instaSell: is,
          netMargin: col('netMargin', i) || 0,
          roiPct:    col('roiPct', i),
          buyLimit:  col('buyLimit', i),
          volume:    col('volume', i),
          geTax:     col('geTax', i),
          gross:     (ib!=null && is!=null) ? (ib-is) : null
        });
      }
      render(rows, true);
    });
  }

  // ORDERING IS LOAD-BEARING, verified live against this org:
  //  * config.subscribe() emits ONCE, early. Any real work done before
  //    registering the handler (even just painting the fallback grid) loses
  //    that emission, and then nothing ever binds.
  //  * subscribeToElementData() only delivers when it is called from INSIDE the
  //    config callback. Calling it later with the same id -- even with a
  //    config.get() that demonstrably holds the right source -- never fires.
  // So: register the config handler FIRST, before touching the DOM, and fall
  // back to the captured snapshot only if nothing has painted shortly after.
  if (client) {
    try { client.config.subscribe(bind); } catch (e) {}
  }
  setTimeout(function () { if (!painted) render(fromSnapshot(), false); }, 900);

  // No animation loop: a headless PNG export has to be able to reach idle.
  new ResizeObserver(function(){}).observe(document.getElementById('frame'));
})();
</script>
</body>
</html>
"""

HTML = (HTML
        .replace("__SPRITES__",  json.dumps(sprites, separators=(",", ":")))
        .replace("__SNAPSHOT__", json.dumps(snap, separators=(",", ":")))
        .replace("__CAPTURED__", meta["snapshot"]))

DEST.parent.mkdir(parents=True, exist_ok=True)
DEST.write_text(HTML)
print(f"wrote {DEST}  ({len(HTML)/1024:.0f} KB, {len(sprites)-1} sprites)")
