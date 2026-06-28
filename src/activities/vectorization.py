import logging
import json
from typing import Dict, Any
from temporalio import activity
from src.schemas.pipeline_config import VectorizationConfig

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
async def embed_and_store_activity(text_to_embed: str, config: VectorizationConfig) -> str:
    """Mock for generating embedding and storing into pgvector."""
    logger.info(f"Embedding text using model {config.embedding_model} and storing to {config.collection_name}")
    # In a real implementation:
    # 1. Call OpenAI or local model to get embeddings
    # 2. Insert into pgvector
    import uuid
    external_id = str(uuid.uuid4())
    return external_id
