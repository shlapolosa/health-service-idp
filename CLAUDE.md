# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. All actions when implimenting code to be driven by operatingmodel  in dev-workflow.mdc

## Project Overview

This is a **Visual Architecture Maintenance Tool** - an AI-powered system that allows architects to create, view, and update enterprise architectures using natural language. The system uses an agentic framework with specialized AI agents for different architectural domains (business, application, infrastructure, etc.).

## Key Architecture Features

- **Multi-Agent System**: Business Analyst, Business Architect, Application Architect, Infrastructure Architect, Solution Architect, Project Manager, Accountant, and Developer agents
- **ArchiMate Notation**: Standardized enterprise architecture visualization with specific color coding
- **Change Propagation**: Updates cascade through all architecture layers automatically
- **Natural Language Interface**: Streamlit-based chat interface for architecture modifications
- **Kubernetes Native**: Deployed on AWS EKS with vcluster, Knative, and Istio

## Infrastructure Commands

### AWS EKS Cluster Management



### vcluster Management

```bash
# Create vcluster for architecture visualization
vcluster create architecture-vizualisation \
  --namespace vcluster-platform \
  --values vcluster.yaml \
  --connect=false

# Connect to vcluster
vcluster platform connect vcluster architecture-vizualisation --project default

# Delete vcluster
vcluster delete architecture-vizualisation --namespace vcluster-platform
```

### Knative and Istio Setup

```bash
# Install Knative Serving
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.18.1/serving-crds.yaml
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.18.1/serving-core.yaml

# Install Istio for Knative
kubectl apply -l knative.dev/crd-install=true -f https://github.com/knative/net-istio/releases/download/knative-v1.18.0/istio.yaml
kubectl apply -f https://github.com/knative/net-istio/releases/download/knative-v1.18.0/istio.yaml
kubectl apply -f https://github.com/knative/net-istio/releases/download/knative-v1.18.0/net-istio.yaml

# Install Knative Eventing
kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v1.18.1/eventing-crds.yaml
kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v1.18.1/eventing-core.yaml

# Verify installations
kubectl get pods -n knative-eventing
kubectl get pods -n knative-serving
kubectl --namespace istio-system get service istio-ingressgateway
```

## Project Structure

```
health-service-idp/
├── spec.md                           # Core project specification and requirements
├── visual-architecture-tool-requirements.md  # Detailed architecture requirements
├── vcluster-knative.sh              # Infrastructure setup script
├── vcluster.yaml                     # vcluster configuration
├── refresh-eksctl.sh                 # AWS EKS cluster management script
├── .env.example                      # Environment variables template
├── .mcp.json                         # MCP server configuration
└── CLAUDE.md                         # This file
```

## Key Requirements from Specifications

### Architecture Layers (ArchiMate Colors)
- **Purple (#CC99FF)**: Strategy elements (octagons)
- **Yellow (#FFFF99)**: Business layer (circles)
- **Light Brown (#E6CC99)**: Passive structures (rectangles)
- **Blue (#99CCFF)**: Application layer (rounded rectangles)
- **Orange (#FFCC99)**: Implementation (sharp rectangles)

### Core Functionality
1. **Natural Language Processing**: Chat interface for architecture modifications
2. **Visual Design**: Embedded HTML architecture visualization with ArchiMate notation
3. **Change Management**: Pending changes shown in gray, approved changes in color
4. **Multi-Agent Workflow**: Sequential processing through specialized agents
5. **Implementation Generation**: Automatic code and infrastructure generation

### Technology Stack
- **Frontend**: Streamlit with chat interface
- **Backend**: Multi-agent orchestration system
- **Infrastructure**: AWS EKS + vcluster + Knative + Istio
- **Deployment**: KubeVela with ArgoCD GitOps
- **Visualization**: HTML/ArchiMate diagrams
- **APIs**: OpenAPI 3.0 with consolidated ingress

## Agent Capabilities

### Business Analyst
- Formats and structures requirements using Subject-Action-Object format
- Creates project requirements documents
- Generates user stories from completed architecture

### Business Architect
- Accesses current HTML architecture from repository
- Assesses strategic, motivational, and business layer impacts
- Updates design with to-be changes using industry capability maps

### Application Architect
- Processes business layer changes
- Accesses reference architectures (AWS, Azure, Kubernetes, MLOps, etc.)
- Updates application layer with required changes

### Infrastructure Architect/DevOps
- Processes application layer changes
- Accesses cloud-native techniques and tools
- Updates infrastructure and operations components

### Solution Architect
- Consolidates changes across all layers
- Accesses latest reference architectures and patterns
- Updates solution architecture with technology-specific designs

### Developer
- Takes user stories and implements code changes
- Outputs working, tested software using best practices
- Integrates with existing systems and deployment pipelines

## MCP Server Configuration

The project uses MCP servers for:
- **Context7**: Reference architecture access
- **TaskMaster**: Task and project management
- **GitHub**: Version control integration
- **Diagramming**: Architecture visualization
- **Web Search**: Real-time knowledge access
- **Terminal/Cloud**: Infrastructure manipulation
- **Kubernetes**: Container orchestration

## Development Commands

### Infrastructure Setup
```bash
# Refresh AWS SSO credentials and setup EKS cluster
./refresh-eksctl.sh

# Setup vcluster with Knative (comprehensive script)
./vcluster-knative.sh
```

### Environment Configuration
```bash
# Export vcluster kubeconfig
export KUBECONFIG="$(mktemp)-vcluster"
vcluster platform connect vcluster architecture-vizualisation --project default --print > "$KUBECONFIG"

# Required environment variables
export GITHUB_TOKEN="your_github_token"     # For MCP GitHub integration
export AWS_PROFILE="your_aws_profile"       # For AWS SSO authentication
```

### Verification Commands
```bash
# Verify vcluster and services
kubectl config current-context
kubectl get pods -n knative-eventing
kubectl get pods -n knative-serving
kubectl --namespace istio-system get service istio-ingressgateway

# Check agent deployment status
kn service list -n knative-serving
```

## Development Workflow

1. **Specification Review**: Always reference `spec.md` and `visual-architecture-tool-requirements.txt`
2. **Infrastructure Setup**: Use provided scripts for AWS EKS and vcluster setup
3. **Agent Development**: Implement agents according to capability specifications
4. **Testing**: Validate in vcluster environment with Knative services
5. **Deployment**: Use KubeVela descriptors for production deployment

## Important Notes

- **Single Ingress**: All traffic routes through one Istio ingress gateway
- **ArgoCD Required**: Must be installed in the vcluster for GitOps workflow
- **Agent Coordination**: Implement robust workflow engine for agent handoffs
- **Change Approval**: All architecture changes require user approval before implementation
- **Taint Tolerance**: Nodes are tainted with `vclusterID=architecture-vizualisation:NoSchedule`

## Architecture Overview

### Multi-Agent Processing Chain
Sequential agent processing order:
1. **Business Analyst** → Structures requirements (Subject-Action-Object format)
2. **Business Architect** → Updates business layer (strategy, motivation, business)
3. **Application Architect** → Updates application layer with reference architectures
4. **Infrastructure Architect** → Updates infrastructure/operations layer
5. **Solution Architect** → Consolidates changes across all layers
6. **Project Manager** → Creates implementation work packages
7. **Accountant** → Provides cost analysis and budgeting
8. **Developer** → Generates working code from user stories

### Core Technology Stack
- **Frontend**: Streamlit with 3-pane layout (menu, visualization, chat)
- **Orchestration**: Event-driven agent coordination with Redis messaging
- **Visualization**: HTML-embedded ArchiMate diagrams with standardized colors
- **Infrastructure**: AWS EKS + vcluster + Knative + Istio service mesh
- **Deployment**: KubeVela + ArgoCD GitOps workflow

### Change Management Workflow
1. User submits natural language request via chat
2. Business Analyst processes and structures requirements
3. Relevant agents process changes in sequence
4. System shows proposed changes in gray (pending approval)
5. User reviews and approves/rejects changes
6. Approved changes rendered in full ArchiMate colors
7. Implementation artifacts generated (code, infrastructure, documentation)

## Task Master Integration

The project includes Task Master AI integration for development workflow management. See the comprehensive Task Master guide sections for detailed usage instructions including:

- Task creation and management
- Agent orchestration
- Development workflow automation
- MCP integration capabilities

---

_This file ensures Claude Code has complete context for developing the Visual Architecture Maintenance Tool with its complex multi-agent system and cloud-native infrastructure requirements._
