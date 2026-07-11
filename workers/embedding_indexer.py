import os
import json
import asyncio
from apps.api.config import get_settings
from apps.api.services.cloudant_service import CloudantService
from apps.api.services.watsonx_service import WatsonxService
from apps.api.services.embedding_service import EmbeddingService

async def rebuild_index(
    cloudant: CloudantService,
    embedding: EmbeddingService,
) -> dict:
    """Rebuild the complete vector index from Cloudant data."""
    grants = cloudant.get_all_active_grants(limit=500)
    count = embedding.index_all_grants(grants)
    return {"indexed": count, "status": "complete"}

async def main():
    settings = get_settings()
    cloudant = CloudantService(
        api_key=settings.cloudant_api_key, 
        url=settings.cloudant_url, 
        database=settings.cloudant_database
    )
    watsonx = WatsonxService(
        api_key=settings.watsonx_api_key,
        project_id=settings.watsonx_project_id,
        url=settings.watsonx_url,
        chat_model_id=settings.granite_chat_model,
        embedding_model_id=settings.granite_embedding_model,
        gemini_api_key=settings.gemini_api_key,
    )
    embedding_svc = EmbeddingService(watsonx_service=watsonx, persist_dir=settings.chroma_persist_dir)

    print("Fetching active grants from Cloudant...")
    result = await rebuild_index(cloudant, embedding_svc)
    print(f"Indexing complete. Indexed {result['indexed']} grants.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
