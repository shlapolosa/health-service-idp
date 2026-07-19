#!/usr/bin/env python3
"""
Business Process Cooperation — proper LAYERED business view (ArchiMate), left-to-right.
Business layer only. Two views in one model.

ArchiMate aspects & rules applied correctly:
  ACTIVE STRUCTURE   Business Roles/Actors — drawn SEPARATELY (not nesting processes). A role relates
                     to behaviour by ASSIGNMENT (performs), never composition.
  BEHAVIOUR          Business Service  = external behaviour offered to a consumer (realized by a
                     process; serves the consumer role).
                     Business Process  = internal, time-ordered flow. A phase is a COMPOSITE process
                     COMPOSED OF its step sub-processes; steps/phases chain by TRIGGERING.
                     (Business Functions = capability grouping of behaviour — kept in view 05.)
  PASSIVE STRUCTURE  Business Objects — bottom lane; processes ACCESS them.

Lanes (top->bottom, all left-to-right): Roles · Services · Processes · Objects.
Relationships: Assignment (role->process), Realization (process->service), Serving (service->consumer),
Composition (process->step), Triggering (flow), Access (step->object). Connectors angled, generous spacing.
"""
from xml.sax.saxutils import escape
NS="http://www.opengroup.org/xsd/archimate/3.0/"
BIZ="#FFFFB5"

EL={};
def el(i,t,n): EL[i]=(t,n); return i
RELS={}; ACC={}
def rel(s,t,ty):
    k=(s,t,ty)
    if k not in RELS: RELS[k]=f"rel-{len(RELS)+1}"
    return RELS[k]
def rela(s,t,acc):   # Access with direction (Read=input, Write=output)
    rid=rel(s,t,"Access"); ACC[rid]=acc; return rid

# shared
el("act_member","BusinessRole","Member / Citizen")
el("act_partner","BusinessRole","Partner (external)")
for i,n in [("obj_voucher","Voucher"),("obj_wallet","Sahatna Points (Wallet)"),("obj_catalogue","Reward Catalogue")]:
    el(i,"BusinessObject",n)

# --- Cross-organisation: three functions (actors) + three data types (owned objects) ---
el("act_sahatna","BusinessActor","Sahatna")
el("act_malaffi","BusinessActor","Malaffi (HIE)")
el("act_gplatform","BusinessActor","Gamification Platform")
el("obj_clinical","BusinessObject","Clinical Data  (diabetes, obesity, …)")
el("obj_demo","BusinessObject","Demographic Data  (gender, nationality, age, …)")
el("obj_telemetry","BusinessObject","Telemetry  (steps, sleep, nutrition, VO2, …)")
# services provided across the boundary
el("bsv_app","BusinessService","Member App Service")            # Sahatna -> Member (mobile UI)
el("bsv_demo","BusinessService","Demographic Data Service")     # Sahatna -> Platform
el("bsv_tele","BusinessService","Telemetry Streaming Service")  # Sahatna -> Platform
el("bsv_member","BusinessService","Membership Query Service")        # Malaffi -> Platform (per-user eligibility)
el("bsv_clin","BusinessService","Segment Metadata Service")    # Malaffi -> Platform (authoring; metadata, not membership)
# Sahatna (mobile app / channel + data source) functions
el("fn_s_app","BusinessFunction","Member Mobile Experience")
el("fn_s_demo","BusinessFunction","Demographics & Profile")
el("fn_s_tele","BusinessFunction","Telemetry Capture & Streaming")
# Malaffi (HIE) functions
el("fn_m_clin","BusinessFunction","Clinical Data Management")
el("fn_m_member","BusinessFunction","Membership Registry")
el("fn_m_cohort","BusinessFunction","Clinical Segment Build & Membership (Clinical Team)")
# Gamification Platform — FULL engine function set (the 12 capabilities + integration).
#   Everything except clinical data is managed here. Detailed in views 05 (capabilities) & 06 (processes).
PLAT_FN=[("fn_p1","Cohort Planning"),("fn_p2","Challenge Lifecycle Management"),
 ("fn_p3","Wellness Scoring & Recognition"),("fn_p4","Activity Verification"),
 ("fn_p5","Reward Points & Wallet"),("fn_p6","Marketplace & Redemption"),
 ("fn_p7","Partner Lifecycle & Settlement"),("fn_p8","Engagement & Nudging"),
 ("fn_p9","Eligibility Evaluation"),("fn_p10","Consent & Identity"),
 ("fn_p11","Fraud & Integrity"),("fn_p12","Analytics & Insight"),
 ("fn_p13","Integration & Interoperability")]
for i,n in PLAT_FN: el(i,"BusinessFunction",n)
el("fn_concl","BusinessFunction","Programme Conclusion")
# trigger events (business events) for the detailed platform flow
for i,n in [("e_start","Nightly cohort run (timer)"),("e_seg","segment.published"),
  ("e_chal","challenge.published"),("e_inelig","Ineligible (end)"),("e_verified","activity.verified"),
  ("e_week","Week close (timer)"),("e_points","points.credited"),("e_voucher","voucher.issued"),
  ("e_pend","Challenge period ended (timer)"),("e_concl","challenge.concluded (end)")]:
    el(i,"BusinessEvent",n)
# intermediate data objects (inputs/outputs along the flow)
for i,n in [("obj_features","Feature Set"),("obj_cohort","Cohort Definition"),
  ("obj_dailyscore","Daily Score"),("obj_standings","Final Standings")]:
    el(i,"BusinessObject",n)

# ===================== VIEW 1 — MEMBER JOURNEY =====================
for i,n in [("r_analytics","Analytics & Data Team"),("r_admin","Programme Administration"),
            ("r_doh","Department of Health"),("r_cms","CMS Author"),("r_verify","Verification Authority")]:
    el(i,"BusinessRole",n)
MJ={
 "c_cohort":("Cohort Identification",["s_cf","s_dc","s_ps"]),
 "c_create":("Challenge Creation",["s_ac","s_be","s_ap","s_pf"]),
 "c_enrol":("Enrolment",["s_en","s_ee","s_tc","s_cn"]),
 "c_earn":("Earning Loop",["s_ca","s_va","s_sg","s_ar","s_aw","s_cp"]),
 "c_reward":("Rewards & Redemption",["s_br","s_rs","s_rd","s_rv"]),
 "c_conclude":("Conclusion",["s_cc","s_hw"]),
}
MJS={"s_cf":"Define Features (DoH)","s_dc":"Build Segment","s_ps":"Publish Segment",
 "s_ac":"Author Challenge","s_be":"Bind challenge_id to segment_id","s_ap":"Author Presentation","s_pf":"Publish & Present",
 "s_en":"Enrol","s_ee":"Evaluate Eligibility (return challenge_ids; CMS hydrates)","s_tc":"Accept T&C","s_cn":"Create Enrolment Subscription",
 "s_ca":"Capture Activity","s_va":"Verify Activity","s_sg":"Score Daily Goals","s_ar":"Apply Recognition",
 "s_aw":"Aggregate Weekly Score","s_cp":"Credit Sahatna Points",
 "s_br":"Browse Rewards","s_rs":"Reserve Points","s_rd":"Redeem with Partner","s_rv":"Receive Voucher",
 "s_cc":"Conclude Challenge","s_hw":"Hand Winners & Prizes"}
for c,(nm,st) in MJ.items(): el(c,"BusinessProcess",nm)
for s,nm in MJS.items(): el(s,"BusinessProcess",nm)
# business services (external) — one per phase, with consumer
MJSVC={"c_cohort":("bsv_cohort","Segment Build Service (local + clinical)","r_admin"),
 "c_create":("bsv_create","Challenge Authoring Service","r_admin"),
 "c_enrol":("bsv_enrol","Enrolment Service","act_member"),
 "c_earn":("bsv_score","Wellness Scoring Service","act_member"),
 "c_reward":("bsv_redeem","Reward Redemption Service","act_member"),
 "c_conclude":("bsv_concl","Programme Conclusion Service","r_doh")}
for c,(sid,nm,cons) in MJSVC.items(): el(sid,"BusinessService",nm)
for i,n in [("obj_segment","Segment (versioned)"),("obj_challenge","Challenge Contract"),
            ("obj_plan","ScoringPlan"),("obj_enrol","Enrolment"),("obj_activity","Verified Activity"),
            ("obj_score","Weekly Score"),("obj_title","Title / Badge")]:
    el(i,"BusinessObject",n)
member={"vid":"view-member-journey","title":"Member Journey — Cohort to Reward",
 "owners":[("r_analytics",["c_cohort"]),("r_admin",["c_create"]),
           ("act_member",["c_enrol","c_earn","c_reward"]),("r_doh",["c_conclude"])],
 "supporting":[("r_cms","s_ap"),("r_verify","s_va")],
 "comp":MJ,"services":MJSVC,
 "flow":[("s_cf","s_dc"),("s_dc","s_ps"),("s_ps","s_ac"),("s_ac","s_be"),("s_be","s_ap"),("s_ap","s_pf"),
   ("s_pf","s_en"),("s_en","s_ee"),("s_ee","s_tc"),("s_tc","s_cn"),("s_cn","s_ca"),("s_ca","s_va"),
   ("s_va","s_sg"),("s_sg","s_ar"),("s_ar","s_aw"),("s_aw","s_cp"),("s_cp","s_br"),("s_br","s_rs"),
   ("s_rs","s_rd"),("s_rd","s_rv"),("s_rv","s_cc"),("s_cc","s_hw")],
 "objects":["obj_demo","obj_telemetry","obj_clinical","obj_segment","obj_challenge","obj_plan",
            "obj_enrol","obj_activity","obj_score","obj_wallet","obj_catalogue","obj_voucher","obj_title"],
 "access":[("s_cf","obj_demo"),("s_cf","obj_telemetry"),("s_dc","obj_clinical"),("s_ps","obj_segment"),
   ("s_be","obj_challenge"),("s_ac","obj_challenge"),("s_ee","obj_challenge"),
   ("s_cn","obj_enrol"),("s_va","obj_activity"),("s_va","obj_telemetry"),("s_sg","obj_plan"),("s_sg","obj_score"),
   ("s_ar","obj_title"),("s_cp","obj_wallet"),("s_br","obj_catalogue"),("s_rs","obj_wallet"),
   ("s_rd","obj_catalogue"),("s_rv","obj_voucher")]}

# ===================== VIEW 2 — PARTNER LIFECYCLE =====================
for i,n in [("r_ponb","Partner Onboarding (Admin)"),("r_market","Marketplace Operations"),
            ("r_redeem","Redemption Ops"),("r_fin","Finance & Settlement"),("r_pexit","Partner Exit (Admin)"),
            ("r_wallet","Wallet / Finance"),("r_fraud","Fraud & Compliance")]:
    el(i,"BusinessRole",n)
PL={"c_onb":("Onboarding & KYB",["p_sub","p_kyb","p_apr"]),
 "c_cat":("Contracting & Catalogue",["p_prov","p_push","p_val","p_idx","p_rel"]),
 "c_red":("Member Redemption",["p_brw","p_res","p_api","p_cmt","p_ntf"]),
 "c_set":("Settlement",["p_agg","p_rec","p_inv","p_pay","p_hld"]),
 "c_off":("Offboarding & Exit",["p_dec","p_wrn","p_rev","p_wnd","p_fin","p_ret"])}
PLS={"p_sub":"Submit Application","p_kyb":"KYB Due Diligence","p_apr":"Approval Decision",
 "p_prov":"Provision Sandbox Creds","p_push":"Push Catalogue","p_val":"Validate Items","p_idx":"Index Catalogue","p_rel":"Release Prod Creds",
 "p_brw":"Browse & Select","p_res":"Reserve Points (5-min)","p_api":"Call Partner API (10s)","p_cmt":"Commit Debit & Voucher","p_ntf":"Notify Member",
 "p_agg":"Aggregate Redemptions","p_rec":"Reconcile Ledger","p_inv":"Generate VAT Invoice","p_pay":"Route Payment","p_hld":"Release 5% Holdback",
 "p_dec":"Offboarding Decision","p_wrn":"Issue 30-day Warning","p_rev":"Revoke & Depublish","p_wnd":"90-day Wind-down","p_fin":"Final Settlement","p_ret":"Retain Data / Mask PII"}
for c,(nm,st) in PL.items(): el(c,"BusinessProcess",nm)
for s,nm in PLS.items(): el(s,"BusinessProcess",nm)
PLSVC={"c_onb":("bsv_onb","Partner Onboarding Service","act_partner"),
 "c_cat":("bsv_cat","Catalogue Management Service","act_partner"),
 "c_red":("bsv_fulfil","Redemption Fulfilment Service","act_member"),
 "c_set":("bsv_settle","Settlement Service","act_partner"),
 "c_off":("bsv_off","Offboarding Service","act_partner")}
for c,(sid,nm,cons) in PLSVC.items(): el(sid,"BusinessService",nm)
for i,n in [("obj_kyb","KYB / Application Record"),("obj_contract","Partner Contract"),
            ("obj_reservation","Point Reservation"),("obj_redemption","Redemption"),
            ("obj_settlement","Settlement / VAT Invoice")]:
    el(i,"BusinessObject",n)
partner={"vid":"view-partner-lifecycle","title":"Partner Lifecycle",
 "owners":[("r_ponb",["c_onb"]),("r_market",["c_cat"]),("r_redeem",["c_red"]),("r_fin",["c_set"]),("r_pexit",["c_off"])],
 "supporting":[("act_partner","p_sub"),("act_partner","p_push"),("act_member","p_brw"),
   ("r_wallet","p_res"),("r_wallet","p_cmt"),("r_fraud","p_api")],
 "comp":PL,"services":PLSVC,
 "flow":[("p_sub","p_kyb"),("p_kyb","p_apr"),("p_apr","p_prov"),("p_prov","p_push"),("p_push","p_val"),
   ("p_val","p_idx"),("p_idx","p_rel"),("p_rel","p_brw"),("p_brw","p_res"),("p_res","p_api"),("p_api","p_cmt"),
   ("p_cmt","p_ntf"),("p_ntf","p_agg"),("p_agg","p_rec"),("p_rec","p_inv"),("p_inv","p_pay"),("p_pay","p_hld"),
   ("p_hld","p_dec"),("p_dec","p_wrn"),("p_wrn","p_rev"),("p_rev","p_wnd"),("p_wnd","p_fin"),("p_fin","p_ret")],
 "objects":["obj_kyb","obj_contract","obj_catalogue","obj_reservation","obj_redemption","obj_voucher","obj_settlement"],
 "access":[("p_kyb","obj_kyb"),("p_prov","obj_contract"),("p_rel","obj_contract"),("p_push","obj_catalogue"),
   ("p_idx","obj_catalogue"),("p_res","obj_reservation"),("p_cmt","obj_redemption"),("p_cmt","obj_voucher"),
   ("p_agg","obj_redemption"),("p_rec","obj_redemption"),("p_inv","obj_settlement")]}

# ----------------------------- layout (generous) -----------------------------
STEP_W,STEP_H=152,56
STEP_GX=86
CPAD,CHDR,VPAD=34,30,30
COMP_GX=110
LANE_GAP=104
ROLE_W,ROLE_H=176,50
SVC_W,SVC_H=186,50
OBJ_W,OBJ_H=176,52; OBJ_GX=48
TOP=24; LEFTM=18
def rgb(h): return (int(h[1:3],16),int(h[3:5],16),int(h[5:7],16))

def render(spec):
    comp=spec["comp"]; svc=spec["services"]
    def cw(cid): n=len(comp[cid][1]); return n*STEP_W+(n-1)*STEP_GX+2*CPAD
    comp_h=CHDR+STEP_H+2*VPAD
    # composite x positions in flow order
    order=[c for _,cs in spec["owners"] for c in cs]
    cx={}; x=LEFTM+12
    for cid in order: cx[cid]=x; x+=cw(cid)+COMP_GX
    canvas_w=x+12
    y_role=TOP
    y_sup=y_role+ROLE_H+16
    y_svc=y_sup+ROLE_H+LANE_GAP
    y_proc=y_svc+SVC_H+LANE_GAP
    y_obj=y_proc+comp_h+LANE_GAP
    pos={}
    # steps — vertically centred in the composite body (below the label)
    for cid in order:
        sx=cx[cid]+CPAD; sy=y_proc+CHDR+VPAD
        for k,sid in enumerate(comp[cid][1]): pos[sid]=(sx+k*(STEP_W+STEP_GX), sy)
    # services centered over composite
    for cid in order:
        sid=svc[cid][0]; pos[sid]=(cx[cid]+cw(cid)//2-SVC_W//2, y_svc)
    # owner roles centered over their composites' span
    for aid,cs in spec["owners"]:
        lo=cx[cs[0]]; hi=cx[cs[-1]]+cw(cs[-1]); pos[aid]=((lo+hi)//2-ROLE_W//2, y_role)
    # supporting actors centered over their target step
    for aid,step in spec["supporting"]:
        tx,_=pos[step]; pos[aid]=(tx+STEP_W//2-ROLE_W//2, y_sup)
    # objects spread along bottom
    for k,oid in enumerate(spec["objects"]): pos[oid]=(LEFTM+12+k*(OBJ_W+OBJ_GX), y_obj)
    canvas_w=max(canvas_w, LEFTM+12+len(spec["objects"])*(OBJ_W+OBJ_GX))+12
    canvas_h=y_obj+OBJ_H+30

    out=[f'<view identifier="{spec["vid"]}" xsi:type="Diagram"><name xml:lang="en">{escape(spec["title"])}</name>']
    nid={}
    def enode(i,x,y,w,h,fs=8):
        n=f'n-{spec["vid"]}-{i}'; nid[i]=n; r,g,b=rgb(BIZ)
        return (f'<node identifier="{n}" elementRef="{i}" xsi:type="Element" x="{x}" y="{y}" w="{w}" h="{h}">'
                f'<style><fillColor r="{r}" g="{g}" b="{b}"/><lineColor r="120" g="120" b="120"/>'
                f'<font name="Sans" size="{fs}"><color r="0" g="0" b="0"/></font></style></node>')
    def lane(gid,label,y,h):
        out.append(f'<node identifier="{gid}" xsi:type="Container" x="{LEFTM}" y="{y}" w="{canvas_w-LEFTM-6}" h="{h}">')
        out.append(f'<label xml:lang="en">{escape(label)}</label>')
        out.append('<style><fillColor r="250" g="250" b="250" a="0"/><lineColor r="175" g="175" b="175"/>'
                   '<font name="Sans" size="9"><color r="95" g="95" b="95"/></font></style>')
    # lane backgrounds with aspect labels
    lane(f'g-{spec["vid"]}-role',"Business Roles / Actors  ·  ACTIVE STRUCTURE",y_role-16,(y_sup+ROLE_H)-(y_role-16)+16)
    out.append('</node>')
    lane(f'g-{spec["vid"]}-svc',"Business Services  ·  BEHAVIOUR (external)",y_svc-18,SVC_H+36); out.append('</node>')
    lane(f'g-{spec["vid"]}-proc',"Business Processes  ·  BEHAVIOUR (internal flow, composite -> steps)",y_proc-18,comp_h+36); out.append('</node>')
    lane(f'g-{spec["vid"]}-obj',"Business Objects  ·  PASSIVE STRUCTURE",y_obj-18,OBJ_H+36); out.append('</node>')
    # roles
    for aid,cs in spec["owners"]:
        x,y=pos[aid]; out.append(enode(aid,x,y,ROLE_W,ROLE_H,9))
        for c in cs: rel(aid,c,"Assignment")
    for aid,step in spec["supporting"]:
        x,y=pos[aid]; out.append(enode(aid,x,y,ROLE_W,ROLE_H))
        rel(aid,step,"Assignment")
    # services
    for cid in order:
        sid,nm,cons=svc[cid]; x,y=pos[sid]; out.append(enode(sid,x,y,SVC_W,SVC_H,9))
        rel(cid,sid,"Realization"); rel(sid,cons,"Serving")
    # composite processes (composed of steps)
    for cid in order:
        out.append(f'<node identifier="g-{spec["vid"]}-{cid}" elementRef="{cid}" xsi:type="Element" x="{cx[cid]}" y="{y_proc}" w="{cw(cid)}" h="{comp_h}">')
        r,g,b=rgb(BIZ)
        out.append(f'<style><fillColor r="{r}" g="{g}" b="{b}"/><lineColor r="120" g="120" b="120"/>'
                   f'<font name="Sans" size="9"><color r="0" g="0" b="0"/></font></style>')
        nid[cid]=f'g-{spec["vid"]}-{cid}'
        for sid in comp[cid][1]:
            x,y=pos[sid]; out.append(enode(sid,x,y,STEP_W,STEP_H))
            rel(cid,sid,"Composition")
        out.append('</node>')
    # objects
    for oid in spec["objects"]: x,y=pos[oid]; out.append(enode(oid,x,y,OBJ_W,OBJ_H))
    # connections — staggered channels in the lane gaps (composition shown by nesting, not drawn)
    def W(i):
        if i in comp: return cw(i)
        t=EL[i][0]
        return SVC_W if t=="BusinessService" else OBJ_W if t=="BusinessObject" else ROLE_W if t in("BusinessRole","BusinessActor") else STEP_W
    def Hh(i):
        if i in comp: return comp_h
        t=EL[i][0]
        return SVC_H if t=="BusinessService" else OBJ_H if t=="BusinessObject" else ROLE_H if t in("BusinessRole","BusinessActor") else STEP_H
    def ctr(i):
        x,y=pos[i] if i in pos else (cx[i],y_proc); return x+W(i)//2, y+Hh(i)//2
    def emit(s,t,rid,ch=None):
        scx,scy=ctr(s); tcx,tcy=ctr(t)
        c=f'<connection identifier="c-{spec["vid"]}-{rid}-{s}-{t}" relationshipRef="{rid}" source="{nid[s]}" target="{nid[t]}" xsi:type="Relationship"'
        if ch is None:
            out.append(c+('/>' if (abs(scx-tcx)<6 or abs(scy-tcy)<6) else f'><bendpoint x="{scx}" y="{(scy+tcy)//2}"/><bendpoint x="{tcx}" y="{(scy+tcy)//2}"/></connection>'))
        else: out.append(c+f'><bendpoint x="{scx}" y="{ch}"/><bendpoint x="{tcx}" y="{ch}"/></connection>')
    def routed(conns, top, bot):
        cs=sorted(conns,key=lambda z:ctr(z[0])[0]); n=len(cs)
        for i,(s,t,ty) in enumerate(cs): emit(s,t,rel(s,t,ty), int(top+(i+1)*(bot-top)/(n+1)))
    for s,t in spec["flow"]: emit(s,t,rel(s,t,"Triggering"))                       # triggers direct
    up=[(a,c,"Assignment") for a,cs in spec["owners"] for c in cs]
    up+=[(a,st,"Assignment") for a,st in spec["supporting"]]
    up+=[(cid,svc[cid][0],"Realization") for cid in order]
    routed(up, y_svc+SVC_H+18, y_proc-18)                                          # assignment + realization
    routed([(svc[cid][0],svc[cid][2],"Serving") for cid in order], y_sup+ROLE_H+18, y_svc-18)  # serving
    routed([(s,o,"Access") for s,o in spec["access"]], y_proc+comp_h+18, y_obj-18) # access
    out.append('</view>')
    return "\n".join(out)

def render_data_view():
    """Cross-organisation cooperation (COMPLEMENTS views 05/06, does not replace):
       Member ── uses ── Sahatna (mobile app + data source) ── data/serves ── Gamification Platform
       (the engine: ALL challenge/gamification management) ── queries ── Malaffi (HIE: clinical)."""
    vid="view-data-cooperation"
    NW,NH,ng=300,56,28
    # container contents (top-to-bottom). Functions then the services that org provides.
    sah=["fn_s_app","fn_s_demo","fn_s_tele","bsv_app","bsv_demo","bsv_tele"]
    plat=["bsv_enrol","bsv_score","bsv_redeem"]+[i for i,_ in PLAT_FN]   # member-facing services + 13 functions
    mal=["fn_m_clin","fn_m_member","fn_m_cohort","bsv_member","bsv_clin"]
    AW=NW+100; AHDR=46; APADB=26; AG=170; x0=270; ytop=70   # wider container, bigger header + bottom pad
    cols={"act_sahatna":(x0,sah),"act_gplatform":(x0+AW+AG,plat),"act_malaffi":(x0+2*(AW+AG),mal)}
    pos={}; cont_h={}
    for a,(ax,items) in cols.items():
        for k,ch in enumerate(items): pos[ch]=(ax+(AW-NW)//2, ytop+AHDR+k*(NH+ng))   # centre horizontally
        cont_h[a]=AHDR+len(items)*(NH+ng)+APADB
    # member actor (the user) standalone top-left
    pos["act_member"]=(30, ytop+AHDR)
    # data objects bottom lane (owned by streaming/exchange orgs)
    oy=ytop+max(cont_h.values())+70
    pos["obj_demo"]=(cols["act_sahatna"][0]+20, oy)
    pos["obj_telemetry"]=(cols["act_sahatna"][0]+20, oy+NH+12)
    pos["obj_clinical"]=(cols["act_malaffi"][0]+20, oy)
    canvas_w=cols["act_malaffi"][0]+AW+30; canvas_h=oy+2*(NH+12)+40
    out=[f'<view identifier="{vid}" xsi:type="Diagram"><name xml:lang="en">Cross-Organisation Cooperation — Sahatna · Platform · Malaffi</name>']
    nid={}
    def en(i,x,y,w,h,fs=8):
        n=f'n-{vid}-{i}'; nid[i]=n; r,g,b=rgb(BIZ)
        return (f'<node identifier="{n}" elementRef="{i}" xsi:type="Element" x="{x}" y="{y}" w="{w}" h="{h}">'
                f'<style><fillColor r="{r}" g="{g}" b="{b}"/><lineColor r="120" g="120" b="120"/>'
                f'<font name="Sans" size="{fs}"><color r="0" g="0" b="0"/></font></style></node>')
    # member actor
    out.append(en("act_member",*pos["act_member"],190,NH+8,9))
    # actor containers, functions/services nested (Assignment by containment)
    for a,(ax,items) in cols.items():
        r,g,b=rgb(BIZ)
        out.append(f'<node identifier="n-{vid}-{a}" elementRef="{a}" xsi:type="Element" x="{ax}" y="{ytop}" w="{AW}" h="{cont_h[a]}">')
        out.append(f'<style><fillColor r="{r}" g="{g}" b="{b}"/><lineColor r="120" g="120" b="120"/><font name="Sans" size="11"><color r="0" g="0" b="0"/></font></style>')
        nid[a]=f'n-{vid}-{a}'
        for ch in items: x,y=pos[ch]; out.append(en(ch,x,y,NW,NH,8))
        out.append('</node>')
    # data lane
    out.append(f'<node identifier="n-{vid}-objlane" xsi:type="Container" x="20" y="{oy-26}" w="{canvas_w-40}" h="{2*(NH+12)+48}">')
    out.append('<label xml:lang="en">Data (passive structure) — owned by its source organisation</label>')
    out.append('<style><fillColor r="250" g="250" b="250" a="0"/><lineColor r="175" g="175" b="175"/><font name="Sans" size="9"><color r="95" g="95" b="95"/></font></style>')
    for o in ["obj_demo","obj_telemetry","obj_clinical"]: x,y=pos[o]; out.append(en(o,x,y,210,NH))
    out.append('</node>')
    # relationships
    R=[("act_member","",""),  # placeholder removed below
       # assignment: actor performs its functions
      ]
    R=[]
    for f in ["fn_s_app","fn_s_demo","fn_s_tele"]: R.append(("act_sahatna",f,"Assignment"))
    for i,_ in PLAT_FN: R.append(("act_gplatform",i,"Assignment"))
    for f in ["fn_m_clin","fn_m_member","fn_m_cohort"]: R.append(("act_malaffi",f,"Assignment"))
    # realization: function realizes the service it offers
    R+=[("fn_s_app","bsv_app","Realization"),("fn_s_demo","bsv_demo","Realization"),("fn_s_tele","bsv_tele","Realization"),
        ("fn_m_member","bsv_member","Realization"),("fn_m_cohort","bsv_clin","Realization"),
        ("fn_p2","bsv_enrol","Realization"),("fn_p3","bsv_score","Realization"),("fn_p6","bsv_redeem","Realization")]
    # serving — the channel + data + clinical cooperation
    R+=[("bsv_app","act_member","Serving"),                       # Sahatna app serves the Member
        ("bsv_enrol","fn_s_app","Serving"),("bsv_score","fn_s_app","Serving"),("bsv_redeem","fn_s_app","Serving"),  # platform services surfaced through the app
        ("bsv_demo","fn_p1","Serving"),("bsv_tele","fn_p1","Serving"),("bsv_clin","fn_p1","Serving"),  # data + clinical cohorts feed Cohort Planning
        ("bsv_tele","fn_p3","Serving"),("bsv_tele","fn_p4","Serving"),       # telemetry feeds scoring + verification
        ("bsv_member","fn_p9","Serving")]                         # platform Eligibility queries Malaffi membership
    # access — ownership (owner writes) + platform reads
    R+=[("fn_s_demo","obj_demo","Access"),("fn_s_tele","obj_telemetry","Access"),("fn_m_clin","obj_clinical","Access"),
        ("fn_p1","obj_demo","Access"),("fn_p1","obj_telemetry","Access")]
    def centre(i):
        for a,(ax,_) in cols.items():
            if i==a: return ax+AW//2, ytop+cont_h[a]//2
        x,y=pos[i]
        w=210 if i.startswith("obj_") else (190 if i=="act_member" else NW)
        return x+w//2, y+NH//2
    seen=set()
    for s,t,ty in R:
        if not s or (s,t,ty) in seen: continue
        seen.add((s,t,ty)); rid=rel(s,t,ty)
        scx,scy=centre(s); tcx,tcy=centre(t); midY=(scy+tcy)//2
        c=f'<connection identifier="c-{vid}-{rid}-{s}-{t}" relationshipRef="{rid}" source="{nid[s]}" target="{nid[t]}" xsi:type="Relationship"'
        out.append(c+('/>' if abs(scx-tcx)<4 else f'><bendpoint x="{scx}" y="{midY}"/><bendpoint x="{tcx}" y="{midY}"/></connection>'))
    out.append('</view>')
    return "\n".join(out)

def render_platform_detail():
    """Detailed platform business flow — functions (grouping processes), trigger events,
    services, actors, and input/output data (Access Read=input, Write=output).
    Layout: generous spacing, events inline in the process row, composition shown by NESTING
    (not drawn), and connectors routed through staggered channels in the lane gaps."""
    vid="view-platform-detail"
    FUNCS=[("fn_p1",["s_cf","s_dc","s_ps"]),("fn_p2",["s_ac","s_be","s_ap","s_pf"]),
           ("fn_p9",["s_en","s_ee","s_tc","s_cn"]),("fn_p4",["s_ca","s_va"]),
           ("fn_p3",["s_sg","s_ar","s_aw"]),("fn_p5",["s_cp"]),
           ("fn_p6",["s_br","s_rs","s_rd","s_rv"]),("fn_concl",["s_cc","s_hw"])]
    fdict=dict(FUNCS)
    SW,SH,SGX=150,56,90; CPAD,CHDR,FPAD=40,32,34; FGX=250
    EW,EH=158,48; ACT_W,ACT_H=200,58; SVC_W,SVC_H=200,52; OW,OH,OGX=164,56,34
    funcH=CHDR+SH+2*FPAD            # bigger group: label + top pad + step + bottom pad
    y_act=30; y_svc=250; y_proc=520; y_data=y_proc+funcH+280
    def fwid(fid): n=len(fdict[fid]); return n*SW+(n-1)*SGX+2*CPAD
    fx={}; x=70
    for fid,_ in FUNCS: fx[fid]=x; x+=fwid(fid)+FGX
    step_y=y_proc+CHDR+FPAD         # vertically centre the step in the group body
    pos={}
    for fid,st in FUNCS:
        pos[fid]=(fx[fid],y_proc); sx=fx[fid]+CPAD
        for k,s in enumerate(st): pos[s]=(sx+k*(SW+SGX), step_y)
    # events inline in the flow
    def gapc(a,b): return (fx[a]+fwid(a)+fx[b])//2
    for ev,a,b in [("e_seg","fn_p1","fn_p2"),("e_chal","fn_p2","fn_p9"),
                   ("e_verified","fn_p4","fn_p3"),("e_points","fn_p5","fn_p6")]:
        pos[ev]=(gapc(a,b)-EW//2, step_y+(SH-EH)//2)
    gc=gapc("fn_p6","fn_concl")
    pos["e_voucher"]=(gc-EW//2, step_y-46); pos["e_pend"]=(gc-EW//2, step_y+58)
    pos["e_start"]=(fx["fn_p1"]-EW-54, step_y+(SH-EH)//2)
    pos["e_concl"]=(fx["fn_concl"]+fwid("fn_concl")+54, step_y+(SH-EH)//2)
    pos["e_week"]=(pos["s_aw"][0]+(SW-EW)//2, y_proc-EH-34)
    pos["e_inelig"]=(pos["s_ee"][0]+(SW-EW)//2, y_proc+funcH+34)
    EVENTS=["e_start","e_seg","e_chal","e_inelig","e_verified","e_week","e_points","e_voucher","e_pend","e_concl"]
    # services over their realizing function
    SVC=[("bsv_enrol","fn_p9","act_member"),("bsv_score","fn_p3","act_member"),("bsv_redeem","fn_p6","act_member")]
    for sid,fid,_ in SVC: pos[sid]=(fx[fid]+fwid(fid)//2-SVC_W//2, y_svc)
    # actors over their primary function, de-overlapped left-to-right
    prim={"r_analytics":"fn_p1","r_admin":"fn_p2","r_cms":"fn_p2","act_member":"fn_p9","r_verify":"fn_p4","r_doh":"fn_concl"}
    ACTORS=["r_analytics","r_admin","r_cms","act_member","r_verify","r_doh"]
    desired={a:fx[prim[a]]+fwid(prim[a])//2-ACT_W//2 for a in ACTORS}
    lastx=-10**9
    for a in sorted(ACTORS,key=lambda a:desired[a]):
        xa=max(desired[a],lastx+ACT_W+34); pos[a]=(xa,y_act); lastx=xa
    # data lane
    DATA=["obj_demo","obj_telemetry","obj_clinical","obj_features","obj_cohort","obj_segment",
          "obj_challenge","obj_enrol","obj_activity","obj_plan","obj_dailyscore","obj_title",
          "obj_score","obj_wallet","obj_catalogue","obj_reservation","obj_redemption","obj_voucher","obj_standings"]
    for k,o in enumerate(DATA): pos[o]=(70+k*(OW+OGX), y_data)
    canvas_w=max(x,70+len(DATA)*(OW+OGX),max(pos[a][0]+ACT_W for a in ACTORS))+70
    canvas_h=y_data+OH+50
    SZ={a:(ACT_W,ACT_H) for a in ACTORS}
    for s,_,_ in SVC: SZ[s]=(SVC_W,SVC_H)
    for e in EVENTS: SZ[e]=(EW,EH)
    for fid,st in FUNCS:
        SZ[fid]=(fwid(fid),funcH)
        for s in st: SZ[s]=(SW,SH)
    for o in DATA: SZ[o]=(OW,OH)
    def ctr(i): x,y=pos[i]; w,h=SZ[i]; return x+w//2,y+h//2

    out=[f'<view identifier="{vid}" xsi:type="Diagram"><name xml:lang="en">Platform — Detailed Business Flow</name>']
    nid={}
    def en(i,fs=8):
        x,y=pos[i]; w,h=SZ[i]; n=f'n-{vid}-{i}'; nid[i]=n; r,g,b=rgb(BIZ)
        return (f'<node identifier="{n}" elementRef="{i}" xsi:type="Element" x="{x}" y="{y}" w="{w}" h="{h}">'
                f'<style><fillColor r="{r}" g="{g}" b="{b}"/><lineColor r="120" g="120" b="120"/>'
                f'<font name="Sans" size="{fs}"><color r="0" g="0" b="0"/></font></style></node>')
    def lane(gid,label,y,h):
        out.append(f'<node identifier="{gid}" xsi:type="Container" x="40" y="{y}" w="{canvas_w-80}" h="{h}">')
        out.append(f'<label xml:lang="en">{escape(label)}</label>')
        out.append('<style><fillColor r="250" g="250" b="250" a="0"/><lineColor r="185" g="185" b="185"/><font name="Sans" size="10"><color r="95" g="95" b="95"/></font></style>')
    lane(f'g-{vid}-act',"Business Roles / Actors (active structure)",y_act-18,ACT_H+36); [out.append(en(a,9)) for a in ACTORS]; out.append('</node>')
    lane(f'g-{vid}-svc',"Business Services (external behaviour)",y_svc-18,SVC_H+36); [out.append(en(s,9)) for s,_,_ in SVC]; out.append('</node>')
    for fid,st in FUNCS:
        x,y=pos[fid]; w,h=SZ[fid]; r,g,b=rgb(BIZ)
        out.append(f'<node identifier="n-{vid}-{fid}" elementRef="{fid}" xsi:type="Element" x="{x}" y="{y}" w="{w}" h="{h}">')
        out.append(f'<style><fillColor r="{r}" g="{g}" b="{b}"/><lineColor r="120" g="120" b="120"/><font name="Sans" size="9"><color r="0" g="0" b="0"/></font></style>')
        nid[fid]=f'n-{vid}-{fid}'
        for s in st: out.append(en(s,8))
        out.append('</node>')
    for e in EVENTS: out.append(en(e,8))
    lane(f'g-{vid}-data',"Input / Output Data (passive structure — Read=input, Write=output)",y_data-18,OH+36); [out.append(en(o,8)) for o in DATA]; out.append('</node>')

    flow=[("s_cf","s_dc"),("s_dc","s_ps"),("s_ac","s_be"),("s_be","s_ap"),("s_ap","s_pf"),
          ("s_en","s_ee"),("s_ee","s_tc"),("s_tc","s_cn"),("s_cn","s_ca"),("s_ca","s_va"),
          ("s_sg","s_ar"),("s_ar","s_aw"),("s_aw","s_cp"),("s_br","s_rs"),("s_rs","s_rd"),("s_rd","s_rv"),("s_cc","s_hw")]
    evflow=[("e_start","s_cf"),("s_ps","e_seg"),("e_seg","s_ac"),("s_pf","e_chal"),("e_chal","s_en"),
            ("s_ee","e_inelig"),("s_va","e_verified"),("e_verified","s_sg"),("e_week","s_aw"),
            ("s_cp","e_points"),("e_points","s_br"),("s_rv","e_voucher"),("e_pend","s_cc"),("s_hw","e_concl")]
    assign=[("r_analytics","s_cf"),("r_analytics","s_dc"),("r_analytics","s_ps"),("r_admin","s_ac"),
            ("r_admin","s_be"),("r_admin","s_pf"),("r_admin","s_cc"),("r_cms","s_ap"),("act_member","s_en"),
            ("act_member","s_tc"),("act_member","s_ca"),("act_member","s_br"),("r_verify","s_va"),("r_doh","s_hw")]
    reads={"s_cf":["obj_demo","obj_telemetry"],"s_dc":["obj_features","obj_clinical"],"s_ps":["obj_cohort"],
           "s_be":["obj_segment"],"s_pf":["obj_challenge"],"s_ee":["obj_segment","obj_challenge"],
           "s_ca":["obj_telemetry"],"s_sg":["obj_activity","obj_plan"],"s_ar":["obj_dailyscore"],
           "s_aw":["obj_dailyscore"],"s_cp":["obj_score"],"s_br":["obj_catalogue"],"s_rs":["obj_wallet"],
           "s_rd":["obj_reservation","obj_catalogue"],"s_cc":["obj_score"],"s_hw":["obj_standings"]}
    writes={"s_cf":["obj_features"],"s_dc":["obj_cohort"],"s_ps":["obj_segment"],"s_ac":["obj_challenge"],
            "s_be":["obj_challenge"],"s_cn":["obj_enrol"],"s_ca":["obj_activity"],"s_va":["obj_activity"],
            "s_sg":["obj_dailyscore"],"s_ar":["obj_title"],"s_aw":["obj_score"],"s_cp":["obj_wallet"],
            "s_rs":["obj_reservation"],"s_rd":["obj_redemption"],"s_rv":["obj_voucher"],"s_cc":["obj_standings"]}
    def emit(s,t,rid,channelY=None):
        scx,scy=ctr(s); tcx,tcy=ctr(t)
        c=f'<connection identifier="c-{vid}-{rid}-{s}-{t}" relationshipRef="{rid}" source="{nid[s]}" target="{nid[t]}" xsi:type="Relationship"'
        if channelY is None:
            if abs(scx-tcx)<6 or abs(scy-tcy)<6: out.append(c+'/>')
            else: out.append(c+f'><bendpoint x="{scx}" y="{(scy+tcy)//2}"/><bendpoint x="{tcx}" y="{(scy+tcy)//2}"/></connection>')
        else:
            out.append(c+f'><bendpoint x="{scx}" y="{channelY}"/><bendpoint x="{tcx}" y="{channelY}"/></connection>')
    # Composition is shown by NESTING (steps inside the function box) — create the relationship but do not draw it.
    for fid,st in FUNCS:
        for s in st: rel(fid,s,"Composition")
    # Triggers — direct (flow is left-to-right at the process row; the two timer/branch events route vertically)
    for s,t in flow+evflow: emit(s,t,rel(s,t,"Triggering"))
    # Assignment (actor->process) + Realization (function->service) share the services-to-process gap; staggered channels
    up=[(s,t,"Assignment") for s,t in assign]+[(fid,sid,"Realization") for sid,fid,_ in SVC]
    up.sort(key=lambda z:ctr(z[0])[0]); n=len(up); top=y_svc+SVC_H+16; bot=y_proc-16
    for i,(s,t,ty) in enumerate(up): emit(s,t,rel(s,t,ty), int(top+(i+1)*(bot-top)/(n+1)))
    # Serving (service->consumer actor) in the actors-to-services gap
    sv=[(sid,cons) for sid,_,cons in SVC]; n=len(sv); top=y_act+ACT_H+16; bot=y_svc-16
    for i,(s,t) in enumerate(sorted(sv,key=lambda z:ctr(z[0])[0])): emit(s,t,rel(s,t,"Serving"), int(top+(i+1)*(bot-top)/(n+1)))
    # Access (Read=input, Write=output) in the process-to-data gap; staggered, sorted by source x
    acc=[(s,o,"Read") for s,objs in reads.items() for o in objs]+[(s,o,"Write") for s,objs in writes.items() for o in objs]
    acc.sort(key=lambda z:ctr(z[0])[0]); n=len(acc); top=y_proc+funcH+16; bot=y_data-16
    for i,(s,o,a) in enumerate(acc): emit(s,o,rela(s,o,a), int(top+(i+1)*(bot-top)/(n+1)))
    out.append('</view>')
    return "\n".join(out)

mv=render(member); pv=render(partner); dv=render_data_view(); pdv=render_platform_detail()
def L(s): return f'<name xml:lang="en">{escape(s)}</name>'
doc=['<?xml version="1.0" encoding="UTF-8"?>',
 f'<model xmlns="{NS}" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
 f'xsi:schemaLocation="{NS} {NS}archimate3_Diagram.xsd" identifier="id-wellness-bizproc">',
 L("Wellness Platform — Business Process Cooperation"),"<elements>"]
for i,(t,n) in EL.items():
    doc.append(f'<element identifier="{i}" xsi:type="{t}"><name xml:lang="en">{escape(n)}</name></element>')
doc.append("</elements>"); doc.append("<relationships>")
for (s,t,ty),rid in RELS.items():
    attr=f' accessType="{ACC[rid]}"' if rid in ACC else ""
    doc.append(f'<relationship identifier="{rid}" source="{s}" target="{t}" xsi:type="{ty}"{attr}/>')
doc.append("</relationships>"); doc.append("<views><diagrams>"); doc+= [dv,pdv,mv,pv]
doc.append("</diagrams></views></model>")
path="/Users/socrateshlapolosa/Development/health-service-idp/factory/docs/analysis/wellness-archimate/business-process-cooperation.archimate.xml"
open(path,"w").write("\n".join(doc))
from collections import Counter
print("elements:",len(EL)," by type:",dict(Counter(t for t,_ in EL.values())))
print("relationships:",len(RELS)," by type:",dict(Counter(ty for (_,_,ty) in RELS)))
print("wrote:",path)
