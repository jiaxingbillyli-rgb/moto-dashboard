"""
Dashboard HTTP server with monthly Excel upload support.

Serves static dashboard files AND provides a POST /upload endpoint that:
  1. Receives a monthly report Excel file (全国摩托车生产企业产销情况月报)
  2. Parses it (summary / manufacturer / manufacturer×displacement / export)
  3. Appends/updates the data CSVs
  4. Re-runs aggregation to refresh dashboard_data.json

Run:  python server.py 8765
"""

import csv
import json
import os
import re
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import openpyxl
import xlrd
import warnings

warnings.filterwarnings("ignore")

# 兼容 pythonw.exe（无窗口版）：此时 sys.stdout / sys.stderr 为 None，
# 任何 print() / 日志输出都会抛 AttributeError 导致服务器崩溃。
# 将其重定向到 null 设备，保证服务器可正常服务。
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# Import extraction functions from sibling scripts
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from extract_data import (
    normalize_name, is_duplicate_row, parse_year_month_from_filename,
    find_sheet, detect_era, extract_summary_sheet,
    extract_manufacturer_old, extract_manufacturer_new,
    VEHICLE_TYPES,
)
from extract_displacement import (
    extract_era_a as disp_extract_era_a,
    extract_era_b as disp_extract_era_b,
)
from extract_export import (
    extract_era_a as export_extract_era_a,
    extract_era_b as export_extract_era_b,
    extract_era_b_xls as export_extract_era_b_xls,
)

OUT = Path(__file__).parent / "output"
SCRIPTS = Path(__file__).parent / "scripts"
UPLOADS = OUT / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)

# Fields for each CSV
SUMMARY_FIELDS = ["year", "month", "indicator", "scope", "category", "type", "value"]
MANUFACTURER_FIELDS = ["year", "month", "manufacturer", "indicator", "value"]
MFG_DISP_FIELDS = ["year", "month", "manufacturer", "scope", "category", "indicator", "value"]
EXPORT_FIELDS = ["year", "month", "scope", "category", "type", "value"]
EXPORT_AMOUNT_FIELDS = ["year", "month", "amount"]
EXPORT_MFG_FIELDS = ["year", "month", "manufacturer", "value"]


def parse_single_excel(path, year, month):
    """Parse a single monthly report Excel into the four data tables.
    Returns dict with keys: summary, manufacturer, mfg_displacement, export, export_amount, export_mfg."""
    result = {
        "summary": [], "manufacturer": [], "mfg_displacement": [],
        "export": [], "export_amount": [], "export_mfg": [],
    }
    path = Path(path)

    if path.suffix.lower() == ".xls":
        wb = xlrd.open_workbook(str(path))
        _parse_xls(wb, year, month, result)
    else:
        wb = openpyxl.load_workbook(str(path), data_only=True)
        era = detect_era(wb)
        if era is None:
            raise ValueError("无法识别报表格式（未找到生产/销售汇总表）")
        # --- summary + manufacturer ---
        if era == "A":
            prod_sheet = find_sheet(wb, ["摩托车生产企业生产情况汇总表"])
            sales_sheet = find_sheet(wb, ["摩托车生产企业销售情况汇总表"])
            if not prod_sheet or not sales_sheet:
                raise ValueError("未找到生产/销售情况汇总表")
            result["summary"].extend(extract_summary_sheet(wb[prod_sheet], year, month, "生产"))
            result["summary"].extend(extract_summary_sheet(wb[sales_sheet], year, month, "销售"))
            result["manufacturer"].extend(extract_manufacturer_old(wb, year, month))
        else:
            prod_sheet = find_sheet(wb, ["生产汇总表"])
            sales_sheet = find_sheet(wb, ["销售汇总表"])
            if not prod_sheet or not sales_sheet:
                raise ValueError("未找到生产/销售汇总表")
            result["summary"].extend(extract_summary_sheet(wb[prod_sheet], year, month, "生产"))
            result["summary"].extend(extract_summary_sheet(wb[sales_sheet], year, month, "销售"))
            mfr_sheet = find_sheet(wb, ["企业产销情况表（合并）", "企业产销（合并）", "企业产销情况表"])
            if mfr_sheet:
                result["manufacturer"].extend(extract_manufacturer_new(wb[mfr_sheet], year, month))

        # --- manufacturer × displacement ---
        if era == "A":
            for sheet_name, indicator in [
                (find_sheet(wb, ["摩托车生产企业生产情况表"]), "生产"),
                (find_sheet(wb, ["摩托车生产企业销售情况表"]), "销售"),
            ]:
                if sheet_name:
                    result["mfg_displacement"].extend(disp_extract_era_a(wb[sheet_name], year, month, indicator))
        else:
            mfr_disp_sheet = find_sheet(wb, ["企业产销情况表（合并）", "企业产销（合并）", "企业产销情况表"])
            if mfr_disp_sheet:
                result["mfg_displacement"].extend(
                    disp_extract_era_b(wb[mfr_disp_sheet], year, month, wb[mfr_disp_sheet].iter_rows(values_only=True)))

        # --- export ---
        if era == "A":
            exp_rows, amount, mfg_rows = export_extract_era_a(wb, year, month)
        else:
            exp_rows, amount, mfg_rows = export_extract_era_b(wb, year, month)
        result["export"].extend(exp_rows)
        if amount is not None:
            result["export_amount"].append({"year": year, "month": month, "amount": amount})
        result["export_mfg"].extend(mfg_rows)

    return result


def _parse_xls(wb, year, month, result):
    """Parse legacy .xls format (Era B only)."""
    era = "B" if any("生产汇总表" in s.name for s in wb.sheets()) else "A"
    if era == "A":
        raise ValueError("暂不支持旧版 .xls 的 Era A 格式，请使用 .xlsx")
    # summary + manufacturer + displacement + export via Era B logic
    from extract_data import extract_combined_manufacturer
    for sheet in wb.sheets():
        name = sheet.name
        if name in ("生产汇总表", "销售汇总表"):
            indicator = "生产" if "生产" in name else "销售"
            for r in range(sheet.nrows):
                row0 = sheet.cell_value(r, 0)
                if not row0:
                    continue
                row_name = normalize_name(row0)
                if not row_name:
                    continue
                v = sheet.cell_value(r, 1)
                if not isinstance(v, (int, float)):
                    continue
                if row_name in VEHICLE_TYPES:
                    result["summary"].append({"year": year, "month": month, "indicator": indicator,
                        "scope": "二轮", "category": row_name.replace("摩托车", ""), "type": "车型", "value": float(v)})
                elif row_name in ("正三轮摩托车", "边三轮摩托车"):
                    result["summary"].append({"year": year, "month": month, "indicator": indicator,
                        "scope": "三轮", "category": row_name.replace("摩托车", ""), "type": "车型", "value": float(v)})
                elif row_name in ("摩托车总计", "一、二轮摩托车合计", "二、三轮摩托车合计"):
                    scope = "总计" if row_name == "摩托车总计" else ("二轮" if "二轮" in row_name else "三轮")
                    result["summary"].append({"year": year, "month": month, "indicator": indicator,
                        "scope": scope, "category": scope, "type": "汇总", "value": float(v)})
        elif "企业产销" in name or "企业生产" in name or "企业销售" in name:
            def rows_iter():
                for r in range(sheet.nrows):
                    yield [sheet.cell_value(r, c) for c in range(sheet.ncols)]
            result["manufacturer"].extend(extract_combined_manufacturer(rows_iter(), year, month))

    exp_rows, amount, mfg_rows = export_extract_era_b_xls(wb, year, month)
    result["export"].extend(exp_rows)
    if amount is not None:
        result["export_amount"].append({"year": year, "month": month, "amount": amount})
    result["export_mfg"].extend(mfg_rows)


def merge_csv_rows(existing_path, new_rows, fields, dedup_key):
    """Append new_rows to existing CSV, dedup by dedup_key (tuple of field names)."""
    existing = []
    if existing_path.exists():
        with open(existing_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            existing = list(reader)

    seen = set()
    for r in existing:
        seen.add(tuple(str(r.get(k, "")) for k in dedup_key))

    added = 0
    for r in new_rows:
        key = tuple(str(r.get(k, "")) for k in dedup_key)
        if key not in seen:
            existing.append(r)
            seen.add(key)
            added += 1

    with open(existing_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(existing)
    return added


def run_aggregation():
    """Re-run aggregate_dashboard.py to refresh dashboard_data.json."""
    import subprocess
    py = sys.executable
    r = subprocess.run([py, str(SCRIPTS / "aggregate_dashboard.py")],
                       capture_output=True, text=True, cwd=str(SCRIPTS))
    if r.returncode != 0:
        raise RuntimeError(f"聚合失败: {r.stderr[-500:]}")
    return r.stdout


def process_upload(filepath, filename):
    """Process an uploaded Excel file: parse and update all data."""
    # Parse year/month from filename
    y, m = parse_year_month_from_filename(filename)
    if y is None:
        # Try to infer from content later; for now require filename pattern
        raise ValueError("无法从文件名识别年月，请保持文件名格式如「2026年7月...月报.xlsx」")

    # Parse
    data = parse_single_excel(filepath, y, m)

    # Validate we actually got data
    if not data["summary"]:
        raise ValueError("解析失败：未从文件中提取到汇总数据，请确认文件是「全国摩托车生产企业产销情况月报」")

    # Merge into CSVs
    summary_added = merge_csv_rows(OUT / "monthly_summary_full.csv", data["summary"],
                                   SUMMARY_FIELDS, ["year", "month", "indicator", "scope", "category", "type"])
    mfr_added = merge_csv_rows(OUT / "monthly_manufacturer.csv", data["manufacturer"],
                               MANUFACTURER_FIELDS, ["year", "month", "manufacturer", "indicator"])
    mfg_disp_added = merge_csv_rows(OUT / "monthly_manufacturer_displacement.csv", data["mfg_displacement"],
                                    MFG_DISP_FIELDS, ["year", "month", "manufacturer", "scope", "category", "indicator"])
    export_added = merge_csv_rows(OUT / "monthly_export.csv", data["export"],
                                  EXPORT_FIELDS, ["year", "month", "scope", "category", "type"])
    export_amt_added = merge_csv_rows(OUT / "monthly_export_amount.csv", data["export_amount"],
                                      EXPORT_AMOUNT_FIELDS, ["year", "month"])
    export_mfg_added = merge_csv_rows(OUT / "monthly_export_mfg.csv", data["export_mfg"],
                                      EXPORT_MFG_FIELDS, ["year", "month", "manufacturer"])

    # Re-aggregate
    agg_out = run_aggregation()

    return {
        "year": y, "month": m,
        "summary_rows": len(data["summary"]), "summary_added": summary_added,
        "manufacturer_rows": len(data["manufacturer"]), "manufacturer_added": mfr_added,
        "mfg_disp_rows": len(data["mfg_displacement"]), "mfg_disp_added": mfg_disp_added,
        "export_rows": len(data["export"]), "export_added": export_added,
        "export_amount_added": export_amt_added, "export_mfg_added": export_mfg_added,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "MotoDashboard/1.0"

    def log_message(self, format, *args):
        sys.stdout.write("[%s] %s\n" % (self.log_date_time_string(), format % args))

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, path):
        # Prevent path traversal
        safe = os.path.normpath(path.lstrip("/"))
        full = (OUT / safe).resolve()
        if not str(full).startswith(str(OUT.resolve())):
            self.send_error(403)
            return
        if not full.exists() or not full.is_file():
            self.send_error(404)
            return
        content_type = "text/html"
        if full.suffix == ".js":
            content_type = "application/javascript"
        elif full.suffix == ".json":
            content_type = "application/json"
        elif full.suffix == ".css":
            content_type = "text/css"
        body = full.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            path = "/dashboard.html"
        if path.startswith("/dashboard") or path.endswith(".js") or path.endswith(".json") or path.endswith(".html") or path.endswith(".css"):
            self._serve_static(path)
        else:
            self._serve_static(path)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if self.path.split("?")[0] != "/upload":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0:
                self._send_json({"ok": False, "error": "空请求"}, 400)
                return

            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" in content_type:
                # Parse multipart
                boundary = content_type.split("boundary=")[1].strip()
                body = self.rfile.read(length)
                filename, filedata = parse_multipart(body, boundary)
                if not filename:
                    self._send_json({"ok": False, "error": "未找到上传文件"}, 400)
                    return
            else:
                # Raw body = file bytes; filename from query
                body = self.rfile.read(length)
                filedata = body
                from urllib.parse import urlparse, parse_qs
                q = parse_qs(urlparse(self.path).query)
                filename = q.get("filename", ["monthly_report.xlsx"])[0]

            # Save upload
            safe_name = re.sub(r'[^\w.\-（）()年月]', '_', filename)
            save_path = UPLOADS / safe_name
            save_path.write_bytes(filedata)

            # Process
            result = process_upload(str(save_path), filename)
            self._send_json({"ok": True, "filename": filename, "result": result})

        except Exception as e:
            traceback.print_exc()
            self._send_json({"ok": False, "error": str(e)}, 500)


def parse_multipart(body, boundary):
    """Minimal multipart parser; returns (filename, data)."""
    delim = b"--" + boundary.encode()
    parts = body.split(delim)
    for part in parts:
        if b"Content-Disposition" in part and b"filename=" in part:
            header, _, data = part.partition(b"\r\n\r\n")
            data = data.rstrip(b"\r\n")
            # Extract filename
            m = re.search(rb'filename="([^"]+)"', header)
            if not m:
                m = re.search(rb'filename=([^\s;]+)', header)
            filename = m.group(1).decode("utf-8", "ignore") if m else None
            return filename, data
    return None, b""


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    print(f"Dashboard server running at http://127.0.0.1:{port}/")
    print(f"  Upload endpoint: POST /upload")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
