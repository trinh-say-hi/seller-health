"""Ke hoach da chot: quyet dinh cuoi cua Truong nhom Seller Success, chay tu app ve Power BI.

Kho du lieu (ban phat hanh) chi doc va bi thay moi lan dung lai, nen quyet dinh khong ghi vao DuckDB ma ghi ra mot file Parquet
rieng nam canh cac file Power BI doc (powerbi/ke_hoach_da_chot.parquet). Moi moc as-of giu dung mot ban chot: chot lai thi thay.
Power BI doc file nay khi bam Lam moi; trang Ke hoach uu tien ke hoach da chot, chua chot thi dung de xuat mac dinh cua MILP.
"""
import datetime as dt
import json
import os
from pathlib import Path

import pandas as pd

from src.config import HOME

FILE = HOME / "powerbi" / "ke_hoach_da_chot.parquet"
COLUMNS = {"as_of": "datetime64[ns]", "as_of_key": "int64", "seller_id": "string", "seller_key": "int64", "action": "string",
           "cost": "float64", "gmv_risk": "float64", "p_decline": "float64", "expected_saved": "float64", "chot_luc": "datetime64[ns]",
           "nguoi_chot": "string", "tham_so": "string", "so_the_keo_tay": "int64"}


def empty() -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype=t) for c, t in COLUMNS.items()})


def load(path: Path = FILE) -> pd.DataFrame:
    try:
        return pd.read_parquet(path)
    except (FileNotFoundError, OSError, ValueError):
        return empty()


def _write(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}_{os.getpid()}.tmp")
    df.astype(COLUMNS).to_parquet(tmp, index=False)
    os.replace(tmp, path)  # Power BI chi thay file cu hoac file moi, khong thay file viet do


def ensure(path: Path = FILE):
    """Tao file rong dung cau truc neu chua co, de Power BI refresh khong loi khi chua ai chot."""
    if not path.exists():
        _write(empty(), path)


def save(as_of: str, plan: pd.DataFrame, seller_keys: dict, params: dict, edited: int, by: str = "Trưởng nhóm Seller Success",
         path: Path = FILE) -> pd.DataFrame:
    """Ghi ke hoach cua mot moc, thay ban chot cu cua moc do. plan can seller_id, action, cost, gmv_risk, p_decline, expected_saved."""
    ts = pd.Timestamp(as_of)
    rows = plan[["seller_id", "action", "cost", "gmv_risk", "p_decline", "expected_saved"]].copy()
    rows.insert(0, "as_of", ts)
    rows.insert(1, "as_of_key", int(ts.strftime("%Y%m%d")))
    rows["seller_key"] = rows.seller_id.map(seller_keys).fillna(-1).astype("int64")
    rows["chot_luc"] = pd.Timestamp(dt.datetime.now().replace(microsecond=0))
    rows["nguoi_chot"] = by
    rows["tham_so"] = json.dumps(params, ensure_ascii=False, sort_keys=True)
    rows["so_the_keo_tay"] = int(edited)
    old = load(path)
    out = pd.concat([old[old.as_of_key != rows.as_of_key.iloc[0]], rows[list(COLUMNS)]], ignore_index=True)
    _write(out, path)
    return out


def status(as_of: str, path: Path = FILE):
    """Lan chot gan nhat cua moc as-of, hoac None."""
    df = load(path)
    df = df[df.as_of_key == int(pd.Timestamp(as_of).strftime("%Y%m%d"))]
    if df.empty:
        return None
    paid = df[df.action.isin(["CALL", "OPS"])]
    return {"chot_luc": df.chot_luc.iloc[0], "n": len(paid), "cost": float(paid.cost.sum()), "edited": int(df.so_the_keo_tay.iloc[0])}
