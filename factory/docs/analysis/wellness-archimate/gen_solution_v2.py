"""drawio-c4 generator — Wellness Platform solution architecture (v2 regenerate).

Re-derived model of solution-architecture-elk.drawio, re-routed through the
drawio-c4 banded engine (barycenter ordering + channel router). Edit the
ZONES/COMPONENTS/EDGES lists and re-run to regenerate.
"""
import sys
sys.path.insert(0, "/Users/socrateshlapolosa/.claude/skills/drawio-c4")
from drawio_c4 import C4Diagram

OUT = "/Users/socrateshlapolosa/Development/health-service-idp/factory/docs/analysis/wellness-archimate/solution-architecture-elk-v2.drawio"

# (zid, label, stroke, comp_fill)  — top -> down
ZONES = [
    ("z_client",    "Sahatna Client (citizen app)",              "#D79B00", "#FFE6CC"),
    ("z_intnorth",  "Integration North",                         "#3A7CA5", "#D7E8F2"),
    ("z_sahatna",   "Sahatna (server-side)",                     "#6C8EBF", "#DAE8FC"),
    ("z_platclient","Platform Client (admin / partner console)", "#2E6E8E", "#CCE5F5"),
    ("z_intsouth",  "Integration South",                         "#3A7CA5", "#D7E8F2"),
    ("z_engine",    "Gamification Engine",                       "#82B366", "#D5E8D4"),
    ("z_wallet",    "Wallet & Marketplace",                      "#9673A6", "#E1D5E7"),
    ("z_persist",   "Persistence",                               "#D6B656", "#FFF2CC"),
    ("z_partner",   "External Partner APIs",                     "#B85450", "#F8CECC"),
    ("z_platsvc",   "Platform Services",                         "#666666", "#EEEEEE"),
    ("z_crosscut",  "Cross-cutting",                             "#666666", "#F5F5F5"),
]

# dotted system boundaries: (label, [zone ids], color)
SYSTEMS = [
    ("SAHATNA (server-side)  ·  north gateway · BFF · renderer · notifications",
     ["z_intnorth", "z_sahatna"], "#D79B00"),
    ("GAMIFICATION PLATFORM  ·  admin console + Knative/Istio mesh · versioned event spine · financial-grade ledger",
     ["z_platclient", "z_intsouth", "z_engine", "z_wallet", "z_persist"], "#3A7CA5"),
    ("PLATFORM SHARED SERVICES  ·  identity · consent · fraud · analytics · GitOps · secrets",
     ["z_platsvc", "z_crosscut"], "#5A5A5A"),
]

# per-band security context (🔒 auto-prefixed)
SEC = {
    "z_intnorth":  "UAE Pass OIDC · JWT mint · rate-limit",
    "z_sahatna":   "JWT validation · idempotency relay",
    "z_platclient":"workforce SSO (Entra) · no public ingress",
    "z_intsouth":  "Entra OAuth2 (B2B client-creds) · mTLS · per-OAM product",
    "z_wallet":    "financial-grade · append-only · inline fraud",
    "z_persist":   "column-level KMS · Key Vault",
    "z_partner":   "outside platform trust zone",
    "z_platsvc":   "consent-gated · PDPL / ADHICS",
}

# (cid, zid, title, desc)
COMPONENTS = [
    ("c124","z_client","Challenges","active list · join · progress · clinical / demographic / telemetry mix"),
    ("c125","z_client","Rewards and Wallet","points balance · transactions · vouchers · re-display voucher (rate-limited)"),
    ("c126","z_client","Marketplace and Redeem","item detail · confirm redemption · Idempotency-Key (client UUIDv4)"),
    ("c127","z_client","Health Connect SDK","on-device wearable telemetry · steps · heart-rate · sleep · workouts"),
    ("c128","z_intnorth","Azure APIM - Citizen Gateway","JWT validation · rate-limit · routing · products · subscription keys"),
    ("c129","z_intnorth","UAE Pass IdP","citizen identity federation (OIDC) · national ID · mints platform JWT"),
    ("c130","z_sahatna","Gamification Service","gameplay BFF · JWT relay · session · fan-out: challenges · wallet · market"),
    ("c131","z_sahatna","Sahatna Renderer (thin)","renders localized published challenge content (Accept-Language) · content owned by Challenge svc (no CMS)"),
    ("c132","z_sahatna","Sahatna Notifications API","Sahatna OWNS delivery (push·email·SMS·in-app) · platform calls via APIM · consent-gated"),
    ("c133","z_sahatna","Wearable Service","ingest Health Connect SDK telemetry · writes telemetry to Event Hub"),
    ("c134","z_platclient","Admin / Partner Console","partner onboarding · item approval · reconciliation · no APIM ingress · connects to Platform APIM"),
    ("c135","z_intsouth","Azure APIM - Platform Gateway","service-to-service (sync) · JWT · policy · per-OAM product · mTLS"),
    ("c136","z_intsouth","Event Hub (EVENT-SVC)","async integration · Kafka + Lenses spine · schema registry · activity.* · wallet.* · voucher.*"),
    ("c137","z_intsouth","Microsoft Entra IdP","workforce / service identity (OAuth2) · B2B: Sahatna app-registration"),
    ("c138","z_engine","Enrolment and Eligibility","resolve eligible challenges · local-vs-Malaffi branch"),
    ("c139","z_engine","Malaffi Adapter","segment metadata (author, no membership) · scoped membership query (eligibility)"),
    ("c140","z_engine","Local Segmentation","demographic/telemetry segments (local) · clinical segments external (Malaffi)"),
    ("c141","z_engine","Verification","wearable / activity verify · emits activity.verified"),
    ("c142","z_engine","Challenge","authoring → publish → conclude · eligibility binding · owns localized content (AR/EN)"),
    ("c143","z_engine","Scoring and Recognition","daily/weekly scoring · titles · badges · streaks"),
    ("c144","z_engine","Engagement","nudges · goals · cohort plans"),
    ("c145","z_engine","Eligibility Resolver","membership → segments → map to challenge_ids · returns ids; Sahatna CMS hydrates"),
    ("c146","z_wallet","Wallet - Points Ledger","authoritative balance (versioned) · append-only · idempotent"),
    ("c147","z_wallet","Marketplace and Voucher","catalog · reserve · issue voucher · encrypted code/PIN"),
    ("c148","z_wallet","Fraud and Integrity","anomaly detection · velocity / duplicate checks"),
    ("c149","z_wallet","Partner Adapter Framework","routing · auth · idempotency overlay · YGG adapter · aggregator adapters"),
    ("c150","z_wallet","Redemption Orchestrator (saga)","reserve → fraud → dispatch partner → confirm/release · reserved · partner_pending"),
    ("c151","z_wallet","Partner and Settlement","contracting · reconciliation · DoH settlement (Phase 4)"),
    ("c152","z_persist","Wallet stores","WalletBalance · Transaction · Reservation (idempotency_key)"),
    ("c153","z_persist","Azure Key Vault","per-partner credentials · version-bumped rotation"),
    ("c154","z_persist","Marketplace stores","Item · Redemption · Voucher · (encrypted columns)"),
    ("c155","z_persist","Challenge and Cohort stores","Challenge · Localized Content (AR/EN) · Segment · Score · Eligibility Result"),
    ("c156","z_partner","Malaffi HIE","clinical membership / eligibility · black box · API only"),
    ("c157","z_partner","Reward Providers","YouGotaGift (eGift v2.4) · aggregators · voucher issue / redeem"),
    ("c158","z_partner","DoH ESB","sponsor · settlement (Phase 4) · IBAN payouts · VAT invoice"),
    ("c159","z_platsvc","CONS-SVC","consent purpose · voucher / data sharing · NOTIFY consent propagated from Sahatna"),
    ("c160","z_platsvc","NUDGE-SVC","compose notification request (no channels) · consent-checked → calls Sahatna"),
    ("c161","z_platsvc","FRAUD-SVC","anomaly detection · DLQ signals"),
    ("c162","z_platsvc","DATA-SVC","warehouse + analytics (OLAP) · settlement aggregation · dashboards"),
    ("c163","z_platsvc","ID-SVC","session and token exchange · member ↔ platform identity"),
    ("c164","z_crosscut","Secrets Management","Azure Key Vault + External Secrets · <comp>-conn injection"),
    ("c165","z_crosscut","Declarative Provisioning","KubeVela + Crossplane + ArgoCD · OAM control plane (GitOps)"),
    ("c166","z_crosscut","Observability","Prometheus · Grafana · Jaeger · Kiali"),
]

# (source, target, kind)  kind = sync | async | xtrust | identity
EDGES = [
    ("c124","c128","sync"), ("c125","c128","sync"), ("c126","c128","sync"),
    ("c128","c130","sync"), ("c128","c131","sync"), ("c130","c135","sync"),
    ("c134","c135","sync"), ("c135","c138","sync"), ("c135","c142","sync"),
    ("c135","c146","sync"), ("c135","c147","sync"), ("c138","c145","sync"),
    ("c145","c140","sync"), ("c130","c131","sync"), ("c147","c150","sync"),
    ("c150","c146","sync"), ("c150","c148","sync"), ("c146","c152","sync"),
    ("c147","c154","sync"), ("c142","c155","sync"),
    ("c139","c156","xtrust"), ("c149","c157","xtrust"), ("c151","c158","xtrust"),
    ("c141","c136","async"), ("c146","c136","async"), ("c147","c136","async"),
    ("c136","c161","async"), ("c136","c160","async"), ("c136","c162","async"),
    ("c136","c148","async"), ("c127","c128","async"), ("c128","c133","async"),
    ("c133","c136","async"), ("c136","c141","async"),
    ("c129","c128","identity"), ("c137","c135","identity"), ("c159","c138","identity"),
    ("c164","c153","identity"), ("c205_src_c160","c159","sync"),  # placeholder fixed below
    ("c160","c128","sync"), ("c128","c132","sync"), ("c135","c159","identity"),
    ("c160","c159","sync"),
]
EDGES = [e for e in EDGES if not e[0].startswith("c205_")]  # drop the placeholder

d = C4Diagram("Value Path — Wellness Platform Solution Architecture", width=1820)
for zid, label, stroke, comp_fill in ZONES:
    d.zone(zid, label, stroke=stroke, comp_fill=comp_fill)
for label, zids, color in SYSTEMS:
    d.system(label, zids, color)
d.trust_boundary("PARTNER TRUST BOUNDARY  ·  mTLS / OAuth2  ·  idempotent  ·  10s timeout · 3 retries  ·  uncertain → manual reconcile", "z_persist")
for zid, text in SEC.items():
    d.security(zid, text)
for cid, zid, title, desc in COMPONENTS:
    d.component(cid, zid, title, desc)
for s, t, kind in EDGES:
    d.edge(s, t, kind)
d.legend([
    ("Synchronous (sync)", "strokeColor=#1A1A1A;"),
    ("Async (animated)",   "strokeColor=#7A7A7A;dashed=1;dashPattern=6 4;"),
    ("Cross trust boundary","strokeColor=#B85450;strokeWidth=2.4;"),
    ("Identity",           "strokeColor=#9966AA;dashed=1;dashPattern=2 4;"),
])

xml = d.render(layout="banded", outline_bands=True, animate_async=True, strict=False)
open(OUT, "w").write(xml)
print("wrote:", OUT)
print("components:", len(COMPONENTS), "edges:", len(EDGES))
print("violations:", d.violations)
print("animated async edges:", getattr(d, "_animated_count", "?"))
