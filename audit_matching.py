import asyncio
import json
from dotenv import load_dotenv

load_dotenv()

from apps.api.config import get_settings
from apps.api.services.cloudant_service import CloudantService
from apps.api.services.embedding_service import EmbeddingService
from apps.api.services.matching_service import MatchingService
from tests.mocks.mock_watsonx import MockWatsonxService

async def trace_matching():
    settings = get_settings()
    cloudant = CloudantService(
        api_key=settings.cloudant_api_key,
        url=settings.cloudant_url,
        database=settings.cloudant_database,
    )
    
    # Using mock watsonx because real one throws 403 quota errors on embedding.
    # Wait, if I use mock watsonx, it won't actually query ChromaDB properly
    # because mock watsonx embedding returns a dummy array which won't match existing vectors.
    # Let me monkeypatch semantic search to just return the results directly from chromadb using a random vector
    # Or better yet, we just print the rule scores!
    # Let's print rule_scores and we can see if BIRAC grants score high enough in rule scores.
    
    watsonx = MockWatsonxService()
    embedding = EmbeddingService(watsonx_service=watsonx, persist_dir=settings.chroma_persist_dir)
    matching = MatchingService(watsonx=watsonx, cloudant=cloudant, embedding=embedding)
    
    profile = {
        "stage": "early-stage",
        "industries": ["biotechnology"],
        "location": {"country": "India"},
        "company_name": "BioTech Startup",
        "description": "We are a biotechnology startup developing new medical devices.",
        "funding_needed": {
            "amount": 5000000,
            "types": ["grant"],
            "currency": "INR"
        }
    }
    
    all_grants = cloudant.get_all_active_grants(limit=200)
    print(f"Total active grants: {len(all_grants)}")
    
    rule_scores = {}
    for grant in all_grants:
        gid = grant.get("_id", "")
        rule_scores[gid] = matching._rule_score(grant, profile)
        
    print("\n=== Rule Scores for BIRAC Grants ===")
    birac_ids = [
        "birac-biotechnology-ignition-grant",
        "birac-leap-fund",
        "birac-sbiri",
        "birac-seed-fund"
    ]
    
    for b_id in birac_ids:
        print(f"\n{b_id}:")
        print(json.dumps(rule_scores.get(b_id), indent=2))
        
    print("\n=== All Rule Scores Sorted ===")
    sorted_scores = sorted(rule_scores.items(), key=lambda x: x[1]['total'], reverse=True)
    for gid, score in sorted_scores:
        print(f"{gid}: {score['total']:.4f}")

if __name__ == "__main__":
    asyncio.run(trace_matching())
