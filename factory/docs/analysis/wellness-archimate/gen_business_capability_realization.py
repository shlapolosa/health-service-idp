#!/usr/bin/env python3
"""
Capability Realization view (Business phase, step 3a) — ArchiMate Model Exchange 3.0.

Chain:  Capability  <-(realization)-  Business Service(s)  <-(realization)-  Business Function(s)
A capability is realized by ONE OR MORE business services (not 1:1); each service is realized by its
specific business function(s) (the ABBs). Services are grouped under their capability; functions
under their service.

Layout: three lanes (Strategy·Capabilities / Capability-Realization·Services / Behaviour·Functions),
columns per capability. Within a capability each service sits centred over its function sub-block.
Elements are vertically CENTRED in each lane and the lanes are generously sized.
"""
from xml.sax.saxutils import escape
NS="http://www.opengroup.org/xsd/archimate/3.0/"

# capability -> [ (service_id, service_name, [ (function_id, function_name), ... ] ) ]
CAP_SVC=[
 ("cap1","Segmentation — Local (platform) & Clinical (external)",[
   ("bs_cohortdef","Local Segment Build Service",[("bf_cohorta","Local Segmentation (demographic/telemetry)")]),
   ("bs_segpub","Malaffi Segment Service",[("bf_segpub","Segment Metadata (author) · Membership Query (eligibility)")]),
 ]),
 ("cap2","Challenge Lifecycle Management",[
   ("bs_chalauth","Challenge Authoring Service",[("bf_chal","Challenge Management")]),
   ("bs_chalpres","Challenge Presentation Service",[("bf_pres","Presentation")]),
   ("bs_chalconcl","Challenge Conclusion Service",[("bf_concl","Programme Conclusion")]),
 ]),
 ("cap3","Wellness Scoring & Recognition",[
   ("bs_dailyscore","Daily Scoring Service",[("bf_score","Wellness Scoring"),("bf_goal","Goal Management")]),
   ("bs_weekagg","Weekly Aggregation Service",[("bf_agg","Score Aggregation")]),
   ("bs_recog","Recognition & Titles Service",[("bf_streak","Streak Management"),("bf_badge","Badge Management"),("bf_title","Title & Progression")]),
 ]),
 ("cap4","Activity & Clinical Verification",[
   ("bs_actv","Activity Verification Service",[("bf_actv","Activity Verification")]),
   ("bs_clin","Clinical Verification Service",[("bf_clin","Clinical Verification")]),
 ]),
 ("cap5","Reward Points & Wallet",[
   ("bs_wallet","Wallet Balance Service",[("bf_wallet","Reward Points Wallet")]),
   ("bs_credit","Points Crediting Service",[("bf_credit","Points Crediting")]),
   ("bs_reserve","Point Reservation Service",[("bf_reserve","Reservation")]),
 ]),
 ("cap6","Marketplace & Redemption",[
   ("bs_browse","Catalogue Browse Service",[("bf_catalog","Catalogue Management")]),
   ("bs_redeem","Reward Redemption Service",[("bf_market","Reward Marketplace")]),
   ("bs_voucher","Voucher Issuance Service",[("bf_voucher","Voucher Management")]),
 ]),
 ("cap7","Partner Lifecycle & Settlement",[
   ("bs_ponb","Partner Onboarding Service",[("bf_plm","Partner Lifecycle Management")]),
   ("bs_pcat","Catalogue Management Service",[("bf_pcat","Partner Catalogue Management")]),
   ("bs_settle","Settlement Service",[("bf_settle","Settlement")]),
 ]),
 ("cap8","Engagement & Nudging",[
   ("bs_nudge","Engagement & Nudge Service",[("bf_nudge","Engagement & Nudge")]),
 ]),
 ("cap9","Consent, Identity & Compliance",[
   ("bs_consent","Consent Management Service",[("bf_cons","Consent Management")]),
   ("bs_identity","Identity & Authentication Service",[("bf_id","Identity & Authentication")]),
 ]),
 ("cap10","Fraud & Integrity",[
   ("bs_integrity","Integrity Check Service",[("bf_fraud","Fraud & Integrity")]),
 ]),
 ("cap11","Integration & Interoperability",[
   ("bs_events","Event Streaming Service",[("bf_event","Event & Integration Management")]),
   ("bs_integ","Partner / Data Integration Service",[("bf_integ","Integration")]),
 ]),
 ("cap12","Analytics & Insight",[
   ("bs_analytics","Analytics Service",[("bf_data","Data Management")]),
   ("bs_reporting","Reporting Service",[("bf_report","Reporting")]),
 ]),
]

# elements + relationships
elements=[]; rels=[]
for cid,cname,svcs in CAP_SVC:
    elements.append((cid,"Capability",cname))
    for sid,sname,funcs in svcs:
        elements.append((sid,"BusinessService",sname))
        rels.append((sid,cid,"Realization"))
        for bf,bfn in funcs:
            elements.append((bf,"BusinessFunction",bfn))
            rels.append((bf,sid,"Realization"))

# --- layout ---
W,H=190,66
SCW=240                      # sub-column width per function
COL_GAP=70                   # gap between capability columns
LABEL_H,LPAD=26,40           # lane label height + bottom pad (top pad = LABEL_H+LPAD -> centred)
LTOP=LABEL_H+LPAD
ROWH=LTOP+H+LPAD
LANE_GAP=64
LEFT,TOP=24,24
CAP_FILL="#F5DEAA"           # strategy tan
BIZ_FILL="#FFFFB5"           # business yellow

lane_y={"cap":TOP,"svc":TOP+ROWH+LANE_GAP,"fun":TOP+2*(ROWH+LANE_GAP)}
pos={}
x=LEFT+12
for cid,cname,svcs in CAP_SVC:
    cap_left=x
    for sid,sname,funcs in svcs:
        nf=max(1,len(funcs)); sw=nf*SCW
        for k,(bf,_) in enumerate(funcs):
            pos[bf]=(x+k*SCW+(SCW-W)//2, lane_y["fun"]+LTOP)
        pos[sid]=(x+sw//2-W//2, lane_y["svc"]+LTOP)
        x+=sw
    cap_right=x
    pos[cid]=((cap_left+cap_right)//2-W//2, lane_y["cap"]+LTOP)
    x+=COL_GAP
CANVAS_W=x+16
CANVAS_H=lane_y["fun"]+ROWH+20

def rgb(h): return (int(h[1:3],16),int(h[3:5],16),int(h[5:7],16))
def L(s): return f'<name xml:lang="en">{escape(s)}</name>'
out=['<?xml version="1.0" encoding="UTF-8"?>']
out.append(f'<model xmlns="{NS}" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           f'xsi:schemaLocation="{NS} {NS}archimate3_Diagram.xsd" identifier="id-wellness-caprealization">')
out.append(L("Wellness Platform — Business Capability Realization"))
out.append('<documentation xml:lang="en">Business services + functions that realize the strategy '
           'capabilities (one capability realized by one or more services). See gen_business_capability_realization.py.</documentation>')
out.append("<elements>")
for i,t,n in elements:
    out.append(f'<element identifier="{i}" xsi:type="{t}"><name xml:lang="en">{escape(n)}</name></element>')
out.append("</elements>")
out.append("<relationships>")
relids={}
for k,(s,t,ty) in enumerate(rels):
    rid=f"rel-{k+1}"; relids[k]=rid
    out.append(f'<relationship identifier="{rid}" source="{s}" target="{t}" xsi:type="{ty}"/>')
out.append("</relationships>")
out.append("<views><diagrams>")
out.append('<view identifier="view-caprealization" xsi:type="Diagram">')
out.append(L("Capability Realization View"))
nodeids={}
def enode(i,fill):
    x,y=pos[i]; nid=f"node-{i}"; nodeids[i]=nid; r,g,b=rgb(fill)
    return (f'<node identifier="{nid}" elementRef="{i}" xsi:type="Element" x="{x}" y="{y}" w="{W}" h="{H}">'
            f'<style><fillColor r="{r}" g="{g}" b="{b}"/><lineColor r="110" g="110" b="120"/>'
            f'<font name="Sans" size="9"><color r="0" g="0" b="0"/></font></style></node>')
def lane(gid,label,y,members,fill):
    out.append(f'<node identifier="{gid}" xsi:type="Container" x="{LEFT}" y="{y}" w="{CANVAS_W-LEFT-8}" h="{ROWH}">')
    out.append(f'<label xml:lang="en">{escape(label)}</label>')
    out.append('<style><fillColor r="252" g="252" b="252" a="0"/><lineColor r="140" g="140" b="140"/>'
               '<font name="Sans" size="10"><color r="80" g="80" b="80"/></font></style>')
    for i in members: out.append(enode(i,fill))
    out.append('</node>')
lane("grp-cap","Strategy · Capabilities",lane_y["cap"],[c for c,_,_ in CAP_SVC],CAP_FILL)
svc_members=[sid for _,_,svcs in CAP_SVC for sid,_,_ in svcs]
lane("grp-svc","Capability Realization · Business Services",lane_y["svc"],svc_members,BIZ_FILL)
fun_members=[bf for _,_,svcs in CAP_SVC for _,_,funcs in svcs for bf,_ in funcs]
lane("grp-fun","Behaviour · Business Functions",lane_y["fun"],fun_members,BIZ_FILL)
# realization connections (angled where columns differ)
for k,(s,t,ty) in enumerate(rels):
    sx,sy=pos[s]; tx,ty_=pos[t]
    scx,scy=sx+W//2,sy+H//2; tcx,tcy=tx+W//2,ty_+H//2; midY=(scy+tcy)//2
    c=f'<connection identifier="conn-{k+1}" relationshipRef="{relids[k]}" source="{nodeids[s]}" target="{nodeids[t]}" xsi:type="Relationship"'
    out.append(c+('/>' if abs(scx-tcx)<5 else f'><bendpoint x="{scx}" y="{midY}"/><bendpoint x="{tcx}" y="{midY}"/></connection>'))
out.append('</view></diagrams></views></model>')
path="/Users/socrateshlapolosa/Development/health-service-idp/factory/docs/analysis/wellness-archimate/business-capability-realization.archimate.xml"
open(path,"w").write("\n".join(out))
from collections import Counter
print("elements:",len(elements)," by type:",dict(Counter(t for _,t,_ in elements)))
print("relationships:",len(rels))
print("services:",sum(len(svcs) for _,_,svcs in CAP_SVC)," functions:",sum(len(f) for _,_,svcs in CAP_SVC for _,_,f in svcs))
print("wrote:",path)
