import json, os, sys
from typing import Any, Dict, List

def unwrap_result(x: Any) -> Any:
    # repeatedly unwrap nested {"result": ...} objects
    # and also support {"success":..., "result":...} envelopes if present
    while isinstance(x, dict):
        if "success" in x and "result" in x:
            x = x.get("result")
            continue
        if "result" in x and len(x) == 1:
            x = x.get("result")
            continue
        break
    return x

payload = json.load(sys.stdin)
context = payload.get("context") or {}
fetch = context.get("fetch_leads") or {}

fetch_unwrapped = unwrap_result(fetch)

records: List[Dict[str, Any]] = []
if isinstance(fetch_unwrapped, dict):
    # data might be directly here, or under another result
    data = fetch_unwrapped.get("data") or fetch_unwrapped.get("Data")
    if not isinstance(data, list):
        inner = unwrap_result(fetch_unwrapped.get("result"))
        if isinstance(inner, dict):
            data = inner.get("data") or inner.get("Data")
    if isinstance(data, list):
        records = [r for r in data if isinstance(r, dict)]

os.makedirs("outputs", exist_ok=True)
out_path = os.path.join("outputs", "leads.md")
with open(out_path, "w", encoding="utf-8") as f:
    f.write("# Zoho Leads\n\n")
    for r in records:
        name = r.get("Full_Name") or r.get("Last_Name") or "Unknown"
        f.write(f"- {name}\n")

json.dump({"status": "success", "files": [out_path], "records_count": len(records)}, sys.stdout)
