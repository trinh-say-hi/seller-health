"""Pipeline Seller Health tren Dagster: moi lop la mot asset, cong chat luong la asset check.

Chay giao dien: .\\run_pipeline.ps1  (mo http://localhost:3000)
Chay khong giao dien: dagster job execute -m src.pipeline.definitions -j dung_lai_toan_bo

Cac asset chi boc cac buoc san co (src.etl.build, src.dss.run, src.etl.catalog, tests.test_system), khong viet lai logic,
nen so lieu giong het run_all.py. Moi buoc chay trong tien trinh con voi OLIST_DB tro vao ban phat hanh cua lan chay nay.
Ban moi chi duoc tro sang (kho_phat_hanh) khi cac check chan (blocking) deu dat.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import duckdb
from dagster import (AssetCheckResult, AssetCheckSeverity, AssetExecutionContext, AssetSelection, DefaultScheduleStatus, Definitions,
                     Failure, MaterializeResult, MetadataValue, ScheduleDefinition, asset, asset_check, define_asset_job)

from src.config import EVIDENCE_DIR, RELEASES_DIR, ROOT, current_db
from src.pipeline import release

N_BATCHES = 26


def _md(df) -> str:
    """Bang markdown cho metadata, khong can thu vien tabulate."""
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join("" if v is None else str(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lines)


def _release_path(context) -> Path:
    """Moi lan chay co mot ban phat hanh rieng, dat ten theo run_id de cac asset trong cung lan chay dung chung."""
    return RELEASES_DIR / f"olist_run_{context.run.run_id[:8]}.duckdb"


def _ensure_release(context) -> Path:
    """Lan chay khong co buoc dung kho (chi chay lai DSS chang han) thi chep kho dang dung lam diem xuat phat."""
    path = _release_path(context)
    if not path.exists():
        src = release.seed_from_current(path)
        context.log.info(f"Lan chay nay khong dung lai kho: chep {src.name} sang {path.name}")
    return path


def _run_module(context, module: str, db: Path) -> float:
    """Chay mot buoc san co trong tien trinh con, day tung dong log vao Dagster. Tien trinh con loi thi asset loi."""
    start = time.time()
    env = {**os.environ, "OLIST_DB": str(db), "PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1"}
    proc = subprocess.Popen([sys.executable, "-m", module], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    tail = []
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            context.log.info(line)
            tail = (tail + [line])[-15:]
    code = proc.wait()
    if code:
        raise Failure(f"{module} dung voi ma {code}", metadata={"log_cuoi": MetadataValue.md("```\n" + "\n".join(tail) + "\n```")})
    return round(time.time() - start, 1)


def _query(db: Path, sql: str):
    con = duckdb.connect(str(db), read_only=True)
    try:
        return con.execute(sql).df()
    finally:
        con.close()


# ---------------------------------------------------------------- Lop kho
@asset(group_name="kho", description="9 file CSV Olist, doi chieu SHA-256 va so dong voi data/manifest.json truoc khi nap.")
def nguon_csv(context: AssetExecutionContext) -> MaterializeResult:
    from src.etl.build import verify_sources
    rows = verify_sources()  # loi neu file doi, thieu, sai hash
    table = "| File | Bảng | Số dòng | SHA-256 |\n|---|---|---:|---|\n" + "\n".join(f"| {f} | {t} | {n:,} | `{h[:12]}` |" for f, t, h, n in rows)
    return MaterializeResult(metadata={"so_file": len(rows), "tong_so_dong": sum(r[3] for r in rows), "nguon": MetadataValue.md(table)})


@asset(group_name="kho", deps=[nguon_csv],
       description="Bronze -> Silver -> Gold trong DuckDB: nap master data roi 26 dot theo thang, moi dot co doi soat giua cac lop.")
def kho_du_lieu(context: AssetExecutionContext) -> MaterializeResult:
    db = _release_path(context)
    seconds = _run_module(context, "src.etl.build", db)
    log = _query(db, "SELECT * FROM ops.etl_log ORDER BY batch")
    facts = _query(db, """SELECT table_name, estimated_size AS so_dong FROM duckdb_tables()
                          WHERE schema_name = 'core' AND table_name LIKE 'fact_%' ORDER BY 1""")
    return MaterializeResult(metadata={
        "ban_phat_hanh": db.name, "thoi_gian_s": seconds, "so_dot_ok": int((log.status == "ok").sum()),
        "bang_fact": MetadataValue.md(_md(facts)),
        "etl_log": MetadataValue.md(_md(log.drop(columns=[c for c in ("error_message",) if c in log])))})


@asset_check(asset=kho_du_lieu, blocking=True,
             description="Cong chat luong: du 26 dot status ok va moi dong trong ops.layer_reconciliation deu khop. Khong dat thi khong phat hanh.")
def doi_soat_cac_lop(context) -> AssetCheckResult:
    db = _release_path(context)
    ok = int(_query(db, "SELECT count(*) AS n FROM ops.etl_log WHERE status = 'ok' AND batch <> 'init'").n[0])
    rec = _query(db, "SELECT count(*) AS n, count(*) FILTER (WHERE NOT is_ok) AS bad FROM ops.layer_reconciliation")
    n, bad = int(rec.n[0]), int(rec.bad[0])
    return AssetCheckResult(passed=bool(ok == N_BATCHES and bad == 0 and n > 0),
                            metadata={"dot_ok": f"{ok}/{N_BATCHES}", "doi_soat_khop": f"{n - bad}/{n}"})


@asset_check(asset=kho_du_lieu, description="Bat thuong du lieu da ghi nhan (ops.dq_issue) va so dong bi cach ly. Chi canh bao.")
def bat_thuong_du_lieu(context) -> AssetCheckResult:
    db = _release_path(context)
    dq = _query(db, "SELECT * FROM ops.dq_issue")
    quarantined = int(_query(db, "SELECT count(*) AS n FROM ops.quarantine").n[0])
    return AssetCheckResult(passed=True, severity=AssetCheckSeverity.WARN,
                            metadata={"so_dong_cach_ly": quarantined, "bat_thuong": MetadataValue.md(_md(dq))})


# ---------------------------------------------------------------- Lop DSS
@asset(group_name="dss", deps=[kho_du_lieu],
       description="Hoi quy logistic cuon theo moc as-of, bang luat, MILP chon seller; danh gia nguoc va do nhay.")
def dss_khuyen_nghi(context: AssetExecutionContext) -> MaterializeResult:
    db = _ensure_release(context)
    seconds = _run_module(context, "src.dss.run", db)
    auc = _query(db, "SELECT * FROM dss.eval_auc")
    last = _query(db, """SELECT action, count(*) AS so_seller, round(sum(cost)) AS chi_phi FROM dss.recommendation
                         WHERE as_of = (SELECT max(as_of) FROM dss.recommendation) GROUP BY 1 ORDER BY 2 DESC""")
    auc_cols = [c for c in auc.columns if c.startswith("auc")]
    by_target = auc.groupby("target")[auc_cols].mean().round(4).reset_index()
    meta = {"ban_phat_hanh": db.name, "thoi_gian_s": seconds, "so_moc_as_of": int(auc.as_of.nunique()),
            "auc_trung_binh": MetadataValue.md(_md(by_target)), "ke_hoach_moc_cuoi": MetadataValue.md(_md(last))}
    return MaterializeResult(metadata=meta)


@asset(group_name="dss", deps=[dss_khuyen_nghi],
       description="Gan mo ta cot tu catalog.yml vao kho va sinh docs/data_catalog.md (metadata).")
def danh_muc_du_lieu(context: AssetExecutionContext) -> MaterializeResult:
    db = _ensure_release(context)
    seconds = _run_module(context, "src.etl.catalog", db)
    cov = _query(db, "SELECT count(*) AS n, count(comment) AS c FROM duckdb_columns() WHERE schema_name IN ('core','mart','dss','ops')")
    return MaterializeResult(metadata={"thoi_gian_s": seconds, "cot_co_mo_ta": f"{int(cov.c[0])}/{int(cov.n[0])}"})


@asset_check(asset=danh_muc_du_lieu, blocking=True,
             description="Chay tests.test_system tren ban phat hanh moi: cau truc, so lieu, che tuong lai, chay lai idempotent, cong chat luong.")
def kiem_thu_he_thong(context) -> AssetCheckResult:
    db = _release_path(context)
    try:
        seconds, passed = _run_module(context, "tests.test_system", db), True
    except Failure:
        seconds, passed = None, False
    results = json.loads((EVIDENCE_DIR / "test_results.json").read_text(encoding="utf-8"))
    bad = [r["test"] for r in results if not r["ok"]]
    meta = {"test_dat": f"{len(results) - len(bad)}/{len(results)}", "thoi_gian_s": seconds}
    if bad:
        meta["test_hong"] = MetadataValue.md("\n".join(f"- {t}" for t in bad[:30]))
    return AssetCheckResult(passed=passed and not bad, metadata=meta)


@asset_check(asset=danh_muc_du_lieu, blocking=True,
             description="Lakehouse Parquet khop kho, so cai nap day du; dbt dung lai kho tu raw vao dbt_* va doi chieu voi kho chinh. "
                         "Cung tieu chuan voi run_all.py. Chua cai dbt-duckdb thi bo qua phan dbt.")
def lakehouse_va_dbt(context) -> AssetCheckResult:
    from src.pipeline import dbt_runner
    db = _release_path(context)
    steps = ["tests.test_lakehouse_medallion"] + (["src.pipeline.dbt_runner"] if dbt_runner.available() else [])
    meta = {}
    for module in steps:
        try:
            meta[module] = f"{_run_module(context, module, db)} s"
        except Failure:
            return AssetCheckResult(passed=False, metadata={**meta, module: "hong"})
    return AssetCheckResult(passed=True, metadata=meta)


# ---------------------------------------------------------------- Phat hanh
@asset(group_name="phat_hanh", deps=[danh_muc_du_lieu],
       description="Tro current.json sang ban moi (doi ten nguyen tu). App tu doc ban moi o lan tai trang sau; ban truoc giu lai de quay lui.")
def kho_phat_hanh(context: AssetExecutionContext) -> MaterializeResult:
    db = _release_path(context)
    info = release.publish(db, note=f"dagster run {context.run.run_id[:8]}")
    return MaterializeResult(metadata={"dang_dung": info["current"], "ban_truoc": str(info["previous"]),
                                       "quay_lui": MetadataValue.md("`python -m src.pipeline.release rollback`")})


# ---------------------------------------------------------------- Lop trinh bay (Power BI)
@asset(group_name="phat_hanh", deps=[kho_phat_hanh],
       description="Xuat cac bang Gold (dim, fact, mart.kpi_monthly, de xuat DSS) cua ban dang dung ra Parquet cho mo hinh Power BI trong powerbi/.")
def xuat_parquet(context: AssetExecutionContext) -> MaterializeResult:
    from src.pipeline import powerbi_export
    start = time.time()
    info = powerbi_export.export(current_db())
    rows = "| Bảng | Số dòng |\n|---|---:|\n" + "\n".join(f"| {k} | {v:,} |" for k, v in info["rows"].items())
    return MaterializeResult(metadata={"ban_phat_hanh": info["release"], "thu_muc": info["out_dir"], "as_of": info["as_of"],
                                       "thoi_gian_s": round(time.time() - start, 1), "so_dong": MetadataValue.md(rows)})


dung_lai_toan_bo = define_asset_job("dung_lai_toan_bo", selection=AssetSelection.all(),
                                    description="Kiem tra nguon, nap 26 dot, DSS, catalog, test, phat hanh, roi xuat Parquet cho Power BI.")
chay_lai_dss = define_asset_job("chay_lai_dss", selection=AssetSelection.assets(dss_khuyen_nghi, danh_muc_du_lieu, kho_phat_hanh, xuat_parquet),
                                description="Giu nguyen kho, chi tinh lai DSS (vi du sau khi doi tham so), test roi phat hanh.")
xuat_power_bi = define_asset_job("xuat_power_bi", selection=AssetSelection.assets(xuat_parquet),
                                 description="Chi xuat lai Parquet tu ban dang dung cho Power BI.")

defs = Definitions(
    assets=[nguon_csv, kho_du_lieu, dss_khuyen_nghi, danh_muc_du_lieu, kho_phat_hanh, xuat_parquet],
    asset_checks=[doi_soat_cac_lop, bat_thuong_du_lieu, kiem_thu_he_thong, lakehouse_va_dbt],
    jobs=[dung_lai_toan_bo, chay_lai_dss, xuat_power_bi],
    # Lam moi kho hang ngay luc 2 gio sang (muc bao tri kho, chuong 3). Mac dinh tat, bat trong giao dien Dagster.
    schedules=[ScheduleDefinition(job=dung_lai_toan_bo, cron_schedule="0 2 * * *", execution_timezone="Asia/Ho_Chi_Minh",
                                  default_status=DefaultScheduleStatus.STOPPED)],
)
