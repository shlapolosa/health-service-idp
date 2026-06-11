#!/usr/bin/env bash
# HARD-1 (#168): rasa/chatbot scaffold — heredoc lines 113-125 verbatim.
mscv_scaffold_rasa() {
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
