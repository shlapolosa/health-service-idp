#!/usr/bin/env bash
# HARD-1 (#168): template selection — extracted verbatim from heredoc lines 13-29.
# Sets TEMPLATE_REPO from LANGUAGE/FRAMEWORK; exits 1 on unsupported combos.
mscv_select_template() {
  # Determine template repository based on service type
  if [ "$LANGUAGE" = "python" ] && [ "$FRAMEWORK" = "fastapi" ]; then
    TEMPLATE_REPO="onion-architecture-template"
    echo "🏗️ Using onion architecture template for Python/FastAPI service"
  elif [ "$LANGUAGE" = "rasa" ] && [ "$FRAMEWORK" = "chatbot" ]; then
    TEMPLATE_REPO="chat-template"
    echo "🤖 Using chat template for RASA chatbot service"
  elif [ "$LANGUAGE" = "nodejs" ] && [ "$FRAMEWORK" = "graphql-gateway" ]; then
    TEMPLATE_REPO="graphql-federation-gateway-template"
    echo "🌐 Using GraphQL federation gateway template for Node.js/GraphQL service"
  elif [ "$LANGUAGE" = "java" ] && [ "$FRAMEWORK" = "springboot" ]; then
    TEMPLATE_REPO="identity-service-template"
    echo "Using identity-service template for Java/Spring Boot service"
  else
    echo "❌ Unsupported service type: $LANGUAGE/$FRAMEWORK"
    exit 1
  fi
}
