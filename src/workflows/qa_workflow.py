from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from typing import Dict, Any, List

with workflow.unsafe.imports_passed_through():
    from src.activities.qa import run_deterministic_qa_activity, run_llm_judge_activity
    from src.schemas.pipeline_config import QARule
    from src.activities.database import (
        update_record_status_activity,
        save_qa_result_activity,
    )


@workflow.defn(name="QAWorkflow")
class QAWorkflow:
    @workflow.run
    async def run(
        self,
        record_id: str,
        raw_content: str,
        extracted_json: Dict[str, Any],
        rules: List[QARule],
        tenant_id: str = "",
    ) -> dict:
        retry_policy = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=5))
        db_retry = RetryPolicy(maximum_attempts=5, initial_interval=timedelta(seconds=2))

        # ── 1. Status: QA_PENDING ─────────────────────────────────────────────
        await workflow.execute_activity(
            update_record_status_activity,
            args=[record_id, "QA_PENDING"],
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=db_retry
        )

        all_issues = []
        passed = True

        # ── 2. Deterministic QA ───────────────────────────────────────────────
        det_result = await workflow.execute_activity(
            run_deterministic_qa_activity,
            args=[extracted_json, rules],
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=retry_policy
        )

        if not det_result.get("passed", False):
            passed = False
            all_issues.extend(det_result.get("issues", []))

        # DB'ye deterministic QA sonucunu kaydet
        await workflow.execute_activity(
            save_qa_result_activity,
            args=[
                record_id,
                "deterministic",
                "PASSED" if det_result.get("passed", False) else "FAILED",
                det_result.get("score", 0.0),
                tenant_id,
                det_result.get("issues", []),
            ],
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=db_retry
        )

        # ── 3. LLM Judge QA ───────────────────────────────────────────────────
        for rule in rules:
            if rule.rule_type == "llm_judge" and passed:
                llm_result = await workflow.execute_activity(
                    run_llm_judge_activity,
                    args=[raw_content, extracted_json, rule],
                    start_to_close_timeout=timedelta(minutes=3),
                    retry_policy=retry_policy
                )
                if not llm_result.get("passed", False):
                    passed = False
                    all_issues.extend(llm_result.get("issues", []))

                # DB'ye LLM Judge sonucunu kaydet
                await workflow.execute_activity(
                    save_qa_result_activity,
                    args=[
                        record_id,
                        "llm_judge",
                        "PASSED" if llm_result.get("passed", False) else "FAILED",
                        llm_result.get("score", 0.0),
                        tenant_id,
                        llm_result.get("issues", []),
                    ],
                    start_to_close_timeout=timedelta(seconds=15),
                    retry_policy=db_retry
                )

        # ── 4. Nihai QA statüsünü kaydet ─────────────────────────────────────
        final_status = "QA_PASSED" if passed else "QA_FAILED"
        await workflow.execute_activity(
            update_record_status_activity,
            args=[record_id, final_status],
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=db_retry
        )

        return {
            "status": final_status,
            "record_id": record_id,
            "issues": all_issues,
        }
