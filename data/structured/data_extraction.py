from __future__ import annotations

import ast
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


# =========================================================
# FILE PATHS
# =========================================================

PROJECT_FOLDER = Path(__file__).resolve().parent

RAW_DATA_FOLDER = (
    PROJECT_FOLDER
    / "data"
    / "raw"
    / "myscheme"
)

OUTPUT_FILE = (
    PROJECT_FOLDER
    / "data"
    / "structured"
    / "grants.json"
)


# =========================================================
# FIND THE RAW CSV AUTOMATICALLY
# =========================================================

def find_csv_file(folder: Path) -> Path:
    if not folder.exists():
        raise FileNotFoundError(
            f"Folder does not exist:\n{folder}"
        )

    csv_files = list(folder.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(
            f"No CSV file found inside:\n{folder}"
        )

    # Prefer schemes.csv when available
    for csv_file in csv_files:
        if csv_file.name.lower() == "schemes.csv":
            return csv_file

    # Otherwise use the largest CSV
    return max(
        csv_files,
        key=lambda file: file.stat().st_size,
    )


# =========================================================
# BASIC CLEANING FUNCTIONS
# =========================================================

def clean_text(value: Any) -> str | None:
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    text = str(value).strip()

    if not text or text.lower() in {
        "nan",
        "none",
        "null",
    }:
        return None

    # Remove unnecessary repeated spaces
    return re.sub(r"\s+", " ", text)


def first_value(
    row: pd.Series,
    possible_columns: list[str],
) -> str | None:
    """
    Return the first usable value found from the provided
    possible column names.
    """

    for column in possible_columns:
        if column in row.index:
            value = clean_text(row[column])

            if value:
                return value

    return None


def make_id(value: str) -> str:
    """
    Turn:
        Startup India Seed Fund Scheme

    Into:
        startup-india-seed-fund-scheme
    """

    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")

    return value[:120] or "unknown-grant"


# =========================================================
# CONVERT TEXT INTO A LIST
# =========================================================

def text_to_list(value: Any) -> list[str]:
    """
    Handles normal text, newline-separated text,
    JSON lists, and Python-style lists.
    """

    if value is None:
        return []

    try:
        if pd.isna(value):
            return []
    except (TypeError, ValueError):
        pass

    if isinstance(value, list):
        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    text = str(value).strip()

    if not text or text.lower() in {
        "nan",
        "none",
        "null",
        "[]",
    }:
        return []

    # Try reading JSON arrays
    try:
        parsed = json.loads(text)

        if isinstance(parsed, list):
            return [
                str(item).strip()
                for item in parsed
                if str(item).strip()
            ]
    except json.JSONDecodeError:
        pass

    # Try reading Python-style arrays
    try:
        parsed = ast.literal_eval(text)

        if isinstance(parsed, list):
            return [
                str(item).strip()
                for item in parsed
                if str(item).strip()
            ]
    except (ValueError, SyntaxError):
        pass

    # Split using lines, bullets, pipes, and semicolons
    parts = re.split(
        r"\n+|•|●|▪|\||;\s*",
        text,
    )

    cleaned_parts = []

    for part in parts:
        cleaned = clean_text(part)

        if cleaned:
            cleaned_parts.append(cleaned)

    return cleaned_parts


def first_list(
    row: pd.Series,
    possible_columns: list[str],
) -> list[str]:
    for column in possible_columns:
        if column in row.index:
            result = text_to_list(row[column])

            if result:
                return result

    return []


# =========================================================
# COMBINE THE ROW'S TEXT FOR FILTERING
# =========================================================

def get_all_row_text(row: pd.Series) -> str:
    values = []

    for value in row.values:
        cleaned = clean_text(value)

        if cleaned:
            values.append(cleaned)

    return " ".join(values).lower()


# =========================================================
# CHECK IF IT LOOKS LIKE STARTUP FUNDING
# =========================================================

STARTUP_PATTERN = re.compile(
    r"\b("
    r"startup|startups|start-up|start-ups|"
    r"entrepreneur|entrepreneurs|entrepreneurship|"
    r"incubator|incubators|incubation|"
    r"prototype|prototypes|"
    r"innovator|innovators"
    r")\b",
    re.IGNORECASE,
)

FUNDING_PATTERN = re.compile(
    r"\b("
    r"grant|grants|funding|fund|"
    r"seed funding|seed fund|seed support|"
    r"financial assistance|financial support|"
    r"capital assistance|capital support|"
    r"subsidy|loan|credit support|"
    r"equity investment|venture funding|"
    r"prize money"
    r")\b",
    re.IGNORECASE,
)


def is_startup_funding(row: pd.Series) -> bool:
    text = get_all_row_text(row)

    has_startup_word = bool(
        STARTUP_PATTERN.search(text)
    )

    has_funding_word = bool(
        FUNDING_PATTERN.search(text)
    )

    return has_startup_word and has_funding_word


# =========================================================
# DETECT THE FUNDING TYPE
# =========================================================

def detect_funding_type(row: pd.Series) -> str:
    text = get_all_row_text(row)

    if re.search(
        r"\bgrant|grants|grant-in-aid\b",
        text,
    ):
        return "grant"

    if re.search(
        r"\bseed fund|seed funding|seed support\b",
        text,
    ):
        return "seed_funding"

    if re.search(
        r"\bequity|equity investment|venture capital\b",
        text,
    ):
        return "equity_investment"

    if re.search(
        r"\bloan|credit support|credit facility\b",
        text,
    ):
        return "loan"

    if re.search(
        r"\bsubsidy|capital subsidy\b",
        text,
    ):
        return "subsidy"

    if re.search(
        r"\bprize|prize money|award money\b",
        text,
    ):
        return "prize"

    if re.search(
        r"\bfinancial assistance|financial support\b",
        text,
    ):
        return "financial_assistance"

    return "unknown"


# =========================================================
# PROVIDER INFORMATION
# =========================================================

def get_provider_name(row: pd.Series) -> str | None:
    return first_value(
        row,
        [
            "nodal_ministry_name",
            "ministry_name",
            "ministry",
            "department_name",
            "department",
            "implementing_agency",
            "agency",
            "provider",
        ],
    )


def detect_provider_type(row: pd.Series) -> str:
    text = get_all_row_text(row)

    if any(
        word in text
        for word in [
            "government of india",
            "ministry",
            "government",
            "department",
            "state government",
        ]
    ):
        return "government"

    return "unknown"


# =========================================================
# LOCATION
# =========================================================

def get_locations(row: pd.Series) -> list[str]:
    locations = first_list(
        row,
        [
            "state",
            "state_name",
            "states",
            "location",
            "locations",
            "geographical_coverage",
        ],
    )

    if locations:
        return locations

    # Do not guess a specific state.
    # myScheme is an Indian government scheme database.
    return ["India"]


# =========================================================
# INDUSTRIES / CATEGORIES
# =========================================================

def get_industries(row: pd.Series) -> list[str]:
    return first_list(
        row,
        [
            "scheme_category",
            "category",
            "categories",
            "sector",
            "sectors",
            "industry",
            "industries",
            "tags",
        ],
    )


# =========================================================
# CREATE ONE GRANT DOCUMENT
# =========================================================

def convert_row_to_grant(
    row: pd.Series,
    retrieved_at: str,
) -> dict[str, Any]:
    grant_name = first_value(
        row,
        [
            "scheme_name",
            "name",
            "title",
            "scheme_title",
        ],
    )

    if not grant_name:
        grant_name = "Unknown Funding Scheme"

    existing_slug = first_value(
        row,
        ["slug", "scheme_slug"],
    )

    grant_id = make_id(
        existing_slug or grant_name
    )

    description = first_value(
        row,
        [
            "brief_description",
            "description",
            "scheme_description",
            "details",
            "about_scheme",
        ],
    )

    source_url = first_value(
        row,
        [
            "source_url",
            "scheme_url",
            "url",
            "website",
            "official_url",
        ],
    )

    application_url = first_value(
        row,
        [
            "application_url",
            "apply_url",
            "application_link",
            "apply_link",
        ],
    )

    eligibility_requirements = first_list(
        row,
        [
            "eligibility",
            "eligibility_criteria",
            "who_can_apply",
            "beneficiary_criteria",
        ],
    )

    required_documents = first_list(
        row,
        [
            "documents_required",
            "required_documents",
            "documents",
        ],
    )

    application_steps = first_list(
        row,
        [
            "application_process",
            "how_to_apply",
            "application_steps",
            "process",
        ],
    )

    startup_stages = first_list(
        row,
        [
            "startup_stages",
            "startup_stage",
            "business_stage",
        ],
    )

    exclusions = first_list(
        row,
        [
            "exclusions",
            "not_eligible",
            "ineligible",
        ],
    )

    open_date = first_value(
        row,
        [
            "open_date",
            "application_open_date",
            "start_date",
        ],
    )

    deadline = first_value(
        row,
        [
            "deadline",
            "last_date",
            "application_deadline",
            "end_date",
        ],
    )

    return {
        "_id": grant_id,
        "type": "grant",
        "grant_name": grant_name,
        "provider": {
            "name": get_provider_name(row),
            "type": detect_provider_type(row),
        },
        "description": description,
        "funding": {
            "minimum_amount": None,
            "maximum_amount": None,
            "currency": "INR",
            "funding_type": detect_funding_type(row),
        },
        "eligibility": {
            "startup_stages": startup_stages,
            "industries": get_industries(row),
            "allowed_locations": get_locations(row),
            "company_requirements": [],
            "applicant_requirements": eligibility_requirements,
            "exclusions": exclusions,
        },
        "application": {
            "open_date": open_date,
            "deadline": deadline,
            "application_url": application_url,
            "required_documents": required_documents,
            "application_steps": application_steps,
        },

        # Do not call it active without proof.
        "status": "unknown",

        "source": {
            "url": source_url,
            "source_type": "myscheme_webpage",
            "dataset": "myScheme India Government Schemes",
            "retrieved_at": retrieved_at,
        },
    }


# =========================================================
# MAIN PROGRAM
# =========================================================

def main() -> None:
    input_csv = find_csv_file(
        RAW_DATA_FOLDER
    )

    print("\nReading raw CSV:")
    print(input_csv)

    df = pd.read_csv(
        input_csv,
        low_memory=False,
    )

    print(f"\nTotal raw schemes: {len(df)}")

    retrieved_at = datetime.now(
        timezone.utc
    ).isoformat()

    grants = []
    seen_ids = set()

    for _, row in df.iterrows():
        # Remove this condition if you really want
        # all 4,000+ government schemes.
        if not is_startup_funding(row):
            continue

        grant = convert_row_to_grant(
            row=row,
            retrieved_at=retrieved_at,
        )

        grant_id = grant["_id"]

        # Prevent duplicate Cloudant IDs
        if grant_id in seen_ids:
            continue

        seen_ids.add(grant_id)
        grants.append(grant)

    grants.sort(
        key=lambda grant: grant["grant_name"].lower()
    )

    final_json = {
        "docs": grants
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # "w" means overwrite the previous file.
    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            final_json,
            file,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )

    print("\n-----------------------------------")
    print("DONE")
    print("-----------------------------------")
    print(f"Startup funding records: {len(grants)}")
    print(f"Previous JSON overwritten at:")
    print(OUTPUT_FILE)

    print("\nFirst 10 grants:\n")

    for grant in grants[:10]:
        print(
            f"- {grant['grant_name']} "
            f"({grant['funding']['funding_type']})"
        )


if __name__ == "__main__":
    main()