# vcluster-standard-contract

**Resource Type:** vcluster  
**Parameter Contract Version:** v1.0  
**Supported Tiers:** 1,2,3  
**Maintainer:** platform-team  

## Description



## Parameter Contract Compliance

This template is compliant with Parameter Contract **v1.0** and supports parameter tiers: **1,2,3**.

## Tier 1: Universal Parameters (Required)

| Parameter | Default | Description | Context |
|-----------|---------|-------------|---------|
| `default-vcluster` | `*Required*` | *No description provided* | Workflow Arguments |
| `vcluster` | `*Required*` | *No description provided* | Workflow Arguments |
| `default` | `*Required*` | *No description provided* | Workflow Arguments |
| `system` | `*Required*` | *No description provided* | Workflow Arguments |
| `VCluster created via standardized parameter contract` | `*Required*` | *No description provided* | Workflow Arguments |
| `socrates12345` | `*Required*` | *No description provided* | Workflow Arguments |
| `docker.io/socrates12345` | `*Required*` | *No description provided* | Workflow Arguments |
| `#vcluster-notifications` | `*Required*` | *No description provided* | Workflow Arguments |
| `UNKNOWN` | `*Required*` | *No description provided* | Workflow Arguments |
| `resource-name` | `VCluster name (DNS-1123 compliant)` | *No description provided* | Template: create-vcluster |
| `resource-type` | `vcluster` | *No description provided* | Template: create-vcluster |
| `namespace` | `default` | Kubernetes namespace for VCluster deployment | Template: create-vcluster |
| `user` | `system` | User requesting VCluster creation | Template: create-vcluster |
| `description` | `VCluster created via standardized parameter contract` | *No description provided* | Template: create-vcluster |
| `github-org` | `socrates12345` | *No description provided* | Template: create-vcluster |
| `docker-registry` | `docker.io/socrates12345` | *No description provided* | Template: create-vcluster |
| `slack-channel` | `#vcluster-notifications` | *No description provided* | Template: create-vcluster |
| `slack-user-id` | `UNKNOWN` | *No description provided* | Template: create-vcluster |
| `resource-name` | `*Required*` | *No description provided* | Template: validate-vcluster-parameters |
| `resource-type` | `*Required*` | *No description provided* | Template: validate-vcluster-parameters |
| `namespace` | `*Required*` | *No description provided* | Template: validate-vcluster-parameters |
| `resource-name` | `*Required*` | *No description provided* | Template: create-vcluster-claim |
| `namespace` | `*Required*` | *No description provided* | Template: create-vcluster-claim |
| `description` | `*Required*` | *No description provided* | Template: create-vcluster-claim |
| `user` | `*Required*` | *No description provided* | Template: create-vcluster-claim |
| `slack-channel` | `*Required*` | *No description provided* | Template: create-vcluster-claim |
| `resource-name` | `*Required*` | *No description provided* | Template: wait-for-vcluster-ready |
| `namespace` | `*Required*` | *No description provided* | Template: wait-for-vcluster-ready |
| `resource-name` | `*Required*` | *No description provided* | Template: configure-vcluster-access |
| `namespace` | `*Required*` | *No description provided* | Template: configure-vcluster-access |
| `user` | `*Required*` | *No description provided* | Template: configure-vcluster-access |

## Tier 2: Platform Parameters (Common)

| Parameter | Default | Description | Context |
|-----------|---------|-------------|---------|
| `true` | `*Required*` | *No description provided* | Workflow Arguments |
| `true` | `*Required*` | *No description provided* | Workflow Arguments |
| `false` | `*Required*` | *No description provided* | Workflow Arguments |
| `development` | `*Required*` | *No description provided* | Workflow Arguments |
| `true` | `*Required*` | *No description provided* | Workflow Arguments |
| `medium` | `*Required*` | *No description provided* | Workflow Arguments |
| `security-enabled` | `true` | Enable security features | Template: create-vcluster |
| `observability-enabled` | `true` | Enable observability stack | Template: create-vcluster |
| `backup-enabled` | `false` | Enable backup functionality | Template: create-vcluster |
| `environment-tier` | `development` | Environment tier (development/staging/production) | Template: create-vcluster |
| `auto-create-dependencies` | `true` | Automatically create required dependencies | Template: create-vcluster |
| `resource-size` | `medium` | VCluster resource allocation size | Template: create-vcluster |
| `environment-tier` | `*Required*` | *No description provided* | Template: validate-vcluster-parameters |
| `security-enabled` | `*Required*` | *No description provided* | Template: create-vcluster-claim |
| `observability-enabled` | `*Required*` | *No description provided* | Template: create-vcluster-claim |
| `backup-enabled` | `*Required*` | *No description provided* | Template: create-vcluster-claim |
| `environment-tier` | `*Required*` | *No description provided* | Template: create-vcluster-claim |
| `security-enabled` | `*Required*` | *No description provided* | Template: configure-vcluster-access |

## Tier 3: Context-Specific Parameters

| Parameter | Default | Description | Context |
|-----------|---------|-------------|---------|
| `medium` | `*Required*` | *No description provided* | Workflow Arguments |
| `"{""observability"":""true"",""security"":""true"",""gitops"":""true"",""logging"":""true"",""networking"":""true"",""autoscaling"":""false"",""backup"":""false""}"` | `*Required*` | *No description provided* | Workflow Arguments |
| `vcluster-size` | `medium` | VCluster-specific sizing (overrides resource-size if provided) | Template: create-vcluster |
| `vcluster-capabilities` | `"{""observability"":""true"",""security"":""true"",""gitops"":""true"",""logging"":""true"",""networking"":""true"",""autoscaling"":""false"",""backup"":""false""}"` | VCluster feature capabilities as JSON | Template: create-vcluster |
| `vcluster-size` | `*Required*` | *No description provided* | Template: validate-vcluster-parameters |
| `vcluster-capabilities` | `*Required*` | *No description provided* | Template: validate-vcluster-parameters |
| `vcluster-size` | `*Required*` | *No description provided* | Template: create-vcluster-claim |
| `vcluster-capabilities` | `*Required*` | *No description provided* | Template: create-vcluster-claim |


## Usage Examples

### Standalone Usage

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: vcluster-standard-contract-
  namespace: argo
spec:
  workflowTemplateRef:
    name: vcluster-standard-contract
  arguments:
    parameters:
    - name: resource-name
      value: "my-vcluster"
    - name: namespace
      value: "default"
    - name: user
      value: "developer"
    # Add other required parameters...
```

### Template Reference Usage

```yaml
steps:
- - name: create-vcluster
    templateRef:
      name: vcluster-standard-contract
      template: create-vcluster
    arguments:
      parameters:
      - name: resource-name
        value: "{{workflow.parameters.resource-name}}"
      - name: namespace
        value: "{{workflow.parameters.namespace}}"
      # Add other required parameters...
```


## Template Structure

```yaml
- create-vcluster
- validate-vcluster-parameters
- create-vcluster-claim
- wait-for-vcluster-ready
- configure-vcluster-access
```

## Validation

This template includes built-in parameter validation for:

- Parameter naming conventions
- Required parameter presence
- Value format validation
- Resource type compliance

## Related Templates

- [vcluster-creation](./vcluster-creation.md)

---

**Generated by:** Parameter Contract Documentation Generator  
**Generated at:** 2025-07-14T07:40:57Z  
**Template file:** argo-workflows/vcluster-standard-contract.yaml  
