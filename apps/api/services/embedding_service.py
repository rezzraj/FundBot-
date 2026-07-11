import os
import chromadb
from typing import List, Dict, Any

from apps.api.services.watsonx_service import WatsonxService

class EmbeddingService:
    def __init__(self, watsonx_service: WatsonxService, persist_dir: str = "./chroma_data"):
        self.watsonx = watsonx_service
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection("grants")

    def embed_text(self, text: str) -> List[float]:
        return self.watsonx.embed_query(text)
        
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return self.watsonx.embed_texts(texts)

    def index_grant(self, grant_id: str, text_content: str, metadata: Dict[str, Any] = None):
        if not metadata:
            metadata = {}
        embedding = self.embed_text(text_content)
        self.collection.upsert(
            ids=[grant_id],
            embeddings=[embedding],
            documents=[text_content],
            metadatas=[metadata]
        )

    def search_similar_grants(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        query_embedding = self.embed_text(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit
        )
        return results

    def index_all_grants(self, grants: list) -> int:
        count = 0
        for grant in grants:
            # Build a comprehensive representation of the grant for semantic search
            parts = [
                f"Grant Name: {grant.get('grant_name', '')}",
                f"Description: {grant.get('description', '')}",
            ]
            
            eligibility = grant.get("eligibility", {})
            if eligibility:
                parts.append(f"Target Industries: {', '.join(eligibility.get('industries', []))}")
                parts.append(f"Target Stages: {', '.join(eligibility.get('startup_stages', []))}")
                parts.append(f"Allowed Locations: {', '.join(eligibility.get('allowed_locations', []))}")
            
            funding = grant.get("funding", {})
            if funding:
                f_type = funding.get("funding_type", "")
                f_max = funding.get("maximum_amount", "")
                parts.append(f"Funding Type: {f_type} | Max Amount: {f_max}")
                
            text_content = "\n".join(parts)
            self.index_grant(grant["_id"], text_content, {"type": grant.get("type", "funding_opportunity")})
            count += 1
        return count

    def semantic_search_grants(self, query: str, n_results: int = 10) -> list:
        results = self.search_similar_grants(query, limit=n_results)
        formatted = []
        if results and results['ids'] and len(results['ids']) > 0:
            for i, grant_id in enumerate(results['ids'][0]):
                formatted.append({
                    "grant_id": grant_id,
                    "document": results['documents'][0][i] if 'documents' in results and results['documents'] else ""
                })
        return formatted

    def search_similar_to_profile(self, profile: dict, n_results: int = 50) -> list:
        query = f"{profile.get('stage', '')} startup in {', '.join(profile.get('industries', []))}"
        results = self.search_similar_grants(query, limit=n_results)
        formatted = []
        if results and results['ids'] and len(results['ids']) > 0:
            for i, grant_id in enumerate(results['ids'][0]):
                dist = results['distances'][0][i] if 'distances' in results and results['distances'] else 0.0
                sim = max(0.0, 1.0 - (dist / 2.0))
                formatted.append({
                    "grant_id": grant_id,
                    "similarity_score": sim,
                    "document": results['documents'][0][i] if 'documents' in results and results['documents'] else ""
                })
        return formatted
