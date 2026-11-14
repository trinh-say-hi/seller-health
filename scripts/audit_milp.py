"""Kiem tra bo giai MILP: trang thai HiGHS, mip_gap va thoi gian giai tai moi moc as-of.

    python scripts/audit_milp.py

Chay lai bo cham diem tren ban kho hien hanh (chi doc), giai ke hoach mac dinh tai 13 moc
va 70 ke hoach cua phan tich do nhay, ghi ket qua vao evidence/milp_audit.json.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import duckdb  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.config import DB_PATH, EVIDENCE_DIR  # noqa: E402
from src.dss import optimize  # noqa: E402
from src.dss.rules import Params  # noqa: E402
from src.dss.run import load_panel, score_all, sensitivity  # noqa: E402

LOG = []
_milp = optimize.milp


def _timed(*a, **k):
    t0 = time.perf_counter()
    r = _milp(*a, **k)
    LOG.append({"status": int(r.status), "message": r.message, "mip_gap": float(getattr(r, "mip_gap", 0.0) or 0.0),
                "seconds": time.perf_counter() - t0, "n_vars": len(k["c"])})
    return r


def main():
    optimize.milp = _timed
    con = duckdb.connect(str(DB_PATH), read_only=True)
    scored, *_ = score_all(load_panel(con))
    con.close()
    default = []
    for t, cur in scored.groupby("as_of"):
        n0 = len(LOG)
        optimize.build_plan(cur, Params())
        default += [{"as_of": str(t.date()), **e} for e in LOG[n0:]]
    n_default = len(LOG)
    sensitivity(scored)
    d, s = pd.DataFrame(default), pd.DataFrame(LOG[n_default:])
    out = {"db": str(DB_PATH.name), "time_limit_s": 10,
           "default": {"calls": len(d), "optimal": int((d.status == 0).sum()), "max_gap": float(d.mip_gap.max()),
                       "median_s": float(d.seconds.median()), "max_s": float(d.seconds.max()),
                       "n_vars_min": int(d.n_vars.min()), "n_vars_max": int(d.n_vars.max()), "per_as_of": default},
           "sensitivity": {"calls": len(s), "optimal": int((s.status == 0).sum()), "max_gap": float(s.mip_gap.max()),
                           "max_s": float(s.seconds.max())}}
    EVIDENCE_DIR.mkdir(exist_ok=True)
    (EVIDENCE_DIR / "milp_audit.json").write_text(json.dumps(out, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "per_as_of"} if isinstance(v, dict) else v
                      for k, v in out.items()}, indent=2, default=float))


if __name__ == "__main__":
    main()
