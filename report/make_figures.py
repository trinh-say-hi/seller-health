"""Sinh bieu do SVG cho bao cao tu kho va tu evidence/. Chay: python report/make_figures.py

Moi so trong bieu do lay tu kho (doc read-only) hoac tu evidence/dss_evaluation.json, khong go tay.
"""
import json
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.config import DB_PATH  # noqa: E402

OUT = ROOT / "report" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
BLUE, ORANGE, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#1f1f1f", "#5f5e5a", "#e3e2de"
FONT = "font-family='Segoe UI, Arial, sans-serif'"


def vn(x, d=0):
    return f"{x:,.{d}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def svg(w, h, body):
    return f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {w} {h}' width='{w}' height='{h}' {FONT}>{body}</svg>"


def text(x, y, s, size=12, color=INK, anchor="start", weight=400):
    return f"<text x='{x:.1f}' y='{y:.1f}' font-size='{size}' fill='{color}' text-anchor='{anchor}' font-weight='{weight}'>{s}</text>"


def legend(x, y, items):
    out, cx = "", x
    for label, color in items:
        out += f"<rect x='{cx}' y='{y - 9}' width='11' height='11' rx='2' fill='{color}'/>" + text(cx + 16, y, label, 12, MUTED)
        cx += 26 + 7.2 * len(label)
    return out


def grouped_bars(path, title_left, months, a, b, labels, ymax, w=520, h=250):
    """Hai chuoi cot canh nhau theo thang, gia tri la ti le 0..1."""
    L, R, T, B = 44, 12, 50, 30
    pw, ph = w - L - R, h - T - B
    body = text(L, 16, title_left, 13, INK, weight=600)
    for k in range(0, int(ymax * 100) + 1, 10):
        y = T + ph - ph * k / 100 / ymax
        body += f"<line x1='{L}' x2='{w - R}' y1='{y:.1f}' y2='{y:.1f}' stroke='{GRID}'/>" + text(L - 6, y + 4, f"{k}%", 11, MUTED, "end")
    gw = pw / len(months)
    bw = gw * 0.32
    for i, m in enumerate(months):
        x0 = L + i * gw + gw / 2
        for j, (vals, col) in enumerate(((a, BLUE), (b, ORANGE))):
            v = vals[i]
            bh = ph * v / ymax
            x = x0 - bw - 2 + j * (bw + 4)
            body += f"<rect x='{x:.1f}' y='{T + ph - bh:.1f}' width='{bw:.1f}' height='{bh:.1f}' rx='3' fill='{col}'/>"
            body += text(x + bw / 2, T + ph - bh - 4, vn(100 * v, 0), 10.5, MUTED, "middle")
        body += text(x0, h - 10, m, 11.5, MUTED, "middle")
    body += legend(L, 36, [(labels[0], BLUE), (labels[1], ORANGE)])
    (OUT / path).write_text(svg(w, h, body), encoding="utf-8")


def main():
    ev = json.loads((ROOT / "evidence" / "dss_evaluation.json").read_text(encoding="utf-8"))
    lists = ev["lists"]
    plan = [r for r in lists if r["scope"] == "plan"]
    months = sorted({r["as_of"] for r in plan})
    get = lambda name, key: [next(r[key] for r in plan if r["as_of"] == m and r["list_name"] == name) for m in months]
    labels = [f"{m[5:7]}/{m[:4]}" for m in months]
    grouped_bars("eval_hit.svg", "Gọi trúng seller thật sự sụt GMV", labels, get("Kế hoạch DSS", "hit_rate"), get("Theo GMV", "hit_rate"),
                 ["Kế hoạch DSS", "Chọn theo GMV"], 0.7)
    grouped_bars("eval_loss.svg", "Phần GMV mất toàn sàn được bao phủ", labels, get("Kế hoạch DSS", "loss_share"), get("Theo GMV", "loss_share"),
                 ["Kế hoạch DSS", "Chọn theo GMV"], 0.4)

    # Nam cach chon 50 seller: scatter trung binh 5 thang
    top = [r for r in lists if r["scope"] == "top50"]
    names = sorted({r["list_name"] for r in top})
    pts = []
    for n in names:
        rs = [r for r in top if r["list_name"] == n]
        pts.append((n, sum(r["hit_rate"] for r in rs) / len(rs), sum(r["loss_share"] for r in rs) / len(rs)))
    w, h, L, R, T, B = 600, 300, 70, 24, 24, 44
    pw, ph = w - L - R, h - T - B
    body = ""
    for k in range(0, 41, 10):
        x = L + pw * k / 40
        body += f"<line x1='{x:.1f}' x2='{x:.1f}' y1='{T}' y2='{T + ph}' stroke='{GRID}'/>" + text(x, T + ph + 16, f"{k}%", 11, MUTED, "middle")
    for k in range(0, 101, 20):
        y = T + ph - ph * k / 100
        body += f"<line x1='{L}' x2='{w - R}' y1='{y:.1f}' y2='{y:.1f}' stroke='{GRID}'/>" + text(L - 6, y + 4, f"{k}%", 11, MUTED, "end")
    body += text(L + pw / 2, h - 6, "Phần GMV mất được bao phủ (càng phải càng tốt)", 11.5, MUTED, "middle")
    body += f"<text x='14' y='{T + ph / 2}' font-size='11.5' fill='{MUTED}' text-anchor='middle' transform='rotate(-90 14 {T + ph / 2})'>Gọi trúng (càng cao càng tốt)</text>"
    for n, hit, loss in pts:
        x, y = L + pw * loss / 0.4, T + ph - ph * hit
        col = BLUE if n.startswith("DSS") else MUTED
        body += f"<circle cx='{x:.1f}' cy='{y:.1f}' r='{7 if n.startswith('DSS') else 5.5}' fill='{col}'/>"
        anchor = "end" if x > L + pw * 0.7 else "start"
        dx = -10 if anchor == "end" else 10
        dy = -12 if n.startswith("DSS") else (16 if "ngẫu nhiên" in n else 4)
        if n.startswith("DSS"):
            anchor, dx = "middle", 0
        body += text(x + dx, y + dy, f"{n} ({vn(100 * hit)}%, {vn(100 * loss, 1)}%)", 11.5, INK if n.startswith("DSS") else MUTED, anchor, 600 if n.startswith("DSS") else 400)
    (OUT / "strategies.svg").write_text(svg(w, h, body), encoding="utf-8")

    # Do nhay: muc trung Jaccard trung binh
    sens = ev["sensitivity"]
    cases = {}
    for r in sens:
        cases.setdefault(r["case_name"], []).append(r["jaccard"])
    rows = sorted(((k, sum(v) / len(v)) for k, v in cases.items()), key=lambda t: t[1])
    w, rh, L = 430, 24, 190
    h = 26 + rh * len(rows)
    body = ""
    for i, (k, v) in enumerate(rows):
        y = 10 + i * rh
        bwid = (w - L - 50) * v
        body += text(L - 8, y + 14, k, 11.5, INK, "end")
        body += f"<rect x='{L}' y='{y + 3}' width='{bwid:.1f}' height='{rh - 8}' rx='3' fill='{BLUE if v >= 0.65 else ORANGE}'/>"
        body += text(L + bwid + 6, y + 15, f"{vn(100 * v)}%", 11, MUTED)
    (OUT / "sensitivity.svg").write_text(svg(w, h, body), encoding="utf-8")

    # GMV va ti le tre theo thang (toan san) tu mart.kpi_monthly
    con = duckdb.connect(str(DB_PATH), read_only=True)
    km = con.execute("""SELECT month, gmv, n_orders, n_late_orders * 1.0 / nullif(n_due_orders, 0) AS late
                        FROM mart.kpi_monthly WHERE is_all_region AND is_all_category AND month BETWEEN DATE '2017-01-01' AND DATE '2018-08-01'
                        ORDER BY month""").fetchall()
    w, h, L, R, T, B = 620, 250, 56, 52, 30, 34
    pw, ph = w - L - R, h - T - B
    gmax = 1_100_000
    body = text(L, 16, "GMV theo tháng (cột) và tỷ lệ đơn trễ hẹn (đường), toàn sàn", 13, INK, weight=600)
    for k in range(0, 11, 2):
        y = T + ph - ph * k / 10
        body += f"<line x1='{L}' x2='{w - R}' y1='{y:.1f}' y2='{y:.1f}' stroke='{GRID}'/>"
        body += text(L - 6, y + 4, f"{vn(gmax * k / 10 / 1000)}k", 10.5, MUTED, "end")
        body += text(w - R + 6, y + 4, f"{k * 2}%", 10.5, ORANGE)
    gw = pw / len(km)
    line = []
    for i, (m, g, n, late) in enumerate(km):
        x = L + i * gw
        bh = ph * float(g) / gmax
        body += f"<rect x='{x + gw * 0.15:.1f}' y='{T + ph - bh:.1f}' width='{gw * 0.7:.1f}' height='{bh:.1f}' rx='2' fill='{BLUE}' opacity='0.85'/>"
        if late is not None:
            line.append((x + gw / 2, T + ph - ph * float(late) / 0.20))
        if m.month in (1, 4, 7, 10):
            body += text(x + gw / 2, h - 12, f"{m.month:02d}/{str(m.year)[2:]}", 10.5, MUTED, "middle")
    body += "<polyline fill='none' stroke='%s' stroke-width='2.2' points='%s'/>" % (ORANGE, " ".join(f"{x:.1f},{y:.1f}" for x, y in line))
    for x, y in line:
        body += f"<circle cx='{x:.1f}' cy='{y:.1f}' r='2.6' fill='{ORANGE}'/>"
    (OUT / "gmv_late_monthly.svg").write_text(svg(w, h, body), encoding="utf-8")
    con.close()
    print("Da sinh:", ", ".join(p.name for p in sorted(OUT.glob("*.svg"))))


if __name__ == "__main__":
    main()
