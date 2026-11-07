"""Chon nguong rui ro mac dinh tren giai doan phat trien, khong dung thang test.

Chay: python -m scripts.tune_threshold
Giai doan chon: 09/2017-02/2018. Thang test 03-07/2018 khong tham gia viec chon.
"""
import json
from dataclasses import replace

import duckdb
import pandas as pd

from src.config import DB_PATH, EVIDENCE_DIR
from src.dss.optimize import build_plan, summarize
from src.dss.rules import CALL, OPS, Params

con = duckdb.connect(str(DB_PATH), read_only=True)
df = con.execute("""SELECT f.*, s.p_decline, s.p_dormant, s.value_45, l.decline, l.loss
                    FROM mart.seller_features f JOIN dss.scores s USING (as_of, seller_id)
                    LEFT JOIN dss.labels l USING (as_of, seller_id)
                    WHERE f.as_of BETWEEN DATE '2017-09-01' AND DATE '2018-02-01'""").df()
con.close()
rows = []
for thr in [.2, .25, .3, .35, .4, .45, .5]:
    q = replace(Params(), risk_threshold=thr)
    for t, cur in df.groupby("as_of"):
        pl = build_plan(cur, q)
        paid = pl[pl.action.isin([CALL, OPS])]
        k = len(paid)
        gmv = cur.nlargest(k, "gmv_90")
        p6 = replace(q, budget=q.budget * 2)
        pl6 = build_plan(cur, p6)
        s0, s6 = set(paid.seller_id), set(pl6[pl6.action.isin([CALL, OPS])].seller_id)
        n_cand = int((pl.risk_high & pl.value_high).sum())
        rows.append({"thr": thr, "as_of": str(t)[:10], "n_cand": n_cand, "k": k, "cost": summarize(pl)["cost"],
                     "slots": summarize(pl)["slots"], "hit": paid.decline.astype(float).mean(), "hit_gmv": gmv.decline.astype(float).mean(),
                     "loss": paid.loss.sum() / cur.loss.sum(), "loss_gmv": gmv.loss.sum() / cur.loss.sum(),
                     "budget_matters": s0 != s6})
r = pd.DataFrame(rows)
s = r.groupby("thr").agg(n_cand=("n_cand", "mean"), k=("k", "mean"), cost=("cost", "mean"), slots=("slots", "mean"),
                         hit=("hit", "mean"), hit_gmv=("hit_gmv", "mean"), loss=("loss", "mean"), loss_gmv=("loss_gmv", "mean"),
                         budget_matters=("budget_matters", "mean")).round(3)
print(s.to_string())
EVIDENCE_DIR.mkdir(exist_ok=True)
(EVIDENCE_DIR / "threshold_selection.json").write_text(json.dumps(s.reset_index().to_dict("records"), indent=1), encoding="utf-8")
