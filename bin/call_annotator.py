#!/usr/bin/env python3
"""
call_annotator.py
-----------------
Calls the BiodivPortal Annotator REST API for a single text string and writes
the result as a JSON file.

The BiodivPortal Annotator is built on the OntoPortal framework. Its endpoint is:
    GET /annotator?text=<text>&apikey=<key>&ontologies=<ids>

Documentation: https://biodivportal.gfbio.org/
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request
import urllib.error


def call_annotator(base_url: str, text: str, apikey: str, ontologies: str) -> dict:
    """
    Call the BiodivPortal annotator endpoint and return the parsed JSON response.
    """
    params = {"text": text}
    if apikey:
        params["apikey"] = apikey
    if ontologies:
        params["ontologies"] = ontologies

    url = f"{base_url.rstrip('/')}/annotator?" + urllib.parse.urlencode(params)

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[ERROR] BiodivPortal HTTP {e.code}: {body}", file=sys.stderr)
        # Return a structured error so the workflow can continue
        return {
            "error": True,
            "status_code": e.code,
            "message": body,
            "annotations": [],
        }
    except urllib.error.URLError as e:
        print(f"[ERROR] BiodivPortal connection error: {e.reason}", file=sys.stderr)
        return {
            "error": True,
            "message": str(e.reason),
            "annotations": [],
        }


def extract_summary(raw_annotations: list) -> list:
    """
    Flatten the raw OntoPortal annotation list into a simpler summary format.
    Each item in the output has:
      - class_id:   the ontology class URI
      - label:      preferred label (if available)
      - ontology:   ontology acronym
      - matched_text: the text span that triggered the annotation
    """
    summary = []
    for annotation in raw_annotations:
        annotated_class = annotation.get("annotatedClass", {})
        links = annotated_class.get("links", {})
        ontology_link = links.get("ontology", "")
        # Extract ontology acronym from the URL (last path segment)
        ontology = ontology_link.rstrip("/").split("/")[-1] if ontology_link else ""

        text_annotations = annotation.get("annotations", [])
        matched_texts = [a.get("text", "") for a in text_annotations]

        summary.append(
            {
                "class_id": annotated_class.get("@id", ""),
                "label": annotated_class.get("prefLabel", ""),
                "ontology": ontology,
                "matched_texts": matched_texts,
            }
        )
    return summary


def main():
    parser = argparse.ArgumentParser(description="Call the BiodivPortal Annotator API")
    parser.add_argument("--id",         required=True,  help="Record identifier")
    parser.add_argument("--text",       required=True,  help="Text to annotate")
    parser.add_argument("--url",        required=True,  help="Base URL of the BiodivPortal")
    parser.add_argument("--apikey",     default="",     help="BiodivPortal API key")
    parser.add_argument("--ontologies", default="",     help="Comma-separated ontology IDs to restrict to")
    parser.add_argument("--output",     required=True,  help="Output JSON file path")
    args = parser.parse_args()

    print(f"[INFO] Annotating record '{args.id}' via BiodivPortal...", file=sys.stderr)

    raw = call_annotator(args.url, args.text, args.apikey, args.ontologies)

    # If the response is a list (normal OntoPortal response), extract summary
    if isinstance(raw, list):
        result = {
            "id": args.id,
            "text": args.text,
            "error": False,
            "annotation_count": len(raw),
            "annotations": extract_summary(raw),
        }
    else:
        # Error dict returned from call_annotator
        result = {
            "id": args.id,
            "text": args.text,
            **raw,
        }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(
        f"[INFO] Done. Found {result.get('annotation_count', 0)} annotations → {args.output}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
