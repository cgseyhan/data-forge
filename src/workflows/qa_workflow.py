from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from typing import Dict, Any, List

with workflow.unsafe.imports_passed_through():
    from src.activities.qa import run_deterministic_qa_activity, run_llm_judge_activity
    from src.schemas.pipeline_config import QARule

@workflow.defn(name="QAWorkflow")
class QAWorkflow:
    @workflow.run
    async def run(self, raw_content: str, extracted_json: Dict[str, Any], rules: List[QARule]) -> dict:
        retry_policy = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=5))
        
        all_issues = []
        passed = True
        
        # 1. Deterministic QA
        det_result = await workflow.execute_activity(
            run_deterministic_qa_activity,
            args=[extracted_json, rules],
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=retry_policy
        )
        
        if not det_result.get("passed", False):
            passed = False
            all_issues.extend(det_result.get("issues", []))
            
        # 2. LLM Judge QA for specific rules
        for rule in rules:
            if rule.rule_type == "llm_judge" and passed: # Skip LLM if deterministic already failed
                llm_result = await workflow.execute_activity(
                    run_llm_judge_activity,
                    args=[raw_content, extracted_json, rule],
                    start_to_close_timeout=timedelta(minutes=3),
                    retry_policy=retry_policy
                )
                if not llm_result.get("passed", False):
                    passed = False
                    all_issues.extend(llm_result.get("issues", []))
                    
        return {
            "status": "QA_PASSED" if passed else "QA_FAILED",
            "issues": all_issues
        }
