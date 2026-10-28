"""Run Oracle_Apply_6_Create_Invoice.xaml for every 'GRN Found' row of an Apply test sheet.

usage: python run_apply_grn_rows.py <xlsx> [--rows 2,3] [--date 26-FEB-2026] [--dry]
Results are appended to Apply_Run_Log.csv next to this script (row, unit, invoice, status).
"""
import argparse, csv, datetime, json, os, re, subprocess, sys, openpyxl

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARGS_FILE = os.path.join(os.environ.get("TEMP", "."), "apply_row_args.json")
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Apply_Run_Log.csv")


def ascii_clean(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\x20-\x7e]", " ", str(s or ""))).strip()


def unit_of(ou):
    return ascii_clean(ou).split(" ")[0]


ap = argparse.ArgumentParser()
ap.add_argument("xlsx")
ap.add_argument("--rows", default="")
ap.add_argument("--date", default="26-FEB-2026")
ap.add_argument("--dry", action="store_true")
a = ap.parse_args()

ws = openpyxl.load_workbook(a.xlsx)["Test"]
head = [c.value for c in ws[1]]
col = {h: i for i, h in enumerate(head)}
want = {int(x) for x in a.rows.split(",") if x}

results = []
results = []
for n, r in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
    if r[col["Status"]] != "GRN Found" or (want and n not in want):
        continue
    unit = unit_of(r[col["OU Name"]])
    amount = r[col["Unapplied"]] or r[col["Dr"]]
    args = {
        "Unit": unit, "Invoice_Date": a.date,
        "Trading_Partner": ascii_clean(r[col["Supplier Name"]]),
        "Site_Name": ascii_clean(r[col["Vendor Site Code"]]),
        "Prepayment_Invoice": ascii_clean(r[col["Invoice Num"]]),
        "Invoice_Amount": str(amount), "Currency": ascii_clean(r[col["Invoice Currency Code"]]),
        "Description": ascii_clean(r[col["Description"]]),
        "LC_Number": ascii_clean(r[col["LC_Number"]]),
        "Receipt_Number": ascii_clean(r[col["Receipt_Number"]]),
        "Supplier_Name": ascii_clean(r[col["Company"]]),
    }
    cmd = ["uip.cmd", "rpa", "run", "--file-path", "Oracle/Apply/Oracle_Apply_6_Create_Invoice.xaml",
           "--project-dir", PROJ, "--input-arguments-file", ARGS_FILE]
    json.dump({**args, "Open_Batch": True}, open(ARGS_FILE, "w", encoding="utf-8"))
    print(f"row {n}: {unit} {args['Prepayment_Invoice']} {args['Supplier_Name']} {amount}")
    if a.dry:
        continue
    p = subprocess.run(cmd, cwd=PROJ, capture_output=True, text=True, encoding="utf-8")
    out = p.stdout + p.stderr
    if "not supported in the current execution state" in out:
        print("Studio is busy (execution state not idle); stopping without recording")
        break
    done = re.search(r"Create invoice done \| Unit=[^|]*\| New=([^|]*)\| ([^\"\\]*)", out)
    err = re.search(r"System\.Exception: ([^\\\"]*)", out)
    new_inv = ""
    if done:
        new_inv, status = done.group(1).strip(), done.group(2).strip()
    elif err:
        status = "Failed: " + err.group(1).strip()
    else:
        status = "Failed: see run output"
    print("   ->", status, flush=True)
    results.append({"Row": n, "Unit": unit, "Prepayment": args["Prepayment_Invoice"], "Supplier": args["Supplier_Name"],
                    "New_Invoice": new_inv, "Amount": amount, "GRN": args["Receipt_Number"], "Result": status,
                    "Run_At": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

if results and not a.dry:
    wb = openpyxl.load_workbook(a.xlsx)
    sh = "Apply_Report"
    if sh not in wb.sheetnames:
        wb.create_sheet(sh).append(list(results[0].keys()))
    for r in results:
        wb[sh].append(list(r.values()))
    wb.save(a.xlsx)
    print("report written to sheet", sh)
