#!/usr/bin/env python3
"""
merge_results.py
----------------
Reads the original input CSV/TSV and merges the per-row JSON outputs from:
  - BiodivPortal Annotator  (*.biodiv.json)
  - Land Taxonomy Classifier (*.land.json)

Produces a single enriched CSV with extra columns added to the right of the
original columns.

New columns added:
  biodiv_annotation_count    - number of ontology annotations found
  biodiv_top_classes         - top-3 class labels (semicolon-separated)
  biodiv_top_ontologies      - top-3 ontology acronyms (semicolon-separated)
  land_top_code              - CLC code of the best land cover match
  land_top_name              - name of the best land cover match
  land_top_confidence        - confidence score of the best match (0.0-1.0)
  land_top_reasoning         - brief reasoning from the LLM
  land_all_classifications   - JSON string with all top-k results
  annotation_error           - True if the annotator returned an error
  classification_error       - True if the classifier returned an error
"""

import argparse
import csv
import glob
import json
import os
import sys


def load_json(filepath: str) -> dict:
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[WARN] Could not load {filepath}: {e}", file=sys.stderr)
        return {}


def build_index(directory: str, suffix: str) -> dict:
    """Return a dict mapping record id → filepath for all *.<suffix>.json files."""
    index = {}
    pattern = os.path.join(directory, f"*.{suffix}.json")
    for path in glob.glob(pattern):
        basename = os.path.basename(path)
        record_id = basename[: -(len(suffix) + 6)]  # strip .<suffix>.json
        index[record_id] = path
    return index


def summarise_biodiv(data: dict) -> dict:
    annotations = data.get("annotations", [])
    top = annotations[:3]
    return {
        "biodiv_annotation_count": data.get("annotation_count", len(annotations)),
        "biodiv_top_classes":      "; ".join(a.get("label", a.get("class_id", "")) for a in top),
        "biodiv_top_ontologies":   "; ".join(a.get("ontology", "") for a in top),
        "annotation_error":        str(data.get("error", False)),
    }


def summarise_land(data: dict) -> dict:
    matches = data.get("matches", data.get("results", []))
    if not matches:
        return {
            "land_top_code":            "",
            "land_top_name":            "",
            "land_top_confidence":      "",
            "land_top_reasoning":       "",
            "land_all_classifications": "[]",
            "classification_error":     str(data.get("error", True)),
        }
    best = matches[0]
    # The classifier returns nested level1/level2/level3; use level3 (most specific)
    level3 = best.get("level3", {})
    level2 = best.get("level2", {})
    top_level = level3 if level3 else level2
    return {
        "land_top_code":            top_level.get("clc_code", ""),
        "land_top_name":            top_level.get("english_name", top_level.get("name", "")),
        "land_top_confidence":      str(best.get("confidence", "")),
        "land_top_reasoning":       best.get("reason", best.get("reasoning", "")),
        "land_all_classifications": json.dumps(matches, ensure_ascii=False),
        "classification_error":     str(data.get("error", False)),
    }


def main():
    parser = argparse.ArgumentParser(description="Merge per-row JSON results into enriched CSV")
    parser.add_argument("--input",      required=True, help="Original input CSV/TSV")
    parser.add_argument("--sep",        default=",",   help="Separator (default: ,)")
    parser.add_argument("--biodiv-dir", required=True, help="Directory containing *.biodiv.json files")
    parser.add_argument("--land-dir",   required=True, help="Directory containing *.land.json files")
    parser.add_argument("--id-column",  default="id",  help="Name of the ID column")
    parser.add_argument("--max-rows",   type=int, default=0, help="Only process the first N data rows (0 = all)")
    parser.add_argument("--output",     required=True, help="Output enriched CSV path")
    args = parser.parse_args()

    sep = "\t" if args.sep in ("\\t", "\t") else args.sep

    biodiv_index = build_index(args.biodiv_dir, "biodiv")
    land_index   = build_index(args.land_dir,   "land")

    print(
        f"[INFO] Found {len(biodiv_index)} biodiv files, {len(land_index)} land files",
        file=sys.stderr,
    )

    enriched_rows = []
    fieldnames = None

    with open(args.input, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=sep)
        for row_num, row in enumerate(reader):
            if args.max_rows and row_num >= args.max_rows:
                break
            record_id = row.get(args.id_column, "")

            # Load and summarise biodiv annotations
            biodiv_path = biodiv_index.get(record_id, "")
            biodiv_data = load_json(biodiv_path) if biodiv_path else {}
            biodiv_cols = summarise_biodiv(biodiv_data)

            # Load and summarise land classifications
            land_path = land_index.get(record_id, "")
            land_data  = load_json(land_path) if land_path else {}
            land_cols  = summarise_land(land_data)

            enriched = {**row, **biodiv_cols, **land_cols}
            enriched_rows.append(enriched)

            if fieldnames is None:
                fieldnames = list(enriched.keys())

    if not enriched_rows:
        print("[ERROR] No rows processed. Check your input file and ID column name.", file=sys.stderr)
        sys.exit(1)

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched_rows)

    print(
        f"[INFO] Written {len(enriched_rows)} enriched rows → {args.output}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
