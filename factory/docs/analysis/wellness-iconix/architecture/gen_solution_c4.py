"""drawio-c4 generator — Wellness Gamification layered solution architecture.

Top-down structure derived from the ICONIX robustness model (wellness-iconix/), placed into the
four system boundaries from LAYERING-SPEC.md: Sahatna Mobile → BFF → Gamification Platform → 3rd-party.
Event-first (async animated) by default; sync only where inherently synchronous. Edit the
ZONES/COMPONENTS/EDGES lists and re-run to regenerate.
"""
import sys
sys.path.insert(0, "/Users/socrateshlapolosa/.claude/skills/drawio-c4")
from drawio_c4 import C4Diagram

OUT = "/Users/socrateshlapolosa/Development/health-service-idp/factory/docs/analysis/wellness-iconix/architecture/solution-c4.drawio"

# (zid, label, stroke, comp_fill) — top -> down
ZONES = [
    ("z_mobile",   "Sahatna Mobile Application (Participant)",          "#D79B00", "#FFE6CC"),
    ("z_intnorth", "Integration North — APIM · UAE Pass",              "#3A7CA5", "#D7E8F2"),
    ("z_bff",      "BFF Layer (presentation-driving)",                  "#6C8EBF", "#DAE8FC"),
    ("z_intsouth", "Integration South — B2B · Entra ID + APIM",        "#3A7CA5", "#D7E8F2"),
    ("z_gpadmin",  "Gamification Platform — Admin Portal (DoH / ADHDS)","#2E6E8E", "#CCE5F5"),
    ("z_gpcore",   "Gamification Platform — Core Gameplay Services",    "#82B366", "#D5E8D4"),
    ("z_gpvalue",  "Gamification Platform — Engagement & Value Services","#82B366", "#D5E8D4"),
    ("z_gpevent",  "Gamification Platform — Event Backbone (async spine)","#9673A6","#E1D5E7"),
    ("z_gpdata",   "Gamification Platform — Datastores (database-per-service)","#D6B656","#FFF2CC"),
    ("z_partners", "3rd-Party Providers (external · API / ACL)",        "#B85450", "#F8CECC"),
]

# dotted system boundaries: (label, [zone ids], color)
SYSTEMS = [
    ("SAHATNA  ·  mobile client + BFF presentation tier (UAE Pass citizen identity)",
     ["z_mobile", "z_intnorth", "z_bff"], "#D79B00"),
    ("GAMIFICATION PLATFORM (GP)  ·  data + logic · admin portal · event-first spine · database-per-service",
     ["z_intsouth", "z_gpadmin", "z_gpcore", "z_gpvalue", "z_gpevent", "z_gpdata"], "#3A7CA5"),
]

# per-band security context (🔒 auto-prefixed)
SEC = {
    "z_intnorth": "UAE Pass OIDC · JWT mint · rate-limit",
    "z_bff":      "no authoritative data · session · composition",
    "z_intsouth": "B2B Entra OAuth2 (client-creds) · per-product APIM · mTLS",
    "z_gpadmin":  "workforce SSO (Entra) · no public ingress",
    "z_gpvalue":  "financial-grade points ledger · consent-gated notify",
    "z_gpdata":   "column-level KMS · Key Vault",
    "z_partners": "outside platform trust zone · ACL per provider",
}

# (cid, zid, title, desc)
COMPONENTS = [
    # --- Mobile (6 feature surfaces) ---
    ("m_disc","z_mobile","Discover & Enrol","discovery · details · enrol wizard · consent · wellness-data connect"),
    ("m_prog","z_mobile","Progress & Streaks","weekly progress · streak builder"),
    ("m_recog","z_mobile","Recognition & Share","badges · OS share · event detail · screening status"),
    ("m_lead","z_mobile","Leaderboard / Track","individual leaderboard (P1)"),
    ("m_wallet","z_mobile","Wallet & Marketplace","wallet · catalog · reward detail + redeem · my rewards"),
    ("m_set","z_mobile","Settings","notification settings · consent"),
    ("m_health","z_mobile","Health Connect SDK","on-device wearable/health telemetry (Apple Health / Google Fit) · streamed to platform"),
    ("m_survey","z_mobile","Surveys / Check-ins","fetch survey info · submit survey responses (streamed like telemetry)"),
    # --- Integration North ---
    ("apim_n","z_intnorth","Azure APIM — Citizen Gateway","JWT validation · rate-limit · routing · subscription keys"),
    ("uaepass","z_intnorth","UAE Pass IdP","citizen OIDC · national ID · mints platform JWT"),
    # --- BFF ---
    ("bff_game","z_bff","Mobile BFF (gameplay)","composition · session · fan-out to GP · localization shaping"),
    ("bff_render","z_bff","Content Renderer","renders localized (AR/EN) published challenge content"),
    ("bff_notify","z_bff","Sahatna Notifications API","Sahatna OWNS delivery + exposes notifications API (in-app feed) · push/email/in-app · consent-gated"),
    ("bff_wear","z_bff","Wearable Ingest Service","receives streamed Health Connect SDK telemetry from the app · relays through B2B to ingestion-svc"),
    ("bff_survey","z_bff","Sahatna Survey API","exposes survey info to the app · ingests streamed survey responses → relays through B2B to ingestion-svc"),
    # --- Integration South ---
    ("apim_s","z_intsouth","Azure APIM — Platform Gateway","service-to-service · per-OAM product · JWT · mTLS"),
    ("entra","z_intsouth","Microsoft Entra IdP","workforce + B2B service identity (OAuth2)"),
    # --- GP Admin Portal ---
    ("adm_auth","z_gpadmin","Authoring & Config Console","request · review · config · goal-set · winning-criteria · catalog · reward submission"),
    ("adm_gov","z_gpadmin","Governance Console","archive action · disenroll confirm (P1)"),
    ("adm_rpt","z_gpadmin","Reporting & Conclusion Console","dashboards · winners review · publish-conclusion · winner contact"),
    # --- GP Core services ---
    ("svc_chal","z_gpcore","challenge-svc","Challenge Authoring & Lifecycle · author→publish→conclude"),
    ("svc_elig","z_gpcore","eligibility-svc","Eligibility & Audience · segment resolve · Malaffi ACL"),
    ("svc_enr","z_gpcore","enrolment-svc","Enrolment & Membership · member-identity shared kernel"),
    ("svc_ing","z_gpcore","ingestion-svc","Activity Ingestion · verify · emit activity events"),
    ("svc_score","z_gpcore","scoring-svc","Scoring & Progression · daily/weekly · streaks · badges"),
    ("svc_lead","z_gpcore","leaderboard-svc","Leaderboard & Ranking · rank · tie-break · snapshots"),
    # --- GP Value services ---
    ("svc_recog","z_gpvalue","recognition-svc","Recognition & Engagement · awards · share cards · nudges/goals"),
    ("svc_rew","z_gpvalue","rewards-svc","Rewards, Wallet & Marketplace · ledger · reserve · issue voucher"),
    ("svc_set","z_gpvalue","settlement-svc","Settlement & Conclusion · winners · reward distribution"),
    ("svc_not","z_gpvalue","notification-svc","Notification · compose · consent-check (delivery via BFF)"),
    ("svc_rpt","z_gpvalue","reporting-svc","Reporting & Analytics · OLAP projections · dashboards"),
    # --- Event backbone ---
    ("eventlog","z_gpevent","domain-event-log","event-first spine · Goal-Met · Streak · Badge · Weekly-Finalized · Points-Credited · Voucher-Issued"),
    # --- GP Datastores (one per service; label lists actual stores) ---
    ("db_chal","z_gpdata","challenge-db","PostgreSQL · Challenge config + content metadata / asset URIs"),
    ("db_content","z_gpdata","challenge-content-store","object storage bucket · authored images · icons · localized (AR/EN) media"),
    ("db_elig","z_gpdata","eligibility-cache","Redis read-model · segment → challenge_ids"),
    ("db_mem","z_gpdata","membership-db","PostgreSQL · Enrollment + Member identity"),
    ("db_act","z_gpdata","activity-log","append-only / time-series · verified activity"),
    ("db_score","z_gpdata","scoring-db","PostgreSQL · WeeklyScore · Streak · Badge"),
    ("db_lead","z_gpdata","leaderboard cache+snapshots","Redis sorted-set + PostgreSQL snapshots"),
    ("db_recog","z_gpdata","recognition-db + sharecard-store","PostgreSQL + object storage"),
    ("db_rew","z_gpdata","points-ledger + marketplace-db + image-store","append-only ledger + PostgreSQL + object storage"),
    ("db_set","z_gpdata","settlement-db","PostgreSQL · winners · distribution"),
    ("db_not","z_gpdata","notification-db","PostgreSQL · consent · dispatch log"),
    ("db_rpt","z_gpdata","analytics-db","OLAP read-model / projection"),
    # --- 3rd-party providers ---
    ("ext_mal","z_partners","Malaffi / DoH-ADHDS","clinical segmentation · manual reward-image intake · winner-confirm gate"),
    ("ext_ifhas","z_partners","IFHAS Screening Module","screening events → bonus points"),
    ("ext_evt","z_partners","Sahatna Events","event sign-up / check-in bonus points"),
    ("ext_notp","z_partners","Notification Provider","push / email delivery (downstream of consent)"),
    ("ext_rew","z_partners","Reward Partners","voucher issue/redeem · partner reward + image submission"),
    ("ext_city","z_partners","Citymoov (P2)","quest completion points"),
]

# (source, target, kind)  kind = sync | async | xtrust | identity
EDGES = [
    # mobile -> north -> bff (sync, identity)
    ("m_disc","apim_n","sync"), ("m_prog","apim_n","sync"), ("m_recog","apim_n","sync"),
    ("m_lead","apim_n","sync"), ("m_wallet","apim_n","sync"), ("m_set","apim_n","sync"),
    ("uaepass","apim_n","identity"),
    ("apim_n","bff_game","sync"), ("apim_n","bff_render","sync"),
    # wearable telemetry: Health Connect SDK (mobile) streams frontend -> north APIM -> BFF Wearable Ingest
    ("m_health","apim_n","async"), ("apim_n","bff_wear","async"),
    # survey responses follow the SAME frontend-stream path; survey info served by Sahatna Survey API
    ("m_survey","apim_n","async"), ("apim_n","bff_survey","async"),
    # app reads notifications via the Sahatna Notifications API
    ("apim_n","bff_notify","sync"),
    # bff -> south -> GP (B2B). event-first but reads/commands sync
    ("bff_game","apim_s","sync"), ("entra","apim_s","identity"),
    ("apim_s","svc_chal","sync"), ("apim_s","svc_enr","sync"),
    # eligibility is INTERNAL (supporting read-model + Malaffi ACL): discovery via challenge-svc, snapshot via enrolment-svc
    ("svc_chal","svc_elig","sync"), ("svc_enr","svc_elig","sync"),
    ("apim_s","svc_score","sync"), ("apim_s","svc_lead","sync"), ("apim_s","svc_rew","sync"),
    ("bff_wear","apim_s","async"), ("apim_s","svc_ing","async"),
    ("bff_survey","apim_s","async"),  # survey responses relayed to ingestion-svc (same as wearables)
    # admin portal -> south -> GP (workforce Entra)
    ("adm_auth","apim_s","sync"), ("adm_gov","apim_s","sync"), ("adm_rpt","apim_s","sync"),
    # content/notify delivery path (Sahatna owns delivery)
    ("svc_not","bff_notify","async"), ("bff_notify","ext_notp","sync"),
    # event-first spine: services publish/subscribe (async, animated)
    ("svc_ing","eventlog","async"), ("svc_score","eventlog","async"), ("svc_chal","eventlog","async"),
    ("svc_rew","eventlog","async"), ("svc_recog","eventlog","async"), ("svc_set","eventlog","async"),
    ("eventlog","svc_score","async"), ("eventlog","svc_lead","async"), ("eventlog","svc_recog","async"),
    ("eventlog","svc_rew","async"), ("eventlog","svc_not","async"), ("eventlog","svc_rpt","async"),
    # authoring: content assets -> object bucket; author-time clinical-segment validate via eligibility -> Malaffi
    ("svc_chal","db_content","sync"),  # author-time listSegments also uses svc_chal->svc_elig (declared above)
    # service -> own datastore (sync)
    ("svc_chal","db_chal","sync"), ("svc_elig","db_elig","sync"), ("svc_enr","db_mem","sync"),
    ("svc_ing","db_act","sync"), ("svc_score","db_score","sync"), ("svc_lead","db_lead","sync"),
    ("svc_recog","db_recog","sync"), ("svc_rew","db_rew","sync"), ("svc_set","db_set","sync"),
    ("svc_not","db_not","sync"), ("svc_rpt","db_rpt","sync"),
    # GP -> 3rd-party via ACL (cross trust boundary)
    ("svc_elig","ext_mal","xtrust"), ("svc_set","ext_mal","xtrust"),
    ("svc_ing","ext_ifhas","xtrust"), ("svc_ing","ext_evt","xtrust"),
    ("svc_rew","ext_rew","xtrust"), ("svc_recog","ext_city","xtrust"),
]

d = C4Diagram("Wellness Gamification — Layered Solution Architecture (ICONIX-derived)", width=2200)
for zid, label, stroke, comp_fill in ZONES:
    d.zone(zid, label, stroke=stroke, comp_fill=comp_fill)
for label, zids, color in SYSTEMS:
    d.system(label, zids, color)
d.trust_boundary("CITIZEN IDENTITY SEAM  ·  Azure APIM + UAE Pass (OIDC)", "z_mobile")
d.trust_boundary("B2B INTEGRATION SEAM  ·  Microsoft Entra ID + Platform APIM  ·  event-first", "z_bff")
d.trust_boundary("PARTNER TRUST BOUNDARY  ·  API / ACL per provider  ·  mTLS / OAuth2", "z_gpdata")
for zid, text in SEC.items():
    d.security(zid, text)
for cid, zid, title, desc in COMPONENTS:
    d.component(cid, zid, title, desc)
for s, t, kind in EDGES:
    d.edge(s, t, kind)
d.legend([
    ("Synchronous (sync)",     "strokeColor=#1A1A1A;"),
    ("Async event (animated)", "strokeColor=#7A7A7A;dashed=1;dashPattern=6 4;"),
    ("Cross trust boundary / ACL", "strokeColor=#B85450;strokeWidth=2.4;"),
    ("Identity (UAE Pass / Entra)", "strokeColor=#9966AA;dashed=1;dashPattern=2 4;"),
])

xml = d.render(layout="banded", outline_bands=True, animate_async=True, strict=False)
open(OUT, "w").write(xml)
print("wrote:", OUT)
print("components:", len(COMPONENTS), "edges:", len(EDGES))
print("violations:", d.violations)
print("animated async edges:", getattr(d, "_animated_count", "?"))
