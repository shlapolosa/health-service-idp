#!/usr/bin/env python3
"""Technology layer (Phase 5) — defined as ARCHITECTURE BUILDING BLOCKS (ABBs), technology-agnostic.

EA discipline (TOGAF): the architecture states WHAT technology capability is required (ABB), not the
product. Concrete products / OAM component types are SOLUTION BUILDING BLOCKS (SBBs) that REALIZE the
ABBs, and live in a separate solution view.

Two views (one model):
  1. Technology Architecture (ABB) — Application Components  ← realized/served by ← technology-agnostic
     ABBs (Workload Runtime, Event Streaming, Relational Persistence, Identity, ...).
  2. Solution Realization (SBB)     — ABB  ← realized by ←  SBB (the concrete products + OAM types).
"""
import sys
sys.path.insert(0, "/Users/socrateshlapolosa/.claude/skills/archimate-view")
from archi_layout import View, compose

APP="#B5FFFF"; ABB="#C9E7B8"; SBB="#DDF0CC"

# ---- ABBs (technology-agnostic building blocks) ----
ABBS = [
    ("abb_runtime","Container Workload Runtime"),
    ("abb_mesh","Service Mesh & API Gateway"),
    ("abb_stream","Event Streaming Platform"),
    ("abb_streamproc","Stream Processing & Feature Computation"),
    ("abb_oltp","Relational Persistence (OLTP)"),
    ("abb_olap","Analytical Data Store (OLAP)"),
    ("abb_push","Real-time Push Channel"),
    ("abb_iam","Identity & Access Management"),
    ("abb_federation","API Federation & Aggregation"),
    ("abb_secrets","Secrets Management"),
    ("abb_gitops","Declarative Provisioning (GitOps)"),
    ("abb_obs","Observability"),
]
# ---- SBBs (concrete realizations: products + OAM component types) ----
SBBS = [
    ("sbb_knative","Knative Serving  ·  OAM: webservice","abb_runtime"),
    ("sbb_istio","Istio + Azure APIM","abb_mesh"),
    ("sbb_kafka","Kafka + Lenses  ·  OAM: realtime-platform","abb_stream"),
    ("sbb_lenses","Lenses SQL processors  ·  OAM: analytics-platform","abb_streamproc"),
    ("sbb_neon","Neon PostgreSQL  ·  OAM: postgresql","abb_oltp"),
    ("sbb_snowflake","Snowflake + Kafka Connect  ·  OAM: analytics-platform","abb_olap"),
    ("sbb_ws","WebSocket Gateway  ·  OAM: realtime-service","abb_push"),
    ("sbb_auth0","Auth0  ·  OAM: auth0-idp","abb_iam"),
    ("sbb_hive","Hive Gateway  ·  OAM: graphql-gateway","abb_federation"),
    ("sbb_kv","Azure Key Vault + External Secrets","abb_secrets"),
    ("sbb_oam","KubeVela + Crossplane + ArgoCD  ·  OAM control plane","abb_gitops"),
    ("sbb_obs","Prometheus + Grafana + Jaeger","abb_obs"),
]
APPS = [("a_platform","Gamification Platform — 13 microservices"),("a_event","Event Hub"),
        ("a_analytics","Analytics & Reporting"),("a_consent","Consent & Identity"),
        ("a_bff","Sahatna BFFs"),("a_gateway","Member Gateway (/ws)"),("a_data","Platform Data Stores")]

# ===== View 1 — Technology Architecture (ABB) =====
v1 = View("view-tech-abb","Technology Architecture — Building Blocks (ABB)")
for i,n in APPS: v1.node(i,"ApplicationComponent",n,fill=APP)
for i,n in ABBS: v1.node(i,"TechnologyService",n,fill=ABB,w=230,h=56)
# ABB realizes the application component whose capability it supplies
for s,t in [("abb_runtime","a_platform"),("abb_stream","a_event"),("abb_olap","a_analytics"),
            ("abb_push","a_gateway"),("abb_iam","a_consent"),("abb_federation","a_bff"),("abb_oltp","a_data")]:
    v1.edge(s,t,f"{s}__{t}__R","Realization")
# cross-cutting ABBs serve the platform / analytics
for s,t in [("abb_mesh","a_platform"),("abb_secrets","a_platform"),("abb_gitops","a_platform"),
            ("abb_obs","a_platform"),("abb_streamproc","a_analytics")]:
    v1.edge(s,t,f"{s}__{t}__S","Serving")

# ===== View 2 — Solution Realization (SBB -> ABB) =====
v2 = View("view-tech-sbb","Solution Realization — SBB realizes ABB")
for i,n in ABBS: v2.node(i,"TechnologyService",n,fill=ABB,w=230,h=56)
for i,n,_ in SBBS: v2.node(i,"SystemSoftware",n,fill=SBB,w=240,h=54)
for i,n,abb in SBBS: v2.edge(i,abb,f"{i}__{abb}__R","Realization")

xml = compose("id-wellness-tech","Wellness Platform — Technology Layer", [v1,v2], strict=False)
path="/Users/socrateshlapolosa/Development/health-service-idp/factory/docs/analysis/wellness-archimate/technology-layer.archimate.xml"
open(path,"w").write(xml)
for v in (v1,v2): print(f"{v.vid:22s} rows={ {r:len(es) for r,es in sorted(v.rows.items())} } violations={v.violations or 'none'}")
print("wrote",path)
