# Smart Parking Meter System - OAM Component Definitions and Application Specifications

**Generated from**: Smart Parking System PRD  
**Platform**: Health Service IDP with OAM/KubeVela + Crossplane  
**Architecture**: Cloud-native microservices with real-time streaming capabilities

## Executive Summary

This document provides comprehensive OAM (Open Application Model) definitions for the Smart Parking Meter System, a cloud-native platform that transforms urban parking management through IoT sensor technology, real-time availability tracking, and AI-powered chat interfaces. The system is designed to reduce parking search time by 40%, increase lot utilization by 25%, and provide transparent, real-time parking information.

## System Architecture Overview

### High-Level Component Mapping

| **Business Capability** | **OAM Component Type** | **Infrastructure Dependencies** | **Scaling Pattern** |
|------------------------|------------------------|--------------------------------|-------------------|
| IoT Sensor Data Processing | `realtime-platform` | Kafka + MQTT + InfluxDB | High-throughput burst scaling |
| Real-time Availability Queries | `webservice` | Redis + PostgreSQL | Sub-second response scaling |
| Conversational AI | `rasa-chatbot` | Redis + NLP Models | Always-on with burst capacity |
| Administrative Dashboard | `webservice` | PostgreSQL + Redis | Standard web scaling |
| Dynamic Pricing Engine | `webservice` | PostgreSQL + Analytics DB | Batch + real-time processing |
| Notification System | `webservice` | Redis + External APIs | Event-driven scaling |
| Analytics & Reporting | `webservice` + `clickhouse` | ClickHouse + Metabase | Analytics workload scaling |

## OAM Application Specifications

### 1. Complete Smart Parking Platform Application

```yaml
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: smart-parking-platform
  namespace: smart-parking
  labels:
    app.kubernetes.io/name: smart-parking-platform
    app.kubernetes.io/version: "1.0.0"
    parking.platform.io/system-type: "complete"
spec:
  components:
  
  # 1. SENSOR DATA INGESTION SERVICE (Real-time IoT Platform)
  - name: sensor-data-platform
    type: realtime-platform
    properties:
      image: socrates12345/smart-parking-sensor-ingestion:latest
      port: 8080
      language: python
      framework: fastapi
      repository: smart-parking-sensor-platform
      database: postgres
      visualization: metabase
      iot: true
      dataRetention: "90d"  # 90 days for compliance
      resources:
        cpu: "2000m"
        memory: "4Gi"
      environment:
        SENSOR_BATCH_SIZE: "1000"
        MQTT_TOPIC_PREFIX: "parking/sensors"
        KAFKA_TOPIC: "sensor_readings"
        INFLUXDB_BUCKET: "parking_sensors"
        MAX_SENSORS_PER_LOT: "500"
        SENSOR_HEARTBEAT_INTERVAL: "30"
      targetEnvironment: parking-production

  # 2. REAL-TIME AVAILABILITY SERVICE (High-performance queries)
  - name: availability-service
    type: webservice
    properties:
      image: socrates12345/smart-parking-availability:latest
      port: 8080
      language: python
      framework: fastapi
      repository: smart-parking-availability-service
      realtime: sensor-data-platform  # Connect to real-time platform
      resources:
        cpu: "1000m"
        memory: "2Gi"
      environment:
        REDIS_CACHE_TTL: "30"
        MAX_QUERY_CONCURRENT: "1000"
        RESPONSE_TARGET_MS: "500"
        CACHE_STRATEGY: "write-through"
        AVAILABILITY_UPDATE_INTERVAL: "5"
      targetEnvironment: parking-production
    traits:
    - type: scaler
      properties:
        replicas: 3
        minReplicas: 2
        maxReplicas: 20
        targetCPU: 70
        targetMemory: 80
        scaleUpSteps: 2
        scaleDownSteps: 1

  # 3. CONVERSATIONAL AI CHAT SERVICE (Rasa-based)
  - name: parking-chat-assistant
    type: rasa-chatbot
    properties:
      rasaImage: socrates12345/smart-parking-chat-rasa:latest
      actionsImage: socrates12345/smart-parking-chat-actions:latest
      language: rasa
      framework: chatbot
      repository: smart-parking-chat-service
      minScale: 2  # Always-on for immediate response
      maxScale: 10
      targetConcurrency: 5
      actionsMinScale: 1
      actionsMaxScale: 8
      actionsTargetConcurrency: 10
      resources:
        cpu: "500m"
        memory: "1Gi"
      actionsResources:
        cpu: "250m"
        memory: "512Mi"
      environment:
        NLP_MODEL_PATH: "/app/models"
        CONVERSATION_TIMEOUT: "1800"
        MAX_HISTORY_LENGTH: "10"
        PARKING_API_ENDPOINT: "http://availability-service:8080"
        MAPS_API_INTEGRATION: "true"
      enableIstioGateway: true
      chatbotHost: "chat.smartparking.local"
      enableTLS: true
      targetEnvironment: parking-production

  # 4. ADMIN MANAGEMENT DASHBOARD (Web interface)
  - name: admin-dashboard
    type: webservice
    properties:
      image: socrates12345/smart-parking-admin:latest
      port: 8080
      language: python
      framework: fastapi
      repository: smart-parking-admin-dashboard
      resources:
        cpu: "500m"
        memory: "1Gi"
      environment:
        DASHBOARD_REFRESH_INTERVAL: "30"
        MAX_CONCURRENT_ADMINS: "50"
        SESSION_TIMEOUT: "3600"
        EXPORT_FORMATS: "pdf,excel,csv"
        ALERT_THRESHOLD_SENSORS_OFFLINE: "5"
        ALERT_THRESHOLD_REVENUE_DROP: "20"
      envFrom:
      - secretRef:
          name: admin-auth-credentials
      targetEnvironment: parking-production
    traits:
    - type: gateway
      properties:
        host: admin.smartparking.local
        http:
          "/": 8080
        tls:
          secretName: smartparking-tls

  # 5. DYNAMIC PRICING SERVICE (Revenue optimization)
  - name: pricing-engine
    type: webservice
    properties:
      image: socrates12345/smart-parking-pricing:latest
      port: 8080
      language: python
      framework: fastapi
      repository: smart-parking-pricing-engine
      realtime: sensor-data-platform  # Access to real-time occupancy data
      resources:
        cpu: "750m"
        memory: "1.5Gi"
      environment:
        PRICING_ALGORITHM: "demand_based"
        PRICE_UPDATE_INTERVAL: "300"  # 5 minutes
        MAX_PRICE_INCREASE_PERCENT: "50"
        MIN_PRICE_DECREASE_PERCENT: "20"
        PEAK_HOURS_START: "07:00"
        PEAK_HOURS_END: "19:00"
        EVENT_SURGE_MULTIPLIER: "2.0"
        A_B_TEST_ENABLED: "true"
      targetEnvironment: parking-production

  # 6. NOTIFICATION SERVICE (Multi-channel alerts)
  - name: notification-service
    type: webservice
    properties:
      image: socrates12345/smart-parking-notifications:latest
      port: 8080
      language: python
      framework: fastapi
      repository: smart-parking-notification-service
      resources:
        cpu: "300m"
        memory: "512Mi"
      environment:
        NOTIFICATION_CHANNELS: "sms,email,push,slack"
        BATCH_SIZE: "100"
        RETRY_ATTEMPTS: "3"
        RATE_LIMIT_PER_USER: "10"
        ALERT_ESCALATION_MINUTES: "15"
      envFrom:
      - secretRef:
          name: notification-provider-credentials
      targetEnvironment: parking-production
    traits:
    - type: scaler
      properties:
        replicas: 1
        minReplicas: 1
        maxReplicas: 5
        targetCPU: 60
        scaleUpSteps: 1
        scaleDownSteps: 1

  # 7. ANALYTICS & REPORTING SERVICE
  - name: analytics-service
    type: webservice
    properties:
      image: socrates12345/smart-parking-analytics:latest
      port: 8080
      language: python
      framework: fastapi
      repository: smart-parking-analytics-service
      realtime: sensor-data-platform  # Access to streaming data
      resources:
        cpu: "1000m"
        memory: "2Gi"
      environment:
        ANALYTICS_BATCH_INTERVAL: "3600"  # Hourly batch processing
        PREDICTION_MODEL_PATH: "/app/models/demand_forecasting"
        REPORT_GENERATION_SCHEDULE: "0 6 * * *"  # Daily at 6 AM
        ML_TRAINING_SCHEDULE: "0 2 * * 0"  # Weekly on Sunday at 2 AM
        FORECAST_HORIZON_DAYS: "30"
      targetEnvironment: parking-production

  # 8. CLICKHOUSE ANALYTICS DATABASE (Time-series and OLAP)
  - name: parking-analytics-db
    type: clickhouse
    properties:
      name: parking-analytics
      auth:
        username: parking_analyst
        password: secure-analytics-password
        database: parking_analytics
      architecture: replication
      replicas: 2
      shards: 2
      storage: 100Gi
      storageClass: gp3
      resources:
        cpu: 4000m
        memory: 8Gi
      security:
        tlsEnabled: true
        networkPolicyEnabled: true
        certificateSecret: clickhouse-tls-cert
      backup:
        enabled: true
        schedule: "0 3 * * *"  # Daily at 3 AM  
        retentionDays: 2555    # 7 years for compliance
      targetEnvironment: parking-production

  # 9. SUPPORTING INFRASTRUCTURE COMPONENTS
  
  # Redis Cache for high-performance queries
  - name: parking-cache
    type: redis
    properties:
      name: parking-cache
      architecture: replication
      replicas: 3
      storage: 20Gi
      auth:
        enabled: true
        password: secure-redis-password
      resources:
        cpu: "500m"
        memory: "2Gi"
      targetEnvironment: parking-production

  # MongoDB for semi-structured data (user preferences, configurations)
  - name: parking-config-db
    type: mongodb
    properties:
      name: parking-config
      architecture: replicaset
      replicas: 3
      storage: 50Gi
      auth:
        enabled: true
        rootPassword: secure-mongo-root-password
        username: parking_app
        password: secure-mongo-password
        database: parking_config
      resources:
        cpu: "750m"
        memory: "1.5Gi"
      targetEnvironment: parking-production

  # PostgreSQL for transactional data
  - name: parking-transactional-db
    type: neon-postgres
    properties:
      name: parking-transactions
      database: parking_system
      targetEnvironment: parking-production

  policies:
  - name: parking-topology
    type: topology
    properties:
      namespace: smart-parking
      clusters:
      - parking-production

  - name: parking-security
    type: security-policy
    properties:
      allowedRegistries:
      - docker.io/socrates12345
      - docker.io/bitnami
      networkPolicies:
        enabled: true
        defaultDeny: true
        allowedNamespaces:
        - istio-system
        - monitoring

  - name: parking-scaling
    type: shared-resource
    properties:
      cpu: "16000m"
      memory: "32Gi"
      clusters:
      - parking-production

  workflow:
    steps:
    - name: deploy-infrastructure
      type: deploy
      properties:
        components:
        - parking-analytics-db
        - parking-cache
        - parking-config-db
        - parking-transactional-db
    - name: deploy-backend-services
      type: deploy
      properties:
        components:
        - sensor-data-platform
        - availability-service
        - pricing-engine
        - notification-service
        - analytics-service
      dependsOn:
      - deploy-infrastructure
    - name: deploy-user-interfaces
      type: deploy
      properties:
        components:
        - parking-chat-assistant
        - admin-dashboard
      dependsOn:
      - deploy-backend-services
```

## TraitDefinitions for Operational Concerns

### 1. Auto-scaling Trait for Sensor Data Bursts

```yaml
apiVersion: core.oam.dev/v1beta1
kind: TraitDefinition
metadata:
  name: sensor-burst-scaler
  annotations:
    definition.oam.dev/description: "Auto-scaling for high-throughput sensor data processing with burst capacity"
spec:
  appliesToWorkloads:
  - serving.knative.dev/v1.Service
  definitionRef:
    name: manualscalertraits.core.oam.dev
  schematic:
    cue:
      template: |
        parameter: {
          // Sensor-specific scaling parameters
          baseReplicas: *2 | int
          maxReplicas: *50 | int
          targetSensorsPerReplica: *1000 | int
          scaleUpThreshold: *80 | int
          scaleDownThreshold: *30 | int
          burstCapacityMultiplier: *3 | int
          cooldownSeconds: *300 | int
        }
        
        // Generate HPA for sensor burst handling
        outputs: {
          hpa: {
            apiVersion: "autoscaling/v2"
            kind: "HorizontalPodAutoscaler"
            metadata: {
              name: context.name + "-sensor-hpa"
              namespace: context.namespace
            }
            spec: {
              scaleTargetRef: {
                apiVersion: "serving.knative.dev/v1"
                kind: "Service"
                name: context.name
              }
              minReplicas: parameter.baseReplicas
              maxReplicas: parameter.maxReplicas
              behavior: {
                scaleUp: {
                  stabilizationWindowSeconds: 60
                  policies: [{
                    type: "Percent"
                    value: parameter.burstCapacityMultiplier * 100
                    periodSeconds: 60
                  }]
                }
                scaleDown: {
                  stabilizationWindowSeconds: parameter.cooldownSeconds
                  policies: [{
                    type: "Percent" 
                    value: 50
                    periodSeconds: 300
                  }]
                }
              }
              metrics: [
                {
                  type: "Resource"
                  resource: {
                    name: "cpu"
                    target: {
                      type: "Utilization"
                      averageUtilization: parameter.scaleUpThreshold
                    }
                  }
                },
                {
                  type: "Resource"
                  resource: {
                    name: "memory"
                    target: {
                      type: "Utilization"
                      averageUtilization: parameter.scaleUpThreshold
                    }
                  }
                }
              ]
            }
          }
        }
```

### 2. Circuit Breaker Trait for External Integrations

```yaml
apiVersion: core.oam.dev/v1beta1
kind: TraitDefinition
metadata:
  name: parking-circuit-breaker
  annotations:
    definition.oam.dev/description: "Circuit breaker for external integrations (Maps API, Payment systems, SMS providers)"
spec:
  appliesToWorkloads:
  - serving.knative.dev/v1.Service
  schematic:
    cue:
      template: |
        parameter: {
          // Circuit breaker configuration
          failureThreshold: *5 | int
          recoveryTimeout: *30 | int
          halfOpenMaxCalls: *3 | int
          endpoints: [...string]
          fallbackEnabled: *true | bool
          retryAttempts: *3 | int
        }
        
        // Generate Istio DestinationRule with circuit breaker
        outputs: {
          "circuit-breaker": {
            apiVersion: "networking.istio.io/v1beta1"
            kind: "DestinationRule"
            metadata: {
              name: context.name + "-circuit-breaker"
              namespace: context.namespace
            }
            spec: {
              host: context.name + "." + context.namespace + ".svc.cluster.local"
              trafficPolicy: {
                outlierDetection: {
                  consecutiveErrors: parameter.failureThreshold
                  interval: parameter.recoveryTimeout + "s"
                  baseEjectionTime: parameter.recoveryTimeout + "s"
                  maxEjectionPercent: 50
                  minHealthPercent: 30
                }
                connectionPool: {
                  tcp: {
                    maxConnections: 100
                    connectTimeout: "10s"
                  }
                  http: {
                    http1MaxPendingRequests: 50
                    maxRequestsPerConnection: 2
                    maxRetries: parameter.retryAttempts
                    consecutiveGatewayErrors: parameter.failureThreshold
                  }
                }
              }
            }
          }
          
          "retry-policy": {
            apiVersion: "networking.istio.io/v1beta1"
            kind: "VirtualService"
            metadata: {
              name: context.name + "-retry-policy"
              namespace: context.namespace
            }
            spec: {
              hosts: [context.name + "." + context.namespace + ".svc.cluster.local"]
              http: [{
                retries: {
                  attempts: parameter.retryAttempts
                  perTryTimeout: "5s"
                  retryOn: "gateway-error,connect-failure,refused-stream"
                }
                route: [{
                  destination: {
                    host: context.name + "." + context.namespace + ".svc.cluster.local"
                  }
                }]
              }]
            }
          }
        }
```

### 3. Monitoring and Observability Trait

```yaml
apiVersion: core.oam.dev/v1beta1
kind: TraitDefinition
metadata:
  name: parking-monitoring
  annotations:
    definition.oam.dev/description: "Comprehensive monitoring for parking system components with business metrics"
spec:
  appliesToWorkloads:
  - serving.knative.dev/v1.Service
  schematic:
    cue:
      template: |
        parameter: {
          // Monitoring configuration
          businessMetrics: *true | bool
          alertingEnabled: *true | bool
          dashboardEnabled: *true | bool
          tracing: *true | bool
          logLevel: *"INFO" | string
          customMetrics: *[] | [...string]
          alertThresholds: *{
            errorRate: 5
            responseTime: 2000
            availability: 99.5
          } | {
            errorRate?: int
            responseTime?: int
            availability?: float
          }
        }
        
        // Generate ServiceMonitor for Prometheus scraping
        outputs: {
          "service-monitor": {
            apiVersion: "monitoring.coreos.com/v1"
            kind: "ServiceMonitor"
            metadata: {
              name: context.name + "-monitoring"
              namespace: context.namespace
              labels: {
                "parking.platform.io/monitoring": "enabled"
                "app.kubernetes.io/name": context.name
              }
            }
            spec: {
              selector: {
                matchLabels: {
                  "app.kubernetes.io/name": context.name
                }
              }
              endpoints: [{
                port: "http"
                path: "/metrics"
                interval: "30s"
                scrapeTimeout: "10s"
              }]
            }
          }
          
          if parameter.alertingEnabled {
            "prometheus-rule": {
              apiVersion: "monitoring.coreos.com/v1"
              kind: "PrometheusRule"
              metadata: {
                name: context.name + "-alerts"
                namespace: context.namespace
                labels: {
                  "parking.platform.io/alerts": "enabled"
                }
              }
              spec: {
                groups: [{
                  name: context.name + ".rules"
                  rules: [
                    {
                      alert: context.name + "HighErrorRate"
                      expr: "rate(http_requests_total{service=\"" + context.name + "\",code!~\"2..\"}[5m]) > " + (parameter.alertThresholds.errorRate / 100)
                      for: "5m"
                      labels: {
                        severity: "warning"
                        service: context.name
                      }
                      annotations: {
                        summary: "High error rate detected for " + context.name
                        description: "Error rate is above " + parameter.alertThresholds.errorRate + "% for 5 minutes"
                      }
                    },
                    {
                      alert: context.name + "HighResponseTime"
                      expr: "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service=\"" + context.name + "\"}[5m])) > " + (parameter.alertThresholds.responseTime / 1000)
                      for: "5m"
                      labels: {
                        severity: "warning"
                        service: context.name
                      }
                      annotations: {
                        summary: "High response time detected for " + context.name
                        description: "95th percentile response time is above " + parameter.alertThresholds.responseTime + "ms"
                      }
                    },
                    {
                      alert: context.name + "ServiceDown"
                      expr: "up{service=\"" + context.name + "\"} == 0"
                      for: "1m"
                      labels: {
                        severity: "critical"
                        service: context.name
                      }
                      annotations: {
                        summary: context.name + " service is down"
                        description: "Service has been down for more than 1 minute"
                      }
                    }
                  ]
                }]
              }
            }
          }
        }
```

### 4. Security Policy Trait

```yaml
apiVersion: core.oam.dev/v1beta1
kind: TraitDefinition
metadata:
  name: parking-security
  annotations:
    definition.oam.dev/description: "Security policies for parking system components with PCI DSS and data protection compliance"
spec:
  appliesToWorkloads:
  - serving.knative.dev/v1.Service
  schematic:
    cue:
      template: |
        parameter: {
          // Security configuration
          networkPolicyEnabled: *true | bool
          tlsRequired: *true | bool
          rbacEnabled: *true | bool
          podSecurityPolicy: *true | bool
          allowedIngressSources: *["istio-system"] | [...string]
          allowedEgressDestinations: *[] | [...string]
          dataEncryption: *true | bool
          auditLogging: *true | bool
        }
        
        // Generate NetworkPolicy
        outputs: {
          if parameter.networkPolicyEnabled {
            "network-policy": {
              apiVersion: "networking.k8s.io/v1"
              kind: "NetworkPolicy"
              metadata: {
                name: context.name + "-network-policy"
                namespace: context.namespace
              }
              spec: {
                podSelector: {
                  matchLabels: {
                    "app.kubernetes.io/name": context.name
                  }
                }
                policyTypes: ["Ingress", "Egress"]
                ingress: [
                  for source in parameter.allowedIngressSources {
                    from: [{
                      namespaceSelector: {
                        matchLabels: {
                          name: source
                        }
                      }
                    }]
                  }
                ]
                egress: [
                  // Always allow DNS
                  {
                    to: []
                    ports: [{
                      protocol: "UDP"
                      port: 53
                    }]
                  }
                ] + [
                  // Allow specific egress destinations
                  for dest in parameter.allowedEgressDestinations {
                    to: [{
                      namespaceSelector: {
                        matchLabels: {
                          name: dest
                        }
                      }
                    }]
                  }
                ]
              }
            }
          }
          
          if parameter.rbacEnabled {
            "service-account": {
              apiVersion: "v1"
              kind: "ServiceAccount"
              metadata: {
                name: context.name + "-sa"
                namespace: context.namespace
                labels: {
                  "parking.platform.io/security": "rbac"
                }
              }
            }
            
            "role": {
              apiVersion: "rbac.authorization.k8s.io/v1"
              kind: "Role"
              metadata: {
                name: context.name + "-role"
                namespace: context.namespace
              }
              rules: [
                {
                  apiGroups: [""]
                  resources: ["secrets", "configmaps"]
                  verbs: ["get", "list"]
                },
                {
                  apiGroups: [""]
                  resources: ["pods"]
                  verbs: ["get", "list", "watch"]
                }
              ]
            }
            
            "role-binding": {
              apiVersion: "rbac.authorization.k8s.io/v1"
              kind: "RoleBinding"
              metadata: {
                name: context.name + "-role-binding"
                namespace: context.namespace
              }
              subjects: [{
                kind: "ServiceAccount"
                name: context.name + "-sa"
                namespace: context.namespace
              }]
              roleRef: {
                kind: "Role"
                name: context.name + "-role"
                apiGroup: "rbac.authorization.k8s.io"
              }
            }
          }
          
          if parameter.tlsRequired {
            "tls-policy": {
              apiVersion: "security.istio.io/v1beta1"
              kind: "PeerAuthentication"
              metadata: {
                name: context.name + "-tls-policy"
                namespace: context.namespace
              }
              spec: {
                selector: {
                  matchLabels: {
                    "app.kubernetes.io/name": context.name
                  }
                }
                mtls: {
                  mode: "STRICT"
                }
              }
            }
          }
        }
```

## WorkloadDefinitions for Different Deployment Patterns

### 1. High-Throughput Sensor Data Processing Workload

```yaml
apiVersion: core.oam.dev/v1beta1
kind: WorkloadDefinition
metadata:
  name: sensor-data-processor
  annotations:
    definition.oam.dev/description: "High-throughput sensor data processing workload with burst capacity and stream processing"
spec:
  definitionRef:
    name: deployments.apps
  schematic:
    cue:
      template: |
        parameter: {
          image: string
          replicas: *3 | int
          maxReplicas: *50 | int
          targetSensorsPerPod: *1000 | int
          processingMode: *"stream" | "batch" | "stream"
          kafkaTopics: [...string]
          mqttTopics: [...string]
          resources: {
            cpu: *"2000m" | string
            memory: *"4Gi" | string
          }
        }
        
        output: {
          apiVersion: "apps/v1"
          kind: "Deployment"
          metadata: {
            name: context.name
            namespace: context.namespace
            labels: {
              "parking.platform.io/workload-type": "sensor-processor"
              "parking.platform.io/processing-mode": parameter.processingMode
            }
          }
          spec: {
            replicas: parameter.replicas
            selector: {
              matchLabels: {
                "app.kubernetes.io/name": context.name
              }
            }
            template: {
              metadata: {
                labels: {
                  "app.kubernetes.io/name": context.name
                  "parking.platform.io/workload-type": "sensor-processor"
                }
                annotations: {
                  "prometheus.io/scrape": "true"
                  "prometheus.io/port": "8080"
                  "prometheus.io/path": "/metrics"
                }
              }
              spec: {
                containers: [{
                  name: "processor"
                  image: parameter.image
                  ports: [
                    {containerPort: 8080, name: "http"},
                    {containerPort: 9092, name: "metrics"}
                  ]
                  env: [
                    {name: "PROCESSING_MODE", value: parameter.processingMode},
                    {name: "KAFKA_TOPICS", value: strings.Join(parameter.kafkaTopics, ",")},
                    {name: "MQTT_TOPICS", value: strings.Join(parameter.mqttTopics, ",")},
                    {name: "TARGET_SENSORS_PER_POD", value: "\(parameter.targetSensorsPerPod)"},
                    {name: "WORKER_CONCURRENCY", value: "10"},
                    {name: "BATCH_SIZE", value: "1000"},
                    {name: "PROCESSING_TIMEOUT", value: "30s"}
                  ]
                  resources: {
                    requests: {
                      cpu: "500m"
                      memory: "1Gi"
                    }
                    limits: {
                      cpu: parameter.resources.cpu
                      memory: parameter.resources.memory
                    }
                  }
                  livenessProbe: {
                    httpGet: {
                      path: "/health"
                      port: 8080
                    }
                    initialDelaySeconds: 30
                    periodSeconds: 10
                  }
                  readinessProbe: {
                    httpGet: {
                      path: "/ready"
                      port: 8080
                    }
                    initialDelaySeconds: 5
                    periodSeconds: 5
                  }
                }]
              }
            }
          }
        }
```

### 2. Real-time Chat Services Workload

```yaml
apiVersion: core.oam.dev/v1beta1
kind: WorkloadDefinition
metadata:
  name: realtime-chat-service
  annotations:
    definition.oam.dev/description: "Real-time chat service workload with WebSocket support and conversation state management"
spec:
  definitionRef:
    name: services.serving.knative.dev
  schematic:
    cue:
      template: |
        parameter: {
          rasaImage: string
          actionsImage: string
          minScale: *2 | int
          maxScale: *10 | int
          conversationTimeout: *1800 | int
          maxConcurrentChats: *100 | int
          websocketEnabled: *true | bool
          nlpModelPath: *"/app/models" | string
          resources: {
            cpu: *"500m" | string
            memory: *"1Gi" | string
          }
        }
        
        output: {
          apiVersion: "serving.knative.dev/v1"
          kind: "Service"
          metadata: {
            name: context.name
            namespace: context.namespace
            labels: {
              "parking.platform.io/workload-type": "realtime-chat"
              "parking.platform.io/websocket-enabled": "\(parameter.websocketEnabled)"
            }
          }
          spec: {
            template: {
              metadata: {
                annotations: {
                  "autoscaling.knative.dev/minScale": "\(parameter.minScale)"
                  "autoscaling.knative.dev/maxScale": "\(parameter.maxScale)"
                  "autoscaling.knative.dev/target": "\(parameter.maxConcurrentChats)"
                  "autoscaling.knative.dev/window": "60s"
                }
                labels: {
                  "parking.platform.io/workload-type": "realtime-chat"
                }
              }
              spec: {
                containerConcurrency: parameter.maxConcurrentChats
                timeoutSeconds: parameter.conversationTimeout
                containers: [{
                  image: parameter.rasaImage
                  ports: [{
                    containerPort: 5005
                    name: "http1"
                  }]
                  env: [
                    {name: "RASA_ACTION_ENDPOINT", value: "http://actions-service:5055/webhook"},
                    {name: "NLP_MODEL_PATH", value: parameter.nlpModelPath},
                    {name: "CONVERSATION_TIMEOUT", value: "\(parameter.conversationTimeout)"},
                    {name: "WEBSOCKET_ENABLED", value: "\(parameter.websocketEnabled)"},
                    {name: "MAX_CONCURRENT_CHATS", value: "\(parameter.maxConcurrentChats)"},
                    {name: "RASA_TELEMETRY_ENABLED", value: "false"}
                  ]
                  resources: {
                    requests: {
                      cpu: "250m"
                      memory: "512Mi"
                    }
                    limits: {
                      cpu: parameter.resources.cpu
                      memory: parameter.resources.memory
                    }
                  }
                  livenessProbe: {
                    httpGet: {
                      path: "/api/status"
                      port: 5005
                    }
                    initialDelaySeconds: 30
                    periodSeconds: 10
                  }
                  readinessProbe: {
                    httpGet: {
                      path: "/api/status"
                      port: 5005
                    }
                    initialDelaySeconds: 5
                    periodSeconds: 5
                  }
                }]
              }
            }
          }
        }
```

### 3. Admin Dashboard Services Workload

```yaml
apiVersion: core.oam.dev/v1beta1
kind: WorkloadDefinition
metadata:
  name: admin-dashboard-service
  annotations:
    definition.oam.dev/description: "Admin dashboard service workload with session management and role-based access"
spec:
  definitionRef:
    name: services.serving.knative.dev
  schematic:
    cue:
      template: |
        parameter: {
          image: string
          minScale: *1 | int
          maxScale: *5 | int
          sessionTimeout: *3600 | int
          maxConcurrentAdmins: *50 | int
          refreshInterval: *30 | int
          authProvider: *"oauth2" | "oauth2" | "ldap" | "local"
          resources: {
            cpu: *"500m" | string
            memory: *"1Gi" | string
          }
        }
        
        output: {
          apiVersion: "serving.knative.dev/v1"
          kind: "Service" 
          metadata: {
            name: context.name
            namespace: context.namespace
            labels: {
              "parking.platform.io/workload-type": "admin-dashboard"
              "parking.platform.io/auth-provider": parameter.authProvider
            }
          }
          spec: {
            template: {
              metadata: {
                annotations: {
                  "autoscaling.knative.dev/minScale": "\(parameter.minScale)"
                  "autoscaling.knative.dev/maxScale": "\(parameter.maxScale)"
                  "autoscaling.knative.dev/target": "\(parameter.maxConcurrentAdmins)"
                }
                labels: {
                  "parking.platform.io/workload-type": "admin-dashboard"
                }
              }
              spec: {
                containerConcurrency: parameter.maxConcurrentAdmins
                containers: [{
                  image: parameter.image
                  ports: [{
                    containerPort: 8080
                    name: "http1"
                  }]
                  env: [
                    {name: "AUTH_PROVIDER", value: parameter.authProvider},
                    {name: "SESSION_TIMEOUT", value: "\(parameter.sessionTimeout)"},
                    {name: "DASHBOARD_REFRESH_INTERVAL", value: "\(parameter.refreshInterval)"},
                    {name: "MAX_CONCURRENT_ADMINS", value: "\(parameter.maxConcurrentAdmins)"},
                    {name: "EXPORT_FORMATS", value: "pdf,excel,csv"},
                    {name: "RBAC_ENABLED", value: "true"}
                  ]
                  resources: {
                    requests: {
                      cpu: "100m"
                      memory: "256Mi"
                    }
                    limits: {
                      cpu: parameter.resources.cpu
                      memory: parameter.resources.memory
                    }
                  }
                  livenessProbe: {
                    httpGet: {
                      path: "/health"
                      port: 8080
                    }
                    initialDelaySeconds: 30
                    periodSeconds: 10
                  }
                  readinessProbe: {
                    httpGet: {
                      path: "/ready"
                      port: 8080
                    }
                    initialDelaySeconds: 5
                    periodSeconds: 5
                  }
                  volumeMounts: [{
                    name: "dashboard-config"
                    mountPath: "/app/config"
                    readOnly: true
                  }]
                }]
                volumes: [{
                  name: "dashboard-config"
                  configMap: {
                    name: context.name + "-config"
                  }
                }]
              }
            }
          }
        }
```

### 4. Background Analytics Jobs Workload

```yaml
apiVersion: core.oam.dev/v1beta1
kind: WorkloadDefinition
metadata:
  name: analytics-job-processor
  annotations:
    definition.oam.dev/description: "Background analytics job processor for batch ML training and report generation"
spec:
  definitionRef:
    name: cronjobs.batch
  schematic:
    cue:
      template: |
        parameter: {
          image: string
          schedule: *"0 2 * * *" | string  // Daily at 2 AM
          jobType: *"analytics" | "analytics" | "ml-training" | "reporting"
          timeoutMinutes: *120 | int
          resources: {
            cpu: *"2000m" | string
            memory: *"4Gi" | string
          }
          modelPath: *"/app/models" | string
          dataRetentionDays: *90 | int
        }
        
        output: {
          apiVersion: "batch/v1"
          kind: "CronJob"
          metadata: {
            name: context.name
            namespace: context.namespace
            labels: {
              "parking.platform.io/workload-type": "analytics-job"
              "parking.platform.io/job-type": parameter.jobType
            }
          }
          spec: {
            schedule: parameter.schedule
            concurrencyPolicy: "Forbid"
            successfulJobsHistoryLimit: 3
            failedJobsHistoryLimit: 1
            jobTemplate: {
              spec: {
                activeDeadlineSeconds: parameter.timeoutMinutes * 60
                template: {
                  metadata: {
                    labels: {
                      "parking.platform.io/workload-type": "analytics-job"
                      "parking.platform.io/job-type": parameter.jobType
                    }
                  }
                  spec: {
                    restartPolicy: "Never"
                    containers: [{
                      name: "analytics-processor"
                      image: parameter.image
                      env: [
                        {name: "JOB_TYPE", value: parameter.jobType},
                        {name: "MODEL_PATH", value: parameter.modelPath},
                        {name: "DATA_RETENTION_DAYS", value: "\(parameter.dataRetentionDays)"},
                        {name: "BATCH_SIZE", value: "10000"},
                        {name: "PARALLEL_WORKERS", value: "4"},
                        {name: "TIMEOUT_MINUTES", value: "\(parameter.timeoutMinutes)"}
                      ]
                      resources: {
                        requests: {
                          cpu: "1000m"
                          memory: "2Gi"
                        }
                        limits: {
                          cpu: parameter.resources.cpu
                          memory: parameter.resources.memory
                        }
                      }
                      volumeMounts: [
                        {
                          name: "model-storage"
                          mountPath: parameter.modelPath
                        },
                        {
                          name: "temp-data"
                          mountPath: "/tmp/analytics"
                        }
                      ]
                    }]
                    volumes: [
                      {
                        name: "model-storage"
                        persistentVolumeClaim: {
                          claimName: context.name + "-model-storage"
                        }
                      },
                      {
                        name: "temp-data"
                        emptyDir: {
                          sizeLimit: "20Gi"
                        }
                      }
                    ]
                  }
                }
              }
            }
          }
        }
```

## Deployment Considerations and Operational Guidance

### Infrastructure Requirements

**Minimum Cluster Resources:**
- **CPU**: 24 cores (48 vCPUs recommended for production)
- **Memory**: 96GB RAM (128GB recommended for production)
- **Storage**: 1TB SSD for databases and analytics
- **Network**: 10Gbps for high-throughput sensor data ingestion

**Scaling Characteristics:**
- **Sensor Data Platform**: Scales to 100,000+ sensors with 50 replicas
- **Availability Service**: Sub-second responses with Redis caching and 20 replicas
- **Chat Service**: Always-on with 2-10 replicas for immediate response
- **Admin Dashboard**: Standard web scaling 1-5 replicas
- **Analytics**: Batch processing jobs with high-memory requirements

### Operational Procedures

**Deployment Order:**
1. **Infrastructure Components**: Databases, caches, message queues
2. **Real-time Platform**: Sensor data ingestion and streaming infrastructure  
3. **Core Services**: Availability, pricing, and notification services
4. **User Interfaces**: Chat assistant and admin dashboard
5. **Analytics**: Background processing and reporting services

**Monitoring Strategy:**
- **Real-time Metrics**: Sensor data throughput, query response times, chat responsiveness
- **Business KPIs**: Parking utilization rates, revenue optimization, user satisfaction
- **Infrastructure Health**: Database performance, cache hit rates, message queue lag
- **Security Monitoring**: Authentication failures, API rate limiting, network policy violations

**Backup and Recovery:**
- **Database Backups**: Daily PostgreSQL and ClickHouse backups with 7-year retention
- **Configuration Backups**: OAM applications and secrets in GitOps repository
- **Model Backups**: ML models and training data with versioning
- **Disaster Recovery**: Cross-region replication for critical components

### Performance Targets

**Service Level Objectives (SLOs):**
- **Availability Service**: 99.9% uptime, < 500ms p95 response time
- **Sensor Data Platform**: 99.5% uptime, < 5 seconds data freshness
- **Chat Service**: 99.8% uptime, < 2 seconds response time
- **Admin Dashboard**: 99.5% uptime, < 3 seconds page load time
- **Overall System**: 99.5% uptime with graceful degradation

**Scaling Targets:**
- **Sensors**: Support for 100,000+ sensors per region
- **Concurrent Users**: 10,000+ simultaneous users
- **API Throughput**: 50,000+ requests/second peak capacity
- **Data Ingestion**: 1M+ sensor readings per minute

### Security Considerations

**Data Protection:**
- **Encryption**: TLS 1.3 in transit, AES-256 at rest
- **Authentication**: OAuth 2.0 with JWT tokens, MFA for admin access
- **Authorization**: Role-based access control (RBAC) with least privilege
- **Audit Logging**: Comprehensive audit trails for all data access

**Compliance:**
- **GDPR**: Data minimization, right to erasure, consent management
- **PCI DSS**: Payment data protection for pricing and billing
- **SOC 2**: Security controls for service organization
- **Local Regulations**: Region-specific data residency requirements

### Cost Optimization

**Resource Management:**
- **Auto-scaling**: Aggressive scale-to-zero for non-critical services
- **Spot Instances**: Use spot instances for batch analytics jobs
- **Data Lifecycle**: Automated data archival and deletion policies
- **Reserved Capacity**: Reserved instances for baseline capacity

**Estimated Monthly Costs** (AWS us-east-1):
- **Compute**: $2,500-$8,000 (depends on traffic patterns)
- **Storage**: $800-$1,500 (databases and analytics)
- **Network**: $200-$500 (data transfer and load balancing)
- **External Services**: $300-$800 (Maps API, SMS, email providers)
- **Total**: $3,800-$10,800 per month at full scale

## Summary

This Smart Parking System OAM definition provides a comprehensive, production-ready architecture that:

1. **Leverages existing OAM components** from the platform infrastructure
2. **Scales to handle 100,000+ sensors** with real-time data processing
3. **Provides sub-second response times** for parking availability queries
4. **Includes comprehensive monitoring and alerting** for operational excellence
5. **Implements security best practices** with encryption, RBAC, and audit logging
6. **Supports business requirements** with dynamic pricing, analytics, and user experience optimization

The architecture follows cloud-native principles with microservices, auto-scaling, circuit breakers, and comprehensive observability, enabling the system to achieve the business goals of 40% reduction in parking search time and 25% increase in lot utilization.