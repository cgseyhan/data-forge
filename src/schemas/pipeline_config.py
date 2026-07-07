from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class QARule(BaseModel):
    rule_type: str = Field(..., description="e.g., 'not_null', 'regex', 'llm_judge'")
    field_name: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    llm_prompt: Optional[str] = None

class ExtractionConfig(BaseModel):
    schema_definition: Dict[str, Any] = Field(..., description="JSON schema for extraction")
    prompt_template: str = Field(..., description="Prompt template for LLM (use {text} for raw content)")

class VectorizationConfig(BaseModel):
    source_field: str = Field(..., description="e.g., 'raw_content', 'extracted_json'")
    template: Optional[str] = Field(None, description="Template for formatting JSON into text for embedding")
    embedding_model: str = Field("default", description="Model to use for embedding")
    collection_name: str = Field(..., description="Vector DB collection/table name")

class PipelineConfig(BaseModel):
    name: str = Field(..., description="Name of the pipeline, e.g., 'legal_contracts'")
    version: str = Field(..., description="Version of the pipeline, e.g., '1.0.0'")
    input_type: str = Field("url", description="url, text, file, pdf_scan, audio, or image")
    
    extraction: Optional[ExtractionConfig] = None
    qa_rules: List[QARule] = Field(default_factory=list)
    vectorization: Optional[VectorizationConfig] = None

    @classmethod
    def from_yaml(cls, file_path: str) -> "PipelineConfig":
        import yaml
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)
