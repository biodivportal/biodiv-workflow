#!/usr/bin/env python3
"""
parse_input.py
--------------
Reads the input CSV using Python's csv module (correctly handles quoted fields
containing commas) and writes a simple tab-separated file with three columns:
  id  text_land  text_biodiv

This bypasses Nextflow's splitCsv, which shifts columns when quoted fields
contain commas (e.g. "Schack,H." in the Sammlerteam column).
"""
import argparse
import csv
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",      required=True, help="Input CSV file")
    parser.add_argument("--id-col",     required=True, help="ID column name")
    parser.add_argument("--land-col",   required=True, help="Land text column name")
    parser.add_argument("--biodiv-col", required=True, help="BiodivPortal text column name")
    parser.add_argument("--max-rows",   type=int, default=0, help="Stop after N rows (0=all)")
    parser.add_argument("--output",     required=True, help="Output TSV file")
    args = parser.parse_args()

    written = skipped = 0
    with open(args.input, newline="", encoding="utf-8") as f_in, \
         open(args.output, "w", newline="", encoding="utf-8") as f_out:

        reader = csv.DictReader(f_in)
        f_out.write("id\ttext_land\ttext_biodiv\n")

        for row in reader:
            id_val = row.get(args.id_col, "").strip()
            if not id_val:
                skipped += 1
                continue

            land   = row.get(args.land_col,   "").strip().replace("\t", " ")
            biodiv = row.get(args.biodiv_col, "").strip().replace("\t", " ")

            f_out.write(f"{id_val}\t{land}\t{biodiv}\n")
            written += 1

            if args.max_rows and written >= args.max_rows:
                break

    print(f"[INFO] {written} records written, {skipped} skipped → {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
