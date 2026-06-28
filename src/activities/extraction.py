import logging
import json
import os
from typing import Dict, Any
from temporalio import activity
from openai import AsyncOpenAI
from src.schemas.pipeline_config import ExtractionConfig

logger = logging.getLogger(__name__)

@activity.defn
async def extract_data_activity(raw_content: str, config: ExtractionConfig) -> Dict[str, Any]:
    """Uses LLM to extract JSON from raw content according to the pipeline schema."""
    logger.info("Extracting data via LLM...")
    
    client = AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", "dummy"),
        base_url=os.environ.get("VLLM_API_BASE", "http://localhost:8000/v1")
    )
    
    schema_str = json.dumps(config.schema_definition, indent=2)
    system_prompt = (
        "You are an expert data extraction engine. "
        "Extract information and output strictly valid JSON conforming to this schema:\n"
        f"{schema_str}"
    )
    
    user_prompt = config.prompt_template.replace("{text}", raw_content)
    
    response = await client.chat.completions.create(
        model=os.environ.get("LLM_MODEL_NAME", "Qwen/Qwen2.5-32B-Instruct-AWQ"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.0
    )
    
    content = response.choices[0].message.content
    return json.loads(content)
