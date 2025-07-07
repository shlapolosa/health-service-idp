# AWS API Gateway Integration for vCluster

This document explains the AWS API Gateway integration implemented in the VClusterEnvironmentClaim composition.

## Architecture Overview

The integration creates a complete AWS API Gateway setup that exposes vCluster applications through a managed AWS API Gateway endpoint:

```
Internet → AWS API Gateway → VPC Link → EKS Private Subnets → Istio Gateway → vCluster Services
```

## Components Created

### 1. AWS API Gateway V2 (HTTP API)
- **Resource**: `AWS::ApiGatewayV2::Api`
- **Purpose**: Main API Gateway endpoint with CORS configuration
- **Features**:
  - HTTP protocol type for better performance and lower cost
  - CORS enabled for web applications
  - Tags for resource management

### 2. VPC Link
- **Resource**: `AWS::ApiGatewayV2::VpcLink`
- **Purpose**: Private network connection between API Gateway and EKS cluster
- **Requirements**:
  - Must use **private subnets** within the EKS VPC
  - Subnets must have route to EKS cluster
  - Optional security groups for additional access control

### 3. Integration
- **Resource**: `AWS::ApiGatewayV2::Integration`
- **Purpose**: Defines how API Gateway routes requests to vCluster
- **Configuration**:
  - `HTTP_PROXY` integration type for pass-through behavior
  - Routes to Istio Gateway service within the cluster
  - 29-second timeout (AWS maximum)

### 4. Route
- **Resource**: `AWS::ApiGatewayV2::Route`
- **Purpose**: Catch-all route (`ANY /{proxy+}`) to forward all requests
- **Behavior**: Forwards all HTTP methods and paths to the vCluster ingress

### 5. Stage
- **Resource**: `AWS::ApiGatewayV2::Stage`
- **Purpose**: Deployment stage with public endpoint
- **Configuration**:
  - `prod` stage with auto-deployment
  - Generates the public API Gateway URL

## Request Flow

1. **External Request**: Client sends request to API Gateway endpoint
2. **API Gateway**: Receives request at `https://{api-id}.execute-api.{region}.amazonaws.com/prod/{path}`
3. **VPC Link**: Routes request through private network to EKS cluster
4. **Istio Gateway**: Receives request within cluster and routes based on host/path
5. **vCluster Service**: Processes request within the virtual cluster
6. **Response**: Returns through the same path back to client

## Configuration Requirements

### VPC Setup
```yaml
spec:
  vpc:
    subnetIds:
    - subnet-1234567890abcdef0  # Private subnet in AZ-a
    - subnet-abcdef1234567890   # Private subnet in AZ-b
    securityGroupIds:           # Optional
    - sg-1234567890abcdef0      # Security group allowing ingress
```

### Network Requirements
- **Private Subnets**: VPC Link requires private subnets (no direct internet gateway route)
- **NAT Gateway**: Private subnets should have NAT Gateway for outbound internet access
- **Security Groups**: Must allow inbound traffic from API Gateway service
- **Route Tables**: Must have routes to EKS cluster nodes

## Application Integration

When applications are deployed to the vCluster, they can be exposed through the API Gateway by:

### 1. Istio VirtualService Configuration
```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: my-app
spec:
  hosts:
  - "my-app.example.com"  # Custom domain or API Gateway domain
  gateways:
  - my-vcluster-gateway   # vCluster Istio Gateway
  http:
  - match:
    - uri:
        prefix: /api/v1/my-app
    route:
    - destination:
        host: my-app-service
        port:
          number: 8080
```

### 2. Automatic Route Creation
Future enhancements can include:
- **Crossplane Functions**: Dynamic API Gateway route creation based on deployed services
- **Service Annotations**: Automatic exposure through annotations on Kubernetes services
- **GitOps Integration**: ArgoCD applications that update API Gateway routes

### 3. Custom Domain Integration
```yaml
# Add to API Gateway configuration
spec:
  domain: my-api.example.com
  # This would require:
  # - Route53 hosted zone
  # - ACM certificate
  # - API Gateway domain name resource
```

## Status Information

The composition provides status information about the API Gateway setup:

```yaml
status:
  apiGateway:
    id: "abc123xyz"                                    # API Gateway ID
    endpoint: "https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod"  # Public endpoint
    vpcLinkId: "vpclink-123abc"                       # VPC Link ID
    stage: "prod"                                     # Stage name
```

## Security Considerations

### 1. Network Security
- **Private Integration**: All traffic flows through VPC Link, not exposing cluster directly
- **Security Groups**: Control access at network level
- **Private Subnets**: API Gateway cannot directly access cluster nodes

### 2. API Gateway Security
- **Rate Limiting**: Can be configured on API Gateway stages
- **WAF Integration**: AWS WAF can be attached to API Gateway
- **Access Logging**: CloudWatch logs for all requests

### 3. Authentication & Authorization
- **JWT Authorization**: Can be configured on API Gateway routes
- **Lambda Authorizers**: Custom authorization logic
- **IAM Authorization**: AWS IAM-based access control

## Cost Optimization

### 1. HTTP API vs REST API
- Uses HTTP API for ~71% cost reduction compared to REST API
- Suitable for most application scenarios

### 2. VPC Link Considerations
- VPC Link has hourly charges (~$22/month)
- Shared across multiple vClusters in same VPC
- Consider reusing VPC Links for multiple environments

### 3. Data Transfer
- No charges for data transfer between API Gateway and VPC Link
- Standard AWS data transfer charges apply for internet egress

## Limitations

### 1. Resource Dependencies
- API Gateway resources have creation order dependencies
- VPC Link creation can take 2-10 minutes
- Changes to VPC Link require replacement

### 2. Integration Constraints
- 29-second maximum timeout
- HTTP methods and headers are passed through
- Binary content requires base64 encoding

### 3. Crossplane Limitations
- Status field dependencies require careful resource ordering
- Circular references between resources need proper patch configuration

## Future Enhancements

### 1. Advanced Routing
- Path-based routing for multiple applications
- Host-based routing for multi-tenant scenarios
- Weighted routing for blue-green deployments

### 2. Monitoring & Observability
- X-Ray tracing integration
- CloudWatch custom metrics
- API Gateway access logs

### 3. Custom Domains
- Route53 integration for custom domains
- ACM certificate management
- Multi-domain support

## Troubleshooting

### Common Issues

1. **VPC Link Connection Failed**
   - Verify private subnets configuration
   - Check security group rules
   - Ensure subnets have connectivity to EKS nodes

2. **504 Gateway Timeout**
   - Verify Istio Gateway is listening on correct port
   - Check vCluster service endpoints
   - Review integration timeout settings

3. **403 Forbidden**
   - Verify API Gateway route configuration
   - Check Istio VirtualService host matching
   - Review security group ingress rules

### Debugging Commands

```bash
# Check VPC Link status
aws apigatewayv2 get-vpc-link --vpc-link-id <vpc-link-id>

# Test API Gateway endpoint
curl -v https://<api-id>.execute-api.<region>.amazonaws.com/prod/health

# Check Istio Gateway configuration
kubectl get gateway -n <vcluster-namespace>
kubectl get virtualservice -n <vcluster-namespace>
```

## Example Complete Configuration

```yaml
apiVersion: platform.example.org/v1alpha1
kind: VClusterEnvironmentClaim
metadata:
  name: production-vcluster
  namespace: default
spec:
  name: prod-env
  domain: api.mycompany.com
  vpc:
    subnetIds:
    - subnet-12345abcde  # us-east-1a private subnet
    - subnet-67890fghij  # us-east-1b private subnet
    securityGroupIds:
    - sg-api-gateway-access
  include:
  - grafana
  - prometheus
  - apiGatewaySupport
```

This creates a production-ready vCluster with AWS API Gateway integration, monitoring stack, and secure network configuration.