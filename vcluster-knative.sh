#!/usr/bin/env bash
# refresh-ekscreds.sh

# 1. Pick your profile
profile="${AWS_PROFILE:-default}"

# 2. Where is your SSO directory?
sso_region=$(aws configure get sso_region        --profile "$profile")

# 3. Where do your AWS services live?
aws_region=$(aws configure get region             --profile "$profile")
# Fallback if you haven’t set it:
aws_region=${aws_region:-us-west-2}

account=$(aws configure get sso_account_id       --profile "$profile")
role=$(aws configure get sso_role_name           --profile "$profile")

# 4. Grab the most recent SSO cache file
cache=$(ls -1t ~/.aws/sso/cache/*.json | head -n1)
token=$(jq -r .accessToken "$cache")

# 5. Exchange for AWS creds in the SSO realm
creds_json=$(
  aws sso get-role-credentials \
    --account-id   "$account" \
    --role-name    "$role" \
    --access-token "$token" \
    --region       "$sso_region"
)

# 6. Export them
export AWS_ACCESS_KEY_ID=$(jq -r .roleCredentials.accessKeyId     <<<"$creds_json")
export AWS_SECRET_ACCESS_KEY=$(jq -r .roleCredentials.secretAccessKey <<<"$creds_json")
export AWS_SESSION_TOKEN=$(jq -r .roleCredentials.sessionToken    <<<"$creds_json")

# 7. And set the AWS region for STS/EKS calls
export AWS_REGION="$aws_region"
export AWS_DEFAULT_REGION="$aws_region"

# 8. Now list clusters

export KARPENTER_NAMESPACE="kube-system"
export KARPENTER_VERSION="1.5.0"
export K8S_VERSION="1.32"

export AWS_PARTITION="aws" # if you are not using standard partitions, you may need to configure to aws-cn / aws-us-gov
export CLUSTER_NAME="${USER}-karpenter-demo"
export AWS_DEFAULT_REGION="us-west-2"
export AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
export TEMPOUT="$(mktemp)"
export ALIAS_VERSION="$(aws ssm get-parameter --name "/aws/service/eks/optimized-ami/${K8S_VERSION}/amazon-linux-2023/x86_64/standard/recommended/image_id" --query Parameter.Value | xargs aws ec2 describe-images --query 'Images[0].Name' --image-ids | sed -r 's/^.*(v[[:digit:]]+).*$/\1/')"

echo "${KARPENTER_NAMESPACE}" "${KARPENTER_VERSION}" "${K8S_VERSION}" "${CLUSTER_NAME}" "${AWS_DEFAULT_REGION}" "${AWS_ACCOUNT_ID}" "${TEMPOUT}" "${ALIAS_VERSION}"


kubectl auth can-i create clusterrole -A

kubectl config current-context


vcluster delete architecture-vizualisation --namespace vcluster-platform
kubectl delete pvc --all -n vcluster-platform 

vcluster create architecture-vizualisation \
  --namespace vcluster-platform \
  --values vcluster.yaml \
  --connect=false


# First create the target file                                                                                                                          
TEMPOUT=$(mktemp)                                                                                                                                       
TARGET_FILE="${TEMPOUT}-vcluster"                                                                                                                       
                                                                                                                                                        
# Then connect and save the config                                                                                                                      
vcluster platform connect vcluster architecture-vizualisation --project default --print > "$TARGET_FILE"                                                
                                                                                                                                                        
# Verify the file was created                                                                                                                           
ls -la "$TARGET_FILE"                                                                                                                                   
                                                                                                                                                        
# To use this config:                                                                                                                                   
export KUBECONFIG="$TARGET_FILE" 

kubectl config current-context


kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.18.1/serving-crds.yaml
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.18.1/serving-core.yaml

kubectl apply -l knative.dev/crd-install=true -f https://github.com/knative/net-istio/releases/download/knative-v1.18.0/istio.yaml
kubectl apply -f https://github.com/knative/net-istio/releases/download/knative-v1.18.0/istio.yaml
kubectl apply -f https://github.com/knative/net-istio/releases/download/knative-v1.18.0/net-istio.yaml

kubectl --namespace istio-system get service istio-ingressgateway

kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v1.18.1/eventing-crds.yaml
kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v1.18.1/eventing-core.yaml

kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v1.18.1/in-memory-channel.yaml

kubectl get pods -n knative-eventing
kubectl get pods -n knative-serving

kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.18.1/serving-default-domain.yaml



# Install func CLI for Knative functions
curl -Lo func https://github.com/knative/func/releases/download/knative-v1.14.0/func_linux_amd64
chmod +x func && sudo mv func /usr/local/bin/

# Create development secrets IN VCLUSTER
kubectl create secret generic github-pat \
  --from-literal=token=${GITHUB_PAT} \
  --namespace knative-serving

# Deploy policy-engine service IN VCLUSTER CONTEXT
kubectl apply -f - <<EOF
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: policy-engine
  namespace: knative-serving
spec:
  template:
    spec:
      containers:
      - image: ghcr.io/yourorg/policy-engine:latest
EOF

# Add smoke test validation
echo "Waiting for policy-engine service to become ready..."
sleep 10  # Give time for service to provision
kn service describe policy-engine -n knative-serving

# Return to host cluster context
unset KUBECONFIG




kubectl delete -f https://github.com/knative/eventing/releases/download/knative-v1.18.1/in-memory-channel.yaml                                          
kubectl delete -f https://github.com/knative/eventing/releases/download/knative-v1.18.1/eventing-core.yaml                                              
kubectl delete -f https://github.com/knative/eventing/releases/download/knative-v1.18.1/eventing-crds.yaml  

kubectl delete -f https://github.com/knative/serving/releases/download/knative-v1.18.1/serving-default-domain.yaml                                      
kubectl delete -f https://github.com/knative/net-istio/releases/download/knative-v1.18.0/net-istio.yaml                                                 
kubectl delete -f https://github.com/knative/serving/releases/download/knative-v1.18.1/serving-core.yaml                                                
kubectl delete -f https://github.com/knative/serving/releases/download/knative-v1.18.1/serving-crds.yaml

kubectl delete -f https://github.com/knative/net-istio/releases/download/knative-v1.18.0/istio.yaml                                                     
kubectl delete -l knative.dev/crd-install=true -f https://github.com/knative/net-istio/releases/download/knative-v1.18.0/istio.yaml 

kubectl delete namespace knative-serving                                                                                                                
kubectl delete namespace knative-eventing                                                                                                               
kubectl delete namespace istio-system 

