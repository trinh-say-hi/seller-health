"""Kiem tra tinh kha thi cua y tuong Seller Health tren du lieu Olist that.

Chay: python -I scripts/feasibility.py data/olist/raw evidence/feasibility.json
Moi feature tai as-of X chi dung thong tin da biet truoc X.
Khi test tai X, chi train tren as-of <= X - 45 ngay de nhan train da quan sat xong.
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
RAW, OUT = Path(sys.argv[1]), Path(sys.argv[2])
H = pd.Timedelta(days=45)
W = pd.Timedelta(days=90)


def gini(x):
    x = np.sort(np.asarray(x, float))
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


o = pd.read_csv(RAW / "olist_orders_dataset.csv", parse_dates=[
    "order_purchase_timestamp", "order_delivered_carrier_date",
    "order_delivered_customer_date", "order_estimated_delivery_date"])
it = pd.read_csv(RAW / "olist_order_items_dataset.csv", parse_dates=["shipping_limit_date"])
rv = pd.read_csv(RAW / "olist_order_reviews_dataset.csv", parse_dates=["review_creation_date"])
pr = pd.read_csv(RAW / "olist_products_dataset.csv")[["product_id", "product_category_name"]]

valid = o[~o.order_status.isin(["canceled", "unavailable"])]
d = it.merge(valid, on="order_id").merge(pr, on="product_id", how="left")
d = d.rename(columns={"order_purchase_timestamp": "ts", "order_delivered_carrier_date": "carrier",
                      "order_delivered_customer_date": "deliv", "order_estimated_delivery_date": "est"})
rev = rv.groupby("order_id").agg(score=("review_score", "mean"), rev_ts=("review_creation_date", "min")).reset_index()
d = d.merge(rev, on="order_id", how="left")
res = {}

# 1. Bao phu thoi gian va quy mo
m = d.groupby(d.ts.dt.to_period("M")).agg(items=("order_id", "size"), orders=("order_id", "nunique"),
                                          sellers=("seller_id", "nunique"), gmv=("price", "sum"))
res["monthly"] = {str(k): {c: round(float(v[c]), 0) for c in m.columns} for k, v in m.iterrows()}
last_full = d.ts.max()
res["max_purchase"] = str(last_full)

# 2. Tap trung doanh thu
g = d.groupby("seller_id").price.sum().sort_values(ascending=False)
res["concentration"] = {"n_sellers": int(len(g)), "gini": round(gini(g), 3),
                        "top20pct_share": round(float(g.head(int(len(g) * .2)).sum() / g.sum()), 3),
                        "top10_sellers_share": round(float(g.head(10).sum() / g.sum()), 3),
                        "median_seller_gmv": round(float(g.median()), 0)}

# 3. Quy lo giao tre cho ai (dung shipping_limit_date = han seller giao cho van chuyen)
oseller = d.groupby("order_id").seller_id.nunique()
res["multi_seller_orders"] = int((oseller > 1).sum())
s = d[d.deliv.notna() & d.carrier.notna()].copy()
s["seller_late"] = s.carrier > s.shipping_limit_date
os_ = s.groupby("order_id").agg(seller_late=("seller_late", "max"), deliv=("deliv", "first"), est=("est", "first"),
                                score=("score", "first"), carrier=("carrier", "first"), ts=("ts", "first"))
os_["cust_late"] = os_.deliv.dt.normalize() > os_.est.dt.normalize()
late = os_[os_.cust_late]
res["blame"] = {
    "n_delivered": int(len(os_)), "cust_late_rate": round(float(os_.cust_late.mean()), 4),
    "seller_late_rate": round(float(os_.seller_late.mean()), 4),
    "late_orders_seller_also_late": round(float(late.seller_late.mean()), 4),
    "P_cust_late_given_seller_late": round(float(os_[os_.seller_late].cust_late.mean()), 4),
    "P_cust_late_given_seller_ontime": round(float(os_[~os_.seller_late].cust_late.mean()), 4),
    "review": {f"seller_late={a},cust_late={b}": round(float(x), 3)
               for (a, b), x in os_.groupby(["seller_late", "cust_late"]).score.mean().items()},
    "median_days_to_carrier": round(float(((os_.carrier - os_.ts).dt.total_seconds() / 86400).median()), 2),
    "median_days_carrier_to_customer": round(float(((os_.deliv - os_.carrier).dt.total_seconds() / 86400).median()), 2),
}


# 4. Feature tai as-of, chi dung thong tin biet truoc as-of
def features(asof):
    h = d[d.ts < asof]
    w = h[h.ts >= asof - W]
    f = pd.DataFrame(index=w.seller_id.unique())
    f["gmv_90"] = w.groupby("seller_id").price.sum()
    f["orders_90"] = w.groupby("seller_id").order_id.nunique()
    w30 = w[w.ts >= asof - pd.Timedelta(days=30)]
    f["gmv_30"] = w30.groupby("seller_id").price.sum()
    f["orders_30"] = w30.groupby("seller_id").order_id.nunique()
    f = f.fillna(0)
    f["trend"] = f.gmv_30 / (f.gmv_90 / 3).replace(0, np.nan) - 1
    f["recency"] = (asof - h.groupby("seller_id").ts.max()).dt.total_seconds() / 86400
    f["tenure"] = (asof - h.groupby("seller_id").ts.min()).dt.total_seconds() / 86400
    f["n_cat"] = w.groupby("seller_id").product_category_name.nunique()
    # Han giao van chuyen da qua truoc as-of: biet chac da tre hay chua
    k = w[w.shipping_limit_date < asof]
    late_handover = k.carrier.isna() | (k.carrier > k.shipping_limit_date)
    f["seller_late_rate"] = late_handover.groupby(k.seller_id).mean()
    # Ngay hen da qua truoc as-of
    e = w[w.est < asof]
    cl = e.deliv.isna() | (e.deliv.dt.normalize() > e.est.dt.normalize())
    f["cust_late_rate"] = cl.groupby(e.seller_id).mean()
    r = w[w.rev_ts < asof]
    f["avg_review"] = r.groupby("seller_id").score.mean()
    c = w[w.carrier < asof]
    f["days_to_carrier"] = ((c.carrier - c.ts).dt.total_seconds() / 86400).groupby(c.seller_id).mean()
    # Nhan: 45 ngay sau as-of
    fut = d[(d.ts >= asof) & (d.ts < asof + H)]
    f["gmv_next45"] = fut.groupby("seller_id").price.sum()
    f["gmv_next45"] = f.gmv_next45.fillna(0)
    f["churn"] = (f.gmv_next45 == 0).astype(int)
    f["decline"] = (f.gmv_next45 < .5 * f.gmv_90 / 2).astype(int)
    # Quay lai sau cua so 45 ngay (toi het du lieu tin cay)
    later = d[(d.ts >= asof + H) & (d.ts < pd.Timestamp("2018-09-01"))]
    f["returned"] = f.index.isin(later.seller_id).astype(int)
    f["loss"] = (f.gmv_90 / 2 - f.gmv_next45).clip(lower=0)
    f["asof"] = asof
    return f


asofs = pd.date_range("2017-04-01", "2018-07-01", freq="MS")
P = pd.concat([features(a) for a in asofs]).rename_axis("seller_id").reset_index()
FEATS = ["gmv_90", "orders_90", "gmv_30", "orders_30", "trend", "recency", "tenure", "n_cat",
         "seller_late_rate", "cust_late_rate", "avg_review", "days_to_carrier"]
OPS = ["seller_late_rate", "cust_late_rate", "avg_review", "days_to_carrier"]
for c in ["gmv_90", "gmv_30"]:
    P[c] = np.log1p(P[c])
P["gmv90_raw"] = np.expm1(P.gmv_90)


# 5. Churn 45 ngay co that la churn khong
tbl = []
for a, x in P.groupby("asof"):
    q = x.gmv90_raw.quantile(.8)
    top = x[x.gmv90_raw >= q]
    tbl.append({"asof": str(a.date()), "active": len(x), "churn_rate": round(x.churn.mean(), 3),
                "top20_n": len(top), "top20_churn_n": int(top.churn.sum()),
                "top20_decline_n": int(top.decline.sum()),
                "gmv90_of_churners_share": round(x[x.churn == 1].gmv90_raw.sum() / x.gmv90_raw.sum(), 3),
                "loss_sum_top20": round(top.loss.sum(), 0),
                "churner_return_rate": round(x[x.churn == 1].returned.mean(), 3)})
res["churn_by_asof"] = tbl

bands = pd.cut(np.expm1(P.orders_90 * 0) + P.orders_90, [0, 2, 5, 10, 30, 1e9], labels=["1-2", "3-5", "6-10", "11-30", "31+"])
early = P[P["asof"] <= "2018-03-01"]
res["by_size_orders90"] = {
    str(b): {"n": int(len(x)), "churn": round(x.churn.mean(), 3), "decline": round(x.decline.mean(), 3),
             "churner_return_rate": round(x[x.churn == 1].returned.mean(), 3)}
    for b, x in early.groupby(bands[P["asof"] <= "2018-03-01"], observed=True)}


# 6. Backtest cuon, khong ro ri nhan
def topk(y, score, k):
    idx = np.argsort(-score)[:k]
    return float(np.asarray(y)[idx].mean())


def backtest(label, pop=lambda x: x):
    out = []
    coefs = []
    for t in pd.date_range("2018-03-01", "2018-07-01", freq="MS"):
        tr = pop(P[P["asof"] <= t - H])
        te = pop(P[P["asof"] == t])
        med = tr[FEATS].median()
        Xtr, Xte = tr[FEATS].fillna(med), te[FEATS].fillna(med)
        y, yt = tr[label], te[label]
        lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(Xtr, y)
        rf = RandomForestClassifier(400, min_samples_leaf=10, n_jobs=-1, random_state=0).fit(Xtr, y)
        ln = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(Xtr.drop(columns=OPS), y)
        p_lr, p_rf = lr.predict_proba(Xte)[:, 1], rf.predict_proba(Xte)[:, 1]
        p_noops = ln.predict_proba(Xte.drop(columns=OPS))[:, 1]
        rule = ((te.trend.fillna(0) < -.5) & (te.recency > 21)).astype(int).values
        rec = te.recency.values
        k = min(50, len(te) // 4)
        out.append({"asof": str(t.date()), "n": len(te), "base": round(yt.mean(), 3),
                    "auc_recency": round(roc_auc_score(yt, rec), 3), "auc_lr": round(roc_auc_score(yt, p_lr), 3),
                    "auc_lr_no_ops": round(roc_auc_score(yt, p_noops), 3), "auc_rf": round(roc_auc_score(yt, p_rf), 3),
                    f"prec@{k}_recency": round(topk(yt, rec, k), 3), f"prec@{k}_lr": round(topk(yt, p_lr, k), 3),
                    "rule_flagged": int(rule.sum()), "rule_precision": round(float(yt[rule == 1].mean()) if rule.sum() else 0, 3),
                    "rule_recall": round(float(rule[yt == 1].mean()), 3)})
        coefs.append(pd.Series(lr[-1].coef_[0], index=FEATS))
    return out, pd.concat(coefs, axis=1).mean(axis=1).round(3).sort_values().to_dict()


res["backtest_churn_all"], res["coef_churn_all"] = backtest("churn")
sized = lambda x: x[x.orders_90 >= 6]
res["backtest_churn_6plus"], res["coef_churn_6plus"] = backtest("churn", sized)
res["backtest_decline_6plus"], res["coef_decline_6plus"] = backtest("decline", sized)


# 7. Danh sach top-N co bat duoc phan GMV mat that khong (khong can gia dinh hieu qua can thiep)
gm = []
for t in pd.date_range("2018-03-01", "2018-07-01", freq="MS"):
    tr, te = P[P["asof"] <= t - H], P[P["asof"] == t].copy()
    med = tr[FEATS].median()
    lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(tr[FEATS].fillna(med), tr.decline)
    te["p"] = lr.predict_proba(te[FEATS].fillna(med))[:, 1]
    te["ev"] = te.p * te.gmv90_raw
    row = {"asof": str(t.date()), "total_loss": round(te.loss.sum(), 0)}
    for name, col in [("by_gmv", "gmv90_raw"), ("by_ev", "ev"), ("by_p", "p")]:
        top = te.nlargest(50, col)
        row[name] = round(top.loss.sum() / te.loss.sum(), 3)
        row[name + "_decline_prec"] = round(top.decline.mean(), 3)
    row["random"] = round(50 / len(te), 3)
    gm.append(row)
res["top50_loss_capture"] = gm

# 8. Giao tre co di truoc sut giam khong (tuong quan, khong phai nhan qua)
x = P[(P.orders_90 >= 6) & (P["asof"] <= "2018-07-01")].copy()
x["ops_band"] = pd.cut(x.seller_late_rate.fillna(0), [-.01, .05, .15, .3, 1], labels=["<=5%", "5-15%", "15-30%", ">30%"])
res["seller_late_vs_outcome"] = {str(b): {"n": int(len(v)), "decline": round(v.decline.mean(), 3), "churn": round(v.churn.mean(), 3),
                                          "avg_review": round(v.avg_review.mean(), 2)}
                                 for b, v in x.groupby("ops_band", observed=True)}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
print(json.dumps(res, indent=1, ensure_ascii=False))
