from pathlib import Path

from data_validation import validate_grants_file
import hashlib



# data_main.py is inside:
# AgenticSomething/data/structured/data_main.py
"""""
PROJECT_ROOT = Path(__file__).resolve().parents[2]

GRANTS_FILE = (
    PROJECT_ROOT
    / "data"
    / "structured"
    / "json_data"
    / "grants.json"
)

print("Looking for file at:")
print(GRANTS_FILE)


try:
    validated_data = validate_grants_file(
        GRANTS_FILE
    )

    print(
        f"✅ Valid dataset: "
        f"{len(validated_data['docs'])} grants"
    )

except (ValueError, FileNotFoundError) as error:
    print(f"❌ {error}")
"""""
from google import genai
client = genai.Client(api_key="AIzaSyAwYKGdDXMiaJIycMjN_9uu1jevB1J4ZJI")

prompt_template = """Read the funding opportunity from the provided link/content and return only valid JSON.

Rules:

* Must provide grant name
* Do not add explanations or markdown.
* Do not invent missing information.
* Do not show your reasoning or analysis.
* Your response must begin with { and end with }.
* Use null for missing single values and [] for missing lists.
* Amounts must be numbers only.
* Dates must use YYYY-MM-DD.
* `type` must always be `funding_opportunity`.
* `status` must be: active, inactive, upcoming, or unknown.
* `funding_type` must be one of: grant, seed_funding, equity_investment, loan, subsidy, prize, financial_assistance, or unknown.
* Keep every field in the structure.
* Use the provided link as `source`.
* Do not use ```json code blocks.

Return exactly:

{
"_id": null,
"type": "funding_opportunity",
"grant_name": null,
"provider": {
"name": null,
"type": "unknown"
},
"description": null,
"funding": {
"minimum_amount": null,
"maximum_amount": null,
"currency": null,
"funding_type": "unknown"
},
"eligibility": {
"startup_stages": [],
"industries": [],
"allowed_locations": [],
"company_requirements": [],
"applicant_requirements": [],
"exclusions": []
},
"application": {
"open_date": null,
"deadline": null,
"application_url": null,
"required_documents": [],
"application_steps": []
},
"status": "unknown",
"source": "{{SOURCE_URL}}"
}

Source link:

{{SOURCE_URL}}
"""
import json
import re
from datetime import date
from typing import Any


def create_id(name: str) -> str:
    grant_id = name.lower().strip()
    grant_id = re.sub(r"[^a-z0-9]+", "-", grant_id)
    grant_id = grant_id.strip("-")

    # Keep IDs within Pydantic's 120-character limit
    if len(grant_id) > 120:
        short_hash = hashlib.sha256(
            grant_id.encode("utf-8")
        ).hexdigest()[:8]

        grant_id = (
            grant_id[:111].rstrip("-")
            + "-"
            + short_hash
        )

    return grant_id


def parse_gemini_response(
    response_text: str,
    source_url: str,
) -> dict[str, Any]:

    # First try to find JSON inside ```json ... ```
    json_block = re.search(
        r"```(?:json)?\s*(\{.*\})\s*```",
        response_text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if json_block:
        cleaned_text = json_block.group(1)

    else:
        # Backup: take everything from the first {
        # until the final }
        start = response_text.find("{")
        end = response_text.rfind("}")

        if start == -1 or end == -1:
            raise ValueError(
                "Gemini response did not contain JSON."
            )

        cleaned_text = response_text[start:end + 1]

    try:
        data = json.loads(cleaned_text)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Gemini returned invalid JSON: {error}"
        ) from error

    # Create ID if Gemini leaves it empty
    if not data.get("_id"):
        grant_name = data.get("grant_name") or "Unknown name"

        data["grant_name"] = grant_name
        data["_id"] = create_id(grant_name)



    # Force correct source
    data["source"] = source_url

    # Correct status using deadline
    deadline_value = (
        data.get("application", {})
        .get("deadline")
    )

    if deadline_value:
        try:
            deadline = date.fromisoformat(
                deadline_value
            )

            if deadline < date.today():
                data["status"] = "inactive"

        except ValueError:
            raise ValueError(
                f"Invalid deadline format: "
                f"{deadline_value}"
            )

    return data







source_url = "https://aim.gov.in/"

prompt = prompt_template.replace(
    "{{SOURCE_URL}}",
    source_url,
)

response = client.interactions.create(
    model="gemini-3.5-flash",
    input=f"""{prompt}
    """,
    tools=[
        {"type": "url_context"}
    ]

)

response_text = response.output_text


print("RAW GEMINI RESPONSE:")
print(repr(response_text))



new_opportunity = parse_gemini_response(
    response_text=response_text,
    source_url=source_url,
)

print(
    json.dumps(
        new_opportunity,
        indent=2,
        ensure_ascii=False,
    )
)

from data_validation import append_grants


append_grants(
    grants_file=r"C:\Users\akshi\PycharmProjects\AgenticSomething\data\structured\json_data\grants.json",
    new_data=new_opportunity,
    on_duplicate="replace",
    require_source=True,
)