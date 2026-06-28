import logging
import os
import json
from typing import Dict, Any, List
from temporalio import activity
from openai import AsyncOpenAI
from src.schemas.pipeline_config import QARule

logger = logging.getLogger(__name__)

@activity.defn
async def run_deterministic_qa_activity(extracted_data: Dict[str, Any], rules: List[QARule]) -> Dict[str, Any]:
    """Runs deterministic checks like not_null or regex."""
    issues = []
    
    for rule in rules:
        if rule.rule_type == "not_null" and rule.field_name:
            val = extracted_data.get(rule.field_name)
            if val is None or val == "":
                issues.append({"field": rule.field_name, "error": "Cannot be null or empty"})
        
        elif rule.rule_type == "regex" and rule.field_name and rule.params:
            import re
            val = extracted_data.get(rule.field_name, "")
            pattern = rule.params.get("pattern", "")
            if not re.match(pattern, str(val)):
                issues.append({"field": rule.field_name, "error": f"Does not match pattern {pattern}"})
                
    passed = len(issues) == 0
    return {
        "passed": passed,
        "issues": issues,
        "score": 100.0 if passed else 0.0
    }

@activity.defn
async def run_llm_judge_activity(raw_content: str, extracted_data: Dict[str, Any], rule: QARule) -> Dict[str, Any]:
    """Runs LLM Judge for hallucination checks based on rule.llm_prompt."""
    if not rule.llm_prompt:
        return {"passed": True, "issues": [], "score": 100.0}

    logger.info("Running LLM Judge QA...")
    client = AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", "dummy"),
        base_url=os.environ.get("VLLM_API_BASE", "http://localhost:8000/v1")
    )
    
    system_prompt = (
        "You are an expert QA Judge. Compare the extracted JSON with the raw text. "
        "Your goal is to detect any hallucinations or errors. "
        "Output JSON with a 'passed' boolean and an 'issues' list."
    )
    
    user_prompt = rule.llm_prompt.format(
        text=raw_content,
        json=json.dumps(extracted_data, indent=2)
    )
    
    response = await client.chat.completions.create(
        model=os.environ.get("LLM_MODEL_NAME", "Qwen/Qwen2.5-32B-Instruct-AWQ"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.0
    )
    
    result = json.loads(response.choices[0].message.content)
    return {
        "passed": result.get("passed", False),
        "issues": result.get("issues", []),
        "score": 100.0 if result.get("passed", False) else 50.0
    }
