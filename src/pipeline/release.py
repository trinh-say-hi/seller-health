"""Ban phat hanh kho: dung vao file moi, kiem tra xong moi tro current.json sang. Giu ban truoc de quay lui.

Vi sao khong ghi de: app giu file kho o che do chi doc, va DuckDB khoa file nen tien trinh khac khong mo de ghi duoc
(truoc day phai tat app moi dung lai kho). Ghi de con co nghia dot loi lam hong kho dang dung.
O day kho dang dung chi doi khi ban moi da qua het kiem tra, va doi bang mot lan doi ten file con tro.

Chay: python -m src.pipeline.release status | rollback | cleanup
"""
import datetime as dt
import json
import os
import shutil
import sys
from pathlib import Path

from src.config import POINTER, RELEASES_DIR, current_db

KEEP = 2  # ban dang dung va ban truoc do


def new_release_path(tag: str) -> Path:
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return RELEASES_DIR / f"olist_{stamp}_{tag}.duckdb"


def read_pointer() -> dict:
    try:
        return json.loads(POINTER.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def _write_pointer(data: dict):
    POINTER.parent.mkdir(parents=True, exist_ok=True)
    tmp = POINTER.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, POINTER)  # doi ten nguyen tu: app chi thay con tro cu hoac con tro moi, khong thay file viet do


def publish(path: Path, note: str = "") -> dict:
    """Tro current.json sang ban moi. Chi goi sau khi ban moi da qua doi soat va test."""
    path = Path(path)
    if path.parent.resolve() != RELEASES_DIR.resolve() or not path.exists():
        raise ValueError(f"Ban phat hanh phai nam trong {RELEASES_DIR}: {path}")
    if path.with_name(path.name + ".wal").exists():
        raise ValueError(f"Ban {path.name} con file .wal, chua CHECKPOINT xong")
    old = read_pointer()
    data = {"current": path.name, "previous": old.get("current"), "published_at": dt.datetime.now().isoformat(timespec="seconds"),
            "note": note}
    _write_pointer(data)
    cleanup()
    return data


def rollback() -> dict:
    """Quay ve ban truoc. Ban dang dung tro thanh 'previous' de co the quay lai."""
    old = read_pointer()
    if not old.get("previous") or not (RELEASES_DIR / old["previous"]).exists():
        raise ValueError("Khong co ban truoc de quay lui")
    data = {"current": old["previous"], "previous": old["current"], "published_at": dt.datetime.now().isoformat(timespec="seconds"),
            "note": f"quay lui tu {old['current']}"}
    _write_pointer(data)
    return data


def cleanup(protect: tuple[str, ...] = ()) -> list[str]:
    """Xoa ban cu ngoai ban dang dung va ban truoc. File dang mo (app chua tai lai, hoac pipeline khac dang ghi) thi de lan sau."""
    keep = {v for k, v in read_pointer().items() if k in ("current", "previous") and v} | set(protect)
    removed = []
    for f in sorted(RELEASES_DIR.glob("olist_*.duckdb")):
        if f.name in keep:
            continue
        try:
            f.unlink()
            wal = f.with_name(f.name + ".wal")
            if wal.exists():
                wal.unlink()
            removed.append(f.name)
        except OSError:
            pass
    return removed


def seed_from_current(target: Path) -> Path:
    """Chep kho dang dung sang ban moi, de chay lai rieng DSS hay catalog ma khong phai nap lai 26 dot."""
    src = current_db()
    if not src.exists():
        raise FileNotFoundError(f"Chua co kho de chep: {src}. Chay toan bo pipeline truoc.")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, target)
    return src


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "rollback":
        print(json.dumps(rollback(), indent=1, ensure_ascii=False))
    elif cmd == "cleanup":
        print("Da xoa:", cleanup() or "khong co")
    else:
        print(json.dumps(read_pointer() or {"current": None}, indent=1, ensure_ascii=False))
        print("Kho dang dung:", current_db())
        for f in sorted(RELEASES_DIR.glob("olist_*.duckdb")):
            print(f"  {f.name}  {f.stat().st_size / 1e6:.0f} MB")
