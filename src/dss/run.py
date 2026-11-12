"""Chay DSS tren kho: nhan -> diem rui ro -> ke hoach mac dinh -> danh gia.

Chay: python -m src.dss.run
Train cuon theo thoi gian: tai as-of t chi hoc tu as-of <= t - 45 ngay, nen nhan train da quan sat xong.
"""
import json
import time
from dataclasses import replace

import duckdb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import DB_PATH, EVIDENCE_DIR, FIRST_SCORED_ASOF, HORIZON_DAYS, LAST_ASOF, LAST_LABELED_ASOF, RELIABLE_END
from src.dss.optimize import build_plan, summarize
from src.dss.rules import CALL, OPS, Params

FEATS = ["gmv_90", "orders_90", "gmv_30", "orders_30", "trend", "recency", "tenure", "n_cat",
         "seller_late_rate", "cust_late_rate", "avg_review", "days_to_carrier"]
OPS_FEATS = ["seller_late_rate", "cust_late_rate", "avg_review", "days_to_carrier"]
TARGETS = ["decline", "dormant"]
TRAIN_START = "2017-04-01"
H = pd.Timedelta(days=HORIZON_DAYS)
EVAL_START = "2018-03-01"


def create_labels(con):
    con.execute(f"""
    CREATE OR REPLACE TABLE dss.labels AS
    WITH sales AS (SELECT seller_id, purchase_ts AS ts, CAST(price AS DOUBLE) AS price
                   FROM core.fact_sales_item WHERE is_valid_sale)
    , n AS (
        SELECT f.as_of, f.seller_id, f.gmv_90,
               coalesce(sum(s.price) FILTER (WHERE s.ts < f.as_of + INTERVAL {HORIZON_DAYS} DAY), 0) AS g,
               count(*) FILTER (WHERE s.ts >= f.as_of + INTERVAL {HORIZON_DAYS} DAY AND s.ts < DATE '{RELIABLE_END}') > 0 AS r
        FROM mart.seller_features f
        LEFT JOIN sales s ON s.seller_id = f.seller_id AND s.ts >= f.as_of
        WHERE f.as_of >= DATE '{TRAIN_START}' AND f.as_of <= DATE '{LAST_LABELED_ASOF}'
        GROUP BY f.as_of, f.seller_id, f.gmv_90)
    SELECT as_of, seller_id, g AS gmv_next45, g = 0 AS dormant, g < 0.5 * gmv_90 / 2 AS decline,
           greatest(gmv_90 / 2 - g, 0) AS loss, r AS returned_later
    FROM n""")


def load_panel(con):
    df = con.execute(f"""
        SELECT f.*, l.gmv_next45, l.dormant, l.decline, l.loss, l.returned_later
        FROM mart.seller_features f LEFT JOIN dss.labels l USING (as_of, seller_id)
        WHERE f.as_of >= DATE '{TRAIN_START}' AND f.as_of <= DATE '{LAST_ASOF}'""").df()
    df["as_of"] = pd.to_datetime(df.as_of)
    df["value_45"] = df.gmv_90 / 2
    return df


def design(df, med=None, cols=FEATS):
    x = df[cols].astype(float).copy()
    for c in ("gmv_90", "gmv_30"):
        if c in x:
            x[c] = np.log1p(x[c])
    med = x.median() if med is None else med
    return x.fillna(med), med


def ops_score(df):
    """Diem van hanh 0-100: cong thuc co trong so, khong train."""
    sl = df.seller_late_rate.fillna(df.seller_late_rate.median())
    cl = df.cust_late_rate.fillna(df.cust_late_rate.median())
    rv = df.avg_review.fillna(df.avg_review.median())
    return (100 * (0.5 * (1 - sl) + 0.2 * (1 - cl) + 0.3 * (rv - 1) / 4)).round(1)


def score_all(panel):
    frames, coefs, aucs, explain = [], [], [], []
    asofs = sorted(a for a in panel.as_of.unique() if a >= pd.Timestamp(FIRST_SCORED_ASOF))
    for t in asofs:
        cur = panel[panel.as_of == t].copy()
        train = panel[(panel.as_of <= t - H) & panel.decline.notna()]
        for target in TARGETS:
            Xtr, med = design(train)
            Xte, _ = design(cur, med)
            y = train[target].astype(int)
            model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000)).fit(Xtr, y)
            cur[f"p_{target}"] = model.predict_proba(Xte)[:, 1]
            coefs += [{"as_of": t, "target": target, "feature": f, "coef": float(c)} for f, c in zip(FEATS, model[-1].coef_[0])]
            if target == "decline":
                # Logistic la tong tuyen tinh: log-odds = he so chan + sum(he so x gia tri chuan hoa).
                # Luu tung so hang de giai thich chinh xac vi sao mot seller bi cham rui ro cao.
                sc, lr = model[0], model[-1]
                z = (Xte.values - sc.mean_) / sc.scale_
                contrib = z * lr.coef_[0]
                sid = cur.seller_id.values
                for i, f in enumerate(FEATS):
                    explain.append(pd.DataFrame({"as_of": t, "seller_id": sid, "feature": f, "value": cur[f].astype(float).values,
                                                 "z": z[:, i], "contrib": contrib[:, i]}))
                explain.append(pd.DataFrame({"as_of": t, "seller_id": sid, "feature": "_intercept", "value": np.nan,
                                             "z": np.nan, "contrib": float(lr.intercept_[0])}))
            if cur[target].notna().all():
                yt = cur[target].astype(int)
                no_ops = [c for c in FEATS if c not in OPS_FEATS]
                m2 = make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000)).fit(Xtr[no_ops], y)
                aucs.append({"as_of": t, "target": target, "n": len(cur), "base_rate": float(yt.mean()),
                             "auc_model": roc_auc_score(yt, cur[f"p_{target}"]),
                             "auc_no_ops": roc_auc_score(yt, m2.predict_proba(Xte[no_ops])[:, 1]),
                             "auc_recency": roc_auc_score(yt, cur.recency),
                             "train_n": len(train), "train_max_as_of": train.as_of.max()})
        cur["ops_score"] = ops_score(cur)
        frames.append(cur)
    return pd.concat(frames, ignore_index=True), pd.DataFrame(coefs), pd.DataFrame(aucs), pd.concat(explain, ignore_index=True)


def evaluate_lists(scored, plans):
    """So sanh cac cach chon cung so seller, tren ket qua that sau do."""
    rows = []
    for t, cur in scored[scored.as_of >= pd.Timestamp(EVAL_START)].groupby("as_of"):
        if cur.decline.isna().any():
            continue
        cur = cur.copy()
        cur["ev"] = cur.p_decline * cur.value_45
        cur["rule"] = ((cur.trend < -0.5) & (cur.recency > 21)).astype(int)
        total_loss = cur.loss.sum()
        plan = plans[plans.as_of == t]
        paid = plan[plan.action.isin([CALL, OPS])].seller_id
        lists = {}
        for name, sort_cols in [("DSS (rủi ro × giá trị)", ["ev"]), ("Theo GMV", ["gmv_90"]), ("Theo số ngày không bán", ["recency"]),
                                ("Luật đơn giản", ["rule", "gmv_90"])]:
            lists[("top50", name)] = cur.sort_values(sort_cols, ascending=False).head(50)
        k = len(paid)
        if k:
            lists[("plan", "Kế hoạch DSS")] = cur[cur.seller_id.isin(paid)]
            lists[("plan", "Theo GMV")] = cur.nlargest(k, "gmv_90")
        for (scope, name), sel in lists.items():
            rows.append({"as_of": t, "scope": scope, "list_name": name, "k": len(sel),
                         "hit_rate": float(sel.decline.astype(float).mean()),
                         "dormant_rate": float(sel.dormant.astype(float).mean()),
                         "loss_share": float(sel.loss.sum() / total_loss), "loss": float(sel.loss.sum())})
        rows.append({"as_of": t, "scope": "top50", "list_name": "Chọn ngẫu nhiên (kỳ vọng)", "k": 50,
                     "hit_rate": float(cur.decline.astype(float).mean()), "dormant_rate": float(cur.dormant.astype(float).mean()),
                     "loss_share": 50 / len(cur), "loss": total_loss * 50 / len(cur)})
    return pd.DataFrame(rows)


def sensitivity(scored):
    """Tap seller duoc chon doi the nao khi gia dinh doi. Trung cua cac thay doi: Jaccard so voi phuong an goc."""
    base = Params()
    cases = {"Hiệu quả hỗ trợ vận hành 15%": replace(base, eff_ops_poor=.15), "Hiệu quả hỗ trợ vận hành 45%": replace(base, eff_ops_poor=.45),
             "Hiệu quả gọi điện 10%": replace(base, eff_call_ok=.10), "Hiệu quả gọi điện 30%": replace(base, eff_call_ok=.30),
             "Ngân sách 1.000 BRL": replace(base, budget=1000), "Ngân sách 4.000 BRL": replace(base, budget=4000),
             "Số suất 20": replace(base, max_slots=20), "Số suất 80": replace(base, max_slots=80),
             "Chi phí hỗ trợ gấp đôi": replace(base, cost_ops=300)}
    rows = []
    for t, cur in scored[scored.as_of >= pd.Timestamp(EVAL_START)].groupby("as_of"):
        plan0 = build_plan(cur, base)
        s0 = set(plan0[plan0.action.isin([CALL, OPS])].seller_id)
        for name, q in cases.items():
            pl = build_plan(cur, q)
            s1 = set(pl[pl.action.isin([CALL, OPS])].seller_id)
            rows.append({"as_of": t, "case_name": name, "n_base": len(s0), "n_case": len(s1),
                         "jaccard": len(s0 & s1) / max(len(s0 | s1), 1), "expected_saved": summarize(pl)["expected_saved"],
                         "expected_saved_base": summarize(plan0)["expected_saved"]})
    return pd.DataFrame(rows)


def main():
    start = time.time()
    con = duckdb.connect(str(DB_PATH))
    create_labels(con)
    panel = load_panel(con)
    scored, coefs, aucs, explain = score_all(panel)
    print(f"Diem xong: {len(scored)} dong, {scored.as_of.nunique()} moc as-of, {time.time() - start:.1f}s", flush=True)
    plans = []
    for t, cur in scored.groupby("as_of"):
        pl = build_plan(cur, Params())
        pl["as_of"] = t
        plans.append(pl)
    plans = pd.concat(plans, ignore_index=True)
    lists = evaluate_lists(scored, plans)
    sens = sensitivity(scored)
    print(f"Ke hoach va danh gia xong {time.time() - start:.1f}s", flush=True)

    keep_score = ["as_of", "seller_id", "p_decline", "p_dormant", "value_45", "ops_score"]
    keep_plan = ["as_of", "seller_id", "segment", "action", "reason", "rank", "cost", "expected_saved", "gmv_risk",
                 "p_decline", "p_dormant", "ops_score"]
    for name, frame in [("scores", scored[keep_score]), ("recommendation", plans[keep_plan]), ("model_coef", coefs), ("explain", explain),
                        ("eval_auc", aucs), ("eval_lists", lists), ("sensitivity", sens)]:
        con.register("_f", frame)
        con.execute(f"CREATE OR REPLACE TABLE dss.{name} AS SELECT * EXCLUDE (as_of), CAST(as_of AS DATE) AS as_of FROM _f")
        con.unregister("_f")
    con.execute(f"CREATE OR REPLACE TABLE dss.default_params AS SELECT * FROM (SELECT '{json.dumps(Params().as_dict())}' AS params_json)")
    con.execute("CHECKPOINT")
    con.close()

    EVIDENCE_DIR.mkdir(exist_ok=True)
    report = {"auc": aucs.round(4).astype({"as_of": str, "train_max_as_of": str}).to_dict("records"),
              "lists": lists.round(4).astype({"as_of": str}).to_dict("records"),
              "sensitivity": sens.round(4).astype({"as_of": str}).to_dict("records"),
              "params": Params().as_dict()}
    (EVIDENCE_DIR / "dss_evaluation.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"DSS xong sau {time.time() - start:.1f}s")


if __name__ == "__main__":
    main()
