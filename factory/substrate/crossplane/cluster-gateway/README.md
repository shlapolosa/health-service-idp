# ClusterGateway CRDs for Multi-Cluster Support

This directory contains the Custom Resource Definitions (CRDs) required for KubeVela's multi-cluster support via ClusterGateway.

## Installation

Apply both CRDs to enable multi-cluster topology policies:

```bash
kubectl apply -f clustergateway-cluster-crd.yaml
kubectl apply -f clustergateway-core-crd.yaml
```

## Purpose

These CRDs are required for:
- OAM topology policies to deploy applications to vClusters
- KubeVela multi-cluster routing and management
- ClusterGateway API aggregation

## Verification

After installation, verify the CRDs are present:

```bash
kubectl get crd | grep -i cluster | grep oam
```

Expected output:
```
clustergateways.cluster.core.oam.dev
clustergateways.core.oam.dev
```

## vCluster Registration

vClusters are automatically registered as ClusterGateways when created via VClusterEnvironmentClaim.
You can list registered clusters with:

```bash
kubectl get clustergateways.cluster.core.oam.dev
```