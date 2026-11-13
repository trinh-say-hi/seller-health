"""Kiem tra toan he thong: nguon, Silver, Gold, doi soat, chong ro ri, DSS, tai lieu.

Chay: python -m tests.test_system
Ket qua ghi vao evidence/test_results.json. Thoat voi ma loi neu co test hong.
"""
import json
import re
import shutil
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import duckdb
import pandas as pd
import yaml

from src.config import DB_PATH, EVIDENCE_DIR, LAST_BATCH, RAW_DIR, ROOT, SQL_DIR
from src.dss.optimize import build_plan
from src.dss.simulate import simulate
from src.dss.rules import CALL, NONE, OPS, Params
from src.etl.build import MANIFEST, ReconciliationError, attach_sources, run_batch, verify_sources

results = []


def check(name, ok, detail=""):
    results.append({"test": name, "ok": bool(ok), "detail": str(detail)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" ({detail})" if detail != "" else ""))


con = duckdb.connect(str(DB_PATH), read_only=True)
one = lambda sql: con.execute(sql).fetchone()[0]

# --- Nguon
check("Nguon: 9 file khop hash trong manifest", len(verify_sources()) == 9)
check("Nguon: da ghi vao ops.source_manifest", one("SELECT count(*) FROM ops.source_manifest") == 9)
with tempfile.TemporaryDirectory() as td:
    bad_manifest = Path(td) / "m.json"
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    m["files"]["olist_sellers_dataset.csv"]["sha256"] = "0" * 64
    bad_manifest.write_text(json.dumps(m), encoding="utf-8")
    try:
        verify_sources(bad_manifest)
        check("Nguon: hash sai thi bi chan", False)
    except ValueError as e:
        check("Nguon: hash sai thi bi chan", "olist_sellers_dataset.csv" in str(e))

# --- Bronze
EXPECT = {"order_items": 112650, "order_payments": 103886, "order_reviews": 99224, "customers": 99441,
          "sellers": 3095, "products": 32951, "geolocation": 1000163, "category_translation": 71}
for t, n in EXPECT.items():
    got = one(f"SELECT count(*) FROM raw.{t}")
    check(f"Bronze: raw.{t} = {n:,}", got == n, got)
check("Bronze: 99.441 don khac nhau", one("SELECT count(DISTINCT order_id) FROM raw.orders") == 99441)
check("Bronze: don co nhieu phien ban", one("SELECT count(*) FROM raw.orders") > 99441, one("SELECT count(*) FROM raw.orders"))
for t in ["orders", "order_items", "order_payments", "order_reviews", "sellers", "geolocation"]:
    nulls = one(f"SELECT count(*) FROM raw.{t} WHERE dwh_batch IS NULL OR dwh_source_file IS NULL OR dwh_row_hash IS NULL OR dwh_loaded_at IS NULL")
    check(f"Bronze: raw.{t} du cot dwh_", nulls == 0, nulls)

src = pd.read_csv(RAW_DIR / "olist_orders_dataset.csv", dtype=str).set_index("order_id").sort_index()
lat = con.execute("""SELECT order_id, order_status, order_approved_at, order_delivered_carrier_date, order_delivered_customer_date
                     FROM raw.orders QUALIFY row_number() OVER (PARTITION BY order_id ORDER BY dwh_batch DESC) = 1""").df().set_index("order_id").sort_index()
check("Bronze: trang thai cuoi trung file nguon", all(src[c].fillna("").equals(lat[c].fillna("")) for c in lat.columns))
leak = one("""SELECT count(*) FROM raw.orders
              WHERE dwh_batch < '2018-10' AND (
                TRY_CAST(order_delivered_customer_date AS TIMESTAMP) >= CAST(dwh_batch || '-01' AS DATE) + INTERVAL 1 MONTH
                OR TRY_CAST(order_delivered_carrier_date AS TIMESTAMP) >= CAST(dwh_batch || '-01' AS DATE) + INTERVAL 1 MONTH)""")
check("Bronze: khong dot nao thay moc sau ngay chot", leak == 0, leak)
early = one("""SELECT count(*) FROM raw.order_reviews WHERE dwh_batch < '2018-10'
               AND CAST(review_answer_timestamp AS TIMESTAMP) >= CAST(dwh_batch || '-01' AS DATE) + INTERVAL 1 MONTH""")
check("Bronze: review den kho sau khi khach tra loi", early == 0, early)

# --- Silver
sellers = con.execute("SELECT city, city_raw, city_source FROM stg.sellers").df()
check("Silver: ten thanh pho seller khong con ky tu la", not sellers.city.str.contains(r"[/\\,@0-9]", regex=True).any())
check("Silver: ten thanh pho seller da bo dau", not sellers.city.str.contains(r"[^\x00-\x7f]", regex=True).any())
bad_city = sellers.city[sellers.city.isin(["sao pauo", "sao paulop", "sp", "são paulo", "sao paulo / sao paulo"])].tolist()
check("Silver: gom bien the Sao Paulo", not bad_city, bad_city or "")
check("Silver: giu ten goc de truy vet", sellers.city_raw.isin(["04482255"]).any() and (sellers.city_source == "theo_zip").sum() > 0, (sellers.city_source == "theo_zip").sum())
check("Silver: 19.015 ZIP trong geography", one("SELECT count(*) FROM stg.geography") == 19015)
check("Silver: toa do deu nam trong Brazil", one("SELECT count(*) FROM stg.geography WHERE lat NOT BETWEEN -34 AND 6 OR lng NOT BETWEEN -74 AND -34") == 0)
check("Silver: bo 2 danh muc thieu ban dich", one("SELECT count(*) FROM stg.products WHERE category_en = 'pc_gamer'") == 3)
check("Silver: danh muc Unknown con 610", one("SELECT count(*) FROM stg.products WHERE category_en = 'Unknown'") == 610)
check("Cach ly: 42 toa do ngoai Brazil", one("SELECT count(*) FROM ops.quarantine WHERE reason_code = 'GEO_OUTSIDE_BRAZIL'") == 42)
check("Cach ly: khong co loi giao dich", one("SELECT count(*) FROM ops.quarantine WHERE table_name <> 'geolocation'") == 0)
check("Cach ly: dong nao cung co ma loi", one("SELECT count(*) FROM ops.quarantine WHERE reason_code IS NULL OR reason IS NULL") == 0)

# --- Gold: so dong va grain
check("Gold: fact_order = 99.441 don", one("SELECT count(*) FROM core.fact_order") == 99441)
check("Gold: fact_order khong trung don", one("SELECT count(*) - count(DISTINCT order_id) FROM core.fact_order") == 0)
check("Gold: fact_review = 99.224", one("SELECT count(*) FROM core.fact_review") == 99224)
check("Gold: fact_review khong trung (review_id, order_id)", one("SELECT count(*) FROM (SELECT review_id, order_id FROM core.fact_review GROUP BY 1,2 HAVING count(*) > 1)") == 0)
check("Gold: 789 review_id dung cho nhieu don", one("SELECT count(*) FROM (SELECT review_id FROM core.fact_review GROUP BY 1 HAVING count(DISTINCT order_id) > 1)") == 789)
check("Gold: fact_order_seller khong trung (don, seller)", one("SELECT count(*) FROM (SELECT order_id, seller_id FROM core.fact_order_seller GROUP BY 1,2 HAVING count(*) > 1)") == 0)
check("Gold: fact_sales_item = 112.650", one("SELECT count(*) FROM core.fact_sales_item") == 112650)
check("Gold: fact_sales_item khong trung", one("SELECT count(*) FROM (SELECT order_id, order_item_id FROM core.fact_sales_item GROUP BY 1,2 HAVING count(*) > 1)") == 0)
check("Gold: fact_payment = 103.886", one("SELECT count(*) FROM core.fact_payment") == 103886)
check("Gold: 775 don khong co dong hang van duoc tinh", one("SELECT count(*) FROM core.fact_order WHERE coalesce(n_items, 0) = 0") == 775)
check("Gold: 1.278 don nhieu seller", one("SELECT count(*) FROM core.fact_order WHERE n_sellers > 1") == 1278)

# --- Gold: tien va chong nhan dong
total = 13591643.70
check("Tien: tong gia dong hang = 13.591.643,70", float(one("SELECT sum(price) FROM core.fact_sales_item")) == total)
check("Tien: fact_order khong nhan dong", float(one("SELECT sum(items_price_total) FROM core.fact_order")) == total)
check("Tien: fact_order_seller khong nhan dong", float(one("SELECT sum(order_value) FROM core.fact_order_seller")) == total)
check("Tien: GMV hop le = 13.494.400,74", float(one("SELECT sum(price) FROM core.fact_sales_item WHERE is_valid_sale")) == 13494400.74)
pay_src = pd.read_csv(RAW_DIR / "olist_order_payments_dataset.csv").payment_value.sum()
check("Tien: tong thanh toan khop nguon", abs(float(one("SELECT sum(payment_value) FROM core.fact_payment")) - pay_src) < 0.01)
p = con.execute("""SELECT count(*) FILTER (WHERE abs(payment_total - order_total) <= 0.01), count(*) FILTER (WHERE payment_total - order_total > 0.01),
                          count(*) FILTER (WHERE order_total - payment_total > 0.01) FROM core.fact_order WHERE payment_count > 0 AND n_items > 0""").fetchone()
check("Tien: thanh toan khop hang + phi, 98.362 / 264 / 39", p == (98362, 264, 39), p)
check("Chong nhan dong: khong dem don tu fact_order_seller khi noi review", one("""SELECT count(*) FROM (SELECT order_id FROM core.fact_order_seller o JOIN core.fact_order f USING (order_id) WHERE f.n_sellers = 1 GROUP BY 1 HAVING count(*) > 1)""") == 0)
check("Khong dong hang hop le nao roi vao seller khong ro", one("SELECT count(*) FROM core.fact_sales_item WHERE seller_key = -1") == 0)
check("Khong dong hang nao roi vao san pham khong ro", one("SELECT count(*) FROM core.fact_sales_item WHERE product_key = -1") == 0)

# --- Gold: dimension
check("Dim: dim_customer = 96.096 khach + 1", one("SELECT count(*) FROM core.dim_customer") == 96097)
n_zip = one("SELECT count(*) FROM (SELECT zip_prefix FROM stg.geography UNION SELECT zip_prefix FROM stg.customers UNION SELECT zip_prefix FROM stg.sellers)")
check("Dim: dim_location co moi ZIP o moi nguon", one("SELECT count(*) FROM core.dim_location WHERE location_key <> -1") == n_zip, n_zip)
check("Dim: dim_location khong con toa do ngoai Brazil", one("SELECT count(*) FROM core.dim_location WHERE lat NOT BETWEEN -34 AND 6") == 0)
check("Dim: dim_location da noi vao fact", one("SELECT count(*) FROM core.fact_sales_item WHERE customer_location_key = -1 OR seller_location_key = -1") == 0)
check("Dim: dim_geography da bo", one("SELECT count(*) FROM duckdb_tables() WHERE table_name = 'dim_geography'") == 0)
check("Dim: dim_order_status du trang thai cua don", one("SELECT count(*) FROM core.fact_order WHERE status_key IS NULL") == 0)
for fact, col, dim in [("fact_sales_item", "product_key", "dim_product"), ("fact_sales_item", "seller_key", "dim_seller"),
                       ("fact_sales_item", "customer_key", "dim_customer"), ("fact_sales_item", "route_key", "dim_route"),
                       ("fact_order_seller", "seller_key", "dim_seller"), ("fact_order_seller", "route_key", "dim_route"),
                       ("fact_order", "customer_key", "dim_customer"), ("fact_order", "status_key", "dim_order_status"),
                       ("fact_review", "customer_key", "dim_customer"), ("fact_seller_monthly", "health_key", "dim_seller_health"),
                       ("fact_seller_monthly", "seller_key", "dim_seller")]:
    orphan = one(f"SELECT count(*) FROM core.{fact} f LEFT JOIN core.{dim} d USING ({col}) WHERE d.{col} IS NULL")
    check(f"FK: {fact}.{col}", orphan == 0, orphan)
for fact, col in [("fact_order", "purchase_date_key"), ("fact_order", "delivered_date_key"), ("fact_order", "estimated_date_key"), ("fact_order", "carrier_date_key"),
                  ("fact_review", "answered_date_key"), ("fact_sales_item", "shipping_limit_date_key")]:
    orphan = one(f"SELECT count(*) FROM core.{fact} f LEFT JOIN core.dim_date d ON f.{col} = d.date_key WHERE f.{col} IS NOT NULL AND d.date_key IS NULL")
    check(f"FK: {fact}.{col} co trong dim_date", orphan == 0, orphan)
n_pk = one("SELECT count(*) FROM duckdb_constraints() WHERE schema_name = 'core' AND constraint_type = 'PRIMARY KEY'")
check("Dim: 7 dimension tinh co khoa chinh", n_pk == 7, n_pk)

# --- SCD2 va mini-dimension
check("SCD2: moi seller dung 1 dong is_current", one("SELECT count(*) FROM (SELECT seller_id FROM core.dim_seller GROUP BY 1 HAVING sum(CASE WHEN is_current THEN 1 ELSE 0 END) <> 1)") == 0)
overlap = one("""SELECT count(*) FROM (SELECT seller_id, valid_from, lag(valid_to) OVER (PARTITION BY seller_id ORDER BY valid_from) AS prev
                 FROM core.dim_seller) WHERE prev IS NOT NULL AND prev <> valid_from""")
check("SCD2: khoang hieu luc lien tuc, khong chong", overlap == 0, overlap)
held = one("""SELECT count(*) FROM core.dim_seller s
              JOIN (SELECT seller_id, valid_from AS vf, lag(health_tier) OVER (PARTITION BY seller_id ORDER BY valid_from) AS prev_tier FROM core.dim_seller) x
                ON x.seller_id = s.seller_id AND x.vf = s.valid_from
              LEFT JOIN mart.seller_tier_monthly p ON p.seller_id = s.seller_id AND p.as_of = CAST(s.valid_from - INTERVAL 1 MONTH AS DATE)
              WHERE x.prev_tier IS NOT NULL AND x.prev_tier <> 'Chưa hoạt động' AND p.health_tier IS DISTINCT FROM s.health_tier""")
check("SCD2: chi doi khi hang giu nguyen 2 ky", held == 0, held)
pit = one("""SELECT count(*) FROM core.fact_sales_item f JOIN core.dim_seller s USING (seller_key)
             WHERE f.purchase_ts < s.valid_from OR f.purchase_ts >= s.valid_to""")
check("SCD2: fact tro dung phien ban luc mua", pit == 0, pit)
ratio = one("SELECT count(*) * 1.0 / count(DISTINCT seller_id) FROM core.dim_seller WHERE seller_key <> -1")
check("SCD2: on dinh hon ban cu (duoi 5,75 dong moi seller)", ratio < 5.75, round(ratio, 2))
check("Mini-dim: moi dong thang co ho so suc khoe", one("SELECT count(*) FROM core.fact_seller_monthly WHERE health_key = -1") == 0)
check("Mini-dim: hang tren fact khop hang thang", one("""SELECT count(*) FROM core.fact_seller_monthly f JOIN core.dim_seller_health h USING (health_key)
      JOIN mart.seller_features s ON s.seller_id = f.seller_id AND s.as_of = CAST(f.month + INTERVAL 1 MONTH AS DATE) WHERE h.health_tier <> s.health_tier""") == 0)
check("Periodic: moi seller x thang chi mot dong", one("SELECT count(*) FROM (SELECT seller_id, month FROM core.fact_seller_monthly GROUP BY 1,2 HAVING count(*) > 1)") == 0)
check("Accumulating: nhieu don cap nhat qua nhieu dot", one("SELECT count(*) FROM core.fact_order WHERE dwh_last_batch > dwh_first_batch") > 10000, one("SELECT count(*) FROM core.fact_order WHERE dwh_last_batch > dwh_first_batch"))

# --- Review
rv = con.execute("""SELECT avg(CASE WHEN is_before_delivery THEN 1.0 ELSE 0 END),
                           avg(r.review_score) FILTER (WHERE is_before_delivery), avg(r.review_score) FILTER (WHERE NOT is_before_delivery)
                    FROM core.fact_review r JOIN core.fact_order o USING (order_id) WHERE o.delivered_ts IS NOT NULL AND r.customer_late""").fetchone()
check("Review: don tre phan lon cham truoc khi nhan", 0.6 < rv[0] < 0.8, round(rv[0], 3))
check("Review: cham truoc khi nhan thap hon ro", rv[1] < 2 and rv[2] > 3.5, (round(rv[1], 2), round(rv[2], 2)))

# --- Doi soat va van hanh
check("Log: du 26 dot va init deu ok", one("SELECT count(*) FROM ops.etl_log WHERE status = 'ok'") == 27)
n_rec = one("SELECT count(*) FROM ops.layer_reconciliation")
check("Doi soat: moi dot 11 phep kiem tra", n_rec == 26 * 11, n_rec)
check("Doi soat: khong dong nao lech", one("SELECT count(*) FROM ops.layer_reconciliation WHERE NOT is_ok") == 0)
cube_gmv = one("SELECT sum(gmv) FROM mart.kpi_monthly WHERE is_all_region AND is_all_category")
check("CUBE: tong GMV = fact", abs(cube_gmv - 13494400.74) < 0.5, f"{cube_gmv:,.2f}")
check("CUBE: cong cac vung = tong", abs(one("SELECT sum(gmv) FROM mart.kpi_monthly WHERE NOT is_all_region AND is_all_category") - cube_gmv) < 0.5)
sql_text = (SQL_DIR / "olap_examples.sql").read_text(encoding="utf-8")
stmts = [s for s in sql_text.split(";") if any(ln.strip() and not ln.strip().startswith("--") for ln in s.splitlines())]
for s in stmts:
    title = [ln for ln in s.splitlines() if ln.startswith("--")][-1][3:].split(":")[0]
    rows = con.execute(s).fetchall()
    check(f"OLAP {title} co ket qua", len(rows) > 0, f"{len(rows)} dong")
check("OLAP: du 8 truy van", len(stmts) == 8, len(stmts))

# --- Doi chieu doc lap voi CSV
asof = pd.Timestamp("2018-03-01")
o = pd.read_csv(RAW_DIR / "olist_orders_dataset.csv", parse_dates=["order_purchase_timestamp", "order_delivered_carrier_date"])
it = pd.read_csv(RAW_DIR / "olist_order_items_dataset.csv", parse_dates=["shipping_limit_date"])
d = it.merge(o[~o.order_status.isin(["canceled", "unavailable"])], on="order_id")
w = d[(d.order_purchase_timestamp < asof) & (d.order_purchase_timestamp >= asof - pd.Timedelta(days=90))]
k = w[w.shipping_limit_date < asof]
carr = k.order_delivered_carrier_date.where(k.order_delivered_carrier_date < asof)
ind = pd.DataFrame({"gmv": w.groupby("seller_id").price.sum(), "orders": w.groupby("seller_id").order_id.nunique(),
                    "late": (carr.isna() | (carr > k.shipping_limit_date)).groupby(k.seller_id).mean()})
dw = con.execute("SELECT seller_id, gmv_90, orders_90, seller_late_rate FROM mart.seller_features WHERE as_of = DATE '2018-03-01'").df().set_index("seller_id")
j = ind.join(dw, how="outer")
check("Doi chieu CSV: 1.338 seller hoat dong tai 01/03/2018", len(dw) == len(ind) == 1338, len(dw))
check("Doi chieu CSV: gmv_90 tung seller", (j.gmv - j.gmv_90).abs().max() < 0.01)
check("Doi chieu CSV: orders_90 tung seller", (j.orders == j.orders_90).all())
check("Doi chieu CSV: seller_late_rate tung seller", (j.late.fillna(-1) - j.seller_late_rate.fillna(-1)).abs().max() < 1e-9)

# --- DSS
train = con.execute("SELECT as_of, train_max_as_of FROM dss.eval_auc").df()
gap = (pd.to_datetime(train.as_of) - pd.to_datetime(train.train_max_as_of)).dt.days
check("DSS: train cach test it nhat 45 ngay", gap.min() >= 45, f"nho nhat {gap.min()} ngay")
gap = one("""SELECT max(abs(1 / (1 + exp(-e.lo)) - s.p_decline)) FROM (SELECT as_of, seller_id, sum(contrib) AS lo FROM dss.explain GROUP BY 1, 2) e
              JOIN dss.scores s USING (as_of, seller_id)""")
check("Giai thich: tong dong gop doi ra xac suat khop p_decline", gap is not None and gap < 1e-6, f"lech lon nhat {gap:.2e}" if gap is not None else "khong co du lieu")
check("DSS: moi seller 1 khuyen nghi moi as-of", one("SELECT count(*) FROM (SELECT as_of, seller_id FROM dss.recommendation GROUP BY 1,2 HAVING count(*) > 1)") == 0)
check("DSS: moi khuyen nghi deu co ly do", one("SELECT count(*) FROM dss.recommendation WHERE reason IS NULL OR length(reason) < 10") == 0)
over = con.execute("SELECT as_of, sum(cost) c, sum(CASE WHEN action='CALL' THEN 1 WHEN action='OPS' THEN 2 ELSE 0 END) s FROM dss.recommendation GROUP BY 1").df()
pr = Params()
check("DSS: ke hoach mac dinh trong rang buoc", (over.c <= pr.budget).all() and (over.s <= pr.max_slots).all(), f"toi da {over.c.max():.0f} BRL, {over.s.max():.0f} suat")
check("DSS: moi as-of co de xuat tra phi", over.c.min() > 0, f"it nhat {over.c.min():.0f} BRL")
toy = pd.DataFrame({"seller_id": list("abcd"), "p_decline": [.9, .8, .7, .6], "value_45": [1000.] * 4,
                    "gmv_90": [2000.] * 4, "seller_late_rate": [.5, 0, 0, .5], "n_limit_known": [10] * 4,
                    "cust_late_rate": [0.] * 4, "n_cust_late_orders": [0] * 4, "n_cust_late_seller_ok": [0] * 4,
                    "trend": [-.6] * 4, "recency": [30.] * 4, "avg_review": [4.] * 4})
t = Params(budget=200, max_slots=4, risk_threshold=.5, value_pct=0.0)
tp = build_plan(toy, t).set_index("seller_id")
check("Toi uu: giai dung bai tinh tay", tp.loc["a", "action"] == OPS and tp.loc["b", "action"] == CALL and abs(tp.expected_saved.sum() - 430) < 1e-6, tp.action.to_dict())
check("Toi uu: ton trong gioi han suat", build_plan(toy, replace(t, budget=1000, max_slots=1)).slots.sum() <= 1)
check("Toi uu: ngan sach 0 khong chon gi tra phi", build_plan(toy, replace(t, budget=0)).cost.sum() == 0)
sim = simulate(tp.reset_index(), t, spread=.5, n=4000)
check("Mo phong: ky vong bang GMV giu duoc cua bo toi uu", abs(sim["expected"] - tp.expected_saved.sum()) < 1e-6, f"{sim['expected']:.1f}")
check("Mo phong: trung binh gan ky vong, P10 <= P50 <= P90", abs(sim["mean"] / sim["expected"] - 1) < .05 and sim["p10"] <= sim["p50"] <= sim["p90"],
      f"{sim['p10']:.0f} / {sim['p50']:.0f} / {sim['p90']:.0f}")
check("Mo phong: do bat dinh lon hon thi khoang rong hon", (lambda a, b: a["p90"] - a["p10"] < b["p90"] - b["p10"])(
      simulate(tp.reset_index(), t, spread=0, n=4000), simulate(tp.reset_index(), t, spread=.9, n=4000)))
import tempfile
from src.app import decisions
with tempfile.TemporaryDirectory() as d:
    f = Path(d) / "ke_hoach_da_chot.parquet"
    decisions.ensure(f)
    check("Khep vong: file ke hoach rong co du cot cho Power BI", list(decisions.load(f).columns) == list(decisions.COLUMNS))
    pl = tp.reset_index()
    decisions.save("2018-07-01", pl, {"a": 1, "b": 2}, {"budget": 200}, 0, path=f)
    decisions.save("2018-08-01", pl, {"a": 1, "b": 2}, {"budget": 200}, 0, path=f)
    decisions.save("2018-07-01", pl.assign(action=NONE, cost=0.0), {"a": 1}, {"budget": 0}, 3, path=f)
    kh = decisions.load(f)
    check("Khep vong: chot lai mot moc thi thay ban cu, moc khac giu nguyen",
          len(kh) == 2 * len(pl) and (kh[kh.as_of_key == 20180701].action == NONE).all() and kh[kh.as_of_key == 20180801].cost.sum() == pl.cost.sum())
    st_ = decisions.status("2018-07-01", f)
    check("Khep vong: trang thai chot dung so seller va so the keo tay", st_["n"] == 0 and st_["edited"] == 3 and decisions.status("2018-09-01", f) is None)

# --- Tai lieu
n_col, n_com = con.execute("SELECT count(*), count(comment) FROM duckdb_columns() WHERE schema_name IN ('core','mart','dss','ops')").fetchone()
check("Catalog: moi cot o Gold, DSS, van hanh deu co mo ta", n_col == n_com, f"{n_com}/{n_col}")
check("Catalog: moi bang deu co mo ta", one("SELECT count(*) FROM duckdb_tables() WHERE schema_name IN ('raw','core','mart','dss','ops') AND comment IS NULL") == 0)
check("Catalog: da sinh data_catalog.md", (ROOT / "docs" / "data_catalog.md").exists())
metrics = yaml.safe_load((ROOT / "metrics.yml").read_text(encoding="utf-8"))
check("Metrics: moi KPI du truong bat buoc", all({"label", "definition", "formula", "window", "source"} <= set(v) for v in metrics.values()), len(metrics))
ui = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "src" / "app").glob("*.py"))
used = set(re.findall(r'kpi\(\s*[^,\n]+,\s*"([a-z_0-9]+)"', ui)) | set(re.findall(r'help_for\("([a-z_0-9]+)"\)', ui))
unknown = used - set(metrics)
check("Metrics: giao dien chi dung KPI co dinh nghia", used and not unknown, unknown or f"{len(used)} KPI")
for name in ["naming_conventions.md", "requirements.md"]:
    check(f"Tai lieu: co {name}", (ROOT / "docs" / name).exists())

con.close()

# --- Chay lai dot cuoi va cong chat luong, tren ban sao
with tempfile.TemporaryDirectory() as td:
    copy = Path(td) / "c.duckdb"
    shutil.copy(DB_PATH, copy)
    c2 = duckdb.connect(str(copy))
    attach_sources(c2)
    tables = ["raw.orders", "raw.order_items", "raw.order_reviews", "core.fact_sales_item", "core.fact_order", "core.fact_order_seller", "core.fact_review", "core.fact_payment",
              "core.dim_seller", "core.fact_seller_monthly", "mart.seller_features", "mart.seller_tier_monthly", "mart.kpi_monthly", "mart.route_delivery", "ops.layer_reconciliation"]
    before = {t: c2.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in tables}
    check("Watermark: dot da nap duoc bo qua", run_batch(c2, LAST_BATCH) is False)
    run_batch(c2, LAST_BATCH, force=True)
    after = {t: c2.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in tables}
    diff = {t: (before[t], after[t]) for t in tables if before[t] != after[t]}
    check("Chay lai dot cuoi khong tao dong trung", not diff, diff or "")

    # Lam mat mot dong o Gold: cong phai dung dot va ghi log
    c2.execute("DELETE FROM core.fact_sales_item WHERE rowid IN (SELECT rowid FROM core.fact_sales_item WHERE dwh_batch = '2018-05' LIMIT 1)")
    try:
        run_batch(c2, LAST_BATCH, force=True)
        check("Cong chat luong: mat dong o Gold thi dung dot", False)
    except ReconciliationError as e:
        check("Cong chat luong: mat dong o Gold thi dung dot", "So dong hang" in str(e), str(e)[:90])
    status, msg = c2.execute("SELECT status, error_message FROM ops.etl_log WHERE batch = ?", [LAST_BATCH]).fetchone()
    check("Cong chat luong: dot loi ghi failed kem noi dung", status == "failed" and "Doi soat" in msg, status)
    check("Cong chat luong: watermark khong tien, lan sau chay lai", c2.execute("SELECT count(*) FROM ops.etl_log WHERE batch = ? AND status = 'ok'", [LAST_BATCH]).fetchone()[0] == 0)
    c2.close()

EVIDENCE_DIR.mkdir(exist_ok=True)
(EVIDENCE_DIR / "test_results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
bad = [r for r in results if not r["ok"]]
if bad:
    print("\nHONG:")
    for r in bad:
        print(" -", r["test"], r["detail"])
print(f"\n{len(results) - len(bad)}/{len(results)} test dat")
sys.exit(1 if bad else 0)
