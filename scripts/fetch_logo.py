#!/usr/bin/env python3
"""
fetch_logo.py — grab a company's OWN published logo by domain, for a Sigma POV
built for that company. No API key, no Googling.

Usage:
    python3 fetch_logo.py exxonmobil.com                 # -> prints a data: URI
    python3 fetch_logo.py exxonmobil.com --out logo.png  # -> saves the raw asset
    python3 fetch_logo.py exxonmobil.com --datauri-file logo.txt

Strategy (best → fallback), all from the company's own site:
  1. Header/footer <img> or inline <svg> whose src/class/alt says "logo"
     (prefer .svg, then @2x/high-res raster).
  2. <link rel="apple-touch-icon"> (high-res square mark).
  3. og:image.
Returns nothing usable -> exit 2 (caller should fall back to a wordmark).

Only use for a legitimate POV/demo for that company — this pulls the
company's own brand asset to represent them, standard sales practice.
"""
import sys, re, base64, urllib.request, urllib.parse

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
    return None

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
