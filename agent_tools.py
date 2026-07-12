import json


SEARCH_GRANTS_TOOL_SCHEMA ={
    "type": "function",
    "function": {
        "name": "search_grants",
        "description": (
            "Search for startup grants and funding opportunities. "
            "Use this when a user wants funding recommendations based "
            "on startup stage, industry, location, funding amount, "
            "or funding type."
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "startup_stage": {
                    "type": "string",
                    "enum": [
                        "idea",
                        "prototype",
                        "early-stage",
                        "growth-stage",
                        "scaling",
                        "unknown"
                    ],
                    "description": "Current stage of the startup."
                },
                "industries": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "minItems": 1,
                    "description": (
                        "Industries in which the startup operates, "
                        "such as biotechnology, healthcare, fintech, "
                        "agriculture, AI, or education."
                    )
                },
                "location": {
                    "type": "string",
                    "description": (
                        "Country or region where the startup is registered."
                    )
                },
                "funding_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "grant",
                            "seed_funding",
                            "equity_investment",
                            "loan",
                            "subsidy",
                            "prize",
                            "financial_assistance"
                        ]
                    },
                    "description": "Funding types preferred by the startup."
                },
                "minimum_funding_needed": {
                    "type": "number",
                    "minimum": 0,
                    "description": (
                        "Minimum amount of funding required by the startup."
                    )
                },
                "currency": {
                    "type": "string",
                    "enum": [
                        "INR",
                        "USD",
                        "EUR",
                        "GBP",
                        "unknown"
                    ],
                    "description": "Currency used for the funding amount."
                },
                "deadline_after": {
                    "type": "string",
                    "format": "date",
                    "description": (
                        "Only return opportunities whose deadline is "
                        "on or after this date. Format: YYYY-MM-DD."
                    )
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 5,
                    "description": "Maximum number of grants to return."
                }
            },
            "required": [
                "startup_stage",
                "industries",
                "location"
            ]
        }
    }
}




#------------------------------- tools________________________________________________
import os
from dotenv import load_dotenv
from data.structured.data_validation import SearchGrantsInput
from ibmcloudant.cloudant_v1 import CloudantV1
load_dotenv()




cloudant_api_key = os.getenv("CLOUDANT_API_KEY")
cloudant_url = os.getenv("CLOUDANT_URL")
DATABASE_NAME = str(os.getenv("CLOUDANT_DATABASE"))

from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
authenticator = IAMAuthenticator(cloudant_api_key)
cloudant = CloudantV1(authenticator=authenticator)
cloudant.set_service_url(cloudant_url)



from typing import Any


def normalize(value: Any) -> str:
    """
    Converts values into a simple format for matching.

    Example:
    'Early-Stage' -> 'early-stage'
    """
    return str(value).strip().casefold()


def normalize_list(values: list[Any]) -> set[str]:
    return {
        normalize(value)
        for value in values
    }
from typing import Any


def get_grants_from_cloudant() -> list[dict[str, Any]]:
    result = cloudant.post_find(
        db=DATABASE_NAME,
        selector={
            "type": "grant",
        },
        limit=200,
    ).get_result()

    if not isinstance(result, dict):
        raise RuntimeError(
            "Expected Cloudant to return a dictionary."
        )

    grants = result.get("docs", [])

    if not isinstance(grants, list):
        raise RuntimeError(
            "Expected 'docs' to be a list."
        )

    return grants

def search_grants(
    search_input: SearchGrantsInput,
) -> dict[str, Any]:

    # First, get grant documents from Cloudant.

    grants = get_grants_from_cloudant()

    matching_grants = []

    for grant in grants:
        print(grant.get("grant_name"))

    requested_stage = normalize(
        search_input.startup_stage
    )

    requested_industries = normalize_list(
        search_input.industries
    )

    requested_location = normalize(
        search_input.location
    )

    requested_funding_types = normalize_list(
        search_input.funding_types
    )

    for grant in grants:
        eligibility = grant.get(
            "eligibility",
            {},
        )

        funding = grant.get(
            "funding",
            {},
        )

        grant_stages = normalize_list(
            eligibility.get(
                "startup_stages",
                [],
            )
        )

        grant_industries = normalize_list(
            eligibility.get(
                "industries",
                [],
            )
        )

        grant_locations = normalize_list(
            eligibility.get(
                "allowed_locations",
                [],
            )
        )

        grant_funding_type = normalize(
            funding.get(
                "funding_type",
                "unknown",
            )
        )

        grant_currency = normalize(
            funding.get(
                "currency",
                "unknown",
            )
        )

        maximum_amount = funding.get(
            "maximum_amount"
        )

        # -----------------------------------------
        # Required eligibility checks
        # -----------------------------------------

        stage_matches = (
            requested_stage in grant_stages
            or "all" in grant_stages
            or "any" in grant_stages
        )

        industry_matches = (
            bool(requested_industries & grant_industries)
            or "all sectors" in grant_industries
            or "any" in grant_industries
            or "all" in grant_industries
        )

        location_matches = (
            requested_location in grant_locations
            or "global" in grant_locations
            or "worldwide" in grant_locations
            or "any" in grant_locations
        )

        if not stage_matches:
            continue

        if not industry_matches:
            continue

        if not location_matches:
            continue

        # -----------------------------------------
        # Optional funding type check
        # -----------------------------------------

        if (
            requested_funding_types
            and grant_funding_type
            not in requested_funding_types
        ):
            continue

        # -----------------------------------------
        # Optional currency check
        # -----------------------------------------

        if search_input.currency is not None:
            requested_currency = normalize(
                search_input.currency
            )

            if grant_currency != requested_currency:
                continue

        # -----------------------------------------
        # Optional amount check
        # -----------------------------------------

        if (
            search_input.minimum_funding_needed
            is not None
            and maximum_amount is not None
            and maximum_amount
            < search_input.minimum_funding_needed
        ):
            continue

        matching_grants.append(
            {
                "_id": grant.get("_id"),
                "grant_name": grant.get(
                    "grant_name"
                ),
                "provider": grant.get(
                    "provider"
                ),
                "description": grant.get(
                    "description"
                ),
                "funding": funding,
                "eligibility": eligibility,
                "application": grant.get(
                    "application"
                ),
                "source": grant.get(
                    "source"
                ),
            }
        )

    limited_results = matching_grants[
        :search_input.limit
    ]

    return {
        "total_matches": len(
            matching_grants
        ),
        "returned_count": len(
            limited_results
        ),
        "grants": limited_results,
    }


