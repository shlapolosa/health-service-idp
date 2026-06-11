#!/usr/bin/env bash
# HARD-1 (#168): java/springboot scaffold — heredoc lines 166-175 verbatim.
mscv_scaffold_java_springboot() {
  # Copy Spring Boot identity service from the NESTED template layout
  # (identity-service-template/microservices/identity-template/, like the
  # rasa + nodejs templates) - copying the repo root nested a second
  # microservices/ level and CI could not find the Dockerfile.
  cp -r $TEMPLATE_DIR/microservices/identity-template/* microservices/$SERVICE_NAME/
  cd microservices/$SERVICE_NAME
  # Customize artifact + references for the specific service
  [ -f pom.xml ] && sed -i "s/identity-template/$SERVICE_NAME/g; s/identity-service/$SERVICE_NAME/g" pom.xml
  find . \( -name "*.yaml" -o -name "*.yml" -o -name "*.md" \) -exec sed -i "s/identity-template/$SERVICE_NAME/g" {} \;
  echo "✅ Successfully created Spring Boot identity microservice from template"
}
