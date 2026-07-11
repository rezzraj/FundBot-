from fastapi import APIRouter, Depends, HTTPException

from apps.api.dependencies import get_services, Services

router = APIRouter()


@router.post("/draft")
async def create_draft(
    request: dict,
    services: Services = Depends(get_services),
):
    """Generate a proposal draft for a grant application."""
    grant_id = request.get("grant_id")
    profile_id = request.get("profile_id")
    additional_context = request.get("additional_context")

    grant = services.cloudant.get_document(grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")

    profile = {}
    if profile_id:
        profile = services.cloudant.get_document(profile_id) or {}

    draft = await services.drafting.generate_draft(
        grant=grant,
        profile=profile,
        additional_context=additional_context,
    )

    # Save as application in Cloudant
    app_data = {
        "profile_id": profile_id,
        "grant_id": grant_id,
        **draft,
    }
    saved = services.cloudant.create_application(app_data)

    return {**draft, "application_id": saved.get("id", "")}


@router.post("/{application_id}/refine")
async def refine_section(
    application_id: str,
    request: dict,
    services: Services = Depends(get_services),
):
    """Refine a specific section of a draft based on feedback."""
    app = services.cloudant.get_document(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    section_name = request.get("section")
    feedback = request.get("feedback")
    current_content = app.get("draft_content", {}).get(section_name, "")

    grant = services.cloudant.get_document(app.get("grant_id", "")) or {}
    profile = services.cloudant.get_document(app.get("profile_id", "")) or {}

    refined = await services.drafting.refine_section(
        section_name=section_name,
        current_content=current_content,
        feedback=feedback,
        grant=grant,
        profile=profile,
    )

    # Update the draft
    app["draft_content"][section_name] = refined
    services.cloudant.update_document(app)

    return {"section": section_name, "content": refined}


@router.get("/")
async def list_applications(
    profile_id: str = None,
    services: Services = Depends(get_services),
):
    """List all applications, optionally filtered by profile."""
    if profile_id:
        apps = services.cloudant.get_applications_for_profile(profile_id)
    else:
        apps = services.cloudant.find_grants(selector={"type": "application"})
    return {"applications": apps, "total": len(apps)}
