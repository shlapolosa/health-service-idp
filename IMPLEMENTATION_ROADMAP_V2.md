# Pattern-Based Architecture Implementation Roadmap (v2)

## Complete Component Inventory & Classification

Based on analysis of existing ComponentDefinitions only (no additions):

### Pattern 3: Infrastructural (Process First)
Components that provide infrastructure services, using existing images or external services.

#### Provider Systems (External Services)
1. **neon-postgres** - External PostgreSQL service ✅
2. **auth0-idp** - External identity provider ✅

#### Infrastructure Components (Internal Services)  
3. **postgresql** - Internal PostgreSQL via Helm ✅
4. **mongodb** - Internal MongoDB via Helm ✅
5. **redis** - Internal Redis via Helm ✅
6. **kafka** - Internal Kafka via Strimzi ✅
7. **clickhouse** - Analytics database ✅

#### Platform Services (Infrastructure with Logic)
8. **realtime-platform** - Streaming infrastructure (includes Kafka/MQTT) ✅
9. **camunda-orchestrator** - Workflow orchestration service ✅

### Pattern 2: Compositional (Process Second)
Components composed of multiple services that need orchestration.

1. **rasa-chatbot** - 3 containers (base, rasa, actions) ✅
2. **graphql-gateway** - Federation gateway ✅
3. **graphql-platform** - GraphQL infrastructure with Hasura ✅
4. **identity-service** - Complex domain service ✅

### Pattern 1: Foundational (Process Last)
Basic units of work that require a repository.

1. **webservice** - Standard microservices ✅
2. **webservice-k8s** - K8s deployment variant ✅
3. **vcluster** - Virtual clusters ✅

## Important Clarifications

1. **Removed application-infrastructure**: As requested, not including this
2. **Camunda-orchestrator vs Orchestration-platform**:
   - `camunda-orchestrator`: ComponentDefinition that creates the Camunda Knative Service (Pattern 3)
   - `orchestration-platform`: Crossplane Claim that creates supporting infrastructure (RBAC, ServiceAccounts)
   - Relationship: orchestration-platform provides infrastructure for camunda-orchestrator
3. **Kafka handling**: Covered by realtime-platform, no separate kafka/confluent-kafka needed
4. **Only existing components**: Not adding any undefined components

## Implementation Tasks

### Phase 0: Architecture Decision & Planning
**Duration**: 1 day
**Owner**: Architecture Team

- [ ] **Task 0.1**: Update ARCHITECTURAL_DECISIONS.md
  ```bash
  # Add decision record for pattern-based architecture
  # Reference: /tmp/pattern-architecture-final.md
  # Include: 3-2-1 pattern hierarchy, processing order, classification matrix
  # Document that kafka is handled by realtime-platform
  ```

- [ ] **Task 0.2**: Document component relationships
  ```markdown
  # Document orchestration-platform → camunda-orchestrator relationship
  # Document realtime-platform includes kafka functionality
  # No new components will be added
  ```

### Phase 1: Crossplane Claims & Compositions
**Duration**: 3 days
**Owner**: Platform Team

#### Pattern 3 Claims (Infrastructural)

- [ ] **Task 1.1**: Create ProviderSecretClaim XRD
  ```yaml
  # File: crossplane/provider-secret-claim-xrd.yaml
  # Reference: /tmp/oam-architectural-patterns-enhanced-v2.md
  apiVersion: apiextensions.crossplane.io/v1
  kind: CompositeResourceDefinition
  metadata:
    name: providersecretclaims.platform.io
  spec:
    group: platform.io
    names:
      kind: ProviderSecretClaim
      plural: providersecretclaims
    versions:
      - name: v1alpha1
        schema:
          openAPIV3Schema:
            properties:
              spec:
                properties:
                  providerType:
                    enum: [neon-postgres, auth0-idp]  # Only existing providers
                  credentials:
                    type: object
                  secretName:
                    type: string
  ```

- [ ] **Task 1.2**: Create ProviderSecretClaim Composition
  ```yaml
  # File: crossplane/provider-secret-claim-composition.yaml
  # Handles existing external service secrets only
  # Creates K8s Secret with connection details
  ```

- [ ] **Task 1.3**: Create InfrastructureClaim XRD
  ```yaml
  # File: crossplane/infrastructure-claim-xrd.yaml
  # Reference: /tmp/oam-architectural-patterns-enhanced-v2.md
  apiVersion: apiextensions.crossplane.io/v1
  kind: CompositeResourceDefinition
  metadata:
    name: infrastructureclaims.platform.io
  spec:
    group: platform.io
    names:
      kind: InfrastructureClaim
      plural: infrastructureclaims
    versions:
      - name: v1alpha1
        schema:
          openAPIV3Schema:
            properties:
              spec:
                properties:
                  infrastructureType:
                    enum: [postgresql, mongodb, redis, kafka, clickhouse]  # Only existing types
                  size:
                    enum: [small, medium, large]
                  version:
                    type: string
  ```

- [ ] **Task 1.4**: Create InfrastructureClaim Composition
  ```yaml
  # File: crossplane/infrastructure-claim-composition.yaml
  # Handles existing internal infrastructure only
  # Creates Helm releases based on infrastructureType
  ```

- [ ] **Task 1.5**: Test Claims
  ```bash
  # Create test claims for existing types only
  kubectl apply -f test/provider-secret-claim-test.yaml
  kubectl apply -f test/infrastructure-claim-test.yaml
  # Verify provisioning
  ```

### Phase 2: Argo Workflows
**Duration**: 3 days
**Owner**: Platform Team

#### Pattern 3: Infrastructural Workflows

- [ ] **Task 2.1**: Create pattern3-provider-workflow
  ```yaml
  # File: argo-workflows/pattern3-provider-workflow.yaml
  # Reference: /tmp/argo-workflow-templates-enhanced.yaml
  # Handles: neon-postgres, auth0-idp only
  apiVersion: argoproj.io/v1alpha1
  kind: WorkflowTemplate
  metadata:
    name: pattern3-provider-workflow
  spec:
    entrypoint: main
    templates:
      - name: main
        steps:
          - - name: validate-provider
          - - name: create-provider-claim
          - - name: create-secret
          - - name: create-service-binding
  ```

- [ ] **Task 2.2**: Create pattern3-infrastructure-workflow
  ```yaml
  # File: argo-workflows/pattern3-infrastructure-workflow.yaml
  # Handles: postgresql, mongodb, redis, kafka, clickhouse
  # Note: realtime-platform and camunda-orchestrator use existing workflows
  apiVersion: argoproj.io/v1alpha1
  kind: WorkflowTemplate
  metadata:
    name: pattern3-infrastructure-workflow
  spec:
    entrypoint: main
    templates:
      - name: main
        steps:
          - - name: create-infrastructure-claim
          - - name: wait-for-provisioning
          - - name: extract-connection-details
          - - name: create-service-monitor
  ```

#### Pattern 2: Compositional Workflows

- [ ] **Task 2.3**: Create pattern2-compositional-workflow
  ```yaml
  # File: argo-workflows/pattern2-compositional-workflow.yaml
  # Handles: rasa-chatbot, graphql-gateway, graphql-platform, identity-service
  apiVersion: argoproj.io/v1alpha1
  kind: WorkflowTemplate
  metadata:
    name: pattern2-compositional-workflow
  spec:
    entrypoint: main
    templates:
      - name: main
        dag:
          tasks:
            - name: check-appcontainer
            - name: add-to-monorepo
              dependencies: [check-appcontainer]
            - name: handle-build-strategy
              dependencies: [add-to-monorepo]
  ```

#### Pattern 1: Foundational Workflows

- [ ] **Task 2.4**: Update pattern1-foundational-workflow
  ```yaml
  # File: argo-workflows/pattern1-foundational-workflow.yaml
  # Keep existing microservice-standard-contract
  # Handles: webservice, webservice-k8s, vcluster
  apiVersion: argoproj.io/v1alpha1
  kind: WorkflowTemplate
  metadata:
    name: pattern1-foundational-workflow
  spec:
    entrypoint: main
    templates:
      - name: main
        steps:
          - - name: create-application-claim
          - - name: wait-for-repository
          - - name: update-gitops
  ```

- [ ] **Task 2.5**: Deploy and test workflows
  ```bash
  # Deploy all workflows
  kubectl apply -f argo-workflows/pattern*.yaml -n argo
  # Test each workflow with sample parameters
  argo submit -n argo --from workflowtemplate/pattern3-provider-workflow \
    -p provider_type=neon-postgres \
    -p secret_name=test-secret
  ```

### Phase 3: Slack API Server Implementation
**Duration**: 4 days
**Owner**: Backend Team

- [ ] **Task 3.1**: Create base pattern handler interface
  ```python
  # File: slack-api-server/src/domain/strategies/base.py
  # Reference: /tmp/slack-api-pattern-handlers.py
  from abc import ABC, abstractmethod
  
  class PatternHandler(ABC):
      @abstractmethod
      def can_handle(self, component_type: str) -> bool:
          pass
      
      @abstractmethod
      def get_workflow_name(self, component: Dict) -> str:
          pass
      
      @abstractmethod
      def prepare_workflow_params(self, component: Dict, context: HandlerContext) -> Dict:
          pass
  ```

- [ ] **Task 3.2**: Implement Pattern 3 Handler (Infrastructural)
  ```python
  # File: slack-api-server/src/domain/strategies/pattern3_handler.py
  class Pattern3Handler(PatternHandler):
      PROVIDER_TYPES = ["neon-postgres", "auth0-idp"]
      INFRASTRUCTURE_TYPES = ["postgresql", "mongodb", "redis", "kafka", "clickhouse"]
      PLATFORM_TYPES = ["realtime-platform", "camunda-orchestrator"]
      
      def get_workflow_name(self, component: Dict) -> str:
          component_type = component["type"]
          if component_type in self.PROVIDER_TYPES:
              return "pattern3-provider-workflow"
          elif component_type in self.INFRASTRUCTURE_TYPES:
              return "pattern3-infrastructure-workflow"
          elif component_type == "realtime-platform":
              return "realtime-platform-workflow"  # Existing workflow
          elif component_type == "camunda-orchestrator":
              return "orchestration-workflow"  # Existing workflow
  ```

- [ ] **Task 3.3**: Implement Pattern 2 Handler (Compositional)
  ```python
  # File: slack-api-server/src/domain/strategies/pattern2_handler.py
  class Pattern2Handler(PatternHandler):
      COMPOSITIONAL_TYPES = {
          "rasa-chatbot": {"template": "chat-template", "build_strategy": "multi-image"},
          "graphql-gateway": {"template": "graphql-federation-gateway-template"},
          "graphql-platform": {"uses_claim": "graphql-platform-claim"},
          "identity-service": {"template": "identity-service-template"}
      }
      
      def get_workflow_name(self, component: Dict) -> str:
          # All use same compositional workflow
          return "pattern2-compositional-workflow"
  ```

- [ ] **Task 3.4**: Implement Pattern 1 Handler (Foundational)
  ```python
  # File: slack-api-server/src/domain/strategies/pattern1_handler.py
  class Pattern1Handler(PatternHandler):
      SUPPORTED_TYPES = ["webservice", "webservice-k8s", "vcluster"]
      
      def get_workflow_name(self, component: Dict) -> str:
          component_type = component["type"]
          if component_type == "vcluster":
              return "vcluster-workflow"  # Existing workflow
          else:
              return "pattern1-foundational-workflow"
  ```

- [ ] **Task 3.5**: Implement Pattern Orchestrator with ordering
  ```python
  # File: slack-api-server/src/domain/strategies/orchestrator.py
  class PatternOrchestrator:
      def handle_oam_application(self, oam_application: Dict):
          components = oam_application["spec"]["components"]
          
          # Sort by pattern: 3 → 2 → 1
          pattern3 = []  # Infrastructure first
          pattern2 = []  # Compositional second
          pattern1 = []  # Foundational last
          
          for component in components:
              if self.is_pattern3(component):
                  pattern3.append(component)
              elif self.is_pattern2(component):
                  pattern2.append(component)
              else:
                  pattern1.append(component)
          
          # Process in order
          sorted_components = pattern3 + pattern2 + pattern1
          
          for component in sorted_components:
              handler = self.get_handler(component)
              result = handler.handle(component, context, self.argo_client)
  ```

- [ ] **Task 3.6**: Update webhook controller
  ```python
  # File: slack-api-server/src/interface/webhook_controller.py
  # Update to use PatternOrchestrator
  # Keep existing identity-service fix from previous changes
  # Keep existing webservice and identity-service handling
  ```

- [ ] **Task 3.7**: Add reference resolution
  ```python
  # File: slack-api-server/src/domain/services/reference_resolver.py
  def resolve_references(component, processed_components):
      """Resolve references to Pattern 3 components"""
      properties = component.get("properties", {})
      
      # Check for database reference
      if "database" in properties:
          db_ref = properties["database"]
          if db_ref in processed_components:
              properties["database_url"] = get_connection_string(db_ref)
      
      # Check for cache reference
      if "cache" in properties:
          cache_ref = properties["cache"]
          if cache_ref in processed_components:
              properties["cache_url"] = get_connection_string(cache_ref)
      
      # Check for realtime reference (existing pattern)
      if "realtime" in properties:
          rt_ref = properties["realtime"]
          if rt_ref in processed_components:
              properties["realtime_endpoint"] = get_endpoint(rt_ref)
  ```

- [ ] **Task 3.8**: Unit tests for all handlers
  ```python
  # File: slack-api-server/tests/test_pattern_handlers.py
  def test_pattern3_provider_handler():
      handler = Pattern3Handler()
      assert handler.can_handle("neon-postgres")
      assert handler.get_workflow_name({"type": "neon-postgres"}) == "pattern3-provider-workflow"
      
  def test_pattern3_platform_handler():
      handler = Pattern3Handler()
      assert handler.can_handle("realtime-platform")
      assert handler.get_workflow_name({"type": "realtime-platform"}) == "realtime-platform-workflow"
  ```

### Phase 4: Argo Events Configuration
**Duration**: 2 days
**Owner**: Platform Team

- [ ] **Task 4.1**: Verify Argo Events Sensor
  ```yaml
  # File: argo-events/oam-webhook-sensor.yaml
  # Ensure it routes to updated Slack API
  # No changes needed if webhook endpoint remains same
  ```

- [ ] **Task 4.2**: Test event flow
  ```bash
  # Create test OAM application with all pattern types
  kubectl apply -f test/mixed-pattern-oam-app.yaml
  # Monitor Argo Events processing
  kubectl logs -n argo-events deployment/webhook-eventsource -f
  ```

### Phase 5: Integration Testing
**Duration**: 3 days
**Owner**: QA Team

- [ ] **Task 5.1**: Test Pattern 3 components
  ```bash
  # Test provider systems
  scripts/test-functional-multicluster.sh  # Existing test
  # Test with neon-postgres
  # Test with auth0-idp
  
  # Test infrastructure components
  # Test postgresql, redis, mongodb
  # Test realtime-platform (includes kafka)
  # Test camunda-orchestrator
  ```

- [ ] **Task 5.2**: Test Pattern 2 components
  ```bash
  # Test compositional services
  # Test rasa-chatbot (3 images)
  # Test graphql-gateway
  # Test graphql-platform
  # Test identity-service
  ```

- [ ] **Task 5.3**: Test Pattern 1 components
  ```bash
  # Test foundational services
  # Test webservice with different languages
  # Test webservice-k8s variant
  # Test vcluster creation
  ```

- [ ] **Task 5.4**: Test reference resolution
  ```yaml
  # Create OAM app with references
  apiVersion: core.oam.dev/v1beta1
  kind: Application
  metadata:
    name: test-reference-app
  spec:
    components:
      - name: user-db
        type: postgresql  # Pattern 3
        properties:
          size: small
      - name: user-cache
        type: redis  # Pattern 3
        properties:
          size: small
      - name: streaming
        type: realtime-platform  # Pattern 3
        properties:
          enableKafka: true
      - name: user-service
        type: webservice  # Pattern 1
        properties:
          database: user-db  # Reference
          cache: user-cache   # Reference
          realtime: streaming # Reference
  ```

- [ ] **Task 5.5**: Test processing order
  ```bash
  # Verify Pattern 3 processes before Pattern 2 before Pattern 1
  kubectl logs -n default deployment/slack-api-server | grep "Processing pattern"
  # Should see:
  # Processing pattern 3: postgresql
  # Processing pattern 3: redis
  # Processing pattern 3: realtime-platform
  # Processing pattern 2: rasa-chatbot
  # Processing pattern 1: webservice
  ```

### Phase 6: Documentation & Cleanup
**Duration**: 2 days
**Owner**: All Teams

- [ ] **Task 6.1**: Update README.md
  ```markdown
  # Add sections:
  ## Pattern-Based Architecture
  - Pattern 3: Infrastructural (9 components)
  - Pattern 2: Compositional (4 components)
  - Pattern 1: Foundational (3 components)
  
  ## Component Processing Order: 3 → 2 → 1
  
  ## Important Notes
  - Kafka functionality is provided by realtime-platform
  - camunda-orchestrator is the service, orchestration-platform is the infrastructure
  ```

- [ ] **Task 6.2**: Update CLAUDE.md
  ```markdown
  # Add pattern classification guidelines
  # When classifying components:
  # 1. Check if infrastructural (no repo, existing images)
  # 2. Check if compositional (multiple services)  
  # 3. Default to foundational (single service, needs repo)
  ```

- [ ] **Task 6.3**: Create pattern documentation
  ```markdown
  # File: docs/PATTERN_ARCHITECTURE.md
  # Document:
  - Complete list of components by pattern
  - Processing order rationale
  - Reference resolution mechanism
  - No new components will be added
  ```

- [ ] **Task 6.4**: Clean up test artifacts
  ```bash
  # Remove test namespaces
  # Clean up test OAM applications
  # Archive old test scripts
  ```

- [ ] **Task 6.5**: Final validation
  ```bash
  # Run existing test suite
  ./scripts/test-functional-multicluster.sh
  # Verify all existing components work
  # Verify identity-service changes preserved
  ```

## Success Criteria

1. **Pattern 3 Components**: All 9 infrastructural components deploy successfully
2. **Pattern 2 Components**: All 4 compositional services work correctly
3. **Pattern 1 Components**: All 3 foundational services create repos and deploy
4. **Processing Order**: Components process in 3→2→1 order
5. **Reference Resolution**: Components can reference Pattern 3 infrastructure
6. **No Breaking Changes**: All existing OAM applications continue to work
7. **No New Components**: Only work with existing defined components

## Component Summary

### Total: 16 Components

**Pattern 3 (Infrastructural): 9 components**
- Providers: neon-postgres, auth0-idp
- Infrastructure: postgresql, mongodb, redis, kafka, clickhouse
- Platform: realtime-platform, camunda-orchestrator

**Pattern 2 (Compositional): 4 components**
- rasa-chatbot, graphql-gateway, graphql-platform, identity-service

**Pattern 1 (Foundational): 3 components**
- webservice, webservice-k8s, vcluster

## Key Clarifications

1. **No application-infrastructure**: Removed as requested
2. **orchestration-platform**: Is a Crossplane claim, not a component
3. **Kafka**: Handled by realtime-platform, no separate component needed
4. **Only existing components**: No new components will be added
5. **Identity-service fixes**: Preserved from previous work

## Timeline

- **Week 1**: Phases 0-2 (Architecture, Claims, Workflows)
- **Week 2**: Phase 3 (Slack API Implementation)
- **Week 3**: Phases 4-5 (Events, Testing)
- **Week 4**: Phase 6 (Documentation, Cleanup)