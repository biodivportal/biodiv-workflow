#!/usr/bin/env python3
"""
convert_xlsx.py
---------------
Converts Belege_aus_D source files into a flat CSV ready for the biodiv-workflow
pipeline.  Two input formats are supported:

  .xlsx  — Excel file where every row stores its data as a CSV string in cell A1
           (the original Belege_aus_D.csv.xlsx format)

  .csv   — Semicolon-delimited CSV where every row stores its data as a quoted
           CSV string in the first column, remaining columns empty
           (the Belege_aus_D_2.csv format)

Both formats share the same 23-column inner schema:
  HerbariumID, Bild, DB, Family, FullNameCache, Anmerkungen, Sammlerteam,
  Sammelnummer, CollectionDateBegin, CollectionDateEnd, Country, Locality,
  TitelEtikett, Expeditionsangabe, ShowOnMap, Latitude, Longitude,
  FundortUNdOeko, NameCache, Genus, Identifier, Barcode, StableURI

Output columns:
  id            — HerbariumID
  text_land     — FundortUNdOeko if non-empty, else Locality  (for Land Taxonomy)
  text_biodiv   — FullNameCache                               (for BiodivPortal)
  locality      — Locality (raw)
  fundort       — FundortUNdOeko (raw)
  species       — FullNameCache (raw)
  family        — Family
  country       — Country
  latitude      — Latitude
  longitude     — Longitude
  barcode       — Barcode
  stable_uri    — StableURI

Usage:
    python bin/convert_xlsx.py \\
        --input  assets/Belege_aus_D_2.csv \\
        --output assets/Belege_aus_D.csv \\
        [--skip-empty-land] \\
        [--max-rows 1000]
"""

import argparse
import csv
import sys

OUTPUT_COLUMNS = [
    "id", "text_land", "text_biodiv",
    "locality", "fundort", "species",
    "family", "country", "latitude", "longitude",
    "barcode", "stable_uri",
]


def iter_raw_lines_csv(filepath: str):
    """
    Yield the CSV-string content of column 1 from a semicolon-delimited file.
    Each cell may be quoted; the inner content is itself a CSV-formatted string.
    """
    with open(filepath, newline="", encoding="latin-1") as f:
        reader = csv.reader(f, delimiter=";")
        for row in reader:
            if row:
                yield row[0]


def iter_raw_lines_xlsx(filepath: str):
    """Yield cell A values row by row from an xlsx workbook."""
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
    """Parse the inner CSV string and return a dict keyed by column name."""
    if not raw_line.strip():
        return None
    try:
        values = list(csv.reader([raw_line]))[0]
    except Exception:
        return None
    return {h: (values[i].strip() if i < len(values) else "") for i, h in enumerate(headers)}


def build_text_land(row: dict) -> str:
    """FundortUNdOeko preferred; fall back to Locality."""
    return row.get("FundortUNdOeko", "").strip() or row.get("Locality", "").strip()


def main():
    parser = argparse.ArgumentParser(
        description="Convert Belege_aus_D source file to a pipeline-ready CSV"
    )
    parser.add_argument("--input",  required=True, help="Path to .xlsx or .csv source file")
    parser.add_argument("--output", required=True, help="Path for the output CSV")
    parser.add_argument(
        "--skip-empty-land",
        action="store_true",
        help="Skip rows where both Locality and FundortUNdOeko are empty",
    )
    parser.add_argument(
        "--max-rows", type=int, default=0,
        help="Stop after this many output rows (0 = all)",
    )
    args = parser.parse_args()

    print(f"[INFO] Opening {args.input} ...", file=sys.stderr)

    is_xlsx = args.input.lower().endswith((".xlsx", ".xlsm"))
    raw_lines = iter_raw_lines_xlsx(args.input) if is_xlsx else iter_raw_lines_csv(args.input)

    # --- Parse header from first line ---
    header_raw = next(raw_lines, None)
    if not header_raw:
        sys.exit("[ERROR] Could not read header row")
    headers = list(csv.reader([header_raw]))[0]
    headers = [h.strip() for h in headers]
    print(f"[INFO] Detected {len(headers)} columns: {headers}", file=sys.stderr)

    required = {"HerbariumID", "Locality", "FundortUNdOeko", "FullNameCache"}
    missing = required - set(headers)
    if missing:
        sys.exit(f"[ERROR] Missing expected columns: {missing}")

    written = skipped = 0

    with open(args.output, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()

        for raw in raw_lines:
            row = parse_inner_csv(raw, headers)
            if row is None:
                skipped += 1
                continue

            text_land = build_text_land(row)
            if not text_land and args.skip_empty_land:
                skipped += 1
                continue

            writer.writerow({
                "id":          row.get("HerbariumID", ""),
                "text_land":   text_land,
                "text_biodiv": row.get("FullNameCache", "").strip(),
                "locality":    row.get("Locality", "").strip(),
                "fundort":     row.get("FundortUNdOeko", "").strip(),
                "species":     row.get("FullNameCache", "").strip(),
                "family":      row.get("Family", "").strip(),
                "country":     row.get("Country", "").strip(),
                "latitude":    row.get("Latitude", "").strip(),
                "longitude":   row.get("Longitude", "").strip(),
                "barcode":     row.get("Barcode", "").strip(),
                "stable_uri":  row.get("StableURI", "").strip(),
            })
            written += 1

            if written % 10000 == 0:
                print(f"[INFO]  ... {written:,} rows written", file=sys.stderr)

            if args.max_rows and written >= args.max_rows:
                print(f"[INFO] Reached --max-rows {args.max_rows}, stopping early.", file=sys.stderr)
                break

    print(
        f"[INFO] Done. {written:,} rows written, {skipped:,} skipped → {args.output}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
