"""Luu va so sanh kich ban ke hoach. Kich ban luu trong mot file JSON canh kho du lieu, nen tat app mo lai van con.

Kho du lieu chi doc, nen kich ban khong ghi vao DuckDB.
"""
import datetime as dt
import json

import pandas as pd

from src.config import HOME
from src.dss.rules import CALL, OPS

FILE = HOME / "scenarios.json"


def load() -> list[dict]:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return []


def _write(items: list[dict]):
    FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(FILE)


def record(name: str, as_of: str, params: dict, summary: dict, plan: pd.DataFrame, edited: int) -> dict:
    """Mot kich ban: tham so, so tong hop va danh sach seller duoc goi hoac ho tro."""
    paid = plan[plan.action.isin([CALL, OPS])]
    return {"name": name, "as_of": str(as_of)[:10], "saved_at": dt.datetime.now().isoformat(timespec="seconds"),
            "params": params, "edited": int(edited),
            "summary": {k: (float(v) if isinstance(v, (int, float)) else v) for k, v in summary.items()},
            "sellers": dict(zip(paid.seller_id, paid.action))}


def save(rec: dict):
    items = [x for x in load() if not (x["name"] == rec["name"] and x["as_of"] == rec["as_of"])]
    _write(items + [rec])


def clear(as_of: str):
    _write([x for x in load() if x["as_of"] != str(as_of)[:10]])


def jaccard(a: dict, b: dict) -> float:
    """Muc trung danh sach seller duoc goi hoac ho tro giua hai kich ban."""
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if sa | sb else 1.0


def compare(current: dict, saved: list[dict]) -> pd.DataFrame:
    rows = []
    for r in [current] + saved:
        s, p = r["summary"], r["params"]
        rows.append({
            "Kịch bản": r["name"],
            "Ngân sách": p["budget"], "Số suất": p["max_slots"], "Ngưỡng rủi ro": p["risk_threshold"],
            "Gọi": int(s["n_call"]), "Hỗ trợ": int(s["n_ops"]), "Sửa tay": r["edited"],
            "Tiền dùng": round(s["cost"]), "GMV rủi ro trong KH": round(s["gmv_risk_covered"]), "Giữ được (giả định)": round(s["expected_saved"]),
            "Giữ được / 1.000 BRL": round(s["expected_saved"] / s["cost"] * 1000) if s["cost"] else None,
            "Trùng với hiện tại": jaccard(r["sellers"], current["sellers"]),
        })
    return pd.DataFrame(rows)
