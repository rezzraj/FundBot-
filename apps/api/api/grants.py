from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from apps.api.dependencies import get_services, Services

router = APIRouter()


@router.get("/")
async def list_grants(
    status: Optional[str] = Query(None, description="Filter by status: active, inactive, upcoming"),
    funding_type: Optional[str] = Query(None, description="Filter by funding type"),
    limit: int = Query(20, ge=1, le=100),
    services: Services = Depends(get_services),
):
    """List all grants with optional filters."""
    selector = {}
    if status:
        selector["status"] = status
    if funding_type:
        selector["funding.funding_type"] = funding_type

    grants = services.cloudant.find_grants(selector=selector, limit=limit)
    return {"grants": grants, "total": len(grants)}


@router.get("/{grant_id}")
async def get_grant(
    grant_id: str,
    services: Services = Depends(get_services),
):
    """Get a single grant by ID."""
    grant = services.cloudant.get_document(grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail=f"Grant '{grant_id}' not found")
    return grant


@router.post("/search")
async def search_grants(
    request: dict,
    services: Services = Depends(get_services),
):
    """Search grants with structured filters."""
    from data.structured.data_validation import SearchGrantsInput
    from agent_tools import search_grants as search_fn

    search_input = SearchGrantsInput(**request)
    return search_fn(search_input)


@router.post("/semantic-search")
async def semantic_search(
    request: dict,
    services: Services = Depends(get_services),
):
    """Search grants using natural language."""
    query = request.get("query", "")
    limit = request.get("limit", 10)

    results = services.embedding.semantic_search_grants(query=query, n_results=limit)

    # Enrich with full grant data
    enriched = []
    for result in results:
        grant = services.cloudant.get_document(result["grant_id"])
        if grant:
            enriched.append({
                **result,
                "grant": grant,
            })

    return {"results": enriched, "total": len(enriched)}


@router.get("/{grant_id}/explain")
async def explain_grant(
    grant_id: str,
    services: Services = Depends(get_services),
):
    """Get an AI-generated explanation of a grant."""
    grant = services.cloudant.get_document(grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")

    explanation = services.watsonx.explain_grant(grant)
    return {"grant_id": grant_id, "explanation": explanation}
