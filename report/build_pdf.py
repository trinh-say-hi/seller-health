"""Xuat bao cao ra PDF. Chay: python report/build_pdf.py

Can: playwright (requirements-dev.txt) va trinh duyet Microsoft Edge.
Trang duoc dan bang Paged.js (MIT, report/vendor/) de co so trang, muc luc co so trang va tieu de chay.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
SRC = HERE / "bao_cao.html"
OUT = HERE / "BaoCao_SellerHealth_CO4031.pdf"

# Truoc khi dan trang: gom moi tieu de voi khoi ngay sau no, va chu thich bang voi bang,
# de khong co tieu de hay chu thich nam le loi cuoi trang (Paged.js chua ho tro break-after: avoid).
KEEP_JS = """
function keepTogether() {
  const wrap = (els) => { const w = document.createElement('div'); w.className = 'keep'; els[0].before(w); els.forEach(e => w.append(e)); return w; };
  document.querySelectorAll('p.tcap').forEach(c => {
    const t = c.nextElementSibling;
    if (t && t.tagName === 'TABLE' && !t.classList.contains('long')) wrap([c, t]);
  });
  document.querySelectorAll('h2, h3').forEach(h => {
    const n = h.nextElementSibling;
    if (!n) return;
    if (n.tagName === 'TABLE' && n.classList.contains('long')) return;
    const els = [h, n];
    if (n.tagName === 'FIGURE' && n.nextElementSibling && n.nextElementSibling.classList.contains('cap')) els.push(n.nextElementSibling);
    if (n.classList.contains('two') && n.nextElementSibling && n.nextElementSibling.classList.contains('cap')) els.push(n.nextElementSibling);
    wrap(els);
  });
  document.querySelectorAll('figure').forEach(f => {
    const c = f.nextElementSibling;
    if (c && c.classList.contains('cap') && !f.parentElement.classList.contains('keep')) wrap([f, c]);
  });
}
"""
HOOK = ("<style>.keep { break-inside: avoid; } table.long { break-inside: auto; }</style>"
        "<script>" + KEEP_JS + "window.PagedConfig = { auto: true, before: () => keepTogether(),"
        " after: () => { document.body.setAttribute('data-paged', 'done'); } };</script>"
        '<script src="vendor/paged.polyfill.js"></script>')


def open_paged(p, name="_print.html"):
    """Mo ban dan trang cua bao cao, tra ve (browser, page, file tam)."""
    tmp = HERE / name
    tmp.write_text(SRC.read_text(encoding="utf-8").replace("</head>", HOOK + "</head>", 1), encoding="utf-8")
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 900, "height": 1200})
    page.goto(tmp.as_uri(), wait_until="load")
    page.wait_for_selector("body[data-paged='done']", timeout=180_000)
    return browser, page, tmp


def main():
    with sync_playwright() as p:
        browser, page, tmp = open_paged(p)
        try:
            n = page.locator(".pagedjs_page").count()
            page.pdf(path=str(OUT), prefer_css_page_size=True, print_background=True)
        finally:
            browser.close()
            tmp.unlink(missing_ok=True)
    print(f"Da xuat {OUT.name}: {n} trang")


if __name__ == "__main__":
    sys.exit(main())
