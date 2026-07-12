import os
import json
from dotenv import load_dotenv

# Load .env explicitly
load_dotenv()

from apps.api.config import get_settings
from apps.api.services.cloudant_service import CloudantService

def audit_cloudant():
    settings = get_settings()
    cloudant = CloudantService(
        api_key=settings.cloudant_api_key,
        url=settings.cloudant_url,
        database=settings.cloudant_database,
    )
    
    # Get all active grants just as the app does
    active_grants = cloudant.get_all_active_grants(limit=200)
    
    active_ids = [g.get('_id') for g in active_grants]
    
    print("=== 1. Every active grant ID in Cloudant ===")
    print(f"Total active grants: {len(active_ids)}")
    print(json.dumps(active_ids, indent=2))
    
    print("\n=== 2. Confirm BIRAC Grants Existence & Status ===")
    birac_ids = [
        "birac-biotechnology-ignition-grant",
        "birac-leap-fund",
        "birac-sbiri",
        "birac-seed-fund"
    ]
    
    for b_id in birac_ids:
        doc = cloudant.get_document(b_id)
        if doc:
            status = doc.get("status", "No status field")
            print(f"- {b_id}: Found in DB. Status = {status}")
        else:
            print(f"- {b_id}: NOT FOUND in DB.")

if __name__ == "__main__":
    audit_cloudant()
