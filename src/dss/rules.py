"""Tham so, bang luat va ly do bang chu cua DSS."""
from dataclasses import asdict, dataclass

import pandas as pd

CALL, OPS, EMAIL, NONE = "CALL", "OPS", "EMAIL", "NONE"
ACTION_LABEL = {CALL: "Gọi ngay", OPS: "Hỗ trợ vận hành", EMAIL: "Email tự động", NONE: "Chưa xử lý"}


@dataclass(frozen=True)
class Params:
    """Chi phi va hieu qua can thiep la GIA DINH, du lieu khong co so that."""
    budget: float = 2000.0
    max_slots: int = 40
    # Chon tren 09/2017-02/2018, xem scripts/tune_threshold.py va evidence/threshold_selection.json
    risk_threshold: float = 0.30
    value_pct: float = 0.80
    ops_late: float = 0.15
    min_known: int = 5
    cost_call: float = 50.0
    cost_ops: float = 150.0
    slots_call: int = 1
    slots_ops: int = 2
    eff_call_ok: float = 0.20
    eff_call_poor: float = 0.08
    eff_ops_poor: float = 0.30
    eff_ops_ok: float = 0.05
    eff_email: float = 0.03

    def as_dict(self):
        return asdict(self)


def classify(df: pd.DataFrame, p: Params) -> pd.DataFrame:
    """Gan phan khuc theo bang luat. Nguong gia tri tinh tren seller dang hoat dong tai as-of."""
    out = df.copy()
    cut = out.gmv_90.quantile(p.value_pct)
    out["risk_high"] = out.p_decline >= p.risk_threshold
    out["value_high"] = out.gmv_90 >= cut
    out["ops_poor"] = (out.seller_late_rate.fillna(0) >= p.ops_late) & (out.n_limit_known >= p.min_known)
    late = out.n_cust_late_orders.fillna(0)
    out["carrier_issue"] = (late >= 2) & (out.n_cust_late_seller_ok.fillna(0) / late.where(late > 0, 1) >= 0.5) & ~out.ops_poor
    seg = pd.Series("Theo dõi", index=out.index, dtype="object")
    seg[~out.risk_high & out.value_high & ~out.ops_poor] = "Seller vàng"
    seg[~out.risk_high & out.ops_poor] = "Cảnh báo vận hành"
    seg[out.risk_high & ~out.value_high] = "Email tự động"
    seg[out.risk_high & out.value_high & out.ops_poor] = "Hỗ trợ vận hành"
    seg[out.risk_high & out.value_high & ~out.ops_poor] = "Giữ chân ngay"
    out["segment"] = seg
    return out


def reason_text(r) -> str:
    """Ly do bang chu cho mot seller, chi dung so da biet tai as-of."""
    parts = [f"Khả năng sụt GMV {r.p_decline:.0%}"]
    if r.recency > 21:
        parts.append(f"{r.recency:.0f} ngày chưa có đơn")
    if pd.notna(r.trend) and r.trend < -0.25:
        parts.append(f"GMV 30 ngày thấp hơn {-r.trend:.0%} so với trung bình 90 ngày")
    if r.ops_poor:
        parts.append(f"{r.seller_late_rate:.0%} sản phẩm giao cho vận chuyển trễ hạn, đây là khâu của seller")
    elif r.carrier_issue:
        parts.append(f"{r.n_cust_late_seller_ok:.0f}/{r.n_cust_late_orders:.0f} đơn trễ có seller đúng hạn, nên xem lại tuyến thay vì phạt seller")
    if pd.notna(r.avg_review) and r.avg_review < 3.5:
        parts.append(f"review trung bình {r.avg_review:.1f}")
    return "; ".join(parts) + "."
