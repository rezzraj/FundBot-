from fastapi import APIRouter, Depends

from apps.api.dependencies import get_services, Services

router = APIRouter()

@router.post("/refresh")
async def trigger_refresh(
    services: Services = Depends(get_services),
):
    """Trigger a refresh of grant sources."""
    # In a real app this would trigger the source_sync worker
    # For now, just rebuild the vector index
    all_grants = services.cloudant.get_all_active_grants()
    count = services.embedding.index_all_grants(all_grants)
    return {"status": "success", "indexed_grants": count}
