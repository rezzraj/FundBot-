from fastapi import APIRouter, Depends, HTTPException

from apps.api.dependencies import get_services, Services

router = APIRouter()


@router.post("/")
async def create_profile(
    request: dict,
    services: Services = Depends(get_services),
):
    """Create a new startup profile."""
    # Ensure it's marked as a profile
    request["type"] = "startup_profile"
    
    # Save to cloudant
    # We would ideally use cloudant.create_document, assuming we have one, or just update_document with a new ID
    # Since we might not have create_profile explicitly in cloudant_service snippet, let's use the generic append logic
    # or assume create_document exists. Let's just create a new document with an auto-generated or provided ID
    if "_id" not in request:
        import uuid
        request["_id"] = f"profile-{uuid.uuid4().hex[:8]}"
        
    services.cloudant.update_document(request)
    return {"profile_id": request["_id"], "status": "created"}


@router.get("/{profile_id}")
async def get_profile(
    profile_id: str,
    services: Services = Depends(get_services),
):
    """Get a startup profile by ID."""
    profile = services.cloudant.get_document(profile_id)
    if not profile or profile.get("type") != "startup_profile":
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("/{profile_id}")
async def update_profile(
    profile_id: str,
    request: dict,
    services: Services = Depends(get_services),
):
    """Update an existing startup profile."""
    profile = services.cloudant.get_document(profile_id)
    if not profile or profile.get("type") != "startup_profile":
        raise HTTPException(status_code=404, detail="Profile not found")

    # Update fields
    for k, v in request.items():
        if k not in ["_id", "_rev", "type"]:
            profile[k] = v

    services.cloudant.update_document(profile)
    return profile


@router.delete("/{profile_id}")
async def delete_profile(
    profile_id: str,
    services: Services = Depends(get_services),
):
    """Delete a startup profile by ID."""
    profile = services.cloudant.get_document(profile_id)
    if not profile or profile.get("type") != "startup_profile":
        raise HTTPException(status_code=404, detail="Profile not found")
    services.cloudant.delete_document(profile_id, profile["_rev"])
    return {"status": "deleted"}
