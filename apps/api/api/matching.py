from fastapi import APIRouter, Depends, HTTPException

from apps.api.dependencies import get_services, Services

router = APIRouter()


@router.post("/")
async def match_grants(
    request: dict,
    services: Services = Depends(get_services),
):
    """Find best matching grants for a startup profile."""
    # Accept either a profile_id or inline profile data
    profile_id = request.get("profile_id")
    if profile_id:
        profile = services.cloudant.get_document(profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
    else:
        profile = request.get("profile", {})

    top_n = request.get("top_n", 10)
    use_ai = request.get("use_ai_assessment", True)

    matches = await services.matching.match_profile_to_grants(
        profile=profile,
        top_n=top_n,
        use_ai_assessment=use_ai,
    )

    return {
        "matches": [
            {
                "grant_id": m.grant_id,
                "grant_name": m.grant_name,
                "final_score": m.final_score,
                "rule_score": m.rule_score,
                "semantic_score": m.semantic_score,
                "ai_score": m.ai_score,
                "eligible": m.eligible,
                "explanation": m.explanation,
                "met_criteria": m.met_criteria,
                "unmet_criteria": m.unmet_criteria,
                "grant": m.grant_data,
            }
            for m in matches
        ],
        "total": len(matches),
    }
