# Standardized Parameter Contract for Argo Workflows

## 🎯 Purpose

This document defines the **Standardized Parameter Contract** for all Argo Workflow templates in the health-service-idp platform. This contract ensures **consistency**, **extensibility**, and **maintainability** across all workflow templates.

## 🏗️ Design Principles

1. **Extensibility First** - Easy to add new parameters without breaking existing templates
2. **Maintainability** - Consistent naming and structure across all templates
3. **Composition Ready** - Templates can be easily composed without parameter mapping
4. **Future Proof** - Schema accommodates current and anticipated future requirements
5. **Type Safety** - Clear parameter types and validation rules

## 📋 Core Parameter Schema

### **Tier 1: Universal Parameters (Required by ALL templates)**

```yaml
# === RESOURCE IDENTITY ===
- name: resource-name
  type: string
  description: "Primary resource identifier (microservice name, appcontainer name, vcluster name)"
  validation: "^[a-z0-9][a-z0-9-]*[a-z0-9]$"
  examples: ["payment-service", "user-management", "analytics-platform"]

- name: resource-type
  type: string
  description: "Type of resource being created"
  allowed: ["microservice", "appcontainer", "vcluster", "database", "cache"]
  
- name: namespace
  type: string
  description: "Kubernetes namespace for resource deployment"
  default: "default"
  validation: "^[a-z0-9][a-z0-9-]*[a-z0-9]$"

# === USER CONTEXT ===
- name: user
  type: string
  description: "User requesting the resource creation"
  default: "system"

- name: description
  type: string
  description: "Human-readable description of the resource"
  default: "Resource created via standardized parameter contract"

# === PLATFORM INTEGRATION ===
- name: github-org
  type: string
  description: "GitHub organization for repository creation"
  default: "socrates12345"

- name: docker-registry
  type: string
  description: "Docker registry for container images"
  default: "docker.io/socrates12345"

# === NOTIFICATION INTEGRATION ===
- name: slack-channel
  type: string
  description: "Slack channel for notifications"
  default: "#platform-notifications"

- name: slack-user-id
  type: string
  description: "Slack user ID for direct notifications"
  default: "UNKNOWN"
```

### **Tier 2: Platform Parameters (Common across resource types)**

```yaml
# === SECURITY & COMPLIANCE ===
- name: security-enabled
  type: boolean
  description: "Enable security features (mTLS, network policies, RBAC)"
  default: "true"

- name: observability-enabled
  type: boolean
  description: "Enable observability stack (metrics, logging, tracing)"
  default: "true"

- name: backup-enabled
  type: boolean
  description: "Enable backup and disaster recovery"
  default: "false"

# === ENVIRONMENT CONFIGURATION ===
- name: environment-tier
  type: string
  description: "Environment tier for resource sizing and policies"
  allowed: ["development", "staging", "production"]
  default: "development"

- name: auto-create-dependencies
  type: boolean
  description: "Automatically create required dependencies"
  default: "true"

# === RESOURCE SIZING ===
- name: resource-size
  type: string
  description: "Resource size configuration"
  allowed: ["small", "medium", "large", "xlarge"]
  default: "medium"
```

### **Tier 3: Context-Specific Parameters (Used by specific resource types)**

```yaml
# === MICROSERVICE PARAMETERS ===
- name: microservice-language
  type: string
  description: "Programming language for microservice"
  allowed: ["python", "java", "go", "nodejs", "rust"]
  context: "microservice"

- name: microservice-framework
  type: string
  description: "Application framework"
  allowed: ["fastapi", "springboot", "gin", "express", "axum"]
  context: "microservice"

- name: microservice-database
  type: string
  description: "Database type for microservice"
  allowed: ["none", "postgres", "mysql", "mongodb", "cassandra"]
  default: "none"
  context: "microservice"

- name: microservice-cache
  type: string
  description: "Cache type for microservice"
  allowed: ["none", "redis", "memcached", "hazelcast"]
  default: "none"
  context: "microservice"

- name: microservice-expose-api
  type: boolean
  description: "Expose microservice via API Gateway"
  default: "false"
  context: "microservice"

# === VCLUSTER PARAMETERS ===
- name: vcluster-size
  type: string
  description: "VCluster resource allocation"
  allowed: ["small", "medium", "large", "xlarge"]
  default: "medium"
  context: "vcluster"

- name: vcluster-capabilities
  type: object
  description: "VCluster feature enablement"
  schema:
    observability: boolean
    security: boolean
    gitops: boolean
    logging: boolean
    networking: boolean
    autoscaling: boolean
    backup: boolean
  context: "vcluster"

# === DATABASE PARAMETERS ===
- name: database-engine
  type: string
  description: "Database engine type"
  allowed: ["postgres", "mysql", "mongodb", "cassandra", "redis"]
  context: "database"

- name: database-storage-size
  type: string
  description: "Database storage allocation"
  default: "10Gi"
  validation: "^[0-9]+[KMGT]i$"
  context: "database"

- name: database-high-availability
  type: boolean
  description: "Enable database high availability"
  default: "false"
  context: "database"
```

### **Tier 4: Advanced Parameters (For complex scenarios)**

```yaml
# === DEPENDENCY MANAGEMENT ===
- name: target-vcluster
  type: string
  description: "Target vCluster for resource deployment"
  default: ""

- name: parent-appcontainer
  type: string
  description: "Parent AppContainer for microservice deployment"
  default: ""

- name: resource-dependencies
  type: array
  description: "List of dependent resources to create"
  items:
    type: object
    properties:
      name: string
      type: string
      config: object

# === WORKFLOW CONTROL ===
- name: workflow-mode
  type: string
  description: "Workflow execution mode"
  allowed: ["create", "update", "delete", "validate"]
  default: "create"

- name: dry-run
  type: boolean
  description: "Perform validation without creating resources"
  default: "false"

- name: force-recreation
  type: boolean
  description: "Force recreation of existing resources"
  default: "false"

# === EXTENSIBILITY ===
- name: custom-labels
  type: object
  description: "Custom labels to apply to all resources"
  default: {}

- name: custom-annotations
  type: object
  description: "Custom annotations to apply to all resources"
  default: {}

- name: feature-flags
  type: object
  description: "Feature flags for experimental functionality"
  default: {}
```

## 🔄 Parameter Transformation Rules

### **Context-Specific Mapping**

Templates can derive context-specific parameters from universal ones:

```yaml
# Microservice Template Parameter Derivation
derived-parameters:
  # Universal -> Context-specific
  - microservice-name: "{{inputs.parameters.resource-name}}"
  - appcontainer-name: "{{inputs.parameters.parent-appcontainer | default(inputs.parameters.resource-name)}}"
  - vcluster-name: "{{inputs.parameters.target-vcluster | default(inputs.parameters.resource-name + '-vcluster')}}"
  
  # Framework derivation
  - framework: |
      {{- if eq .microservice-language "python" -}}fastapi
      {{- else if eq .microservice-language "java" -}}springboot
      {{- else if eq .microservice-language "go" -}}gin
      {{- else -}}{{.microservice-framework}}{{- end -}}
```

### **Backward Compatibility**

For existing templates, provide transformation adapters:

```yaml
# Legacy Parameter Adapter
legacy-mapping:
  # Old -> New
  appcontainer-name: resource-name
  microservice-name: resource-name
  vcluster-name: resource-name
  observability: observability-enabled
  security: security-enabled
  auto-create-vcluster: auto-create-dependencies
```

## 📝 Template Implementation Requirements

### **Template Header Standard**

```yaml
apiVersion: argoproj.io/v1alpha1
kind: WorkflowTemplate
metadata:
  name: template-name
  namespace: argo
  labels:
    parameter-contract-version: "v1.0"
    resource-type: "microservice|appcontainer|vcluster"
  annotations:
    description: "Template description"
    parameter-contract: "compliant"
    supported-tiers: "1,2,3"  # Which parameter tiers this template supports
```

### **Input Parameters Section**

```yaml
spec:
  templates:
  - name: template-main
    inputs:
      parameters:
      # === TIER 1: UNIVERSAL (Required) ===
      - name: resource-name
      - name: resource-type
      - name: namespace
        default: "default"
      - name: user
        default: "system"
      - name: description
        default: "Created via standardized parameter contract"
      - name: github-org
        default: "socrates12345"
      - name: docker-registry
        default: "docker.io/socrates12345"
      - name: slack-channel
        default: "#platform-notifications"
      - name: slack-user-id
        default: "UNKNOWN"
      
      # === TIER 2: PLATFORM (Common) ===
      - name: security-enabled
        default: "true"
      - name: observability-enabled
        default: "true"
      - name: environment-tier
        default: "development"
      - name: auto-create-dependencies
        default: "true"
      - name: resource-size
        default: "medium"
      
      # === TIER 3: CONTEXT-SPECIFIC (As needed) ===
      # Add only parameters relevant to this template's resource type
```

## 🧪 Validation and Compliance

### **Template Validation Tool**

```bash
# Validate template compliance
./scripts/validate-parameter-contract.sh template-file.yaml

# Generate parameter documentation
./scripts/generate-parameter-docs.sh template-file.yaml

# Check parameter tier usage
./scripts/audit-parameter-usage.sh argo-workflows/
```

### **Runtime Validation**

Templates should include parameter validation:

```yaml
- name: validate-parameters
  script:
    image: alpine:3.18
    command: [sh]
    source: |
      echo "🔍 Validating parameter contract compliance..."
      
      # Validate required Tier 1 parameters
      if [ -z "{{inputs.parameters.resource-name}}" ]; then
        echo "❌ Missing required parameter: resource-name"
        exit 1
      fi
      
      # Validate resource-name format
      if ! echo "{{inputs.parameters.resource-name}}" | grep -E '^[a-z0-9][a-z0-9-]*[a-z0-9]$'; then
        echo "❌ Invalid resource-name format"
        exit 1
      fi
      
      # Validate environment-tier
      case "{{inputs.parameters.environment-tier}}" in
        development|staging|production)
          echo "✅ Valid environment-tier: {{inputs.parameters.environment-tier}}"
          ;;
        *)
          echo "❌ Invalid environment-tier: {{inputs.parameters.environment-tier}}"
          exit 1
          ;;
      esac
      
      echo "✅ Parameter contract validation successful"
```

## 🚀 Migration Strategy

### **Phase 1: Foundation (Week 1)**
1. Create standardized parameter contract specification
2. Build validation and compliance tools
3. Create template generation utilities

### **Phase 2: Core Templates (Week 2)**
1. Update VCluster templates to use standard contract
2. Update Slack notification templates
3. Create universal parameter transformation utilities

### **Phase 3: Platform Templates (Week 3)**
1. Create unified AppContainer template with standard parameters
2. Create unified microservice template with standard parameters
3. Create database and cache templates with standard parameters

### **Phase 4: Integration & Testing (Week 4)**
1. End-to-end workflow testing
2. Performance optimization
3. Documentation and training materials

## 📚 Benefits of This Approach

1. **✅ Extensibility** - Easy to add new parameter tiers without breaking existing templates
2. **✅ Maintainability** - Consistent structure and naming across all templates
3. **✅ Composition** - Templates naturally compose without parameter mapping overhead
4. **✅ Validation** - Built-in parameter validation and compliance checking
5. **✅ Documentation** - Self-documenting parameter structure
6. **✅ Future-Proof** - Accommodates current and future platform requirements
7. **✅ Debugging** - Clear parameter flow and consistent error handling

This standardized approach will create a robust, scalable foundation for the entire platform.