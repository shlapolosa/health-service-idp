# Simplified VPC Setup for AWS API Gateway Integration

This guide explains the simplified VPC configuration approach for the VClusterEnvironmentClaim.

## Overview

Instead of requiring users to know subnet IDs, we use **EnvironmentConfig** to provide platform-level network configuration. This approach:

- ✅ **Simplifies user experience** - no need to know subnet IDs
- ✅ **Centralizes network config** - managed by platform admins
- ✅ **Environment-specific** - different configs per env (dev/prod/etc)
- ✅ **Secure by default** - uses private subnets automatically

## For Platform Administrators

### 1. One-Time Setup: Discover Your VPC Configuration

```bash
# Find your VPC ID (or use default VPC)
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text)
echo "VPC ID: $VPC_ID"

# Find private subnets in your VPC
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[*].[SubnetId,AvailabilityZone,CidrBlock,Tags[?Key==`Name`].Value|[0]]' \
  --output table

# Check which subnets are private (no direct internet gateway route)
for subnet in $(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[*].SubnetId' --output text); do
  echo "Subnet: $subnet"
  aws ec2 describe-route-tables \
    --filters "Name=association.subnet-id,Values=$subnet" \
    --query 'RouteTables[0].Routes[?GatewayId!=null && starts_with(GatewayId, `igw-`)]' \
    --output text | grep -q "igw-" && echo "  -> Public subnet" || echo "  -> Private subnet"
done
```

### 2. Create EnvironmentConfig

Create an EnvironmentConfig with your discovered subnet information:

```yaml
apiVersion: apiextensions.crossplane.io/v1alpha1
kind: EnvironmentConfig
metadata:
  name: production-vpc-config
  labels:
    environment: production  # Change this per environment
data:
  vpc:
    # Replace with your actual subnet IDs (must be in different AZs)
    privateSubnetIds:
    - subnet-1234567890abcdef0  # us-east-1a private
    - subnet-abcdef1234567890   # us-east-1b private
    # Optional: public subnets (less secure)
    publicSubnetIds:
    - subnet-public1a
    - subnet-public1b
```

### 3. Apply the Configuration

```bash
kubectl apply -f environment-config.yaml
```

### 4. Verify Configuration

```bash
kubectl get environmentconfigs
kubectl describe environmentconfig production-vpc-config
```

## For Developers (End Users)

### Simple vCluster Creation

With the EnvironmentConfig in place, developers can create vClusters without knowing any VPC details:

```yaml
apiVersion: platform.example.org/v1alpha1
kind: VClusterEnvironmentClaim
metadata:
  name: my-vcluster
  namespace: default
spec:
  name: my-app-env
  components:
    apiGateway: true   # Automatically gets AWS API Gateway
    grafana: true      # Optional: monitoring
    prometheus: true   # Optional: metrics collection
    # All other components default to false
```

That's it! No subnet IDs, security groups, or VPC configuration needed.

## Multiple Environments

### Environment-Specific Configurations

```yaml
# Production environment
apiVersion: apiextensions.crossplane.io/v1alpha1
kind: EnvironmentConfig
metadata:
  name: prod-vpc-config
  labels:
    environment: production
data:
  vpc:
    privateSubnetIds:
    - subnet-prod-private-1a
    - subnet-prod-private-1b

---
# Development environment
apiVersion: apiextensions.crossplane.io/v1alpha1
kind: EnvironmentConfig
metadata:
  name: dev-vpc-config
  labels:
    environment: development
data:
  vpc:
    privateSubnetIds:
    - subnet-dev-private-1a
    - subnet-dev-private-1b
```

### Environment Selection in Composition

The Composition can be configured to use different environments:

```yaml
# In the Composition
spec:
  environment:
    environmentRefs:
    - type: Selector
      selector:
        matchLabels:
        - key: environment
          type: Value
          value: production  # or development, staging, etc.
```

## Network Requirements

### Subnet Requirements

✅ **Required for VPC Link:**
- At least 2 subnets in different Availability Zones
- Subnets must be in the same VPC as your EKS cluster
- Subnets must have connectivity to EKS worker nodes

✅ **Recommended for Security:**
- Use private subnets (no direct internet gateway route)
- Private subnets should have NAT Gateway for outbound access
- Separate subnets from public-facing load balancers

### Connectivity Verification

Test connectivity between API Gateway and your cluster:

```bash
# Check if subnets can reach EKS nodes
kubectl get nodes -o wide  # Get node IPs

# From a pod in your subnet, test connectivity
kubectl run test-connectivity --image=busybox -it --rm -- \
  sh -c "ping -c 3 <node-ip> && wget -O- http://<node-ip>:80"
```

## Security Considerations

### Default Security

The composition automatically:
- Creates dedicated security group for API Gateway VPC Link
- Allows HTTP (80) and HTTPS (443) inbound from anywhere
- Allows all outbound traffic to cluster

### Custom Security Groups

For additional security, you can reference existing security groups in your EnvironmentConfig:

```yaml
data:
  vpc:
    privateSubnetIds: [...]
    securityGroups:
      apiGateway: sg-custom-api-gateway-sg
```

## Troubleshooting

### Common Issues

1. **"No subnets configured"**
   ```bash
   # Check EnvironmentConfig
   kubectl get environmentconfigs
   kubectl describe environmentconfig <name>
   ```

2. **"VPC Link creation failed"**
   ```bash
   # Check subnet availability and AZ distribution
   aws ec2 describe-subnets --subnet-ids subnet-1 subnet-2
   ```

3. **"Cannot reach vCluster services"**
   ```bash
   # Check security group rules
   aws ec2 describe-security-groups --group-ids sg-xxxxxxxxx
   
   # Test from VPC Link subnet to EKS nodes
   # (requires temporary EC2 instance in same subnet)
   ```

### Manual Override

If automatic configuration doesn't work, you can still override in the claim:

```yaml
spec:
  name: my-env
  vpc:
    vpcId: vpc-specific-override
    # This would require composition enhancement
```

## Migration from Manual Configuration

### From Manual Subnet IDs

If you were previously specifying subnet IDs in claims:

1. Create EnvironmentConfig with those subnet IDs
2. Remove VPC configuration from existing claims
3. Claims will automatically use EnvironmentConfig

### Backward Compatibility

The composition maintains backward compatibility - if no EnvironmentConfig is found, it will fail with clear error messages indicating the required setup.

## Benefits Summary

| Aspect | Before (Manual) | After (EnvironmentConfig) |
|--------|----------------|---------------------------|
| User Experience | Must know subnet IDs | Just specify application needs |
| Security | User responsibility | Platform-managed defaults |
| Consistency | Varies per user | Consistent across environment |
| Maintenance | Per-application | Per-environment |
| Error-prone | High (wrong subnets) | Low (validated by platform) |

## Next Steps

1. **Enhanced Discovery**: Future versions could auto-discover subnets based on EKS cluster tags
2. **Regional Support**: Multi-region EnvironmentConfigs
3. **Custom Domains**: Automatic Route53 and ACM integration
4. **Cost Optimization**: Shared VPC Links across multiple vClusters

This simplified approach makes AWS API Gateway integration accessible to developers while maintaining security and consistency across the platform.