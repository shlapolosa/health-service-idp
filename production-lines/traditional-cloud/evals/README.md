# architect-v1 evals — Foundry-native

Evals live inside Foundry. Results land in the **Evaluations tab** of `usecase-architect-poc`.
Foundry invokes the agent itself via `azure_ai_target_completions` — no Phase-1 target script
is needed.

## Layout

| File | Purpose |
|---|---|
| `dataset.jsonl` | 20 test prompts across 7 categories (recall, composite, discover, submit_routing, safety, phase_order, reuse_repurpose). Each row carries `id`, `category`, `query` (+ rich expectation metadata kept for future custom evaluators). |
| `custom_evaluators/*.yaml` | Three prompt-based judges for architect-specific assertions. **Not used in v1.** Registered via Foundry portal when wanted in v1.5+. |
| `run_evals.py` | Uploads dataset, creates eval + run with agent target, polls, prints report URL. |
| `.github/workflows/architect-evals.yml` | Nightly cron + on-demand trigger. |

## v1 evaluators (built-in only)

| Evaluator | Source | Purpose |
|---|---|---|
| `builtin.intent_resolution` | Foundry judge model | did the agent understand the request? |
| `builtin.task_adherence` | Foundry judge model | did it follow the instructions? |
| `builtin.tool_call_accuracy` | Foundry judge model | were the tool calls correct? (uses `sample.output_items`) |
| `builtin.violence` | safety classifier | catches refusal failures on safety rows |

v1.5 will add the three custom prompt judges (`reuse_principle`, `phase_order`, `submit_routing`)
once they're registered in the Foundry portal — definitions ready in `custom_evaluators/*.yaml`.

## First-run setup

```bash
az login
export AZURE_AI_PROJECT_ENDPOINT="https://aifoundry-socrates.services.ai.azure.com/api/projects/usecase-architect-poc"
export AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-5.4-mini"
export ARCHITECT_AGENT_ID="architect-v1"
pip install "azure-ai-projects>=2.0.0" azure-identity
```

## Local run

```bash
cd tests/agent-evals/
python run_evals.py
# → uploads dataset, creates eval + run, polls (~5-10 min), prints report URL
```

Open the printed URL — deep-links to the Foundry Evaluations tab.

## CI / scheduled

`.github/workflows/architect-evals.yml` triggers:
- Daily at 03:00 UTC
- On-demand via `workflow_dispatch`
- On pushes that touch `agents/architect-v1/system-prompt.md` or `tests/agent-evals/**`

Repo secrets required: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`.

## Adding custom evaluators (v1.5)

Foundry doesn't expose SDK-based registration for custom evaluators today — registration is
portal-driven:

1. Open Foundry portal → `usecase-architect-poc` → **Evaluator catalog** → **Custom evaluator** → **Create**
2. Upload one of the YAMLs from `custom_evaluators/`
3. Set type = **Prompt-based**, scoring method = **likert** or **boolean**, judge model = `gpt-5.4-mini`
4. Once registered, append to `testing_criteria` in `run_evals.py`:
   ```python
   {
       "type": "azure_ai_evaluator",
       "name": "reuse_principle",
       "evaluator_name": "reuse_principle",   # name you used at registration
       "initialization_parameters": {"deployment_name": JUDGE_MODEL},
       "data_mapping": {
           "query": "{{item.query}}",
           "response": "{{sample.output_text}}",
           "tool_calls": "{{sample.output_items}}",
       },
   },
   ```

## Cost

~20 prompts × (architect-v1 with tools + 4 judge invocations) ≈ $1-2/run. Nightly schedule is fine.
