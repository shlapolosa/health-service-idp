#!/usr/bin/env bash
# CAMUNDA-WORKFLOW: camunda/zeebe-worker variant scaffold.
#
# Mirrors lib/rasa.sh (RASA-CONTAINER #178): the generated service dir is
# VARIANT-ONLY — the dev-agent / developer edit surface:
#   processes/*.bpmn   the workflow definitions deployed to Zeebe
#   workers/*.py       the job-worker handler code a worker runs for each
#                      Zeebe service task (the business logic slot)
#   deploy/deploy.py   a THIN deploy step (deploy BPMN to the Zeebe gateway)
# plus a THIN Dockerfile (FROM zeebe-worker-base:vX.Y.Z + COPY) at the SAME path
# the generated-repo CI already watches (docker/worker/Dockerfile) so the
# pipeline keeps working unchanged — it just stops reinstalling deps on every
# build.
#
# Everything invariant (the pyzeebe runtime, python deps, the worker bootstrap
# that reads ZEEBE_ADDRESS from the orchestrator's <name>-conn secret, the
# graceful-shutdown loop) lives in the prebaked base image at
# factory/production-lines/traditional-cloud/adapters/zeebe-worker-base-image/
# (a follow-up build; the thin Dockerfile here references it by pinned tag).
#
# Every file is CREATE-IF-ABSENT (no-clobber), mirroring rasa's actions.py
# logic-slot pattern: the scaffold ships a minimal WORKING approval process
# (a single "review-request" service task wired to a worker that auto-approves)
# so the workflow deploys and an instance completes before any real logic lands;
# the dev-agent then edits processes/*.bpmn + workers/ in place and re-runs never
# overwrite them (#175 / RECREATE-STORM).
#
# HARD-3: the base image is pinned by version tag. NEVER :latest. Bumps are
# explicit edits to ZEEBE_WORKER_BASE_IMAGE_DEFAULT (or the ZEEBE_WORKER_BASE_IMAGE
# env var on the Job for canarying a new base).

ZEEBE_WORKER_BASE_IMAGE_DEFAULT="healthidpuaeacr.azurecr.io/zeebe-worker-base:v1.0.0"

mscv_scaffold_camunda() {
  BASE_IMAGE="${ZEEBE_WORKER_BASE_IMAGE:-$ZEEBE_WORKER_BASE_IMAGE_DEFAULT}"

  cd microservices/$SERVICE_NAME
  mkdir -p processes workers deploy docker/worker

  # --- processes/*.bpmn (VARIANT: the workflow definitions) ----------------
  # A minimal working approval process: start -> review-request (service task,
  # job type "review-request") -> approved? gateway -> end. The dev-agent edits
  # this in Camunda Modeler / by hand; it is the workflow design surface.
  if [ ! -f processes/approval.bpmn ]; then
    cat > processes/approval.bpmn << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!-- CAMUNDA-WORKFLOW: minimal working approval process for $SERVICE_NAME.
     Dev-agent edit surface — extend with real tasks/gateways here; the Zeebe
     runtime + workers connect via the orchestrator's <name>-conn secret. -->
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:zeebe="http://camunda.org/schema/zeebe/1.0"
                  id="Definitions_${SERVICE_NAME}"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="approval-process" name="Approval Process" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1" name="Request received">
      <bpmn:outgoing>Flow_start_review</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:serviceTask id="Task_review" name="Review request">
      <bpmn:extensionElements>
        <zeebe:taskDefinition type="review-request" />
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_start_review</bpmn:incoming>
      <bpmn:outgoing>Flow_review_end</bpmn:outgoing>
    </bpmn:serviceTask>
    <bpmn:endEvent id="EndEvent_1" name="Decision made">
      <bpmn:incoming>Flow_review_end</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_start_review" sourceRef="StartEvent_1" targetRef="Task_review" />
    <bpmn:sequenceFlow id="Flow_review_end" sourceRef="Task_review" targetRef="EndEvent_1" />
  </bpmn:process>
</bpmn:definitions>
EOF
  fi

  # --- workers/*.py (VARIANT: the job-worker handler logic slot) -----------
  if [ ! -f workers/__init__.py ]; then
    echo "" > workers/__init__.py
  fi

  if [ ! -f workers/handlers.py ]; then
    cat > workers/handlers.py << EOF
# CAMUNDA-WORKFLOW (#camunda): job-worker handler logic slot for $SERVICE_NAME.
#
# This is the dev-agent edit surface (the camunda analogue of rasa's actions.py
# and realtime's src/handlers.py): a passthrough default ships so the worker
# boots and completes "review-request" jobs before any real logic lands. Add a
# handler per Zeebe service-task job type; the base image's bootstrap registers
# every function decorated with @register here against the gateway from
# ZEEBE_ADDRESS (the orchestrator's <name>-conn secret, envFrom).
#
# Docs: https://camunda.com/docs/components/concepts/job-workers/
from typing import Any, Dict


# The base-image bootstrap discovers handlers via this registry (a tiny shim so
# the variant never imports the pyzeebe client directly — that lives in the
# base image). Map: Zeebe job type -> handler(variables) -> result variables.
HANDLERS: Dict[str, Any] = {}


def register(job_type: str):
    def _wrap(fn):
        HANDLERS[job_type] = fn
        return fn
    return _wrap


@register("review-request")
def review_request(variables: Dict[str, Any]) -> Dict[str, Any]:
    """Passthrough default — proves the worker is wired to the gateway and a
    process instance can complete. Replace with real review logic; return the
    variables the next BPMN element needs."""
    return {"approved": True, "reviewed_by": "$SERVICE_NAME-auto"}
EOF
  fi

  # --- deploy/deploy.py (THIN deploy step) ---------------------------------
  # Invoked by CI (or once at boot by the base image) to upload processes/*.bpmn
  # to the Zeebe gateway. Kept thin: the pyzeebe client + connection plumbing
  # live in the base image; this just enumerates the variant's BPMN files.
  if [ ! -f deploy/deploy.py ]; then
    cat > deploy/deploy.py << 'EOF'
# CAMUNDA-WORKFLOW: thin deploy step — upload processes/*.bpmn to Zeebe.
#
# The base image exposes deploy_processes(paths) which reads ZEEBE_ADDRESS from
# the orchestrator's <name>-conn secret (envFrom). This file just resolves the
# variant's BPMN paths so adding a new .bpmn requires no code change.
import glob
import os
import sys

from zeebe_worker_base import deploy_processes  # provided by the base image


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    bpmn = sorted(glob.glob(os.path.join(here, "..", "processes", "*.bpmn")))
    if not bpmn:
        print("no processes/*.bpmn to deploy", file=sys.stderr)
        return 0
    deploy_processes(bpmn)
    print("deployed: " + ", ".join(os.path.basename(p) for p in bpmn))
    return 0


if __name__ == "__main__":
    sys.exit(main())
EOF
  fi

  # --- thin Dockerfile (same CI-watched path convention as rasa) -----------
  if [ ! -f docker/worker/Dockerfile ]; then
    cat > docker/worker/Dockerfile << EOF
# CAMUNDA-WORKFLOW: THIN variant layer — the pyzeebe runtime + worker bootstrap
# live in zeebe-worker-base. Build context = this service directory. The worker
# connects to the Zeebe gateway via ZEEBE_ADDRESS (the orchestrator's
# <name>-conn secret, envFrom) and deploys processes/*.bpmn on start.
FROM $BASE_IMAGE
COPY --chown=1001:1001 . /app/workflow/
CMD ["worker"]
EOF
  fi

  echo "✅ Successfully created Camunda workflow microservice (variant-only, base image $BASE_IMAGE)"
}
