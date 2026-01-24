import json, os, sys

payload = json.load(sys.stdin)
context = payload.get("context") or {}
fetch = context.get("fetch_leads") or {}

# This depends on the Zoho executor response shape; adapt as needed.
records = []
if isinstance(fetch, dict):
    records = (fetch.get("data") or fetch.get("Data") or []) or []

os.makedirs("outputs", exist_ok=True)
out_path = os.path.join("outputs", "leads.md")
with open(out_path, "w", encoding="utf-8") as f:
    f.write("# Zoho Leads\\n\\n")
    for r in records:
        if not isinstance(r, dict):
            continue
        name = r.get("Full_Name") or r.get("Last_Name") or "Unknown"
        f.write(f"- {name}\\n")

json.dump({"status": "success", "files": [out_path]}, sys.stdout)
