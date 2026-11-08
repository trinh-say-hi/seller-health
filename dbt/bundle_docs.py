"""
Script đóng gói dbt docs (index.html + manifest.json + catalog.json)
thành một file HTML duy nhất (Standalone Lineage Viewer)
giúp xem Interactive Lineage DAG trực tiếp offline mà không bị lỗi CORS của trình duyệt.
"""
from pathlib import Path

def bundle_docs():
    target_dir = Path(__file__).resolve().parent / "target"
    index_file = target_dir / "index.html"
    manifest_file = target_dir / "manifest.json"
    catalog_file = target_dir / "catalog.json"
    output_file = target_dir / "lineage_standalone.html"

    if not index_file.exists() or not manifest_file.exists():
        raise FileNotFoundError("Chưa tìm thấy target/index.html hoặc target/manifest.json. Hãy chạy dbt docs generate trước.")

    html = index_file.read_text(encoding="utf-8")
    manifest_str = manifest_file.read_text(encoding="utf-8")
    catalog_str = catalog_file.read_text(encoding="utf-8") if catalog_file.exists() else "{}"

    target_pattern = 'n=[o("manifest","manifest.json"+t),o("catalog","catalog.json"+t)]'
    replacement = 'n=[e.when({label:"manifest",data:window.dbt_manifest}),e.when({label:"catalog",data:window.dbt_catalog})]'

    if target_pattern in html:
        html = html.replace(target_pattern, replacement)
        script_inject = f'<script type="text/javascript">window.dbt_manifest = {manifest_str}; window.dbt_catalog = {catalog_str};</script>'
        html = html.replace('</head>', script_inject + '</head>')
        output_file.write_text(html, encoding="utf-8")
        print(f"[OK] Successfully created standalone lineage DAG: {output_file} ({output_file.stat().st_size / (1024*1024):.2f} MB)")
        return output_file
    else:
        print("[WARN] Target string not found in index.html.")
        return None

if __name__ == "__main__":
    bundle_docs()
