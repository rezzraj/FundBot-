from datetime import date, timedelta
from apps.api.services.cloudant_service import CloudantService


async def check_deadlines(cloudant: CloudantService) -> dict:
    """
    Check for grants with approaching deadlines.
    Returns grants grouped by urgency.
    """
    today = date.today()
    results = {"expired": [], "urgent": [], "upcoming": [], "safe": []}

    grants = cloudant.get_all_active_grants()

    for grant in grants:
        deadline_str = grant.get("application", {}).get("deadline")
        if not deadline_str:
            continue

        try:
            deadline = date.fromisoformat(deadline_str)
        except ValueError:
            continue

        days_left = (deadline - today).days

        entry = {
            "grant_id": grant["_id"],
            "grant_name": grant.get("grant_name", ""),
            "deadline": deadline_str,
            "days_left": days_left,
        }

        if days_left < 0:
            results["expired"].append(entry)
            # Update status to inactive
            grant["status"] = "inactive"
            cloudant.update_document(grant)
        elif days_left <= 7:
            results["urgent"].append(entry)
        elif days_left <= 30:
            results["upcoming"].append(entry)
        else:
            results["safe"].append(entry)

    return results
