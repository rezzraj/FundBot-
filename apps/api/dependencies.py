from dataclasses import dataclass
from functools import lru_cache

from apps.api.config import get_settings
from apps.api.services.watsonx_service import WatsonxService
from apps.api.services.cloudant_service import CloudantService
from apps.api.services.embedding_service import EmbeddingService
from apps.api.services.matching_service import MatchingService
from apps.api.services.drafting_service import DraftingService
from apps.api.services.guardian_service import GuardianService
from apps.api.services.agent_service import AgentService


@dataclass
class Services:
    watsonx: WatsonxService
    cloudant: CloudantService
    embedding: EmbeddingService
    matching: MatchingService
    drafting: DraftingService
    guardian: GuardianService
    agent: AgentService


@lru_cache()
def get_services() -> Services:
    settings = get_settings()
    if settings.use_mock_ai:
        return get_mock_services()

    watsonx = WatsonxService(
        api_key=settings.watsonx_api_key,
        project_id=settings.watsonx_project_id,
        url=settings.watsonx_url,
        chat_model_id=settings.granite_chat_model,
        embedding_model_id=settings.granite_embedding_model,
        gemini_api_key=settings.gemini_api_key,
    )

    cloudant = CloudantService(
        api_key=settings.cloudant_api_key,
        url=settings.cloudant_url,
        database=settings.cloudant_database,
    )

    embedding = EmbeddingService(
        watsonx_service=watsonx, 
        persist_dir=settings.chroma_persist_dir
    )

    matching = MatchingService(
        watsonx=watsonx,
        cloudant=cloudant,
        embedding=embedding,
    )

    drafting = DraftingService(
        watsonx=watsonx,
        embedding=embedding,
    )
    
    guardian = GuardianService(
        watsonx=watsonx,
    )

    agent = AgentService(
        watsonx=watsonx,
        cloudant=cloudant,
        matching=matching,
        drafting=drafting,
        embedding=embedding,
    )

    return Services(
        watsonx=watsonx,
        cloudant=cloudant,
        embedding=embedding,
        matching=matching,
        drafting=drafting,
        guardian=guardian,
        agent=agent,
    )


def get_mock_services() -> Services:
    from tests.mocks.mock_watsonx import MockWatsonxService
    from tests.mocks.mock_cloudant import MockCloudantService
    from apps.api.services.embedding_service import EmbeddingService
    from apps.api.services.matching_service import MatchingService
    from apps.api.services.drafting_service import DraftingService
    from apps.api.services.guardian_service import GuardianService
    from apps.api.services.agent_service import AgentService

    watsonx = MockWatsonxService()
    cloudant = MockCloudantService()
    
    # Use standard services wrap with the mock dependencies
    embedding = EmbeddingService(
        watsonx_service=watsonx, 
        persist_dir="./chroma_test"
    )
    
    matching = MatchingService(
        watsonx=watsonx,
        cloudant=cloudant,
        embedding=embedding,
    )
    
    drafting = DraftingService(
        watsonx=watsonx,
        embedding=embedding,
    )
    
    guardian = GuardianService(
        watsonx=watsonx,
    )
    
    agent = AgentService(
        watsonx=watsonx,
        cloudant=cloudant,
        matching=matching,
        drafting=drafting,
        embedding=embedding,
    )
    
    return Services(
        watsonx=watsonx,
        cloudant=cloudant,
        embedding=embedding,
        matching=matching,
        drafting=drafting,
        guardian=guardian,
        agent=agent,
    )
