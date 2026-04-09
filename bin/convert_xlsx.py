#!/usr/bin/env python3
"""
convert_xlsx.py
---------------
Converts Belege_aus_D source files into a flat CSV ready for the biodiv-workflow
pipeline.  Two input formats are supported:

  .xlsx  — Excel file where every row stores its data as a CSV string in cell A1
  .csv   — Semicolon-delimited CSV where data is packed as a CSV string in column 1
           (Belege_aus_D_2.csv format)

The output CSV preserves all original column names from the source:
  HerbariumID, Bild, DB, Family, FullNameCache, Anmerkungen, Sammlerteam,
  Sammelnummer, CollectionDateBegin, CollectionDateEnd, Country, Locality,
  TitelEtikett, Expeditionsangabe, ShowOnMap, Latitude, Longitude,
  FundortUNdOeko, NameCache, Genus, Identifier, Barcode, StableURI

Usage:
    python bin/convert_xlsx.py \\
        --input  assets/Belege_aus_D_2.csv \\
        --output assets/Belege_aus_D.csv \\
        [--max-rows 20]
"""

import argparse
import csv
import sys


def iter_raw_lines_csv(filepath: str):
    with open(filepath, newline="", encoding="latin-1") as f:
        reader = csv.reader(f, delimiter=";")
        for row in reader:
            if row:
                yield row[0]


def iter_raw_lines_xlsx(filepath: str):
    try:
        import openpyxl
    except ImportError:
        sys.exit("[ERROR] openpyxl is required for xlsx input: pip install openpyxl")
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    ws = wb.active
    for row in ws.iter_rows(max_col=1, values_only=True):
        if row[0] is not None:
            yield str(row[0])
    wb.close()


def parse_inner_csv(raw_line: str, headers: list) -> dict | None:
    if not raw_line.strip():
        return None
    try:
        values = list(csv.reader([raw_line]))[0]
    except Exception:
        return None
    return {h: (values[i].strip() if i < len(values) else "") for i, h in enumerate(headers)}


def main():
    parser = argparse.ArgumentParser(
        description="Convert Belege_aus_D source file to a pipeline-ready flat CSV"
    )
    parser.add_argument("--input",    required=True, help="Path to .xlsx or .csv source file")
    parser.add_argument("--output",   required=True, help="Path for the output CSV")
    parser.add_argument("--max-rows", type=int, default=0,
                        help="Stop after this many rows (0 = all)")
    args = parser.parse_args()

    print(f"[INFO] Opening {args.input} ...", file=sys.stderr)

    is_xlsx  = args.input.lower().endswith((".xlsx", ".xlsm"))
    raw_lines = iter_raw_lines_xlsx(args.input) if is_xlsx else iter_raw_lines_csv(args.input)

    header_raw = next(raw_lines, None)
    if not header_raw:
        sys.exit("[ERROR] Could not read header row")
    headers = [h.strip() for h in list(csv.reader([header_raw]))[0]]
    print(f"[INFO] Detected {len(headers)} columns: {headers}", file=sys.stderr)

    written = 0

    with open(args.output, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=headers)
        writer.writeheader()

        for raw in raw_lines:
            row = parse_inner_csv(raw, headers)
            if row is None:
                continue

            writer.writerow(row)
            written += 1

            if written % 10000 == 0:
                print(f"[INFO]  ... {written:,} rows written", file=sys.stderr)

            if args.max_rows and written >= args.max_rows:
                print(f"[INFO] Reached --max-rows {args.max_rows}, stopping early.", file=sys.stderr)
                break

    print(f"[INFO] Done. {written:,} rows written → {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
