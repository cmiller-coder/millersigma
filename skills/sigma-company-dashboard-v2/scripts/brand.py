"""SoFi brand kit. Colours are taken from the official logo asset itself
(Wikimedia Commons SoFi_logo.svg): the mark is #00A2C7 and its gradient runs
#0074F5 -> #03AAFF."""

import base64
import pathlib

ASSETS = pathlib.Path(__file__).resolve().parent.parent / "assets"

# Defaults are SoFi; apply() rebinds them from the active company config so the
# whole build retargets from one place. Module-level names are kept (rather than
# a palette object) so none of the call sites have to change.
NAVY = "#0B2740"
NAVY_DEEP = "#06172A"
SOFI_BLUE = "#00A2C7"
SOFI_BRIGHT = "#0074F5"
SOFI_CYAN = "#03AAFF"
SOFI_MINT = "#00C4A7"
COMPANY = "SoFi"
LOGO_DOMAIN = "sofi.com"


def apply(cfg):
    """Rebind the palette to a company config. Called once at import time."""
    global NAVY, NAVY_DEEP, SOFI_BLUE, SOFI_BRIGHT, SOFI_CYAN, SOFI_MINT
    global CATEGORICAL, TEXT_DARK, COMPANY, LOGO_DOMAIN
    pal = cfg["palette"]
    NAVY, NAVY_DEEP = pal["navy"], pal["navy_deep"]
    SOFI_BRIGHT, SOFI_BLUE = pal["primary"], pal["secondary"]
    SOFI_CYAN, SOFI_MINT = pal["accent"], pal["mint"]
    TEXT_DARK = pal["navy"]
    COMPANY, LOGO_DOMAIN = cfg["name"], cfg["logo_domain"]
    global LOGO_PREFIX
    LOGO_PREFIX = {"mcd": "mcd"}.get(cfg["key"], cfg["key"])
    CATEGORICAL = [SOFI_BRIGHT, SOFI_MINT, NAVY, SOFI_CYAN,
                   SOFI_BLUE, "#7CC7E8", "#4A90E2", "#0A4E8B"]

# Light-surface system so native dark text stays high-contrast everywhere.
CANVAS = "#EEF2F7"
CARD = "#FFFFFF"
CARD_ALT = "#F4F8FC"
BORDER = "#DCE4EE"
TEXT_DARK = "#0B2740"
TEXT_MUTED = "#5B6B7F"
GOOD = "#0EA5A0"
BAD = "#EF4444"
WARN = "#E1A32D"

# All SoFi family -- the old list carried a purple (#5B4B8A) and a gold
# (#E1A32D) that read as someone else's brand in the donut and the category bars.
CATEGORICAL = [SOFI_BRIGHT, SOFI_MINT, NAVY, SOFI_CYAN,
               SOFI_BLUE, "#7CC7E8", "#4A90E2", "#0A4E8B"]


def datauri_svg(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


LOGO_PREFIX = "sofi"


def _uri(name: str) -> str:
    """Logo data-URI for the active company, falling back to the white mark when
    a prospect only has one recolour on disk."""
    f = ASSETS / ("%s_logo_%s.datauri.txt" % (LOGO_PREFIX, name))
    if not f.exists():
        f = ASSETS / ("%s_logo_white.datauri.txt" % LOGO_PREFIX)
    return f.read_text().strip()


def logo_white():
    return _uri("white")


def logo_navy():
    return _uri("navy")


def logo_blue():
    return _uri("blue")


def header_bg(width=1600, height=240) -> str:
    """Brand-gradient header band with a soft radial glow and faint rings."""
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="0.4">
      <stop offset="0%" stop-color="{NAVY_DEEP}"/>
      <stop offset="42%" stop-color="{NAVY}"/>
      <stop offset="100%" stop-color="{SOFI_BRIGHT}"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.78" cy="0.3" r="0.6">
      <stop offset="0%" stop-color="{SOFI_CYAN}" stop-opacity="0.45"/>
      <stop offset="60%" stop-color="{SOFI_BLUE}" stop-opacity="0.14"/>
      <stop offset="100%" stop-color="{NAVY}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="{width}" height="{height}" fill="url(#g)"/>
  <rect width="{width}" height="{height}" fill="url(#glow)"/>
  <g fill="none" stroke="#FFFFFF" stroke-opacity="0.07">
    <circle cx="{int(width*0.79)}" cy="{int(height*0.34)}" r="118"/>
    <circle cx="{int(width*0.79)}" cy="{int(height*0.34)}" r="184"/>
    <circle cx="{int(width*0.79)}" cy="{int(height*0.34)}" r="250"/>
  </g>
  <rect y="{height-3}" width="{width}" height="3" fill="{SOFI_CYAN}" fill-opacity="0.9"/>
</svg>"""
    return datauri_svg(svg)


def card_gradient(a=NAVY, b=SOFI_BRIGHT, width=520, height=300) -> str:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs><linearGradient id="c" x1="0" y1="0" x2="0.9" y2="1">
    <stop offset="0%" stop-color="{a}"/><stop offset="100%" stop-color="{b}"/>
  </linearGradient></defs>
  <rect width="{width}" height="{height}" fill="url(#c)"/>
</svg>"""
    return datauri_svg(svg)


def icon(path_d: str, color=SOFI_BRIGHT, size=24) -> str:
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
           f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
           f'stroke-linecap="round" stroke-linejoin="round">{path_d}</svg>')
    return datauri_svg(svg)


ICON_SPARK = '<polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>'
ICON_TREND = ('<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>'
              '<polyline points="17 6 23 6 23 12"/>')
ICON_USERS = ('<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
              '<path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>')
ICON_WHEEL = ('<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/>'
              '<line x1="12" y1="3" x2="12" y2="9"/><line x1="12" y1="15" x2="12" y2="21"/>'
              '<line x1="3" y1="12" x2="9" y2="12"/><line x1="15" y1="12" x2="21" y2="12"/>')
ICON_SLIDERS = ('<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/>'
                '<line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/>'
                '<line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/>'
                '<line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/>'
                '<line x1="17" y1="16" x2="23" y2="16"/>')
