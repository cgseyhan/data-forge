import logging
import json
from typing import Dict, Any
from temporalio import activity
from src.schemas.pipeline_config import VectorizationConfig
from src.infrastructure.vector.pgvector_client import pgvector_client

logger = logging.getLogger(__name__)

@activity.defn
async def prepare_vector_text_activity(raw_content: str, extracted_data: Dict[str, Any], config: VectorizationConfig) -> str:
    """Prepares the text string to be vectorized based on config."""
    if config.source_field == "raw_content":
        return raw_content
    elif config.source_field == "extracted_json":
        if config.template:
            # Simple template replacement
            text = config.template
            for k, v in extracted_data.items():
                text = text.replace(f"{{{{{k}}}}}", str(v))
            return text
        else:
            return json.dumps(extracted_data)
    else:
        return ""

@activity.defn
async def embed_and_store_activity(text_to_embed: str, config: VectorizationConfig, tenant_id: str) -> str:
    """Uses pgvector_client to generate embeddings and store them with tenant isolation."""
    logger.info(f"Embedding text using model {config.embedding_model} and storing to {config.collection_name}")
    
    # Generate embeddings
    vector = await pgvector_client.get_embedding(text_to_embed, config.embedding_model)
    
    # Store into vector database tied to the tenant_id
    metadata = {
        "model": config.embedding_model,
        "source_field": config.source_field
    }
    
    external_id = await pgvector_client.store_vector(
        tenant_id=tenant_id,
        collection_name=config.collection_name,
        vector=vector,
        metadata=metadata
    )
    
    return external_id
