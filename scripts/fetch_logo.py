#!/usr/bin/env python3
"""
fetch_logo.py — grab a company's OWN published logo by domain, for a Sigma POV
built for that company. No API key, no Googling.

Usage:
    python3 fetch_logo.py exxonmobil.com                 # -> prints a data: URI
    python3 fetch_logo.py exxonmobil.com --out logo.png  # -> saves the raw asset
    python3 fetch_logo.py exxonmobil.com --datauri-file logo.txt

Strategy (best → fallback):
  1. Header/footer <img> or inline <svg> whose src/class/alt says "logo"
     (prefer .svg, then @2x/high-res raster), from the company's own site.
  2. <link rel="apple-touch-icon"> (high-res square mark), from the company's own site.
  3. og:image, from the company's own site.
  4. Wikipedia's own API (opensearch -> pageimages) for the company's article lead
     image — some corporate sites (verified: amazon.com) return an empty 202
     "Accepted" body to any non-browser request, so steps 1-3 have nothing to parse
     no matter how they're worded. Wikipedia's lead/infobox image for a company
     article is very often its official logo, and the API path (not HTML scraping)
     is far more reliable than guessing at markup. Still a REAL, official brand
     asset — public-domain-in-the-US trademark files on Commons, not a redraw.
Returns nothing usable -> exit 2 (caller should fall back to a wordmark, but should
say so explicitly rather than silently drawing one — see the "don't hand-draw" rule
in sigma-company-dashboard/SKILL.md).

Only use for a legitimate POV/demo for that company — this pulls the
company's own brand asset (or its public-domain-in-the-US Wikipedia/Commons
counterpart) to represent them, standard sales practice.
"""
import sys, re, json, base64, urllib.request, urllib.parse

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

def get(url, timeout=15):
    r = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return resp.read(), resp.headers.get("Content-Type", ""), resp.geturl()

def homepages(domain):
    domain = domain.replace("https://", "").replace("http://", "").strip("/")
    for pre in ("https://corporate.", "https://www.", "https://"):
        yield pre + domain

def score(cand):
    """higher = more logo-like"""
    u, alt, cls = cand
    s = 0
    low = (u + " " + alt + " " + cls).lower()
    if u.lower().endswith(".svg"): s += 40
    if "logo" in low: s += 30
    if "2x" in u or "@2x" in u or "retina" in low: s += 8
    if any(b in low for b in ("sprite", "icon-", "favicon", "spinner", "loader")): s -= 25
    if alt: s += 5
    return s

def find_logo_url(html, base):
    cands = []
    for m in re.finditer(r'<img\b[^>]*>', html, re.I):
        tag = m.group(0)
        src = re.search(r'src\s*=\s*["\']([^"\']+)["\']', tag, re.I)
        if not src: continue
        alt = re.search(r'alt\s*=\s*["\']([^"\']*)["\']', tag, re.I)
        cls = re.search(r'class\s*=\s*["\']([^"\']*)["\']', tag, re.I)
        cands.append((src.group(1), alt.group(1) if alt else "", cls.group(1) if cls else ""))
    # apple-touch-icon
    for m in re.finditer(r'<link\b[^>]*rel\s*=\s*["\'][^"\']*apple-touch-icon[^"\']*["\'][^>]*>', html, re.I):
        href = re.search(r'href\s*=\s*["\']([^"\']+)["\']', m.group(0), re.I)
        if href: cands.append((href.group(1), "", "apple-touch-icon"))
    # og:image
    m = re.search(r'<meta\b[^>]*property\s*=\s*["\']og:image["\'][^>]*content\s*=\s*["\']([^"\']+)["\']', html, re.I)
    if m: cands.append((m.group(1), "", "og-image"))
    if not cands: return None
    cands.sort(key=score, reverse=True)
    return urllib.parse.urljoin(base, cands[0][0])

def _wiki_api(params):
    return json.loads(get("https://en.wikipedia.org/w/api.php?" + params)[0].decode("utf-8", "ignore"))

def wikipedia_logo(domain):
    """Fallback when the company's own site returns nothing parseable (e.g. an
    anti-bot 202/empty-body response on every homepage variant -- verified for
    amazon.com). Resolve a Wikipedia article, read its INFOBOX `logo =` field
    from the raw wikitext (NOT the `pageimages` API -- that picks whatever image
    the API's heuristic likes, which for a company article is very often a HQ
    building photo or an exec headshot, not the logo -- verified: "Amazon
    (company)"'s pageimage is a tower photo), then resolve that filename to a
    direct Commons URL via the imageinfo API. API-driven throughout, not HTML
    scraping, so it doesn't depend on guessing markup."""
    domain_only = domain.replace("https://", "").replace("http://", "").split("/")[0]
    stripped = re.sub(r"\.(com|org|net|io|co|healthcare|inc)$", "", domain_only, flags=re.I).replace("-", " ").replace("_", " ")
    candidates = [domain_only, stripped + " company", stripped]
    tried_titles = []
    try:
        for guess in candidates:
            hits = _wiki_api("action=opensearch&search=" + urllib.parse.quote(guess) + "&limit=1&namespace=0&format=json")[1]
            if hits and hits[0] not in tried_titles:
                tried_titles.append(hits[0])
        for title in tried_titles:
            data = _wiki_api("action=query&prop=revisions&rvprop=content&rvslots=main&format=json&titles=" + urllib.parse.quote(title))
            pages = data.get("query", {}).get("pages", {})
            page = next(iter(pages.values()), {})
            revs = page.get("revisions")
            if not revs: continue
            content = revs[0]["slots"]["main"]["*"]
            m = re.search(r"\|\s*logo\s*=\s*\[\[File:([^|\]]+)", content, re.I)
            if not m: continue
            fname = m.group(1).strip()
            info = _wiki_api("action=query&titles=" + urllib.parse.quote("File:" + fname) + "&prop=imageinfo&iiprop=url&format=json")
            fpages = info.get("query", {}).get("pages", {})
            fpage = next(iter(fpages.values()), {})
            imgurl = (fpage.get("imageinfo") or [{}])[0].get("url")
            if not imgurl: continue
            img, ct2, _ = get(imgurl)
            mime = "image/svg+xml" if imgurl.lower().endswith(".svg") else \
                   ("image/png" if "png" in ct2 or imgurl.lower().endswith(".png") else
                    "image/jpeg" if "jpeg" in ct2 or imgurl.lower().endswith((".jpg", ".jpeg")) else ct2 or "image/png")
            return img, mime, imgurl + f" (via Wikipedia infobox on '{title}', {domain} itself returned nothing)"
    except Exception:
        pass
    return None

def fetch(domain):
    for hp in homepages(domain):
        try:
            html, ct, final = get(hp)
        except Exception:
            continue
        if b"<html" not in html[:4000].lower() and b"<!doctype" not in html[:100].lower():
            continue
        logo_url = find_logo_url(html.decode("utf-8", "ignore"), final)
        if not logo_url: continue
        try:
            data, ct2, _ = get(logo_url)
        except Exception:
            continue
        if b"<html" in data[:200].lower(): continue          # 404 page
        mime = "image/svg+xml" if logo_url.lower().endswith(".svg") or "svg" in ct2 else \
               ("image/png" if "png" in ct2 or logo_url.lower().endswith(".png") else
                "image/jpeg" if "jpeg" in ct2 or logo_url.lower().endswith((".jpg", ".jpeg")) else ct2 or "image/png")
        return data, mime, logo_url
    return wikipedia_logo(domain)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: fetch_logo.py <domain> [--out file] [--datauri-file file]", file=sys.stderr); sys.exit(1)
    domain = sys.argv[1]
    res = fetch(domain)
    if not res:
        print("no logo found for " + domain, file=sys.stderr); sys.exit(2)
    data, mime, url = res
    print("source: " + url, file=sys.stderr)
    if "--out" in sys.argv:
        open(sys.argv[sys.argv.index("--out") + 1], "wb").write(data); sys.exit(0)
    datauri = "data:" + mime + ";base64," + base64.b64encode(data).decode()
    if "--datauri-file" in sys.argv:
        open(sys.argv[sys.argv.index("--datauri-file") + 1], "w").write(datauri)
    else:
        print(datauri)
