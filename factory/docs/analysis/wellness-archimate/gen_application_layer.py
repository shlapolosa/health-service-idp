#!/usr/bin/env python3
"""
Application layer (Phase 4) — ArchiMate Model Exchange 3.0. Full application-layer symbol set.
Three views:
  1. Application Cooperation — 4 system boundaries (Application Collaborations) with their components,
     the interfaces on the boundaries, cross-system Flow of data, and the Data Objects.
  2. Eligibility Determination — the login -> eligibility branch rule as an Application Interaction /
     Process (Functions, Events, Services, Interfaces, Data Objects, the Malaffi black box).
  3. Application -> Business Realization seam — components realize services that serve business functions.

Colours: Application = cyan (#B5FFFF), Business = yellow (#FFFFB5). OAM mapping deferred to Technology.
"""
from xml.sax.saxutils import escape
NS="http://www.opengroup.org/xsd/archimate/3.0/"
APP="#B5FFFF"; BIZ="#FFFFB5"
EL={}; RELS={}; ACC={}
def el(i,t,n): EL[i]=(t,n); return i
def rel(s,t,ty):
    k=(s,t,ty)
    if k not in RELS: RELS[k]=f"rel-{len(RELS)+1}"
    return RELS[k]
def rela(s,t,acc): rid=rel(s,t,"Access"); ACC[rid]=acc; return rid
def rgb(h): return (int(h[1:3],16),int(h[3:5],16),int(h[5:7],16))

# ---------------- elements ----------------
# system boundaries (Application Collaboration)
el("col_sahatna","ApplicationCollaboration","Sahatna")
el("col_platform","ApplicationCollaboration","Gamification Platform")
el("col_elig","ApplicationCollaboration","Eligibility Determination")
el("col_redeem","ApplicationCollaboration","Redemption Fulfilment")
# Sahatna components
SAH=[("ac_mobile","Mobile App"),("ac_gw","API Gateway"),("ac_bff_member","Member BFF"),
     ("ac_bff_chal","Challenge BFF"),("ac_bff_rewards","Rewards BFF")]
for i,n in SAH: el(i,"ApplicationComponent",n)
# Platform components -> service -> business function (for the seam)
PLAT=[("ac_cohort","Cohort & Segmentation Service","as_cohort","Cohort & Segmentation API","fn_p1"),
 ("ac_challenge","Challenge Service","as_challenge","Challenge Management API","fn_p2"),
 ("ac_enrol","Enrolment & Eligibility Service","as_elig","Eligibility Service","fn_p9"),
 ("ac_scoring","Scoring & Recognition Service","as_scoring","Scoring Service","fn_p3"),
 ("ac_verify","Verification Service","as_verify","Verification API","fn_p4"),
 ("ac_wallet","Wallet Service","as_wallet","Wallet Service","fn_p5"),
 ("ac_market","Marketplace & Voucher Service","as_redeem","Redemption Service","fn_p6"),
 ("ac_partner","Partner & Settlement Service","as_partner","Partner API","fn_p7"),
 ("ac_engage","Engagement Service","as_engage","Engagement Service","fn_p8"),
 ("ac_consent","Consent & Identity Service","as_consent","Consent & Identity Service","fn_p10"),
 ("ac_fraud","Fraud & Integrity Service","as_fraud","Integrity API","fn_p11"),
 ("ac_analytics","Analytics & Reporting Service","as_analytics","Analytics Service","fn_p12"),
 ("ac_event","Event Hub","as_eventsvc","Event Streaming Service","fn_p13")]
BFN={"fn_p1":"Cohort Planning","fn_p2":"Challenge Lifecycle Management","fn_p9":"Eligibility Evaluation",
 "fn_p3":"Wellness Scoring & Recognition","fn_p4":"Activity Verification","fn_p5":"Reward Points & Wallet",
 "fn_p6":"Marketplace & Redemption","fn_p7":"Partner Lifecycle & Settlement","fn_p8":"Engagement & Nudging",
 "fn_p10":"Consent & Identity","fn_p11":"Fraud & Integrity","fn_p12":"Analytics & Insight",
 "fn_p13":"Integration & Interoperability"}
for i,n in BFN.items(): el(i,"BusinessFunction",n)
for ac,acn,sv,svn,fn in PLAT:
    el(ac,"ApplicationComponent",acn); el(sv,"ApplicationService",svn)
    rel("col_platform",ac,"Composition"); rel(ac,sv,"Realization"); rel(sv,fn,"Serving")
for i,_ in SAH: rel("col_sahatna",i,"Composition")
# external black boxes
el("ac_malaffi","ApplicationComponent","Malaffi HIE  (external)")
el("ac_provider","Reward Providers  (external)" and "ac_provider","ApplicationComponent")  # placeholder
EL["ac_provider"]=("ApplicationComponent","Reward Providers  (external)")
# interfaces
IFACE=[("if_appui","Sahatna App UI","ac_mobile"),("if_gwapi","Sahatna Gateway API","ac_gw"),
 ("if_pubapi","Platform Public API","ac_enrol"),("if_maladapter","Malaffi Adapter Interface","ac_enrol"),
 ("if_provadapter","Provider Adapter Interface","ac_market"),("if_eventif","Event Streaming Interface","ac_event"),
 ("if_malapi","Malaffi API","ac_malaffi"),("if_provapi","Provider Redemption API","ac_provider")]
for i,n,owner in IFACE: el(i,"ApplicationInterface",n); rel(owner,i,"Assignment")
# Malaffi & Provider services (behind their interfaces)
el("as_malmember","ApplicationService","Membership & Eligibility Service"); rel("ac_malaffi","as_malmember","Realization")
el("as_malclin","ApplicationService","Clinical Cohort & Segmentation Service"); rel("ac_malaffi","as_malclin","Realization")
el("as_provredeem","ApplicationService","Voucher Redemption Service"); rel("ac_provider","as_provredeem","Realization")
el("as_memberapp","ApplicationService","Member App Service"); rel("ac_bff_member","as_memberapp","Realization")
# Programme Conclusion — realized by the Challenge Service; winners/prizes handed to DoH (off-platform boundary)
el("fn_concl","BusinessFunction","Programme Conclusion")
el("as_concl","ApplicationService","Programme Conclusion Service")
rel("ac_challenge","as_concl","Realization"); rel("as_concl","fn_concl","Serving")
el("ac_doh","ApplicationComponent","Department of Health  (external)")
el("do_standings","DataObject","Final Standings")
rela("ac_challenge","do_standings","Write"); rel("ac_challenge","ac_doh","Flow")
# Partner Lifecycle — detailed application behaviour (Part 5): KYB -> Contracting -> Settlement -> Offboarding
for i,n in [("fn_kyb","KYB Verification"),("fn_contract","Contracting & Catalogue Setup"),
            ("fn_settle","Settlement Reconciliation"),("fn_offboard","Offboarding")]:
    el(i,"ApplicationFunction",n); rel("ac_partner",i,"Assignment")
el("if_partnerportal","ApplicationInterface","Partner Portal API"); rel("ac_partner","if_partnerportal","Assignment")
rel("if_partnerportal","ac_provider","Serving")
EL["col_settle"]=("ApplicationCollaboration","Settlement Collaboration"); EL["ia_settle"]=("ApplicationInteraction","Reconcile & Settle")
rel("col_settle","ia_settle","Assignment")
for c in ["ac_partner","ac_wallet","ac_analytics"]: rel("col_settle",c,"Aggregation")
el("pr_partner","ApplicationProcess","Partner Onboarding & Settlement")
for i,n in [("ev_partner_approved","Partner Approved"),("ev_settlement","Settlement Generated")]: el(i,"ApplicationEvent",n)
for i,n in [("do_kyb","KYB / Application Record"),("do_contract","Partner Contract"),
            ("do_catalogue","Catalogue Data"),("do_settlement","Settlement / Invoice")]: el(i,"DataObject",n)
for s,t in [("fn_kyb","ev_partner_approved"),("ev_partner_approved","fn_contract"),("fn_contract","ia_settle"),
            ("ia_settle","fn_settle"),("fn_settle","ev_settlement"),("ev_settlement","fn_offboard")]: rel(s,t,"Triggering")
for sub in ["fn_kyb","fn_contract","fn_settle","fn_offboard"]: rel("pr_partner",sub,"Composition")
rela("fn_kyb","do_kyb","Write"); rela("fn_contract","do_contract","Write"); rela("fn_contract","do_catalogue","Write")
rela("fn_settle","do_redemption","Read"); rela("fn_settle","do_settlement","Write"); rela("fn_offboard","do_contract","Read")
# Challenge Authoring + Activity Verification + Conclusion — detailed behaviour for fn_p2, fn_p4, fn_concl
for i,n in [("fn_author","Challenge Authoring"),("fn_bind","Eligibility Binding"),("fn_publish","Publish & Freeze"),("fn_conclude","Conclude & Standings")]:
    el(i,"ApplicationFunction",n); rel("ac_challenge",i,"Assignment")
el("fn_verify","ApplicationFunction","Activity Verification"); rel("ac_verify","fn_verify","Assignment")
for i,n in [("ev_chalpub","Challenge Published"),("ev_actsynced","Activity Synced"),
            ("ev_periodend","Challenge Period Ended"),("ev_concluded","Challenge Concluded")]: el(i,"ApplicationEvent",n)
el("do_activity","DataObject","Verified Activity")
for s,t in [("fn_author","fn_bind"),("fn_bind","fn_publish"),("fn_publish","ev_chalpub"),
            ("ev_actsynced","fn_verify"),("fn_verify","ev_verified"),
            ("ev_periodend","fn_conclude"),("fn_conclude","ev_concluded")]: rel(s,t,"Triggering")
rel("ev_concluded","ac_doh","Flow")
rela("fn_author","do_segment","Read"); rela("fn_author","do_challenge","Write"); rela("fn_bind","do_challenge","Write")
rela("fn_publish","do_challenge","Read"); rela("fn_verify","do_telemetry","Read"); rela("fn_verify","do_activity","Write")
rela("fn_conclude","do_score","Read"); rela("fn_conclude","do_standings","Write")
# functions
FUN=[("fn_elig","Eligibility Resolution","ac_enrol"),("fn_localmem","Local Membership Check","ac_cohort"),
 ("fn_cohortmatch","Cohort Matching","ac_cohort"),("fn_score","Scoring","ac_scoring"),
 ("fn_rescred","Reservation & Crediting","ac_wallet"),("fn_redorch","Redemption Orchestration","ac_market"),
 ("fn_fraudchk","Fraud Check","ac_fraud"),("fn_eventpub","Event Publish / Subscribe","ac_event"),
 ("fn_present","Presentation & Aggregation","ac_bff_member")]
for i,n,owner in FUN: el(i,"ApplicationFunction",n); rel(owner,i,"Assignment")
# interactions (collective behaviour of collaborations)
el("ia_elig","Determine Eligible Challenges","ApplicationInteraction") and None
EL["ia_elig"]=("ApplicationInteraction","Determine Eligible Challenges")
EL["ia_redeem"]=("ApplicationInteraction","Fulfil Redemption")
rel("col_elig","ia_elig","Assignment"); rel("col_redeem","ia_redeem","Assignment")
for c in ["ac_enrol","ac_cohort","ac_malaffi"]: rel("col_elig",c,"Aggregation")
for c in ["ac_market","ac_wallet","ac_fraud","ac_provider"]: rel("col_redeem",c,"Aggregation")
# processes
for i,n in [("pr_login","Login & Challenge Presentation"),("pr_earn","Earn"),("pr_redeem","Redeem")]:
    el(i,"ApplicationProcess",n)
# events
for i,n in [("ev_login","User Logged In"),("ev_elig","Eligibility Resolved"),("ev_verified","Activity Verified"),
            ("ev_credited","Points Credited"),("ev_voucher","Voucher Issued")]:
    el(i,"ApplicationEvent",n)
# data objects
DO={"do_demographic":"Demographic Data","do_telemetry":"Telemetry Data","do_clinical":"Clinical Data",
 "do_segment":"Segment / Local Membership","do_challenge":"Challenge Data","do_eligresult":"Eligibility Result",
 "do_score":"Score Data","do_wallet":"Wallet Ledger","do_redemption":"Redemption Data","do_voucher":"Voucher Data"}
for i,n in DO.items(): el(i,"DataObject",n)
el("act_member","BusinessRole","Member / Citizen")

# ---------------- relationships (behaviour / flow / access) ----------------
# serving — interfaces / services to consumers
rel("if_appui","act_member","Serving"); rel("as_memberapp","act_member","Serving")
for b in ["ac_bff_member","ac_bff_chal","ac_bff_rewards"]: rel("if_pubapi",b,"Serving")
rel("as_elig","ac_bff_chal","Serving")
rel("as_malmember","fn_elig","Serving"); rel("as_malclin","fn_cohortmatch","Serving")
rel("as_provredeem","fn_redorch","Serving")
rel("if_malapi","if_maladapter","Serving"); rel("if_provapi","if_provadapter","Serving")
# cross-boundary data Flow
rel("col_sahatna","col_platform","Flow"); rel("ac_malaffi","col_platform","Flow"); rel("col_platform","ac_provider","Flow")
# process triggering (login -> eligibility -> present)
for s,t in [("ev_login","fn_present"),("fn_present","ia_elig"),("ia_elig","fn_elig"),
            ("fn_localmem","ev_elig"),("ev_elig","as_elig")]:
    rel(s,t,"Triggering")
rel("fn_elig","fn_localmem","Triggering")
# access (Read/Write)
def W(f,d): rela(f,d,"Write")
def R(f,d): rela(f,d,"Read")
R("fn_elig","do_challenge"); W("fn_elig","do_eligresult"); R("fn_elig","do_segment")
R("fn_localmem","do_segment"); R("fn_localmem","do_demographic"); R("fn_localmem","do_telemetry")
R("fn_cohortmatch","do_demographic"); R("fn_cohortmatch","do_telemetry"); W("fn_cohortmatch","do_segment")
R("fn_cohortmatch","do_clinical")
R("fn_score","do_telemetry"); W("fn_score","do_score"); W("fn_rescred","do_wallet"); R("fn_redorch","do_wallet"); W("fn_redorch","do_redemption"); W("fn_redorch","do_voucher")
# component-level access for the cooperation view
CACC=[("ac_cohort","do_segment","Write"),("ac_cohort","do_demographic","Read"),("ac_cohort","do_telemetry","Read"),
 ("ac_challenge","do_challenge","Write"),("ac_enrol","do_eligresult","Write"),("ac_enrol","do_challenge","Read"),
 ("ac_verify","do_telemetry","Read"),("ac_scoring","do_score","Write"),("ac_wallet","do_wallet","Write"),
 ("ac_market","do_redemption","Write"),("ac_market","do_voucher","Write"),("ac_malaffi","do_clinical","Write")]
for s,d,a in CACC: rela(s,d,a)

# ================= shared render helpers =================
def make(vid,title):
    out=[f'<view identifier="{vid}" xsi:type="Diagram"><name xml:lang="en">{escape(title)}</name>']
    nid={}; SZ={}; pos={}
    def setnode(i,x,y,w,h): pos[i]=(x,y); SZ[i]=(w,h)
    def enode(i,fill,fs=8):
        x,y=pos[i]; w,h=SZ[i]; n=f'n-{vid}-{i}'; nid[i]=n; r,g,b=rgb(fill)
        out.append(f'<node identifier="{n}" elementRef="{i}" xsi:type="Element" x="{x}" y="{y}" w="{w}" h="{h}">'
                   f'<style><fillColor r="{r}" g="{g}" b="{b}"/><lineColor r="90" g="110" b="130"/>'
                   f'<font name="Sans" size="{fs}"><color r="0" g="0" b="0"/></font></style></node>')
    def container(i,fill,fs,children):  # nested element container (collaboration/component boundary)
        x,y=pos[i]; w,h=SZ[i]; n=f'n-{vid}-{i}'; nid[i]=n; r,g,b=rgb(fill)
        out.append(f'<node identifier="{n}" elementRef="{i}" xsi:type="Element" x="{x}" y="{y}" w="{w}" h="{h}">'
                   f'<style><fillColor r="{r}" g="{g}" b="{b}"/><lineColor r="90" g="110" b="130"/>'
                   f'<font name="Sans" size="{fs}"><color r="0" g="0" b="0"/></font></style>')
        for c in children: enode(c,fill,8)
        out.append('</node>')
    def lane(gid,label,x,y,w,h):
        # plain text Label (no grey group box); transparent fill + line so only the title text shows
        out.append(f'<node identifier="{gid}" xsi:type="Label" x="{x}" y="{y-6}" w="420" h="26">'
                   f'<label xml:lang="en">{escape(label)}</label>'
                   '<style><fillColor r="255" g="255" b="255" a="0"/><lineColor r="255" g="255" b="255" a="0"/>'
                   '<font name="Sans" size="11"><color r="70" g="80" b="110"/></font></style></node>')
    def ctr(i): x,y=pos[i]; w,h=SZ[i]; return x+w//2,y+h//2
    def conn(s,t,rid,ch=None):
        scx,scy=ctr(s); tcx,tcy=ctr(t)
        c=f'<connection identifier="c-{vid}-{rid}-{s}-{t}" relationshipRef="{rid}" source="{nid[s]}" target="{nid[t]}" xsi:type="Relationship"'
        if ch is None: out.append(c+('/>' if (abs(scx-tcx)<6 or abs(scy-tcy)<6) else f'><bendpoint x="{scx}" y="{(scy+tcy)//2}"/><bendpoint x="{tcx}" y="{(scy+tcy)//2}"/></connection>'))
        else: out.append(c+f'><bendpoint x="{scx}" y="{ch}"/><bendpoint x="{tcx}" y="{ch}"/></connection>')
    def routed(conns, top, bot):
        cs=sorted(conns,key=lambda z:ctr(z[0])[0]); n=len(cs)
        for i,(s,t,ty) in enumerate(cs): conn(s,t,rel(s,t,ty), int(top+(i+1)*(bot-top)/(n+1)))
    return out,nid,setnode,enode,container,lane,ctr,conn,routed,pos,SZ

# ================= VIEW 1 — cooperation =================
def cooperation():
    out,nid,setnode,enode,container,lane,ctr,conn,routed,pos,SZ=make("view-app-cooperation","Application Cooperation")
    CW,CH=176,60; CGY=CH+34; CGX=CW+54         # generous component grid spacing
    # member
    setnode("act_member",30,150,160,CH)
    # Sahatna container (5 components stacked)
    sx=240; sy=80
    for k,(i,_) in enumerate(SAH): setnode(i,sx+30,sy+56+k*CGY,CW,CH)
    setnode("col_sahatna",sx,sy,CW+60,56+5*CGY+12)
    # interfaces (small) on sahatna edge
    setnode("if_appui",sx-40,150,128,40); setnode("if_gwapi",sx+CW+70,180,128,40)
    # Platform container (13 components, 3 balanced columns, generously spaced)
    px=sx+CW+330; py=80; cols2=3; rows=-(-len(PLAT)//cols2)
    for k,(ac,*_ ) in enumerate(PLAT):
        cxi=px+30+(k%cols2)*CGX; cyi=py+56+(k//cols2)*CGY; setnode(ac,cxi,cyi,CW,CH)
    pw=30+cols2*CGX-(CGX-CW)+30; ph=56+rows*CGY+12
    setnode("col_platform",px,py,pw,ph)
    setnode("if_pubapi",px-44,190,128,40)
    setnode("if_maladapter",px+pw-20,190,140,40); setnode("if_provadapter",px+pw-20,360,140,40); setnode("if_eventif",px+pw//2-64,py+ph+8,128,40)
    # Malaffi (black box) + interface + 2 services
    mx=px+pw+360
    setnode("ac_malaffi",mx,150,CW,CH); setnode("if_malapi",mx-44,160,128,40)
    setnode("as_malmember",mx+12,150+CH+30,CW-24,46); setnode("as_malclin",mx+12,150+CH+30+72,CW-24,46)
    # Providers
    setnode("ac_provider",mx,420,CW,CH); setnode("if_provapi",mx-44,430,128,40); setnode("as_provredeem",mx+12,420+CH+30,CW-24,46)
    canvas_w=mx+CW+80
    # data lane
    dy=max(py+ph, 420+CH+120)+110
    dlist=list(DO.keys()); OWd=172; OGd=48
    for k,d in enumerate(dlist): setnode(d,60+k*(OWd+OGd),dy,OWd,52)
    canvas_w=max(canvas_w,60+len(dlist)*(OWd+OGd))+60
    canvas_h=dy+52+50
    # emit containers + nodes
    enode("act_member",BIZ,9)
    container("col_sahatna",APP,11,[i for i,_ in SAH])
    container("col_platform",APP,11,[ac for ac,*_ in PLAT])
    for i in ["if_appui","if_gwapi","if_pubapi","if_maladapter","if_provadapter","if_eventif","if_malapi","if_provapi"]:
        if i in pos: enode(i,APP,8)
    for i in ["ac_malaffi","ac_provider","as_malmember","as_malclin","as_provredeem"]: enode(i,APP,8)
    lane(f'g-cw-data',"Data Objects (passive structure — Read/Write, cross-boundary Flow)",40,dy-20,canvas_w-80,52+36); [enode(d,APP,8) for d in DO]
    # connections
    for owner,iface in [("ac_mobile","if_appui"),("ac_gw","if_gwapi"),("ac_enrol","if_pubapi"),
                        ("ac_enrol","if_maladapter"),("ac_market","if_provadapter"),("ac_event","if_eventif"),
                        ("ac_malaffi","if_malapi"),("ac_provider","if_provapi")]:
        conn(owner,iface,rel(owner,iface,"Assignment"))
    for s in ["ac_malaffi"]: conn(s,"as_malmember",rel(s,"as_malmember","Realization")); conn(s,"as_malclin",rel(s,"as_malclin","Realization"))
    conn("ac_provider","as_provredeem",rel("ac_provider","as_provredeem","Realization"))
    conn("if_appui","act_member",rel("if_appui","act_member","Serving"))
    for b in ["ac_bff_member","ac_bff_chal","ac_bff_rewards"]: conn("if_pubapi",b,rel("if_pubapi",b,"Serving"))
    conn("if_malapi","if_maladapter",rel("if_malapi","if_maladapter","Serving")); conn("if_provapi","if_provadapter",rel("if_provapi","if_provadapter","Serving"))
    conn("col_sahatna","col_platform",rel("col_sahatna","col_platform","Flow"))
    conn("ac_malaffi","col_platform",rel("ac_malaffi","col_platform","Flow"))
    conn("col_platform","ac_provider",rel("col_platform","ac_provider","Flow"))
    routed([(s,d,"Access") for s,d,_ in CACC], dy-180, dy-16)
    out.append('</view>'); return "\n".join(out)

# ================= VIEW 2 — eligibility determination =================
def eligibility():
    out,nid,setnode,enode,container,lane,ctr,conn,routed,pos,SZ=make("view-app-eligibility","Eligibility Determination")
    # Clean layered left-to-right flow + staggered routing (no crossing).
    W,H=192,58; GX=78; EVW,EVH=152,46
    y_biz=40; y_svc=190; y_flow=400; y_data=700
    fy=y_flow+(H-H)//2
    fx=60
    setnode("act_member",fx,y_flow,156,H); fx+=156+GX
    setnode("ac_mobile",fx,y_flow,W,H); fx+=W+GX
    setnode("ev_login",fx,y_flow+(H-EVH)//2,EVW,EVH); fx+=EVW+GX
    setnode("fn_present",fx,y_flow,W,H); fx+=W+GX
    setnode("if_pubapi",fx,y_flow+(H-44)//2,132,44); fx+=132+GX        # Platform Public API (entry interface)
    # Eligibility Determination collaboration — 3 platform behaviours, evenly spaced + centred
    colx=fx
    for j,n in enumerate(["ia_elig","fn_elig","fn_localmem"]): setnode(n,colx+26+j*(W+GX),y_flow,W,H)
    cw=26+3*W+2*GX+26
    setnode("col_elig",colx,y_flow-46,cw,H+46+26)
    fx=colx+cw+GX
    setnode("ev_elig",fx,y_flow+(H-EVH)//2,EVW,EVH); fx+=EVW+GX
    # Malaffi black box — placed BELOW-right (in the band under the flow) so the clinical-branch call
    # routes under the boxes instead of horizontally through them.
    mx=fx; y_mal=y_flow+140
    setnode("if_malapi",mx,y_mal+(H-44)//2,134,44)                 # platform-facing interface
    setnode("ac_malaffi",mx+134+30,y_mal,W,H)                      # HIE component
    setnode("as_malmember",mx+134+30,y_mal+H+22,W,46)              # membership service
    fx=mx+134+30+W+GX
    # business function + service stacked straight above the interaction they hang off (no diagonal)
    midx=pos["ia_elig"][0]
    setnode("fn_p9",midx,y_biz,W,H); setnode("as_elig",midx,y_svc,W,H)
    # data objects evenly spaced in a single row (no overlap); access routes in staggered channels
    OWD,OGD=192,72
    dl=["do_challenge","do_eligresult","do_segment","do_demographic","do_telemetry","do_clinical"]
    for k,d in enumerate(dl): setnode(d,60+k*(OWD+OGD),y_data,OWD,54)
    canvas_w=max(fx,60+len(dl)*(OWD+OGD))+40; canvas_h=y_data+54+50
    # section labels (text only)
    lane("g-el-biz","BUSINESS  ·  served function",40,y_biz,0,0)
    lane("g-el-svc","APPLICATION  ·  services",40,y_svc,0,0)
    lane("g-el-flow","APPLICATION  ·  behaviour — Login → Determine Eligible Challenges",40,y_flow-72,0,0)
    lane("g-el-data","DATA OBJECTS  ·  Read=input · Write=output",40,y_data-26,0,0)
    # nodes
    enode("fn_p9",BIZ,9); enode("as_elig",APP,9)
    for i in ["ac_mobile","ev_login","fn_present","if_pubapi","ev_elig","ac_malaffi","if_malapi","as_malmember"]: enode(i,APP,9)
    enode("act_member",BIZ,9)
    container("col_elig",APP,11,["ia_elig","fn_elig","fn_localmem"])
    for d in dl: enode(d,APP,8)
    # connections — flow goes THROUGH the interfaces (Platform Public API, Malaffi API)
    conn("as_elig","fn_p9",rel("as_elig","fn_p9","Serving"))                    # service serves business (up)
    conn("ia_elig","as_elig",rel("ia_elig","as_elig","Realization"))           # the interaction realizes the service (no longer floating)
    rel("col_elig","if_pubapi","Assignment")                                    # collaboration exposes the public API
    for s,t in [("act_member","ac_mobile"),("ac_mobile","ev_login"),("ev_login","fn_present"),
                ("fn_present","if_pubapi"),("if_pubapi","ia_elig"),
                ("ia_elig","fn_elig"),("fn_elig","fn_localmem"),("fn_localmem","ev_elig")]:
        conn(s,t,rel(s,t,"Triggering"))                                          # horizontal flow, step by step (no jump-over)
    conn("col_elig","if_pubapi",rel("col_elig","if_pubapi","Assignment"))
    conn("ac_malaffi","if_malapi",rel("ac_malaffi","if_malapi","Assignment"))
    conn("ac_malaffi","as_malmember",rel("ac_malaffi","as_malmember","Realization"))
    conn("fn_elig","if_malapi",rel("fn_elig","if_malapi","Serving"))            # resolution calls the Malaffi API
    conn("if_malapi","as_malmember",rel("if_malapi","as_malmember","Serving"))  # ... which exposes the membership service
    routed([("fn_elig","do_challenge","Access"),("fn_elig","do_segment","Access"),("fn_elig","do_eligresult","Access"),
            ("fn_localmem","do_segment","Access"),("fn_localmem","do_demographic","Access"),("fn_localmem","do_telemetry","Access"),
            ("ac_malaffi","do_clinical","Access")], y_flow+H+62, y_data-22)        # access in staggered channels, below the Malaffi-call lane
    out.append('</view>'); return "\n".join(out)

# ================= VIEW 3 — realization seam =================
def seam():
    out,nid,setnode,enode,container,lane,ctr,conn,routed,pos,SZ=make("view-app-realization","Application → Business Realization Seam")
    W3,H3=196,64; GX=60
    y_fn=40; y_sv=y_fn+H3+110; y_ac=y_sv+H3+110; x=60
    cols=[(ac,sv,fn) for ac,acn,sv,svn,fn in PLAT]
    for ac,sv,fn in cols:
        setnode(fn,x,y_fn,W3,H3); setnode(sv,x,y_sv,W3,H3); setnode(ac,x,y_ac,W3,H3); x+=W3+GX
    setnode("fn_concl",x,y_fn,W3,H3); setnode("as_concl",x,y_sv,W3,H3); x+=W3+GX   # 8th: Programme Conclusion
    canvas_w=x+60; canvas_h=y_ac+H3+50
    lane("g-seam-fn","Business Functions  ·  BUSINESS (engine behaviour)",40,y_fn-18,canvas_w-80,H3+36); [enode(fn,BIZ,9) for _,_,fn in cols]; enode("fn_concl",BIZ,9)
    lane("g-seam-sv","Application Services  ·  APPLICATION (offered)",40,y_sv-18,canvas_w-80,H3+36); [enode(sv,APP,9) for _,sv,_ in cols]; enode("as_concl",APP,9)
    lane("g-seam-ac","Application Components  ·  APPLICATION (microservices)",40,y_ac-18,canvas_w-80,H3+36); [enode(ac,APP,9) for ac,_,_ in cols]
    for ac,sv,fn in cols:
        conn(ac,sv,rel(ac,sv,"Realization")); conn(sv,fn,rel(sv,fn,"Serving"))
    conn("ac_challenge","as_concl",rel("ac_challenge","as_concl","Realization")); conn("as_concl","fn_concl",rel("as_concl","fn_concl","Serving"))
    out.append('</view>'); return "\n".join(out)

def earn_redeem():
    out,nid,setnode,enode,container,lane,ctr,conn,routed,pos,SZ=make("view-app-earn-redeem","Earn & Redeem")
    W,H=200,56
    setnode("fn_p3",140,40,W,H); setnode("fn_p5",540,40,W,H); setnode("fn_p6",940,40,W,H)            # business functions
    setnode("as_scoring",140,180,W,H); setnode("as_wallet",540,180,W,H); setnode("as_redeem",940,180,W,H)
    ye=360                                                                                            # earn flow
    setnode("ev_verified",60,ye+5,160,46); setnode("fn_score",300,ye,W,H); setnode("fn_rescred",560,ye,W,H); setnode("ev_credited",820,ye+5,160,46)
    yr=580                                                                                           # redeem collaboration
    setnode("act_member",60,yr+44,160,H); setnode("ac_bff_rewards",260,yr+44,W,H)
    cx=500; setnode("ia_redeem",cx+24,yr+44,W,H); setnode("fn_redorch",cx+24,yr+44+H+22,W,H); setnode("fn_fraudchk",cx+24+W+30,yr+44,W,H)
    setnode("col_redeem",cx,yr-6,2*W+24+30+24,2*H+44+44)
    pxx=cx+2*W+24+30+24+70
    setnode("ac_provider",pxx,yr+44,W,H); setnode("if_provapi",pxx-30,yr+54,110,40); setnode("as_provredeem",pxx,yr+44+H+22,W,46); setnode("ev_voucher",pxx,yr+44+2*(H+22),160,46)
    canvas_w=pxx+W+70
    yd=yr+44+2*(H+22)+120
    dl=["do_telemetry","do_score","do_wallet","do_redemption","do_voucher"]
    for k,d in enumerate(dl): setnode(d,80+k*(180+44),yd,180,52)
    canvas_w=max(canvas_w,80+len(dl)*(180+44))+60; canvas_h=yd+52+50
    lane("g-er-biz","Business Functions  ·  served by the application",40,40-18,canvas_w-80,H+36); [enode(i,BIZ,9) for i in ["fn_p3","fn_p5","fn_p6"]]
    lane("g-er-svc","Application Services",40,180-18,canvas_w-80,H+36); [enode(i,APP,9) for i in ["as_scoring","as_wallet","as_redeem"]]
    for i in ["ev_verified","fn_score","fn_rescred","ev_credited","ac_bff_rewards","ac_provider","if_provapi","as_provredeem","ev_voucher"]: enode(i,APP,9)
    enode("act_member",BIZ,9)
    container("col_redeem",APP,11,["ia_redeem","fn_redorch","fn_fraudchk"])
    lane("g-er-data","Data Objects (Read=input · Write=output)",40,yd-18,canvas_w-80,52+36); [enode(d,APP,8) for d in dl]
    for s,t in [("as_scoring","fn_p3"),("as_wallet","fn_p5"),("as_redeem","fn_p6")]: conn(s,t,rel(s,t,"Serving"))
    for s,t in [("ev_verified","fn_score"),("fn_score","fn_rescred"),("fn_rescred","ev_credited")]: conn(s,t,rel(s,t,"Triggering"))
    for s,t,ty in [("act_member","ac_bff_rewards","Serving"),("ac_bff_rewards","as_redeem","Serving"),("as_redeem","ia_redeem","Triggering"),
                   ("ia_redeem","fn_redorch","Triggering"),("fn_redorch","fn_fraudchk","Triggering"),
                   ("fn_redorch","as_provredeem","Triggering"),("as_provredeem","ev_voucher","Triggering"),
                   ("ac_provider","if_provapi","Assignment"),("ac_provider","as_provredeem","Realization")]:
        conn(s,t,rel(s,t,ty))
    routed([("fn_score","do_telemetry","Access"),("fn_score","do_score","Access"),("fn_rescred","do_wallet","Access"),
            ("fn_redorch","do_wallet","Access"),("fn_redorch","do_redemption","Access"),("fn_redorch","do_voucher","Access")], yd-150, yd-16)
    out.append('</view>'); return "\n".join(out)

def partner():
    out,nid,setnode,enode,container,lane,ctr,conn,routed,pos,SZ=make("view-app-partner","Partner Lifecycle")
    W,H=184,56
    setnode("fn_p7",860,40,W,H); setnode("as_partner",860,180,W,H); setnode("ac_partner",860,320,W,H)   # served business fn + service + component
    setnode("ac_provider",60,320,W,H); setnode("if_partnerportal",60+W+18,330,120,40)                   # external partner + portal
    setnode("pr_partner",60,470,260,46)                                                                  # process banner
    yf=620; x=60                                                                                          # process flow
    setnode("fn_kyb",x,yf,W,H); x+=W+54
    setnode("ev_partner_approved",x,yf+5,164,46); x+=164+54
    setnode("fn_contract",x,yf,W,H); x+=W+54
    setnode("ia_settle",x+24,yf,W,H); setnode("fn_settle",x+24,yf+H+24,W,H); setnode("col_settle",x,yf-8,W+48,2*H+24+16); x+=W+48+54
    setnode("ev_settlement",x,yf+5,164,46); x+=164+54
    setnode("fn_offboard",x,yf,W,H); x+=W+54
    canvas_w=max(x,860+W)+60
    yd=yf+2*H+24+120
    dl=["do_kyb","do_contract","do_catalogue","do_redemption","do_settlement"]
    for k,d in enumerate(dl): setnode(d,80+k*(184+44),yd,184,52)
    canvas_w=max(canvas_w,80+len(dl)*(184+44))+60; canvas_h=yd+52+50
    lane("g-pl-biz","Business Function  ·  served by the application",40,40-18,canvas_w-80,H+36); enode("fn_p7",BIZ,9)
    lane("g-pl-svc","Application Service",40,180-18,canvas_w-80,H+36); enode("as_partner",APP,9)
    for i in ["ac_partner","ac_provider","if_partnerportal","pr_partner","fn_kyb","ev_partner_approved","fn_contract","ev_settlement","fn_offboard"]: enode(i,APP,9)
    container("col_settle",APP,11,["ia_settle","fn_settle"])
    lane("g-pl-data","Data Objects (Read=input · Write=output)",40,yd-18,canvas_w-80,52+36); [enode(d,APP,8) for d in dl]
    conn("ac_partner","as_partner",rel("ac_partner","as_partner","Realization")); conn("as_partner","fn_p7",rel("as_partner","fn_p7","Serving"))
    conn("ac_partner","if_partnerportal",rel("ac_partner","if_partnerportal","Assignment")); conn("if_partnerportal","ac_provider",rel("if_partnerportal","ac_provider","Serving"))
    for s,t in [("fn_kyb","ev_partner_approved"),("ev_partner_approved","fn_contract"),("fn_contract","ia_settle"),("ia_settle","fn_settle"),("fn_settle","ev_settlement"),("ev_settlement","fn_offboard")]:
        conn(s,t,rel(s,t,"Triggering"))
    routed([("fn_kyb","do_kyb","Access"),("fn_contract","do_contract","Access"),("fn_contract","do_catalogue","Access"),
            ("fn_settle","do_redemption","Access"),("fn_settle","do_settlement","Access"),("fn_offboard","do_contract","Access")], yd-150, yd-16)
    out.append('</view>'); return "\n".join(out)

def author():
    out,nid,setnode,enode,container,lane,ctr,conn,routed,pos,SZ=make("view-app-author","Authoring · Verification · Conclusion")
    W,H=190,56; colx=[80,580,1080]
    cols=[("fn_p2","as_challenge",["fn_author","fn_bind","fn_publish","ev_chalpub"]),
          ("fn_p4","as_verify",["ev_actsynced","fn_verify","ev_verified"]),
          ("fn_concl","as_concl",["ev_periodend","fn_conclude","ev_concluded"])]
    y_biz=40; y_svc=180; y0=360; dy=110
    for k,(bf,sv,flow) in enumerate(cols):
        x=colx[k]; setnode(bf,x,y_biz,W,H); setnode(sv,x,y_svc,W,H)
        for j,n in enumerate(flow):
            ev=n.startswith("ev_"); setnode(n,x+(15 if ev else 0),y0+j*dy,(164 if ev else W),46 if ev else H)
    canvas_w=colx[-1]+W+80
    yd=y0+4*dy+70
    dl=["do_segment","do_challenge","do_telemetry","do_activity","do_score","do_standings"]
    for k,d in enumerate(dl): setnode(d,80+k*(184+40),yd,184,52)
    canvas_w=max(canvas_w,80+len(dl)*(184+40))+60; canvas_h=yd+52+50
    lane("g-au-biz","Business Functions  ·  served by the application",40,y_biz-18,canvas_w-80,H+36); [enode(c[0],BIZ,9) for c in cols]
    lane("g-au-svc","Application Services",40,y_svc-18,canvas_w-80,H+36); [enode(c[1],APP,9) for c in cols]
    for bf,sv,flow in cols:
        for n in flow: enode(n,APP,9)
    lane("g-au-data","Data Objects (Read=input · Write=output)",40,yd-18,canvas_w-80,52+36); [enode(d,APP,8) for d in dl]
    for s,t in [("as_challenge","fn_p2"),("as_verify","fn_p4"),("as_concl","fn_concl")]: conn(s,t,rel(s,t,"Serving"))
    for s,t in [("fn_author","fn_bind"),("fn_bind","fn_publish"),("fn_publish","ev_chalpub"),
                ("ev_actsynced","fn_verify"),("fn_verify","ev_verified"),("ev_periodend","fn_conclude"),("fn_conclude","ev_concluded")]:
        conn(s,t,rel(s,t,"Triggering"))
    routed([("fn_author","do_segment","Access"),("fn_author","do_challenge","Access"),("fn_bind","do_challenge","Access"),
            ("fn_publish","do_challenge","Access"),("fn_verify","do_telemetry","Access"),("fn_verify","do_activity","Access"),
            ("fn_conclude","do_score","Access"),("fn_conclude","do_standings","Access")], yd-150, yd-16)
    out.append('</view>'); return "\n".join(out)

cv=cooperation(); ev=eligibility(); er=earn_redeem(); pl=partner(); au=author(); sm=seam()
def L(s): return f'<name xml:lang="en">{escape(s)}</name>'
doc=['<?xml version="1.0" encoding="UTF-8"?>',
 f'<model xmlns="{NS}" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
 f'xsi:schemaLocation="{NS} {NS}archimate3_Diagram.xsd" identifier="id-wellness-applayer">',
 L("Wellness Platform — Application Layer"),"<elements>"]
for i,(t,n) in EL.items():
    doc.append(f'<element identifier="{i}" xsi:type="{t}"><name xml:lang="en">{escape(n)}</name></element>')
doc.append("</elements>"); doc.append("<relationships>")
for (s,t,ty),rid in RELS.items():
    attr=f' accessType="{ACC[rid]}"' if rid in ACC else ""
    doc.append(f'<relationship identifier="{rid}" source="{s}" target="{t}" xsi:type="{ty}"{attr}/>')
doc.append("</relationships>"); doc.append("<views><diagrams>"); doc+=[cv,ev,er,pl,au,sm]
doc.append("</diagrams></views></model>")
path="/Users/socrateshlapolosa/Development/health-service-idp/factory/docs/analysis/wellness-archimate/application-layer.archimate.xml"
open(path,"w").write("\n".join(doc))
from collections import Counter
print("elements:",len(EL)," by type:",dict(Counter(t for t,_ in EL.values())))
print("relationships:",len(RELS)," by type:",dict(Counter(ty for (_,_,ty) in RELS)))
print("views: 6"); print("wrote:",path)
