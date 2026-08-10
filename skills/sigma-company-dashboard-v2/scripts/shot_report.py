"""Export the statement report to PDF and rasterize a page to PNG.

Reports are PDF-only (`format.type` must be "pdf" and `format.layout` is
required), so the workbook PNG path in shot.py doesn't apply. macOS ships no
pdftoppm/gs and the system Python has no Quartz bindings, but `swift` can drive
CoreGraphics directly -- that's the only dependency-free way to get a specific
page out as an image on this machine. qlmanage only ever renders page 1.

    python3 shot_report.py <reportId> [page] [outPng]
"""

import pathlib
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

import sigmaapi as S

SWIFT = '''
import Foundation
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers
let doc = CGPDFDocument(URL(fileURLWithPath: "__PDF__") as CFURL)!
guard let page = doc.page(at: __PAGE__) else { exit(1) }
let r = page.getBoxRect(.mediaBox); let sc: CGFloat = 2
let w = Int(r.size.width*sc), h = Int(r.size.height*sc)
let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
    space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue)!
ctx.setFillColor(CGColor(red:1,green:1,blue:1,alpha:1))
ctx.fill(CGRect(x:0,y:0,width:w,height:h))
ctx.scaleBy(x: sc, y: sc); ctx.drawPDFPage(page)
let img = ctx.makeImage()!
let dst = CGImageDestinationCreateWithURL(
    URL(fileURLWithPath:"__OUT__") as CFURL, UTType.png.identifier as CFString, 1, nil)!
CGImageDestinationAddImage(dst, img, nil)
CGImageDestinationFinalize(dst)
'''


def export_pdf(report_id, dest):
    q = S.call("POST", "/v2/reports/%s/export" % report_id,
               {"format": {"type": "pdf", "layout": "portrait"}})
    qid = q.get("queryId") or q.get("exportId")
    for _ in range(80):
        req = urllib.request.Request(
            S.BASE + "/v2/query/%s/download" % qid,
            headers={"Authorization": "Bearer " + S.token(), "Accept": "*/*"})
        try:
            data = urllib.request.urlopen(req).read()
        except urllib.error.HTTPError as exc:
            if exc.code in (404, 409, 425, 500, 502, 503, 504):
                time.sleep(3)
                continue
            raise
        if data:                      # zero bytes means "not ready yet"
            dest.write_bytes(data)
            return len(data)
        time.sleep(3)
    raise SystemExit("export never became ready")


def main():
    report_id = sys.argv[1]
    page = sys.argv[2] if len(sys.argv) > 2 else "1"
    out = pathlib.Path(sys.argv[3] if len(sys.argv) > 3 else "../shots/report-p%s.png" % page)
    out.parent.mkdir(parents=True, exist_ok=True)
    pdf = pathlib.Path(tempfile.mkdtemp()) / "report.pdf"
    print("pdf bytes:", export_pdf(report_id, pdf))
    src = pathlib.Path(tempfile.mkdtemp()) / "r.swift"
    src.write_text(SWIFT.replace("__PDF__", str(pdf))
                        .replace("__PAGE__", page)
                        .replace("__OUT__", str(out)))
    subprocess.run(["swift", str(src)], check=True)
    print("wrote", out, out.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
