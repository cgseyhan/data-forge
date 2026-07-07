import sys
import asyncio
import uuid
import json
from pathlib import Path
from temporalio.client import Client

# Add the src dir to path so we can import modules
sys.path.append(str(Path(__file__).parent.parent))

from src.schemas.pipeline_config import PipelineConfig

async def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/trigger_pipeline.py <config_path> <source>")
        print("Example: python scripts/trigger_pipeline.py src/configs/ecommerce_products.yaml 'https://example.com/product/1'")
        sys.exit(1)

    config_path = sys.argv[1]
    source = sys.argv[2]

    # Parse config
    try:
        config = PipelineConfig.from_yaml(config_path)
    except Exception as e:
        print(f"Failed to load config: {e}")
        sys.exit(1)

    print(f"Connecting to Temporal Server...")
    client = await Client.connect("localhost:7233")

    workflow_id = f"dataforge-{config.name}-{uuid.uuid4()}"
    
    print(f"Starting FullPipelineWorkflow for source: {source}")
    print(f"Workflow ID: {workflow_id}")

    try:
        result = await client.execute_workflow(
            "FullPipelineWorkflow",
            args=[source, config],
            id=workflow_id,
            task_queue="dataforge-task-queue",
        )
        print("\nWorkflow Completed Successfully!")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"\nWorkflow Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
