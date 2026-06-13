#!/usr/bin/env bash
# HARD-1 (#168): rasa/chatbot scaffold.
#
# RASA-CONTAINER (#178): invariant container + variant repo.
# The generated service dir is now VARIANT-ONLY — the dev-agent edit surface:
#   domain.yml, config.yml, data/{nlu,stories,rules}.yml, actions/actions.py
# plus two THIN Dockerfiles (FROM rasa-base:vX.Y.Z + COPY) at the SAME paths
# the generated-repo CI already watches (docker/rasa/Dockerfile,
# docker/rasa-actions/Dockerfile) so the pipeline keeps working unchanged —
# it just stops reinstalling deps and retraining on every build.
#
# Everything invariant (rasa runtime, python deps, server settings,
# endpoints/credentials plumbing, train-cache entrypoint) lives in
# factory/production-lines/traditional-cloud/adapters/rasa-base-image/.
#
# Every file is CREATE-IF-ABSENT (no-clobber), mirroring the src/handlers.py
# logic-slot pattern from RT-2 (#176): the scaffold ships a minimal WORKING
# bot (greet/goodbye/bot_challenge + a passthrough action_health_check) so the
# service boots and trains before any real logic lands; the dev-agent then
# edits these files in place and re-runs never overwrite them (#175).
#
# HARD-3: the base image is pinned by version tag. NEVER :latest. Bumps are
# explicit edits to RASA_BASE_IMAGE_DEFAULT (or the RASA_BASE_IMAGE env var
# on the Job for canarying a new base).
#
# The pre-#178 template-copy scaffold is preserved verbatim as
# mscv_scaffold_rasa_legacy (RASA_SCAFFOLD_MODE=legacy) until the base image
# is proven, then it can be deleted.

# v1.1.0: deterministic train-cache (#178) — boot reuses the CI-baked model
# instead of re-training. The fingerprint + sidecar .bot-hash change boot
# behavior, so the tag is bumped from v1.0.0. NEVER :latest (HARD-3).
RASA_BASE_IMAGE_DEFAULT="healthidpuaeacr.azurecr.io/rasa-base:v1.1.0"

mscv_scaffold_rasa() {
  if [ "${RASA_SCAFFOLD_MODE:-base-image}" = "legacy" ]; then
    mscv_scaffold_rasa_legacy
    return
  fi

  BASE_IMAGE="${RASA_BASE_IMAGE:-$RASA_BASE_IMAGE_DEFAULT}"

  cd microservices/$SERVICE_NAME
  mkdir -p data actions docker/rasa docker/rasa-actions

  # --- domain.yml (VARIANT: assistant identity, intents, responses) --------
  if [ ! -f domain.yml ]; then
    cat > domain.yml << EOF
version: "3.1"

# $SERVICE_NAME Support Bot — minimal working domain (RASA-CONTAINER #178).
# This file is the dev-agent edit surface: extend intents/responses/actions
# here; the rasa runtime itself lives in the rasa-base image.
intents:
  - greet
  - goodbye
  - bot_challenge
  - health_check

responses:
  utter_greet:
    - text: "Hello from $SERVICE_NAME Support Bot! How can I help you today?"
  utter_goodbye:
    - text: "Goodbye! Talk to you soon."
  utter_iamabot:
    - text: "I am $SERVICE_NAME Support Bot, powered by Rasa."

actions:
  - action_health_check

session_config:
  session_expiration_time: 60
  carry_over_slots_to_new_session: true
EOF
  fi

  # --- config.yml (VARIANT: NLU pipeline + dialogue policies) --------------
  if [ ! -f config.yml ]; then
    cat > config.yml << 'EOF'
# NLU pipeline + dialogue policies (RASA-CONTAINER #178 — variant surface).
# Same proven defaults as the chat-template; tune here, never in the image.
recipe: default.v1
language: en

pipeline:
  - name: WhitespaceTokenizer
  - name: RegexFeaturizer
  - name: LexicalSyntacticFeaturizer
  - name: CountVectorsFeaturizer
  - name: CountVectorsFeaturizer
    analyzer: char_wb
    min_ngram: 1
    max_ngram: 4
  - name: DIETClassifier
    epochs: 100
    constrain_similarities: true
  - name: EntitySynonymMapper
  - name: ResponseSelector
    epochs: 100
    constrain_similarities: true
  - name: FallbackClassifier
    threshold: 0.3
    ambiguity_threshold: 0.1

policies:
  - name: MemoizationPolicy
  - name: RulePolicy
  - name: TEDPolicy
    max_history: 5
    epochs: 100
    constrain_similarities: true
EOF
  fi

  # --- training data (VARIANT) ---------------------------------------------
  if [ ! -f data/nlu.yml ]; then
    cat > data/nlu.yml << 'EOF'
version: "3.1"

nlu:
  - intent: greet
    examples: |
      - hey
      - hello
      - hi
      - good morning
      - good evening
      - hey there
  - intent: goodbye
    examples: |
      - bye
      - goodbye
      - see you later
      - have a nice day
      - cya
  - intent: bot_challenge
    examples: |
      - are you a bot?
      - are you a human?
      - am I talking to a bot?
      - who are you?
  - intent: health_check
    examples: |
      - are you up?
      - health check
      - status
      - is the service running?
      - ping
EOF
  fi

  if [ ! -f data/rules.yml ]; then
    cat > data/rules.yml << 'EOF'
version: "3.1"

rules:
  - rule: Say hello whenever the user greets
    steps:
      - intent: greet
      - action: utter_greet
  - rule: Say goodbye whenever the user says goodbye
    steps:
      - intent: goodbye
      - action: utter_goodbye
  - rule: Answer the bot challenge
    steps:
      - intent: bot_challenge
      - action: utter_iamabot
  - rule: Run the health check action
    steps:
      - intent: health_check
      - action: action_health_check
EOF
  fi

  if [ ! -f data/stories.yml ]; then
    cat > data/stories.yml << 'EOF'
version: "3.1"

stories:
  - story: greet and leave
    steps:
      - intent: greet
      - action: utter_greet
      - intent: goodbye
      - action: utter_goodbye
EOF
  fi

  # --- actions (VARIANT: the custom-code logic slot, like src/handlers.py) -
  if [ ! -f actions/__init__.py ]; then
    echo "" > actions/__init__.py
  fi

  if [ ! -f actions/actions.py ]; then
    cat > actions/actions.py << EOF
# RASA-CONTAINER (#178): custom-action logic slot for $SERVICE_NAME.
#
# This is the dev-agent edit surface (the rasa analogue of src/handlers.py in
# realtime services): a passthrough default ships so the actions server boots
# and answers /webhook before any real logic lands. Add Action subclasses
# here and declare them under "actions:" in domain.yml.
#
# Docs: https://rasa.com/docs/rasa/custom-actions
from typing import Any, Dict, List, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher


class ActionHealthCheck(Action):
    """Passthrough default — proves the actions container is wired up."""

    def name(self) -> Text:
        return "action_health_check"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(text="$SERVICE_NAME actions server is up.")
        return []
EOF
  fi

  # --- thin Dockerfiles (same CI-watched paths as the legacy template) ------
  if [ ! -f docker/rasa/Dockerfile ]; then
    cat > docker/rasa/Dockerfile << EOF
# RASA-CONTAINER (#178): THIN variant layer — all deps live in rasa-base.
# Build context = this service directory. The RUN bakes the trained model at
# build time; the entrypoint's content-hash cache makes it a no-op at boot.
FROM $BASE_IMAGE
COPY --chown=1001:1001 . /app/bot/
RUN train-if-needed.sh
EOF
  fi

  if [ ! -f docker/rasa-actions/Dockerfile ]; then
    cat > docker/rasa-actions/Dockerfile << EOF
# RASA-CONTAINER (#178): THIN variant layer for the actions server.
# Same base, "actions" mode (rasa run actions --actions actions --port 5055).
FROM $BASE_IMAGE
COPY --chown=1001:1001 . /app/bot/
CMD ["actions"]
EOF
  fi

  echo "✅ Successfully created RASA chatbot microservice (variant-only, base image $BASE_IMAGE)"
}

# Pre-#178 template-copy scaffold, byte-preserved (heredoc lines 113-125 of
# the original Job). Reachable via RASA_SCAFFOLD_MODE=legacy until rasa-base
# is proven in a live chatbot, then delete.
mscv_scaffold_rasa_legacy() {
  # Copy chat template structure
  cp -r $TEMPLATE_DIR/microservices/chat-template/* microservices/$SERVICE_NAME/
  cd microservices/$SERVICE_NAME

  # Customize template for the specific service
  sed -i "s/chat-template/$SERVICE_NAME/g" README.md docker-compose.yml
  sed -i "s/Development Bot/$SERVICE_NAME Bot/g" docker-compose.yml
  sed -i "s/Customer Support Bot/$SERVICE_NAME Support Bot/g" domain.yml

  # Update OAM files
  find oam/ -name "*.yaml" -exec sed -i "s/chat-template/$SERVICE_NAME/g" {} \;

  echo "✅ Successfully created RASA chatbot microservice from template"
}
