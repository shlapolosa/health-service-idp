# Visual Architecture Tool - Request Call Flow Sequence Diagram

This sequence diagram depicts the comprehensive call flow from frontend user interaction to backend response in the Visual Architecture Tool system.

```mermaid
sequenceDiagram
    participant User
    participant StreamlitUI as Streamlit UI<br/>(Chat Interface)
    participant SessionMgr as Session Manager
    participant APIClient as API Client
    participant Istio as Istio Gateway<br/>(Load Balancer)
    participant FastAPI as FastAPI App<br/>(Main Server)
    participant AuthMW as Auth Middleware
    participant TraceMW as Tracing Middleware
    participant MetricsMW as Metrics Middleware
    participant Router as API Router
    participant Orchestrator as Multi-Agent<br/>Orchestrator
    participant BusinessAnalyst as Business<br/>Analyst Agent
    participant BusinessArch as Business<br/>Architect Agent
    participant AppArch as Application<br/>Architect Agent
    participant InfraArch as Infrastructure<br/>Architect Agent
    participant SolutionArch as Solution<br/>Architect Agent
    participant DecisionSupport as Decision<br/>Support System
    participant ProjectMgr as Project Manager<br/>Agent
    participant Accountant as Accountant<br/>Agent
    participant Database as PostgreSQL<br/>Database
    participant Cache as Redis Cache
    participant AnthropicAPI as Anthropic API<br/>(Claude)
    participant CloudAPIs as Cloud Provider<br/>APIs
    participant Prometheus as Prometheus<br/>Metrics
    participant Jaeger as Jaeger<br/>Tracing

    %% User Interaction
    User->>StreamlitUI: Enter natural language request
    StreamlitUI->>SessionMgr: Get user session context
    SessionMgr-->>StreamlitUI: Return session data
    StreamlitUI->>APIClient: Format API request with context

    %% Frontend to Backend
    APIClient->>Istio: HTTP POST /api/v1/architectures/chat
    Note over Istio: Load balancing across pods<br/>SSL termination<br/>Rate limiting
    Istio->>FastAPI: Forward request to app pod

    %% Middleware Processing
    FastAPI->>TraceMW: Process request
    TraceMW->>Jaeger: Start trace span
    TraceMW->>MetricsMW: Continue middleware chain
    MetricsMW->>Prometheus: Record HTTP metrics
    MetricsMW->>AuthMW: Continue middleware chain
    AuthMW->>Database: Validate JWT token
    Database-->>AuthMW: User authentication result
    AuthMW->>Router: Authenticated request

    %% API Routing
    Router->>Orchestrator: Route to chat endpoint
    Note over Router: Dependency injection:<br/>- Database session<br/>- User context<br/>- Redis client

    %% Agent Orchestration Workflow
    Orchestrator->>Jaeger: Create workflow span
    Orchestrator->>Prometheus: Record workflow metrics
    
    %% Step 1: Requirements Analysis
    Orchestrator->>BusinessAnalyst: Analyze user requirements
    BusinessAnalyst->>AnthropicAPI: Process natural language
    AnthropicAPI-->>BusinessAnalyst: Structured requirements
    BusinessAnalyst->>Cache: Cache analysis results
    BusinessAnalyst-->>Orchestrator: Requirements analysis complete

    %% Step 2: Architecture Design (Sequential)
    Orchestrator->>BusinessArch: Design business architecture
    BusinessArch->>AnthropicAPI: Business layer analysis
    BusinessArch->>Database: Query existing architectures
    Database-->>BusinessArch: Architecture templates
    AnthropicAPI-->>BusinessArch: Business design recommendations
    BusinessArch-->>Orchestrator: Business architecture complete

    Orchestrator->>AppArch: Design application architecture
    AppArch->>AnthropicAPI: Application layer analysis
    AppArch->>Cache: Get reference architectures
    Cache-->>AppArch: Cached patterns
    AnthropicAPI-->>AppArch: Application design recommendations
    AppArch-->>Orchestrator: Application architecture complete

    Orchestrator->>InfraArch: Design infrastructure architecture
    InfraArch->>AnthropicAPI: Infrastructure analysis
    InfraArch->>CloudAPIs: Get cloud pricing/capabilities
    CloudAPIs-->>InfraArch: Cloud service data
    AnthropicAPI-->>InfraArch: Infrastructure recommendations
    InfraArch-->>Orchestrator: Infrastructure architecture complete

    %% Step 3: Solution Integration
    Orchestrator->>SolutionArch: Integrate all architectures
    SolutionArch->>AnthropicAPI: Solution integration analysis
    SolutionArch->>Database: Store integrated solution
    Database-->>SolutionArch: Storage confirmation
    AnthropicAPI-->>SolutionArch: Integrated solution
    SolutionArch-->>Orchestrator: Solution integration complete

    %% Step 4: Decision Support
    Orchestrator->>DecisionSupport: Analyze options and recommend
    DecisionSupport->>AnthropicAPI: Multi-criteria analysis
    DecisionSupport->>Cache: Cache decision analysis
    AnthropicAPI-->>DecisionSupport: Decision recommendations
    DecisionSupport-->>Orchestrator: Decision analysis complete

    %% Step 5: Conditional Specialized Processing
    alt Implementation Planning Required
        Orchestrator->>ProjectMgr: Generate project plan
        ProjectMgr->>AnthropicAPI: Project planning analysis
        AnthropicAPI-->>ProjectMgr: Project plan
        ProjectMgr-->>Orchestrator: Project plan complete
    end

    alt Cost Analysis Required
        Orchestrator->>Accountant: Perform financial analysis
        Accountant->>AnthropicAPI: Financial analysis
        Accountant->>CloudAPIs: Get cost estimates
        CloudAPIs-->>Accountant: Pricing data
        AnthropicAPI-->>Accountant: Financial recommendations
        Accountant-->>Orchestrator: Financial analysis complete
    end

    %% Step 6: Workflow Finalization
    Orchestrator->>Database: Store workflow results
    Database-->>Orchestrator: Storage confirmation
    Orchestrator->>Prometheus: Record completion metrics
    Orchestrator->>Jaeger: Complete workflow span

    %% Response Generation
    Orchestrator-->>Router: Workflow result
    Router-->>MetricsMW: API response
    MetricsMW->>Prometheus: Record response metrics
    MetricsMW-->>TraceMW: Continue response chain
    TraceMW->>Jaeger: Complete request span
    TraceMW-->>FastAPI: HTTP response

    %% Backend to Frontend
    FastAPI-->>Istio: Return response
    Istio-->>APIClient: Forward response
    APIClient-->>StreamlitUI: Parsed response data
    StreamlitUI->>SessionMgr: Update session state
    SessionMgr-->>StreamlitUI: State updated
    StreamlitUI-->>User: Display agent responses

    %% Monitoring and Observability (Parallel)
    par Performance Monitoring
        Prometheus->>Prometheus: Aggregate metrics
        Note over Prometheus: - HTTP request rates<br/>- Response times<br/>- Error rates<br/>- Agent execution times<br/>- Database performance
    and Distributed Tracing
        Jaeger->>Jaeger: Collect trace data
        Note over Jaeger: - End-to-end request flow<br/>- Agent execution spans<br/>- Database query traces<br/>- External API calls<br/>- Performance bottlenecks
    and Database Optimization
        Database->>Database: Monitor performance
        Note over Database: - Query optimization<br/>- Connection pooling<br/>- Index recommendations<br/>- Cache hit ratios
    and Cache Management
        Cache->>Cache: Manage cached data
        Note over Cache: - Query result caching<br/>- Session data<br/>- Reference architectures<br/>- Agent configurations
    end

    %% Performance Optimization Loop
    Note over Orchestrator,Prometheus: Continuous performance optimization based on metrics:<br/>- Auto-scaling triggers (HPA)<br/>- Connection pool adjustments<br/>- Cache warming strategies<br/>- Circuit breaker activation
```

## Key Components and Their Interactions

### 1. **Frontend Layer**
- **Streamlit UI**: User interface with chat components
- **Session Manager**: Maintains user context and conversation history
- **API Client**: HTTP client with authentication and request formatting

### 2. **Infrastructure Layer**
- **Istio Gateway**: Service mesh with load balancing, SSL, and traffic management
- **FastAPI App**: Main application server with ASGI runtime
- **Middleware Stack**: Authentication, tracing, and metrics collection

### 3. **Agent Orchestration Layer**
- **Multi-Agent Orchestrator**: Coordinates workflow between specialized agents
- **Sequential Agent Processing**: Business → Application → Infrastructure → Solution → Decision
- **Conditional Routing**: Project Management and Financial Analysis based on request type

### 4. **AI Agent Layer**
- **Business Analyst**: Natural language processing and requirements analysis
- **Architecture Agents**: Specialized domain experts for different architecture layers
- **Decision Support**: Multi-criteria analysis and recommendation generation

### 5. **Data and Integration Layer**
- **PostgreSQL Database**: Persistent storage with connection pooling
- **Redis Cache**: Multi-level caching for performance optimization
- **External APIs**: Anthropic Claude API and cloud provider integrations

### 6. **Observability Layer**
- **Prometheus**: Metrics collection and aggregation
- **Jaeger**: Distributed tracing and performance analysis
- **Performance Optimization**: Real-time monitoring and auto-scaling

## Performance Characteristics

### **Timing Breakdown (Typical Request)**
- **Frontend Processing**: 10-20ms
- **Network/Load Balancer**: 5-10ms
- **Authentication/Middleware**: 15-25ms
- **Agent Orchestration**: 2-8 seconds (depending on complexity)
  - Business Analyst: 500-1000ms
  - Architecture Agents: 1-2 seconds each
  - Decision Support: 500-1500ms
- **Database Operations**: 10-50ms
- **Response Generation**: 20-50ms
- **Total Response Time**: 3-10 seconds

### **Scalability Features**
- **Horizontal Pod Autoscaling**: 2-10 replicas based on CPU/memory
- **Database Connection Pooling**: 20 connections + 30 overflow
- **Redis Caching**: 90%+ cache hit ratio target
- **Circuit Breakers**: Protect against external API failures
- **Load Balancing**: Even distribution across available pods

### **Monitoring and Alerting**
- **Response Time Alerts**: >2 seconds for 95th percentile
- **Error Rate Alerts**: >5% error rate
- **Resource Utilization**: CPU >80%, Memory >90%
- **Agent Performance**: Execution time and success rates
- **Database Performance**: Query latency and connection pool usage

This sequence diagram illustrates the sophisticated, multi-layered architecture designed for scalability, observability, and optimal performance in processing complex architectural requests through AI-powered agent workflows.