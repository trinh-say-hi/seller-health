"""Mo phong Monte Carlo cho mot ke hoach: GMV giu duoc la mot khoang, khong phai mot con so.

Hai nguon bat dinh (chuong 7: ra quyet dinh trong dieu kien rui ro):
1. Seller co sut that hay khong: moi seller sut voi xac suat p_decline cua mo hinh (Bernoulli, doc lap).
2. Hieu qua can thiep la gia dinh: moi lan mo phong rut mot he so cho tung loai hanh dong tu phan phoi tam giac
   quanh gia tri gia dinh (thap = gia dinh x (1 - do bat dinh), cao = gia dinh x (1 + do bat dinh)). Cung mot he so dung chung
   cho moi seller cung loai, vi neu gia dinh sai thi sai cho ca nhom.

Gia tri ky vong cua mo phong bang dung expected_saved cua bo toi uu, nen hai so khop nhau.
"""
import numpy as np
import pandas as pd

from src.dss.rules import CALL, EMAIL, OPS, Params

# Loai hieu qua theo hanh dong va tinh trang van hanh, cung cach tinh voi optimize.efficacy
KINDS = ["call_ok", "call_poor", "ops_poor", "ops_ok", "email"]


def _kind(action, ops_poor):
    if action == CALL:
        return "call_poor" if ops_poor else "call_ok"
    if action == OPS:
        return "ops_poor" if ops_poor else "ops_ok"
    if action == EMAIL:
        return "email"
    return None


def _assumed(p: Params) -> dict:
    return {"call_ok": p.eff_call_ok, "call_poor": p.eff_call_poor, "ops_poor": p.eff_ops_poor, "ops_ok": p.eff_ops_ok, "email": p.eff_email}


def simulate(plan: pd.DataFrame, p: Params, spread: float = .5, n: int = 2000, seed: int = 0) -> dict:
    """plan can cot action, ops_poor, p_decline, value_45, cost. Tra ve phan vi cua GMV giu duoc va xac suat giu duoc it hon tien bo ra."""
    kinds = [_kind(a, o) for a, o in zip(plan.action, plan.ops_poor)]
    sub = plan.assign(kind=kinds).dropna(subset=["kind"])
    cost = float(plan.cost.sum())
    if sub.empty:
        return {"p10": 0.0, "p50": 0.0, "p90": 0.0, "mean": 0.0, "expected": 0.0, "p_below_cost": 1.0 if cost > 0 else 0.0, "draws": np.zeros(n)}
    rng = np.random.default_rng(seed)
    base = _assumed(p)
    eff = {}
    for k in KINDS:
        m = base[k]
        lo, hi = m * (1 - spread), min(m * (1 + spread), 1.0)
        eff[k] = rng.triangular(lo, m, hi, size=n) if hi > lo else np.full(n, m)
    prob = sub.p_decline.to_numpy()
    value = sub.value_45.to_numpy()
    declined = rng.random((n, len(sub))) < prob                      # n x seller: seller co sut that khong
    eff_matrix = np.column_stack([eff[k] for k in sub.kind])          # n x seller: hieu qua rut cho loai hanh dong cua seller
    draws = (declined * value * eff_matrix).sum(axis=1)
    expected = float((prob * value * np.array([base[k] for k in sub.kind])).sum())
    return {"p10": float(np.percentile(draws, 10)), "p50": float(np.percentile(draws, 50)), "p90": float(np.percentile(draws, 90)),
            "mean": float(draws.mean()), "expected": expected, "p_below_cost": float((draws < cost).mean()) if cost > 0 else 0.0,
            "draws": draws}
