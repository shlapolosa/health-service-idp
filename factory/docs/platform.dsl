workspace "Internal Developer Platform" "Full-capability runtime view — 15 in-scope ComponentDefinitions + their bundled dependencies, all deployed" {

    # In scope: 10 application + 1 identity + 4 data CDs, PLUS the helper containers
    #   each capability bundles at runtime (Lenses, Metabase, MQTT, Svix, Zeebe, etc.).
    # Out of scope (excluded by request): mongodb, clickhouse, nats-jetstream,
    #   application-infrastructure, vcluster.

    model {
        dev   = person "Developer / API Consumer" "Submits OAM apps; calls exposed APIs."
        user  = person "End User" "Chats, opens GraphQL/UI, receives realtime streams."

        iot   = softwareSystem "IoT / Telemetry Source" "Pushes sensor data to ingest." "External,ZoneExternal"
        rcvr  = softwareSystem "External Webhook Receiver" "3rd-party HTTPS endpoint." "External,ZoneExternal"
        auth0 = softwareSystem "Auth0" "Hosted identity provider (OIDC/JWT)." "External,ZoneExternal"
        apim  = softwareSystem "Azure APIM" "API gateway - dual auth (JWT OR sub-key)." "External,ZoneExternal"
        akv   = softwareSystem "Azure Key Vault" "Secret store (Auth0 creds)." "External,ZoneData"

        idp = softwareSystem "Internal Developer Platform" "OAM/GitOps IDP on AKS." {

            group "Edge" {
                istio = container "Istio Ingress Gateway" "Single LB entrypoint (*.nip.io); mTLS mesh." "Istio 1.27" "ZoneEdge"
            }

            # ===== webservice =====
            group "webservice (app)" {
                wsApp   = container "webservice ksvc" "Onion-arch HTTP API; binds db/cache/identity; exposed via APIM." "Knative / python|node|go|java"
                wsShape = container "webservice-shape" "Shape-only ksvc primitive the webservice CD renders from." "Knative"
            }

            # ===== identity-service =====
            group "identity-service (app)" {
                idSvc = container "identity-service ksvc" "Domain IAM service; issues/validates tokens." "Knative / Spring Boot"
            }

            # ===== realtime-platform (+ realtime-service roles) =====
            group "realtime-platform (app + bundled deps)" {
                rtKafka   = container "Kafka broker" "Topics: sensor_raw, sensor_agg, ..." "Strimzi / Kafka"
                rtLensesHq = container "Lenses HQ" "Stream-SQL console + management UI." "Lenses CE 6.2"
                rtLensesAg = container "Lenses Agent" "Connects HQ to the Kafka cluster." "Lenses CE"
                rtMetabase = container "Metabase" "Analytics / dashboards over stream data." "Metabase"
                rtMqtt    = container "MQTT broker" "IoT ingest transport." "Mosquitto"
                rtPg      = container "Postgres (rt-meta)" "Lenses + Metabase metadata." "Postgres"
                rtIngest  = container "realtime-service: ingest" "HTTP /ingest → produces sensor_raw." "Knative / FastAPI"
                rtProc    = container "realtime-service: processor" "Consumes sensor_raw → aggregates → sensor_agg." "Knative / FastAPI"
                rtGateway = container "realtime-service: gateway" "Consumes sensor_agg → WebSocket /ws." "Knative / FastAPI"
            }

            # ===== webhook-platform (+ bridge) =====
            group "webhook-platform (app + bundled deps)" {
                whSvix   = container "Svix engine" "Outbound webhook delivery (HMAC sign, retry)." "svix-server v1.69"
                whPg     = container "Postgres (svix)" "Delivery metadata + logs." "Postgres"
                whRedis  = container "Redis (svix)" "Queue + retry backoff + cache." "Redis"
                whPortal = container "App Portal" "Externally-exposed self-service endpoint UI." "Istio VS" "ZoneExternal"
                whBridge = container "realtime-service: webhook bridge" "Consumes sensor_agg → POST Svix /msg." "Knative / FastAPI + realtime-transport"
            }

            # ===== graphql =====
            group "graphql (gateway + platform)" {
                gqlHive  = container "Hive Gateway" "Auto-federates sibling GraphQL subgraphs; JWT-enforced." "Knative / Hive"
                gqlRedis = container "graphql-platform Redis" "Gateway cache + config (ConfigMap)." "Helm / Redis"
                gqlSubA  = container "subgraph-a ksvc" "Federated GraphQL subgraph." "Knative"
                gqlSubB  = container "subgraph-b ksvc" "Federated GraphQL subgraph." "Knative"
            }

            # ===== camunda-orchestrator (Camunda 8) =====
            group "camunda-orchestrator (app + bundled deps)" {
                camZeebe  = container "Zeebe broker" "BPMN workflow engine." "Camunda 8 / Zeebe"
                camOperate = container "Operate" "Process monitoring UI." "Camunda 8"
                camTasklist = container "Tasklist" "Human task UI." "Camunda 8"
                camOptimize = container "Optimize" "Process analytics." "Camunda 8"
                camEs     = container "Elasticsearch" "Operate/Tasklist/Optimize datastore." "Elasticsearch"
                camWorker = container "zeebe-worker ksvc" "Job workers (handlers.py)." "Knative / FastAPI"
            }

            # ===== rasa-chatbot =====
            group "rasa-chatbot (app)" {
                rasaSrv  = container "Rasa server" "NLU + dialogue (prebaked model)." "Knative / Rasa"
                rasaAct  = container "Rasa actions" "Custom action server." "Knative / Rasa SDK"
            }

            # ===== identity binding =====
            group "Identity" {
                auth0Idp = container "auth0-idp" "ESO pulls Auth0 creds from Key Vault → <name>-conn for JWT verify." "ExternalSecret"
            }

            # ===== standalone data CDs (bindable backing stores) =====
            group "Data stores (standalone CDs)" {
                pg    = container "postgresql" "Relational DB (Crossplane Helm)." "Helm / Postgres" "ZoneData"
                neon  = container "neon-postgres" "Serverless Postgres (autoscale/branching)." "Neon API" "ZoneData"
                redis = container "redis" "Cache / queue." "Helm / Redis" "ZoneData"
                kafka = container "kafka" "Standalone event streaming." "Strimzi" "ZoneData"
            }

            # ===== platform plane =====
            group "Platform plane (shared)" {
                vela   = container "KubeVela" "Renders OAM → workloads + claims." "vela-core"
                xplane = container "Crossplane" "Reconciles backing-infra claims." "v2.3"
                argocd = container "ArgoCD" "GitOps sync per-service repos." "v3.4"
                knative = container "Knative Serving" "Scale-to-zero runtime." "v1.22"
            }
        }

        # ---------- People / edge ----------
        dev -> apim "Calls exposed APIs"
        dev -> idp  "Submits OAM apps (Slack / MCP / architect)"
        user -> istio "HTTP / WS / chat"
        iot -> rtMqtt "Telemetry (MQTT)" "Async"
        iot -> rtIngest "Telemetry (HTTP /ingest)"

        # ---------- Edge → apps ----------
        apim -> wsApp "expose-api route"
        apim -> gqlHive "federated GraphQL"
        istio -> rtIngest "/ingest"
        istio -> rtGateway "/ws"
        istio -> camOperate "Operate UI"
        istio -> camTasklist "Tasklist UI"
        istio -> rasaSrv "chat"
        istio -> idSvc "token endpoints"
        istio -> whPortal "self-service portal"

        # ---------- webservice bindings ----------
        wsApp -> pg "binds db"
        wsApp -> redis "binds cache"
        wsApp -> neon "binds (serverless pg alt)"
        wsApp -> auth0Idp "binds identity"
        wsApp -> wsShape "rendered from"
        wsApp -> auth0 "validates JWT"
        idSvc -> pg "user store"

        # ---------- realtime internals ----------
        rtIngest -> rtKafka "produce sensor_raw" "Async"
        rtKafka -> rtProc "consume sensor_raw" "Async"
        rtProc -> rtKafka "produce sensor_agg" "Async"
        rtKafka -> rtGateway "consume sensor_agg" "Async"
        rtGateway -> user "WebSocket stream" "Async"
        rtLensesAg -> rtKafka "manages"
        rtLensesHq -> rtLensesAg "controls"
        rtMetabase -> rtPg "queries"
        rtLensesHq -> rtPg "metadata"
        rtMqtt -> rtKafka "bridges to topics" "Async"

        # ---------- realtime → webhook cross-capability ----------
        rtKafka -> whBridge "consume sensor_agg" "Async"
        whBridge -> whSvix "POST /app/.../msg"
        whSvix -> whPg "store messages"
        whSvix -> whRedis "queue + retry" "Async"
        whSvix -> whPortal "serves"
        whSvix   -> rcvr "HMAC-signed delivery" "Async"
        rcvr -> whPortal "self-registers endpoint"

        # ---------- graphql ----------
        gqlHive -> gqlSubA "federates"
        gqlHive -> gqlSubB "federates"
        gqlHive -> gqlRedis "cache/config"
        gqlHive -> wsApp "can federate webservice subgraph"

        # ---------- camunda ----------
        camWorker -> camZeebe "activates jobs" "Async"
        camZeebe -> camEs "exports records" "Async"
        camOperate -> camEs "reads"
        camTasklist -> camEs "reads"
        camOptimize -> camEs "reads"

        # ---------- rasa ----------
        rasaSrv -> rasaAct "custom actions"

        # ---------- identity / secrets ----------
        auth0Idp -> akv "pulls Auth0 creds (ESO)"
        auth0Idp -> auth0 "tenant"

        # ---------- platform plane ----------
        vela -> xplane "emits claims"
        vela -> knative "renders ksvc"
        argocd -> knative "syncs workloads"
        xplane -> pg "provisions"
        xplane -> rtKafka "provisions"
    }

    views {
        systemContext idp "Context" {
            include *
            autolayout lr
        }

        container idp "AllContainers" {
            include *
            autolayout
        }

        styles {
            element "Person" {
                shape person
                background #08427b
                color #ffffff
            }
            element "External" {
                background #999999
                color #ffffff
            }
            element "Software System" {
                background #1168bd
                color #ffffff
            }
            element "Container" {
                background #438dd5
                color #ffffff
            }

            # ----- Trust-zone element styling (EXTERNAL=red, EDGE=orange, INTERNAL=green, DATA=blue) -----
            element "ZoneExternal" {
                background #c0392b
                color #ffffff
            }
            element "ZoneEdge" {
                background #e67e22
                color #ffffff
            }
            element "ZoneInternal" {
                background #27ae60
                color #ffffff
            }
            element "ZoneData" {
                background #2471a3
                color #ffffff
            }

            # ----- Sync vs Async relationship styling -----
            relationship "Relationship" {
                color #707070
                dashed false
            }
            relationship "Async" {
                color #8e44ad
                dashed true
            }
        }
    }
}
