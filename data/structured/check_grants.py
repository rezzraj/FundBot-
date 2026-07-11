from pathlib import Path
import json


grants_file = (
    Path(__file__).resolve().parent
    / "json_data"
    / "grants.json"
)

target_id = "startup-india-seed-fund-scheme"

print("Reading from:", grants_file)

if not grants_file.exists():
    raise FileNotFoundError(
        f"grants.json was not found at:\n{grants_file}"
    )

with grants_file.open("r", encoding="utf-8") as file:
    saved_data = json.load(file)

saved_record = next(
    (
        item
        for item in saved_data["docs"]
        if item["_id"] == target_id
    ),
    None,
)

if saved_record:
    print("Record exists")
    print("Name:", saved_record["grant_name"])
    print("Source:", saved_record.get("source"))
else:
    print("Record was not found")
    print("\nAvailable IDs:")

    for item in saved_data["docs"]:
        print("-", item.get("_id"))
