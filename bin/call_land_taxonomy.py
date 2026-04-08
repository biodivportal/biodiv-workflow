#!/usr/bin/env python3
"""
call_land_taxonomy.py
---------------------
Calls the local Land Taxonomy Classifier FastAPI service for a single text string
and writes the result as a JSON file.

The classifier service must be running locally (see INSTALL.md, Step 7).
Default endpoint: POST http://127.0.0.1:8000/classify

GitHub: https://github.com/biodivportal/land-taxonomy-classifier
"""

import argparse
import json
import sys
import urllib.request
import urllib.error


def call_land_classifier(base_url: str, text: str, top_k: int, model: str) -> dict:
    """
    POST to the /classify endpoint of the land-taxonomy-classifier service.
    Returns the parsed JSON response.
    """
    url = f"{base_url.rstrip('/')}/classify"
    payload = json.dumps(
        {"text": text, "top_k": top_k, "model": model}
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[ERROR] Land Classifier HTTP {e.code}: {body}", file=sys.stderr)
        return {
            "error": True,
            "status_code": e.code,
            "message": body,
            "results": [],
        }
    except urllib.error.URLError as e:
        print(
            f"[ERROR] Could not connect to land classifier at {url}: {e.reason}",
            file=sys.stderr,
        )
        print(
            "[ERROR] Make sure the service is running: uvicorn main:app --host 0.0.0.0 --port 8000",
            file=sys.stderr,
        )
        return {
            "error": True,
            "message": str(e.reason),
            "results": [],
        }


def main():
    parser = argparse.ArgumentParser(
        description="Call the local Land Taxonomy Classifier service"
    )
    parser.add_argument("--id",      required=True,               help="Record identifier")
    parser.add_argument("--text",    required=True,               help="Text to classify")
    parser.add_argument("--url",     default="http://127.0.0.1:8000", help="Base URL of the classifier")
    parser.add_argument("--top-k",   type=int, default=5,         help="Number of top results to return")
    parser.add_argument("--model",   default="gpt-4o-mini",       help="OpenAI model to use")
    parser.add_argument("--output",  required=True,               help="Output JSON file path")
    args = parser.parse_args()

    print(
        f"[INFO] Classifying record '{args.id}' via land-taxonomy-classifier...",
        file=sys.stderr,
    )

    raw = call_land_classifier(args.url, args.text, args.top_k, args.model)

    # Wrap in a standard envelope
    result = {
        "id": args.id,
        "text": args.text,
        "error": raw.get("error", False),
        **raw,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    if raw.get("error"):
        print(f"[WARN] Classification failed for '{args.id}': {raw.get('message','')}", file=sys.stderr)
    else:
        n = len(raw.get("results", []))
        print(f"[INFO] Done. Got {n} classifications → {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
