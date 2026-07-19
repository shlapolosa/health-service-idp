#!/usr/bin/env python3
"""Application-layer views, regenerated through the archimate-view engine (auto-layout, no hand
coordinates). Reuses the element catalogue (type+name) from gen_application_layer.py and re-declares
each view's membership + relationships; the engine ranks/orders/places/routes/verifies.

Output: application-layer.archimate.xml  (6 composed views).
"""
import sys
sys.path.insert(0, "/Users/socrateshlapolosa/.claude/skills/archimate-view")
from archi_layout import View, compose
import gen_application_layer as M   # provides EL (id->(type,name)), PLAT, SAH, DO

EL = M.EL
# Corrected terminology (per 18-eligibility-terminology-analysis.md): override/add element labels.
EXTRA = {
    "if_malapi": ("ApplicationInterface", "Malaffi Membership API"),
    "as_malmember": ("ApplicationService", "Membership Query (scoped)"),
    "ac_cms": ("ApplicationComponent", "Sahatna CMS"),
    "fn_hydrate": ("ApplicationFunction", "Hydrate Published Content"),
    "fn_enrolsub": ("ApplicationFunction", "Create Enrolment Subscription"),
}
def cat(i): return EXTRA.get(i) or EL[i]
SIZE = {"ApplicationEvent":(162,46),"BusinessEvent":(162,46),"ApplicationInterface":(140,44),
        "BusinessInterface":(140,44),"DataObject":(180,52),"BusinessObject":(180,52),
        "ApplicationService":(196,54),"BusinessService":(196,54)}
def sz(t): return SIZE.get(t,(192,58))

def build(vid, title, leaves, containers, edges):
    v = View(vid, title)
    allnodes = list(leaves)
    for kids in containers.values(): allnodes += kids        # container children are nodes too
    for i in allnodes:
        t,n = cat(i); w,h = sz(t); v.node(i,t,n,w=w,h=h)
    for cid,kids in containers.items():
        t,n = cat(cid); v.container(cid,t,n,kids)
    for (s,t,kind,acc) in edges:
        v.edge(s,t,f"{s}__{t}__{kind}",kind,acc)
    return v

# ---------------- VIEW: realization seam ----------------
seam_leaves=[]; seam_edges=[]
for ac,acn,sv,svn,fn in M.PLAT:
    seam_leaves += [fn,sv,ac]
    seam_edges += [(ac,sv,"Realization",None),(sv,fn,"Serving",None)]
seam_leaves += ["fn_concl","as_concl"]
seam_edges += [("ac_challenge","as_concl","Realization",None),("as_concl","fn_concl","Serving",None)]
seam = build("view-app-realization","Application → Business Realization Seam", seam_leaves, {}, seam_edges)

# ---------------- VIEW: earn & redeem ----------------
er = build("view-app-earn-redeem","Earn & Redeem",
    ["fn_p3","fn_p5","fn_p6","as_scoring","as_wallet","as_redeem",
     "ev_verified","fn_score","fn_rescred","ev_credited","act_member","ac_bff_rewards",
     "ac_provider","if_provapi","as_provredeem","ev_voucher",
     "do_telemetry","do_score","do_wallet","do_redemption","do_voucher"],
    {"col_redeem":["ia_redeem","fn_redorch","fn_fraudchk"]},
    [("as_scoring","fn_p3","Serving",None),("as_wallet","fn_p5","Serving",None),("as_redeem","fn_p6","Serving",None),
     ("ev_verified","fn_score","Triggering",None),("fn_score","fn_rescred","Triggering",None),("fn_rescred","ev_credited","Triggering",None),
     ("act_member","ac_bff_rewards","Serving",None),("ac_bff_rewards","as_redeem","Serving",None),("as_redeem","ia_redeem","Triggering",None),
     ("ia_redeem","fn_redorch","Triggering",None),("fn_redorch","fn_fraudchk","Triggering",None),("fn_redorch","as_provredeem","Triggering",None),
     ("as_provredeem","ev_voucher","Triggering",None),("ac_provider","if_provapi","Assignment",None),("ac_provider","as_provredeem","Realization",None),
     ("fn_score","do_telemetry","Access","Read"),("fn_score","do_score","Access","Write"),("fn_rescred","do_wallet","Access","Write"),
     ("fn_redorch","do_wallet","Access","Read"),("fn_redorch","do_redemption","Access","Write"),("fn_redorch","do_voucher","Access","Write")])

# ---------------- VIEW: partner lifecycle ----------------
pl = build("view-app-partner","Partner Lifecycle",
    ["fn_p7","as_partner","ac_partner","ac_provider","if_partnerportal",
     "fn_kyb","ev_partner_approved","fn_contract","ev_settlement","fn_offboard",
     "do_kyb","do_contract","do_catalogue","do_redemption","do_settlement"],
    {"col_settle":["ia_settle","fn_settle"]},
    [("ac_partner","as_partner","Realization",None),("as_partner","fn_p7","Serving",None),
     ("ac_partner","if_partnerportal","Assignment",None),("if_partnerportal","ac_provider","Serving",None),
     ("fn_kyb","ev_partner_approved","Triggering",None),("ev_partner_approved","fn_contract","Triggering",None),
     ("fn_contract","ia_settle","Triggering",None),("ia_settle","fn_settle","Triggering",None),
     ("fn_settle","ev_settlement","Triggering",None),("ev_settlement","fn_offboard","Triggering",None),
     ("fn_kyb","do_kyb","Access","Write"),("fn_contract","do_contract","Access","Write"),("fn_contract","do_catalogue","Access","Write"),
     ("fn_settle","do_redemption","Access","Read"),("fn_settle","do_settlement","Access","Write"),("fn_offboard","do_contract","Access","Read")])

# ---------------- VIEW: authoring · verification · conclusion ----------------
au = build("view-app-author","Authoring · Verification · Conclusion",
    ["fn_p2","as_challenge","fn_author","fn_bind","fn_publish","ev_chalpub",
     "fn_p4","as_verify","ev_actsynced","fn_verify","ev_verified",
     "fn_concl","as_concl","ev_periodend","fn_conclude","ev_concluded",
     "do_segment","do_challenge","do_telemetry","do_activity","do_score","do_standings"],
    {},
    [("as_challenge","fn_p2","Serving",None),("as_verify","fn_p4","Serving",None),("as_concl","fn_concl","Serving",None),
     # each detailed flow realizes its service -> the engine stacks fn(top)/service/flow/data per column
     ("fn_author","as_challenge","Realization",None),("fn_verify","as_verify","Realization",None),("fn_conclude","as_concl","Realization",None),
     ("fn_author","fn_bind","Triggering",None),("fn_bind","fn_publish","Triggering",None),("fn_publish","ev_chalpub","Triggering",None),
     ("ev_actsynced","fn_verify","Triggering",None),("fn_verify","ev_verified","Triggering",None),
     ("ev_periodend","fn_conclude","Triggering",None),("fn_conclude","ev_concluded","Triggering",None),
     ("fn_author","do_segment","Access","Read"),("fn_author","do_challenge","Access","Write"),("fn_bind","do_challenge","Access","Write"),
     ("fn_publish","do_challenge","Access","Read"),("fn_verify","do_telemetry","Access","Read"),("fn_verify","do_activity","Access","Write"),
     ("fn_conclude","do_score","Access","Read"),("fn_conclude","do_standings","Access","Write")])

# ---------------- VIEW: eligibility (engine-laid; corrected terminology per 18-...) ----------------
# Malaffi = the SCOPED Membership Query (relabelled via EXTRA). Platform returns challenge_ids; the
# Sahatna CMS (ac_cms ▸ Hydrate) hydrates to published content; enrolment creates a scoring subscription.
elig = build("view-app-eligibility","Eligibility Determination",
    ["fn_p9","act_member","as_elig","ev_login","if_pubapi","ev_elig","fn_enrolsub",
     "as_malmember","ac_malaffi","if_malapi",
     "do_challenge","do_eligresult","do_segment","do_demographic","do_telemetry","do_clinical"],
    {"ac_mobile":["fn_present"],"col_elig":["ia_elig","fn_elig","fn_localmem"],"ac_cms":["fn_hydrate"]},
    [("act_member","ev_login","Triggering",None),("ev_login","fn_present","Triggering",None),
     ("fn_present","if_pubapi","Triggering",None),("if_pubapi","ia_elig","Triggering",None),
     ("ia_elig","fn_elig","Triggering",None),("fn_elig","fn_localmem","Triggering",None),("fn_localmem","ev_elig","Triggering",None),
     ("ev_elig","fn_hydrate","Triggering",None),("fn_hydrate","fn_enrolsub","Triggering",None),
     ("as_elig","fn_p9","Serving",None),("ia_elig","as_elig","Realization",None),
     ("ac_malaffi","if_malapi","Assignment",None),("ac_malaffi","as_malmember","Realization",None),
     ("if_malapi","fn_elig","Serving",None),("as_malmember","fn_elig","Serving",None),
     ("fn_elig","do_challenge","Access","Read"),("fn_elig","do_eligresult","Access","Write"),("fn_elig","do_segment","Access","Read"),
     ("fn_localmem","do_segment","Access","Read"),("fn_localmem","do_demographic","Access","Read"),
     ("fn_localmem","do_telemetry","Access","Read"),("ac_malaffi","do_clinical","Access","Write")])

# ---------------- VIEW: cooperation (system boundaries) ----------------
coop_leaves = ["act_member"]
coop_leaves += [i for i,_ in M.SAH if i!="ac_mobile"]  # (mobile shown via Sahatna container below)
coop_leaves += ["if_appui","if_gwapi","if_pubapi","if_maladapter","if_provadapter","if_eventif","if_malapi","if_provapi"]
coop_leaves += ["ac_malaffi","ac_provider","as_malmember","as_malclin","as_provredeem"]
coop_leaves += list(M.DO.keys())
coop_containers = {"col_sahatna":[i for i,_ in M.SAH], "col_platform":[ac for ac,*_ in M.PLAT]}
coop_edges = []
for owner,iface in [("ac_mobile","if_appui"),("ac_gw","if_gwapi"),("ac_enrol","if_pubapi"),
                    ("ac_enrol","if_maladapter"),("ac_market","if_provadapter"),("ac_event","if_eventif"),
                    ("ac_malaffi","if_malapi"),("ac_provider","if_provapi")]:
    coop_edges.append((owner,iface,"Assignment",None))
coop_edges += [("ac_malaffi","as_malmember","Realization",None),("ac_malaffi","as_malclin","Realization",None),
               ("ac_provider","as_provredeem","Realization",None),("if_appui","act_member","Serving",None),
               ("if_malapi","if_maladapter","Serving",None),("if_provapi","if_provadapter","Serving",None)]
for b in ["ac_bff_member","ac_bff_chal","ac_bff_rewards"]: coop_edges.append(("if_pubapi",b,"Serving",None))
for s,d,a in M.CACC: coop_edges.append((s,d,"Access",a))
coop = build("view-app-cooperation","Application Cooperation", coop_leaves, coop_containers, coop_edges)

# ---------------- compose ----------------
views=[coop,elig,er,pl,au,seam]
xml = compose("id-wellness-applayer","Wellness Platform — Application Layer", views, strict=False)
path="/Users/socrateshlapolosa/Development/health-service-idp/factory/docs/analysis/wellness-archimate/application-layer.archimate.xml"
open(path,"w").write(xml)
for v in views: print(f"{v.vid:28s} rows={ {r:len(es) for r,es in sorted(v.rows.items())} }  violations={v.violations or 'none'}")
print("wrote",path)
