"""""
import json
import shutil
from pathlib import Path


GRANTS_FILE = (
    Path(__file__).resolve().parent
    / "json_data"
    / "grants.json"
)

BACKUP_FILE = (
    Path(__file__).resolve().parent
    / "json_data"
    / "grants_before_source_migration.json"
)


def migrate_sources() -> None:
    if not GRANTS_FILE.exists():
        raise FileNotFoundError(
            f"grants.json was not found:\n{GRANTS_FILE}"
        )

    # Make a backup before changing anything
    shutil.copy2(
        GRANTS_FILE,
        BACKUP_FILE,
    )

    with GRANTS_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    changed = 0
    missing = 0

    for opportunity in data.get("docs", []):
        source = opportunity.get("source")

        # Old format:
        # "source": {"url": "...", ...}
        if isinstance(source, dict):
            source_url = source.get("url")

            if source_url:
                opportunity["source"] = source_url
                changed += 1
            else:
                opportunity["source"] = None
                missing += 1

    # Safely write through a temporary file
    temporary_file = GRANTS_FILE.with_suffix(
        ".json.tmp"
    )

    with temporary_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )

    temporary_file.replace(GRANTS_FILE)

    print("✅ Migration finished")
    print("Sources converted:", changed)
    print("Sources missing URLs:", missing)
    print("Updated file:", GRANTS_FILE)
    print("Backup file:", BACKUP_FILE)


if __name__ == "__main__":
    migrate_sources()
"""""


import json
from data_validation import read_json_file

data=read_json_file(r"C:\Users\akshi\PycharmProjects\AgenticSomething\data\structured\json_data\grants.json")

print(len(data["docs"]))