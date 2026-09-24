#!/usr/bin/env python3
"""Fetch the real OSRS wiki sprite for every item in our universe; base64 them."""
import json, pathlib, re, time, urllib.parse, urllib.request, base64, sys

OUT = pathlib.Path("/private/tmp/claude-502/rs")
mapping = json.loads(pathlib.Path("/tmp/osrs_map.json").read_text())
sql = (OUT / "market_layer.sql").read_text()

# recover the exact item names we kept, from the generated VALUES rows
names = set(re.findall(r"^\s+\(\d+,'((?:[^']|'')+)'", sql, re.M))
names = {n.replace("''", "'") for n in names}
icon_by_name = {m["name"]: m.get("icon") for m in mapping}

UA = "sigma-demo-build/1.0 (cmiller@sigmacomputing.com) OSRS market workbook"
sprites, missing = {}, []
for i, name in enumerate(sorted(names)):
    icon = icon_by_name.get(name)
    if not icon:
        missing.append(name); continue
    url = "https://oldschool.runescape.wiki/images/" + urllib.parse.quote(icon.replace(" ", "_"))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            blob = r.read()
        if blob[:8] != b"\x89PNG\r\n\x1a\n":
            missing.append(name); continue
        sprites[name] = base64.b64encode(blob).decode()
    except Exception as e:
        missing.append(f"{name} ({e.__class__.__name__})")
    if i % 40 == 0:
        print(f"  {i}/{len(names)}", flush=True)
    time.sleep(0.06)

json.dump(sprites, open(OUT / "sprites.json", "w"))
raw = sum(len(base64.b64decode(v)) for v in sprites.values())
print(f"\nfetched {len(sprites)}/{len(names)} sprites  raw={raw/1024:.0f}KB  b64={sum(len(v) for v in sprites.values())/1024:.0f}KB")
if missing:
    print(f"missing {len(missing)}: {missing[:15]}")
