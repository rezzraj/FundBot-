import os
import json
from apps.api.services.watsonx_service import WatsonxService
from apps.api.services.embedding_service import EmbeddingService
from apps.api.config import get_settings

def run_audit():
    settings = get_settings()
    watsonx = WatsonxService(
        api_key=settings.watsonx_api_key,
        project_id=settings.watsonx_project_id,
        url=settings.watsonx_url,
    )
    embedding = EmbeddingService(watsonx_service=watsonx, persist_dir=settings.chroma_persist_dir)
    
    # 1. Profile being queried
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
    
    # Constructing query parts just like matching_service.py does
    description = profile.get('description', '').strip()
    raw_loc = profile.get('location', {})
    loc_str = raw_loc.get('country', 'India') if isinstance(raw_loc, dict) else raw_loc
    query_parts = [
        f"Company: {profile.get('company_name', 'Unknown')}",
        f"Industry: {', '.join(profile.get('industries', []))}",
        f"Stage: {profile.get('stage', 'unknown')}",
        f"Location: {loc_str}",
        f"Description: {description}",
    ]
    funding_needed = profile.get("funding_needed", {})
    if funding_needed.get("types"):
        query_parts.append(f"Looking for: {', '.join(funding_needed['types'])}")
    query = "\n".join(query_parts)

    print("=== 1 & 2. Exact text converted into an embedding ===")
    print("Yes, it includes the startup profile (company, industry, stage, location, description, funding needed).")
    print("=== 3. Exact query embedding input ===")
    print(repr(query))
    
    # Let's get the embedding to print (skip printing full array, just show we got it)
    query_embedding = embedding.embed_text(query)
    
    limit = 50
    print(f"\n=== 4. ChromaDB query call ===")
    print("self.collection.query(")
    print("    query_embeddings=[query_embedding],")
    print(f"    n_results={limit}")
    print(")")
    
    print(f"\n=== 5. Value of n_results ===")
    print(limit)
    
    print("\n=== 6. Any metadata filters used ===")
    print("None in ChromaDB query call (no `where` clause used).")

    # Actually perform the query
    results = embedding.collection.query(
        query_embeddings=[query_embedding],
        n_results=limit
    )

    print("\n=== 7 & 8. Raw retrieval results BEFORE any reranking/filtering and Similarity Scores ===")
    
    if results and results['ids'] and len(results['ids']) > 0:
        for i, grant_id in enumerate(results['ids'][0]):
            dist = results['distances'][0][i] if 'distances' in results and results['distances'] else 0.0
            # From matching_service.py: similarity = 1.0 - distance
            similarity = 1.0 - dist
            doc = results['documents'][0][i] if 'documents' in results and results['documents'] else ""
            print(f"Rank {i+1}: ID={grant_id} | Distance={dist:.4f} | Similarity={similarity:.4f}")
            if "birac" in grant_id.lower() or "biotechnology" in doc.lower():
                print(f"   => Matched BIRAC or Biotech. Doc preview: {doc[:150].replace(chr(10), ' ')}")

    # Fetch BIRAC from Chroma to see why it wasn't retrieved
    all_docs = embedding.collection.get()
    birac_docs = [g_id for g_id in all_docs['ids'] if 'birac' in g_id.lower()]
    print("\n=== 9. Explain why the BIRAC grants were not retrieved ===")
    print("Checking if BIRAC is in ChromaDB...")
    print(f"Found BIRAC grants in ChromaDB: {birac_docs}")
    for b_id in birac_docs:
        idx = all_docs['ids'].index(b_id)
        print(f"BIRAC Doc ID: {b_id}")
        print(f"BIRAC Doc Text: {repr(all_docs['documents'][idx])}")
    
run_audit()
