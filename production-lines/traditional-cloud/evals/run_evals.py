"""Foundry-native eval run for architect-v1.

Foundry invokes the agent itself (no Phase-1 target script needed):
  - data_source.target = {type: azure_ai_agent, id: architect-v1}
  - Foundry sends each row's `query` to the agent, captures sample.output_text + sample.output_items
  - Evaluators score per row; results land in the project's Evaluations tab.

Prereqs:
  - `az login` (or SP env vars in CI)
  - Env (defaults shown):
      AZURE_AI_PROJECT_ENDPOINT — usecase-architect-poc endpoint
      AZURE_AI_MODEL_DEPLOYMENT_NAME — gpt-5-mini (judge model)
      ARCHITECT_AGENT_ID — architect-v1

  - pip install "azure-ai-projects>=2.0.0" azure-identity
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

HERE = Path(__file__).parent
DATASET = HERE / "dataset.jsonl"

ENDPOINT = os.environ.get(
    "AZURE_AI_PROJECT_ENDPOINT",
    "https://aifoundry-socrates.services.ai.azure.com/api/projects/usecase-architect-poc",
)
JUDGE_MODEL = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5.4-mini")
AGENT_ID = os.environ.get("ARCHITECT_AGENT_ID", "architect-v1")
EVAL_NAME = os.environ.get("EVAL_NAME", "architect-v1-suite")
RUN_NAME = os.environ.get("RUN_NAME", f"run-{int(time.time())}")


def main() -> int:
    if not DATASET.exists():
        print(f"dataset not found: {DATASET}", file=sys.stderr)
        return 1

    project = AIProjectClient(endpoint=ENDPOINT, credential=DefaultAzureCredential())
    client = project.get_openai_client()

    print(f"uploading {DATASET}")
    ds = project.datasets.upload_file(
        name="architect-v1-eval-prompts",
        version=str(int(time.time())),
        file_path=str(DATASET),
    )
    print(f"  dataset_id={ds.id}")

    testing_criteria = [
        {
            "type": "azure_ai_evaluator",
            "name": "intent_resolution",
            "evaluator_name": "builtin.intent_resolution",
            "initialization_parameters": {"deployment_name": JUDGE_MODEL},
            "data_mapping": {
                "query": "{{item.query}}",
                "response": "{{sample.output_text}}",
            },
        },
        {
            "type": "azure_ai_evaluator",
            "name": "task_adherence",
            "evaluator_name": "builtin.task_adherence",
            "initialization_parameters": {"deployment_name": JUDGE_MODEL},
            "data_mapping": {
                "query": "{{item.query}}",
                "response": "{{sample.output_text}}",
            },
        },
        # tool_call_accuracy: deferred to v1.5 — requires `tool_definitions` mapping.
        # violence: not available in UAE North region — RAI safety classifier deferred to v1.5 or
        #   reroute eval to a region with content-harm support.
    ]

    print(f"creating eval '{EVAL_NAME}'")
    evaluation = client.evals.create(
        name=EVAL_NAME,
        data_source_config={
            "type": "custom",
            "item_schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "category": {"type": "string"},
                    "query": {"type": "string"},
                    "messages": {"type": "array"},
                },
                "required": ["query", "messages"],
            },
            "include_sample_schema": True,
        },
        testing_criteria=testing_criteria,
    )
    print(f"  eval_id={evaluation.id}")

    print(f"creating run '{RUN_NAME}' (target: agent {AGENT_ID})")
    eval_run = client.evals.runs.create(
        eval_id=evaluation.id,
        name=RUN_NAME,
        data_source={
            "type": "azure_ai_target_completions",
            "source": {"type": "file_id", "id": ds.id},
            "target": {"type": "azure_ai_agent", "name": AGENT_ID},
            "input_messages": {
                "type": "item_reference",
                "item_reference": "item.messages",
            },
        },
    )
    print(f"  run_id={eval_run.id}, status={eval_run.status}")

    print("polling to completion...")
    while True:
        run = client.evals.runs.retrieve(run_id=eval_run.id, eval_id=evaluation.id)
        print(f"  status={run.status}")
        if run.status in ("completed", "failed", "canceled"):
            break
        time.sleep(20)

    print(f"\nfinished: {run.status}")
    print(f"report: {getattr(run, 'report_url', '(see Foundry portal → Evaluations)')}")
    return 0 if run.status == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
