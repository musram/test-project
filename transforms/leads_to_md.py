import json, os, sys
from typing import Any, Dict, List, Tuple

def is_envelope(x: Any) -> bool:
    return isinstance(x, dict) and isinstance(x.get("success"), bool) and ("result" in x)

def unwrap_envelope(x: Any) -> Any:
    if is_envelope(x):
        return x.get("result")
    return x

def load_context(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    dbg: Dict[str, Any] = {}
    ctx = payload.get("context")

    # Primary path: stdin payload.context
    if isinstance(ctx, dict) and len(ctx) > 0:
        dbg["context_source"] = "stdin.payload.context"
        return ctx, dbg

    # Fallback: STEP_CONTEXT env (runner context)
    raw = os.environ.get("STEP_CONTEXT")
    dbg["context_source"] = "env.STEP_CONTEXT"
    dbg["step_context_env_present"] = raw is not None
    dbg["step_context_env_len_bytes"] = len(raw.encode("utf-8")) if isinstance(raw, str) else 0

    if not raw:
        return {}, dbg

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            dbg["step_context_env_parsed_ok"] = True
            return parsed, dbg
        dbg["step_context_env_parsed_ok"] = False
        dbg["step_context_env_parsed_type"] = type(parsed).__name__
        return {}, dbg
    except Exception as e:
        dbg["step_context_env_parsed_ok"] = False
        dbg["step_context_env_parse_error"] = str(e)
        return {}, dbg

def extract_records(context: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    fetch_ctx = context.get("fetch_leads")
    dbg: Dict[str, Any] = {
        "context_keys": list(context.keys()),
        "has_fetch_leads": "fetch_leads" in context,
        "fetch_type": type(fetch_ctx).__name__,
        "fetch_keys": list(fetch_ctx.keys()) if isinstance(fetch_ctx, dict) else None,
    }

    records: List[Dict[str, Any]] = []
    if fetch_ctx is None:
        dbg["error"] = "context.fetch_leads is missing"
        return records, dbg

    fetch_unwrapped = unwrap_envelope(fetch_ctx)
    dbg["fetch_unwrapped_type"] = type(fetch_unwrapped).__name__
    dbg["fetch_unwrapped_keys"] = list(fetch_unwrapped.keys()) if isinstance(fetch_unwrapped, dict) else None

    result_obj: Any = None
    if isinstance(fetch_unwrapped, dict):
        result_obj = fetch_unwrapped.get("result")
        if result_obj is None:
            result_obj = fetch_unwrapped

    result_obj = unwrap_envelope(result_obj)
    dbg["result_type"] = type(result_obj).__name__
    dbg["result_keys"] = list(result_obj.keys()) if isinstance(result_obj, dict) else None

    if isinstance(result_obj, dict):
        data = (
            result_obj.get("data")
            or result_obj.get("Data")
            or result_obj.get("records")
            or result_obj.get("Records")
            or []
        )
        if isinstance(data, list):
            dbg["data_list_len"] = len(data)
            records = [r for r in data if isinstance(r, dict)]
        else:
            dbg["data_non_list_type"] = type(data).__name__
    elif isinstance(result_obj, list):
        dbg["result_list_len"] = len(result_obj)
        records = [r for r in result_obj if isinstance(r, dict)]

    return records, dbg

def main() -> int:
    payload = json.load(sys.stdin)
    if not isinstance(payload, dict):
        payload = {}

    context, ctx_dbg = load_context(payload)

    os.makedirs("outputs", exist_ok=True)
    out_path = os.path.join("outputs", "leads.md")
    debug_path = os.path.join("outputs", "leads_debug.json")

    records, fetch_dbg = extract_records(context if isinstance(context, dict) else {})

    debug: Dict[str, Any] = {
        "context_debug": ctx_dbg,
        "fetch_debug": fetch_dbg,
        "records_count": len(records),
    }

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Zoho Leads\n\n")
        if not records:
            f.write("(no records found)\n")
        else:
            for r in records:
                name = r.get("Full_Name") or r.get("Last_Name") or r.get("Name") or "Unknown"
                f.write(f"- {name}\n")

    with open(debug_path, "w", encoding="utf-8") as f:
        json.dump(debug, f, indent=2, sort_keys=True)

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
