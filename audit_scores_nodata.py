import asyncio, json
from dotenv import load_dotenv; load_dotenv()
from apps.api.config import get_settings; from apps.api.services.cloudant_service import CloudantService; from apps.api.services.matching_service import MatchingService
from tests.mocks.mock_watsonx import MockWatsonxService; from apps.api.services.embedding_service import EmbeddingService

s=get_settings()
c=CloudantService(s.cloudant_api_key, s.cloudant_url, s.cloudant_database)
m=MatchingService(watsonx=MockWatsonxService(), cloudant=c, embedding=EmbeddingService(MockWatsonxService(), persist_dir=s.chroma_persist_dir))

profile = {
    'company_name': 'BioTech Innovators',
    'stage': 'early-stage',
    'industries': ['biotechnology'],
    'location': {'country': 'India'}
}
all_grants = c.get_all_active_grants(limit=200)
scores = []
for g in all_grants:
    r = m._rule_score(g, profile)
    scores.append({'id': g['_id'], 'score': r['total']})
scores.sort(key=lambda x: x['score'], reverse=True)
for x in scores[:10]:
    print(f"{x['id']}: {x['score']:.4f}")
