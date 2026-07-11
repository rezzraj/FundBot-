from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    ValidationError,
    model_validator,
)

"""""
| Function                  | What it does                                   | When to use it                              |
| ------------------------- | ---------------------------------------------- | ------------------------------------------- |
| `read_json_file()`        | Opens a JSON file                              | When you only want to read JSON             |
| `validate_grants_data()`  | Validates Python data like a dictionary        | When data comes from Gemini or your code    |
| `validate_grants_file()`  | Reads and validates the complete `grants.json` | To check whether your whole file is correct |
| `validate_single_grant()` | Validates only one funding opportunity         | Before adding one new record                |
| `normalize_new_grants()`  | Converts different input shapes into a list    | Used internally before appending            |
| `write_json_safely()`     | Writes JSON without damaging the old file      | Used when saving                            |
| `append_grants()`         | Validates and adds new records                 | Main function for adding data               |
| `append_from_json_file()` | Adds records from another JSON file            | When another source produces a JSON file    |



.........................
4. append_grants()

This is probably the most useful function for your project.

It:

Reads your current grants.json
Validates the existing records
Validates the new record
Checks duplicate IDs
Adds or updates the record
Validates everything again
Overwrites grants.json safely

Example:

from grant_validator import append_grants


result = append_grants(
    grants_file="data/structured/json_data/grants.json",
    new_data=new_opportunity,
    on_duplicate="error",
    require_source=True,
)

print("Total records:", len(result["docs"]))
Duplicate options
Stop when duplicate exists
on_duplicate="error"

Example:

A funding opportunity with this _id already exists.
Ignore the new duplicate
on_duplicate="skip"

The old record stays unchanged.

Replace the old record
on_duplicate="replace"

Use this when you have newer data.

Example:

append_grants(
    grants_file="data/structured/json_data/grants.json",
    new_data=new_opportunity,
    on_duplicate="replace",
    require_source=True,
)

For your project, "replace" will be useful when deadlines or funding amounts change.

"""""
# =========================================================
# REUSABLE TYPES
# =========================================================

NonEmptyString = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
    ),
]

GrantId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=120,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    ),
]

PositiveAmount = Annotated[
    int,
    Field(
        strict=True,
        ge=0,
    ),
]


# =========================================================
# BASE MODEL
# =========================================================

class StrictModel(BaseModel):
    """
    Reject any field that is not defined in the model.
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )


# =========================================================
# NESTED MODELS
# =========================================================

class Provider(StrictModel):
    name: NonEmptyString | None

    type: Literal[
        "government",
        "private",
        "nonprofit",
        "non-profit",
        "international",
        "unknown",
    ]


class Funding(StrictModel):
    minimum_amount: PositiveAmount | None
    maximum_amount: PositiveAmount | None

    currency: Literal[
        "INR",
        "USD",
        "EUR",
        "GBP",
        "unknown",
    ] | None= None

    funding_type: Literal[
        "grant",
        "seed_funding",
        "equity_investment",
        "loan",
        "subsidy",
        "prize",
        "financial_assistance",
        "unknown",
    ]

    @model_validator(mode="after")
    def validate_amount_range(self) -> "Funding":
        if (
            self.minimum_amount is not None
            and self.maximum_amount is not None
            and self.minimum_amount > self.maximum_amount
        ):
            raise ValueError(
                "minimum_amount cannot be greater than maximum_amount"
            )

        return self

class Eligibility(StrictModel):
    startup_stages: list[NonEmptyString]
    industries: list[NonEmptyString]
    allowed_locations: list[NonEmptyString]
    company_requirements: list[NonEmptyString]
    applicant_requirements: list[NonEmptyString]
    exclusions: list[NonEmptyString]

class FundingOpportunity(StrictModel):
    id: GrantId = Field(alias="_id")

    type: Literal[
        "grant",
        "funding_opportunity",
    ]

    grant_name: NonEmptyString

    provider: Provider
    description: NonEmptyString | None
    funding: Funding
    eligibility: Eligibility
    application: Application

    status: Literal[
        "active",
        "inactive",
        "upcoming",
        "unknown",
    ]

    source: HttpUrl | None = None
class Application(StrictModel):
    open_date: date | None
    deadline: date | None
    application_url: HttpUrl | None
    required_documents: list[NonEmptyString]
    application_steps: list[NonEmptyString]

    @model_validator(mode="after")
    def validate_dates(self) -> "Application":
        if (
            self.open_date is not None
            and self.deadline is not None
            and self.open_date > self.deadline
        ):
            raise ValueError(
                "open_date cannot be later than deadline"
            )

        return self


# Optional because your example does not contain source,
# but your generator from earlier adds it.
class Source(StrictModel):
    url: HttpUrl
    source_type: NonEmptyString
    dataset: NonEmptyString | None = None
    retrieved_at: NonEmptyString


# =========================================================
# ONE GRANT DOCUMENT
# =========================================================

class Grant(StrictModel):
    id: GrantId = Field(alias="_id")

    type: Literal["grant"]

    grant_name: NonEmptyString

    provider: Provider

    description: NonEmptyString | None

    funding: Funding

    eligibility: Eligibility

    application: Application

    status: Literal[
        "active",
        "inactive",
        "upcoming",
        "unknown",
    ]

    # Old records without source will still validate.
    source: Source | None = None


# =========================================================
# COMPLETE GRANTS FILE
# =========================================================

class GrantsDataset(StrictModel):
    docs: list[FundingOpportunity]

    @model_validator(mode="after")
    def ensure_unique_ids(self) -> "GrantsDataset":
        seen_ids: set[str] = set()
        duplicate_ids: set[str] = set()

        for opportunity in self.docs:
            opportunity_id = opportunity.id

            if opportunity_id in seen_ids:
                duplicate_ids.add(opportunity_id)

            seen_ids.add(opportunity_id)

        if duplicate_ids:
            raise ValueError(
                "Duplicate _id values found: "
                + ", ".join(sorted(duplicate_ids))
            )

        return self


# =========================================================
# READ JSON
# =========================================================

def read_json_file(file_path: str | Path) -> Any:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"JSON file does not exist:\n{path.resolve()}"
        )

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON inside {path.name}:\n"
            f"Line {error.lineno}, column {error.colno}\n"
            f"{error.msg}"
        ) from error


# =========================================================
# FORMAT VALIDATION ERRORS NICELY
# =========================================================

def format_validation_error(
    error: ValidationError,
) -> str:
    messages: list[str] = []

    for problem in error.errors():
        location = " -> ".join(
            str(part)
            for part in problem["loc"]
        )

        message = problem["msg"]

        messages.append(
            f"{location}: {message}"
        )

    return "\n".join(messages)


# =========================================================
# VALIDATE NORMAL PYTHON DATA
# =========================================================

def validate_grants_data(
    data: Any,
    require_source: bool = False,
) -> dict:
    """
    Validate a complete object shaped like:

    {
        "docs": [...]
    }

    Returns clean JSON-compatible data when valid.
    Raises ValueError when invalid.
    """

    try:
        validated_dataset = GrantsDataset.model_validate(
            data
        )

    except ValidationError as error:
        readable_errors = format_validation_error(
            error
        )

        raise ValueError(
            "Grant dataset validation failed:\n\n"
            f"{readable_errors}"
        ) from error

    if require_source:
        missing_sources = [
            grant.id
            for grant in validated_dataset.docs
            if grant.source is None
        ]

        if missing_sources:
            raise ValueError(
                "These grants do not have source information:\n"
                + "\n".join(
                    f"- {grant_id}"
                    for grant_id in missing_sources
                )
            )

    return validated_dataset.model_dump(
        by_alias=True,
        mode="json",
    )


# =========================================================
# VALIDATE AN EXISTING FILE
# =========================================================

def validate_grants_file(
    file_path: str | Path,
    require_source: bool = False,
) -> dict:
    """
    Read and validate an existing grants.json file.
    """

    data = read_json_file(file_path)

    validated_data = validate_grants_data(
        data=data,
        require_source=require_source,
    )

    return validated_data


# =========================================================
# VALIDATE ONE SINGLE GRANT
# =========================================================

def validate_single_grant(
    grant_data: dict,
    require_source: bool = False,
) -> dict:
    """
    Validate one grant object.
    """

    wrapper = {
        "docs": [grant_data]
    }

    validated = validate_grants_data(
        data=wrapper,
        require_source=require_source,
    )

    return validated["docs"][0]


# =========================================================
# NORMALIZE NEW DATA
# =========================================================

def normalize_new_grants(
    new_data: Any,
) -> list[dict]:
    """
    Accept any of these:

    One grant:
        {...}

    List of grants:
        [{...}, {...}]

    Full dataset:
        {"docs": [{...}, {...}]}
    """

    if isinstance(new_data, dict):
        if "docs" in new_data:
            docs = new_data["docs"]

            if not isinstance(docs, list):
                raise ValueError(
                    "'docs' must contain a list"
                )

            return docs

        return [new_data]

    if isinstance(new_data, list):
        return new_data

    raise ValueError(
        "New grant data must be a grant object, "
        "a list of grants, or {'docs': [...]}"
    )


# =========================================================
# SAFE JSON WRITER
# =========================================================

def write_json_safely(
    file_path: str | Path,
    data: dict,
) -> None:
    """
    Write through a temporary file first.

    This prevents grants.json from being damaged
    if writing stops halfway.
    """

    path = Path(file_path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = path.with_suffix(
        path.suffix + ".tmp"
    )

    with temporary_path.open(
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

    # Replace the previous grants.json only after
    # the complete new file has been written.
    temporary_path.replace(path)


# =========================================================
# APPEND VALIDATED GRANTS
# =========================================================

def append_grants(
    grants_file: str | Path,
    new_data: Any,
    on_duplicate: Literal[
        "error",
        "skip",
        "replace",
    ] = "error",
    require_source: bool = True,
) -> dict:
    """
    Validate existing grants.json.
    Validate all new grants.
    Merge them.
    Validate the final merged dataset.
    Overwrite grants.json safely.

    on_duplicate:
        error   -> stop when the _id already exists
        skip    -> keep the old record
        replace -> replace the old record with the new one
    """

    path = Path(grants_file)

    # ---------------------------------------------
    # Load and validate existing data
    # ---------------------------------------------

    if path.exists():
        existing_data = validate_grants_file(
            file_path=path,
            require_source=False,
        )
    else:
        existing_data = {
            "docs": []
        }

    # ---------------------------------------------
    # Normalize and validate incoming records
    # ---------------------------------------------

    incoming_docs = normalize_new_grants(
        new_data
    )

    validated_incoming = validate_grants_data(
        data={
            "docs": incoming_docs
        },
        require_source=require_source,
    )

    # ---------------------------------------------
    # Create lookup using _id
    # ---------------------------------------------

    merged_by_id = {
        grant["_id"]: grant
        for grant in existing_data["docs"]
    }

    # ---------------------------------------------
    # Merge new records
    # ---------------------------------------------

    for new_grant in validated_incoming["docs"]:
        grant_id = new_grant["_id"]

        already_exists = grant_id in merged_by_id

        if already_exists:
            if on_duplicate == "error":
                raise ValueError(
                    f"A grant with _id '{grant_id}' "
                    "already exists"
                )

            if on_duplicate == "skip":
                continue

            if on_duplicate == "replace":
                merged_by_id[grant_id] = new_grant
                continue

        merged_by_id[grant_id] = new_grant

    merged_dataset = {
        "docs": list(
            merged_by_id.values()
        )
    }

    # ---------------------------------------------
    # Validate everything one final time
    # ---------------------------------------------

    final_validated_data = validate_grants_data(
        data=merged_dataset,
        require_source=False,
    )

    final_validated_data["docs"].sort(
        key=lambda grant: grant["grant_name"].lower()
    )

    # ---------------------------------------------
    # Overwrite grants.json
    # ---------------------------------------------

    write_json_safely(
        file_path=path,
        data=final_validated_data,
    )

    return final_validated_data


# =========================================================
# APPEND FROM ANOTHER JSON FILE
# =========================================================

def append_from_json_file(
    grants_file: str | Path,
    incoming_file: str | Path,
    on_duplicate: Literal[
        "error",
        "skip",
        "replace",
    ] = "error",
    require_source: bool = True,
) -> dict:
    """
    Append records from another JSON file.
    """

    incoming_data = read_json_file(
        incoming_file
    )

    return append_grants(
        grants_file=grants_file,
        new_data=incoming_data,
        on_duplicate=on_duplicate,
        require_source=require_source,
    )




#________________________________________________for ai tools______________________
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


StartupStage = Literal[
    "idea",
    "prototype",
    "early-stage",
    "growth-stage",
    "scaling",
    "unknown",
]

FundingType = Literal[
    "grant",
    "seed_funding",
    "equity_investment",
    "loan",
    "subsidy",
    "prize",
    "financial_assistance",
]

Currency = Literal[
    "INR",
    "USD",
    "EUR",
    "GBP",
    "unknown",
]


class SearchGrantsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    startup_stage: StartupStage

    industries: list[str] = Field(
        min_length=1
    )

    location: str = Field(
        min_length=2
    )

    funding_types: list[FundingType] = []

    minimum_funding_needed: float | None = Field(
        default=None,
        ge=0,
    )

    currency: Currency | None = None

    deadline_after: date | None = None

    limit: int = Field(
        default=5,
        ge=1,
        le=20,
    )