"""Toi uu phan bo: moi seller toi da 1 hanh dong tra phi, duoi rang buoc ngan sach va cong suat.

Muc tieu: toi da GMV ky vong giu duoc = p_decline x gia tri 45 ngay x hieu qua gia dinh.
Giai chinh xac bang MILP (HiGHS qua SciPy).
"""
import warnings

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from src.dss.rules import CALL, EMAIL, NONE, OPS, Params, classify, reason_text


def efficacy(action, ops_poor, p: Params):
    if action == CALL:
        return p.eff_call_poor if ops_poor else p.eff_call_ok
    if action == OPS:
        return p.eff_ops_poor if ops_poor else p.eff_ops_ok
    if action == EMAIL:
        return p.eff_email
    return 0.0


def cost_of(action, p: Params):
    return {CALL: p.cost_call, OPS: p.cost_ops}.get(action, 0.0)


def slots_of(action, p: Params):
    return {CALL: p.slots_call, OPS: p.slots_ops}.get(action, 0)


def gain(row, action, p: Params):
    return row.p_decline * row.value_45 * efficacy(action, row.ops_poor, p)


def solve(df: pd.DataFrame, p: Params) -> dict:
    """df da qua classify. Tra ve {seller_id: action} cho phan tra phi."""
    cand = df[df.risk_high & df.value_high]
    options = []
    for r in cand.itertuples():
        for a in (CALL, OPS):
            g = gain(r, a, p)
            if g > 0:
                options.append((r.seller_id, a, g))
    if not options:
        return {}
    n = len(options)
    sellers = {s: i for i, s in enumerate(dict.fromkeys(o[0] for o in options))}
    A = lil_matrix((2 + len(sellers), n))
    for j, (s, a, _) in enumerate(options):
        A[0, j] = cost_of(a, p)
        A[1, j] = slots_of(a, p)
        A[2 + sellers[s], j] = 1
    ub = np.r_[p.budget, p.max_slots, np.ones(len(sellers))]
    res = milp(c=-np.array([o[2] for o in options]), constraints=LinearConstraint(A.tocsr(), -np.inf, ub),
               integrality=np.ones(n), bounds=Bounds(0, 1), options={"time_limit": 10})
    if res.status != 0:
        # 0 = HiGHS chung minh toi uu; 1 = het gio, nghiem tra ve (neu co) chi la nghiem kha thi tot nhat tim duoc
        warnings.warn(f"MILP chua chung minh toi uu: status={res.status}, mip_gap={getattr(res, 'mip_gap', None)}, {res.message}")
    if res.x is None:
        return {}
    return {options[j][0]: options[j][1] for j in np.flatnonzero(res.x > 0.5)}


def build_plan(df: pd.DataFrame, p: Params) -> pd.DataFrame:
    """Tu bang diem den ke hoach day du: hanh dong, chi phi, GMV ky vong, ly do, thu tu."""
    out = classify(df, p)
    paid = solve(out, p)
    out["action"] = out.seller_id.map(paid).astype(object)
    email = out.action.isna() & out.segment.isin(["Email tự động", "Cảnh báo vận hành"])
    out.loc[email, "action"] = EMAIL
    out["action"] = out.action.fillna(NONE)
    out["cost"] = [cost_of(a, p) for a in out.action]
    out["slots"] = [slots_of(a, p) for a in out.action]
    out["expected_saved"] = [gain(r, r.action, p) for r in out.itertuples()]
    out["gmv_risk"] = out.p_decline * out.value_45
    out["reason"] = [reason_text(r) for r in out.itertuples()]
    order = {CALL: 0, OPS: 0, EMAIL: 1, NONE: 2}
    out["_o"] = out.action.map(order)
    out = out.sort_values(["_o", "gmv_risk"], ascending=[True, False]).drop(columns="_o").reset_index(drop=True)
    out["rank"] = out.index + 1
    return out


def summarize(plan: pd.DataFrame) -> dict:
    paid = plan[plan.action.isin([CALL, OPS])]
    return {"n_call": int((plan.action == CALL).sum()), "n_ops": int((plan.action == OPS).sum()),
            "n_email": int((plan.action == EMAIL).sum()), "cost": float(plan.cost.sum()), "slots": int(plan.slots.sum()),
            "gmv_risk_covered": float(paid.gmv_risk.sum()), "expected_saved": float(plan.expected_saved.sum()),
            "gmv_risk_total": float(plan[plan.risk_high].gmv_risk.sum())}


def budget_curve(df: pd.DataFrame, p: Params, budgets) -> pd.DataFrame:
    from dataclasses import replace
    base = classify(df, p)
    rows = []
    for b in budgets:
        q = replace(p, budget=float(b))
        paid = solve(base, q)
        sub = base[base.seller_id.isin(paid)]
        saved = sum(gain(r, paid[r.seller_id], q) for r in sub.itertuples())
        rows.append({"budget": b, "expected_saved": saved, "n_sellers": len(paid)})
    return pd.DataFrame(rows)
