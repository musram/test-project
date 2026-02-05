import json, os, sys
from typing import Any, Dict, List, Tuple, Optional

def is_envelope(x: Any) -> bool:
    return isinstance(x, dict) and isinstance(x.get("success"), bool) and ("result" in x)

def unwrap_envelope(x: Any) -> Any:
    # Unwrap one layer of {success,result,...}
    if is_envelope(x):
        return x.get("result")
    return x

def extract_records(fetch_ctx: Any) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Returns (records, debug_info)
    """
    dbg: Dict[str, Any] = {
        "fetch_type": type(fetch_ctx).__name__,
        "fetch_keys": list(fetch_ctx.keys()) if isinstance(fetch_ctx, dict) else None,
    }

    # Allow nested envelopes: fetch_ctx might already be an envelope,
    # and fetch_ctx["result"] might itself be an envelope.
    fetch_unwrapped = unwrap_envelope(fetch_ctx)
    dbg["fetch_unwrapped_type"] = type(fetch_unwrapped).__name__
    dbg["fetch_unwrapped_keys"] = list(fetch_unwrapped.keys()) if isinstance(fetch_unwrapped, dict) else None

    # Common shapes:
    # - fetch is envelope -> fetch.result is dict with data
    # - fetch is dict with data directly (legacy)
    # - fetch.result is another envelope -> unwrap again
    result_obj: Any = None

    if isinstance(fetch_unwrapped, dict):
        # Prefer .result if present
        result_obj = fetch_unwrapped.get("result")
        if result_obj is None:
            # Legacy fallback: fetch itself might be the result object
            result_obj = fetch_unwrapped

    # Unwrap possible envelope inside result
    result_obj = unwrap_envelope(result_obj)
    dbg["result_type"] = type(result_obj).__name__
    dbg["result_keys"] = list(result_obj.keys()) if isinstance(result_obj, dict) else None

    # Extract records
    records: List[Dict[str, Any]] = []

    if isinstance(result_obj, dict):
        data = (
            result_obj.get("data")
            or result_obj.get("Data")
            or result_obj.get("records")
            or result_obj.get("Records")
            or []
        )
        if isinstance(data, list):
            records = [r for r in data if isinstance(r, dict)]
            dbg["data_list_len"] = len(data)
        else:
            dbg["data_non_list_type"] = type(data).__name__
    elif isinstance(result_obj, list):
        records = [r for r in result_obj if isinstance(r, dict)]
        dbg["result_list_len"] = len(result_obj)
    elif isinstance(fetch_unwrapped, list):
        # Very legacy/odd: fetch itself is list
        records = [r for r in fetch_unwrapped if isinstance(r, dict)]
        dbg["fetch_list_len"] = len(fetch_unwrapped)

    return records, dbg

def main() -> int:
    payload = json.load(sys.stdin)
    context = payload.get("context") or {}
    fetch = context.get("fetch_leads")

    os.makedirs("outputs", exist_ok=True)
    out_path = os.path.join("outputs", "leads.md")
    debug_path = os.path.join("outputs", "leads_debug.json")

    debug: Dict[str, Any] = {
        "context_keys": list(context.keys()) if isinstance(context, dict) else None,
        "has_fetch_leads": "fetch_leads" in context if isinstance(context, dict) else False,
    }

    records: List[Dict[str, Any]] = []
    if fetch is not None:
        records, fetch_dbg = extract_records(fetch)
        debug["fetch_debug"] = fetch_dbg
    else:
        debug["fetch_debug"] = {"error": "context.fetch_leads is missing"}

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Zoho Leads\n\n")
        if not records:
            f.write("(no records found)\n")
        else:
            for r in records:
                name = r.get("Full_Name") or r.get("Last_Name") or r.get("Name") or "Unknown"
                f.write(f"- {name}\n")

    debug["records_count"] = len(records)
    with open(debug_path, "w", encoding="utf-8") as f:
        json.dump(debug, f, indent=2, sort_keys=True)

    # Declare both outputs so you can inspect debug from the UI evidence pack.
    json.dump(
        {
            "status": "success",
            "files": [out_path, debug_path],
            "records_count": len(records),
        },
        sys.stdout,
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
