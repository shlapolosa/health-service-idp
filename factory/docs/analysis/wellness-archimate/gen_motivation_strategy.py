#!/usr/bin/env python3
"""
Generate an ArchiMate Model Exchange File Format 3.0 XML for the Wellness Platform
Motivation + Strategy view, derived from the business requirements/rules catalogue
(00-business-requirements-and-rules.md) and the structural-element inventory.

Design (ArchiMate metamodel rules applied):
  Motivation:  Stakeholder -assoc-> Driver ; Assessment -assoc-> Driver, -influence-> Goal ;
               Driver -influence(+)-> Goal ; Outcome -realize-> Goal ; Requirement -realize-> Goal ;
               Principle -influence-> Requirement (+ -realize-> Goal where direct) ;
               Constraint -realize-> Goal, -influence(-)-> Requirement ; Value -assoc-> Stakeholder.
  Strategy:    Resource -assign-> Capability ; CourseOfAction -realize-> Capability ;
               Capability -realize-> Outcome ; CourseOfAction -realize-> Goal ;
               Capability -realize-> ValueStream ; ValueStream -serve-> Stakeholder ;
               ValueStream -realize-> Value.

Layout: banded top->bottom by element type (motivation chain then strategy), and within each
band sorted by THEME so related elements cluster horizontally. Coordinates are emitted into a
single diagram <view>. Themes: 0 Behaviour-change/engagement, 1 Reward-economy/integrity,
2 Reproducibility/audit, 3 Loose-coupling/integration, 4 Redemption/partner/settlement,
5 Compliance/fraud.
"""
from xml.sax.saxutils import escape

NS = "http://www.opengroup.org/xsd/archimate/3.0/"

# ---- elements: (id, xsi:type, name, theme, documentation) -------------------
E = []
def el(i, t, n, theme, doc):
    E.append((i, t, n, theme, doc)); return i

# Stakeholders
el("member","Stakeholder","Member / Citizen",0,"The wellness participant who enrols in challenges, earns Sahatna Points and redeems rewards.")
el("doh","Stakeholder","Department of Health (ADPHC/DoH)",2,"Programme sponsor, regulator and prize authority. Winners/prizes sit on the off-platform DoH trust boundary (RULE-333).")
el("partner","Stakeholder","Reward Partner / Aggregator",4,"Voucher and merchant providers (incl. UAE aggregators YouGotaGift/Reloadly and direct e&) supplying redeemable value.")
el("admin","Stakeholder","Programme Administrator / CMS Author",2,"Authors challenges, segments, scoring plans and surveys; operates the programme.")
el("fraud","Stakeholder","Fraud & Integrity Analyst",5,"Owns gaming/abuse risk and inline integrity checks on the value path.")
el("ops","Stakeholder","Platform Operator / Engineering",3,"Owns maintainability, evolvability and operability of the platform.")

# Values
el("val_member","Value","Healthier, rewarded life",0,"Sustained wellbeing plus a rewarding, trustworthy earning experience for the member.")
el("val_doh","Value","Population-health ROI & accountability",2,"Demonstrable, auditable public-health outcomes and programme accountability for the DoH.")

# Drivers
el("d1","Driver","Population health & behaviour change",0,"Drive sustained healthy behaviour across the population (DoH mandate).")
el("d2","Driver","Member engagement & retention",0,"Keep members active and returning across multi-week challenges.")
el("d3","Driver","Reward-economy trust & financial integrity",1,"Points have real monetary value; the economy must be trustworthy and balanced.")
el("d4","Driver","Fraud, gaming & abuse risk",5,"Rewards attract gaming of activity, scoring and redemption.")
el("d5","Driver","Regulatory & data-protection compliance",5,"UAE PDPL, health-data sensitivity, 7y retention obligations.")
el("d6","Driver","Partner ecosystem viability & redemption reliability",4,"Redemption depends on a viable, reliable partner/aggregator network.")
el("d7","Driver","Auditability & reproducibility",2,"Scoring/eligibility decisions on a money path must be replayable and auditable.")
el("d8","Driver","Maintainability & evolvability",3,"The platform must evolve cohorts, scoring and partners without re-engineering.")

# Assessments
el("a1","Assessment","Manual/hardcoded scoring is not reproducible",2,"Hardcoding or a rules engine makes historical scoring non-replayable and unauditable.")
el("a2","Assessment","Warehouse-as-source-of-truth risks money integrity",1,"If OLTP read state/money from the warehouse, integrity and latency would be compromised.")
el("a3","Assessment","Unverified activity enables gaming",5,"Without a verification gate, self-reported/raw activity can be gamed for rewards.")
el("a4","Assessment","Engagement decays without timely nudges",0,"Members disengage if recognition and nudges are not timely and contextual.")
el("a5","Assessment","Fragmented UAE partner integration is slow",4,"Per-partner direct integration is slow; coverage is fragmented without aggregators.")
el("a6","Assessment","Tight OLAP/OLTP coupling breaks latency & agility",3,"Coupling analytics to operations would break sub-50ms enrolment and cohort agility.")

# Goals
el("g1","Goal","Drive sustained healthy behaviour change",0,"Members adopt and sustain measurably healthier behaviour.")
el("g2","Goal","Operate a trustworthy, auditable reward economy",1,"A balanced, tamper-evident points economy redeemable for real value.")
el("g3","Goal","Reproducible, version-pinned scoring & eligibility",2,"Every scoring and eligibility decision is exactly replayable.")
el("g4","Goal","Keep OLAP & OLTP planes loosely coupled",3,"Analytics and operations evolve independently behind a published-artifact seam.")
el("g5","Goal","Reliable partner redemption & reconciled settlement",4,"Members redeem reliably; partner settlement reconciles to the ledger.")
el("g6","Goal","Regulatory-compliant data handling & consent",5,"Consent-driven, PDPL-compliant handling of personal and clinical data.")
el("g7","Goal","Prevent fraud & gaming of rewards",5,"Gaming of activity, scoring and redemption is detected and blocked.")
el("g8","Goal","Maximise engagement via recognition & nudges",0,"Timely recognition, streaks and nudges keep members engaged.")

# Outcomes
el("o1","Outcome","Cohorts identified & version-pinned",2,"Segments published as membership or portable predicate, versioned (RULE-001/008).")
el("o2","Outcome","Eligibility evaluated <50ms against frozen binding",3,"OLTP enrolment reads only published artifacts within latency budget (RULE-003/004).")
el("o3","Outcome","Weekly score computed deterministically",2,"WeeklyScore = min(100, Σ daily-goal + Σ balanced-day + streak bonus) (RULE-318).")
el("o4","Outcome","Sahatna Points credited at week close",1,"SahatnaPoints = WeeklyScore×10, cumulative, never reset (RULE-319/321).")
el("o5","Outcome","Reward redeemed & voucher delivered in budget",4,"Reservation honoured; voucher delivered within the redemption latency budget (RULE-210..).")
el("o6","Outcome","Settlement reconciled monthly",4,"5% holdback released after 30-day dispute window; discrepancy <0.1% flagged (RULE-214/215).")
el("o7","Outcome","Only verified activity scores",5,"activity.verified gate: unverified activity never scores (RULE-110/103).")
el("o8","Outcome","Engagement nudges delivered on key events",0,"Nudges fire on streak-at-risk / goal events (NUDGE).")
el("o9","Outcome","Historical scoring & eligibility replayable",2,"Frozen-on-publish makes past decisions exactly reproducible (RULE-328/323).")

# Principles
el("p1","Principle","Frozen-on-publish",2,"Segments and ScoringPlans are version-pinned at publish (RULE-002/005/328).")
el("p2","Principle","Warehouse is never source of truth for state/money",1,"The hot path never reads the warehouse for state or value (RULE-004).")
el("p3","Principle","Verified-signal gate",5,"Only activity.verified advances goals/streaks/scores (RULE-110).")
el("p4","Principle","Financial-grade ledger",1,"Append-only, double-entry, idempotent, two-phase reservation (RULE-025).")
el("p5","Principle","Inline fraud guard on value transfer",5,"Synchronous fraud check before any value movement (RULE-121).")
el("p6","Principle","Versioned event spine",3,"Ordered, partitioned, dead-lettered, schema-versioned async transport (RULE-122/123).")
el("p7","Principle","Typed-data scoring, not a rules engine",2,"ScoringPlan is typed data with a strategy registry, not hardcode (RULE-323).")
el("p8","Principle","Idempotency at value boundaries",4,"Every external/value boundary is idempotent (NFR).")
el("p9","Principle","Loose OLAP/OLTP coupling via published artifacts",3,"CDC ingest + reverse-ETL of published artifacts decouples the planes.")

# Requirements (representative/aggregate; each traces to a BR cluster / ABB)
el("r1","Requirement","Identify & version cohorts/segments",2,"Cohort Identification (OLAP): define WHO, versioned segments, binding [BR-001..].")
el("r2","Requirement","Author & publish challenges with frozen eligibility",2,"CHAL-SVC: challenge lifecycle + frozen {segmentId,segmentVersion} binding.")
el("r3","Requirement","Verify activity & clinical signals before scoring",5,"ACTV-SVC/CLIN-SVC: emit activity.verified only on validated, normalised input.")
el("r4","Requirement","Score goals, streaks, weekly & challenge scores",0,"SCORE/GOAL/STREAK/BADGE: daily goal, streak tiers, weekly & challenge score.")
el("r5","Requirement","Maintain reward-points wallet ledger with reservations",1,"WALLET-SVC: append-only ledger, two-phase reservation, idempotent credits.")
el("r6","Requirement","Operate marketplace redemption with partner adapters",4,"MARKET-SVC: redemption via PartnerAdapter, routing policy, failure sweepers.")
el("r7","Requirement","Manage partner lifecycle KYB→…→settlement→offboard",4,"Partner lifecycle: onboarding/KYB, contracting, redemption, settlement, offboarding.")
el("r8","Requirement","Provide engagement & nudge across the journey",0,"NUDGE-SVC: contextual nudges across enrolment and earning loop.")
el("r9","Requirement","Manage consent & identity per PDPL",5,"CONS-SVC/ID-SVC: consent purposes, identity & auth.")
el("r10","Requirement","Provide an event streaming spine",3,"EVENT-SVC: versioned, durable, ordered async backbone.")
el("r11","Requirement","Provide data lake/warehouse & reporting",3,"DATA-SVC/REPORT-SVC: warehouse + reporting (OLAP plane).")
el("r12","Requirement","Enforce fraud & integrity checks inline",5,"FRAUD-SVC: synchronous integrity check on the value path.")

# Constraints (restrictive rules)
el("c1","Constraint","Eligibility frozen to {segmentId, segmentVersion}",2,"Binding frozen at publish for reproducible, auditable eligibility (RULE-002/005).")
el("c2","Constraint","OLTP reads published artifacts <50ms; warehouse never SoT",3,"Hot path latency + source-of-truth boundary (RULE-003/004).")
el("c3","Constraint","Reservation 300s; partner timeout 10s; 3 retries then release",4,"Redemption timing & retry discipline (RULE-210/211/212).")
el("c4","Constraint","Settlement: 5% holdback, 30-day dispute, 0.1% discrepancy",4,"Settlement controls (RULE-214/215).")
el("c5","Constraint","Retain 7y; mask PII at 2y; 90-day offboarding wind-down",5,"Data retention & partner offboarding (RULE-206/218).")
el("c6","Constraint","Withdrawal irreversible — no credit, emit challenge.withdrawn",0,"Score/streak voided, no wallet credit (RULE-332).")
el("c7","Constraint","WeeklyScore capped at 100; Points = score×10, never reset",1,"Scoring/points invariants (RULE-318/319/321).")
el("c8","Constraint","Winners/prizes are off-platform (DoH boundary)",5,"Prize award sits outside the platform trust boundary (RULE-333).")

# Capabilities (strategy; map to ABB clusters)
el("cap1","Capability","Cohort Identification & Segmentation",2,"OLAP cohort definition + versioned segments.")
el("cap2","Capability","Challenge Lifecycle Management",2,"Authoring, publishing, enrolment, conclusion of challenges.")
el("cap3","Capability","Wellness Scoring & Recognition",0,"Goal/streak/badge scoring, weekly & challenge aggregation.")
el("cap4","Capability","Activity & Clinical Verification",5,"Validate and normalise activity/clinical signals.")
el("cap5","Capability","Reward Points & Wallet",1,"Ledger, reservations, credits.")
el("cap6","Capability","Marketplace & Redemption",4,"Catalogue, redemption, partner adapters.")
el("cap7","Capability","Partner Lifecycle & Settlement",4,"KYB, contracting, settlement, offboarding.")
el("cap8","Capability","Engagement & Nudging",0,"Contextual nudges and recognition.")
el("cap9","Capability","Consent, Identity & Compliance",5,"Consent purposes, identity, data-protection.")
el("cap10","Capability","Fraud & Integrity",5,"Inline and async integrity checks.")
el("cap11","Capability","Event Streaming & Integration",3,"Versioned event spine + connectors.")
el("cap12","Capability","Data, Analytics & Reporting",3,"Warehouse, analytics, reporting.")

# Courses of Action (strategic choices)
el("coa1","CourseOfAction","Adopt the OLAP/OLTP seam (CDC + reverse-ETL)",3,"Decouple planes behind published artifacts.")
el("coa2","CourseOfAction","Event-driven ABB decomposition on a versioned spine",3,"Microservice ABBs integrated via the event spine.")
el("coa3","CourseOfAction","Versioned strategy-registry scoring engine",2,"ScoringPlan as typed data, frozen on publish.")
el("coa4","CourseOfAction","Two-phase reservation + double-entry ledger",1,"Financial-grade wallet mechanics.")
el("coa5","CourseOfAction","Aggregator-first UAE partner sourcing",4,"YouGotaGift/Reloadly + direct e& for coverage and speed.")
el("coa6","CourseOfAction","Inline fraud guard + idempotency at value boundaries",5,"Synchronous integrity + idempotent value movement.")

# Resources
el("res1","Resource","ScoringPlan / strategy registry",2,"Versioned scoring assets (primitives + plans).")
el("res2","Resource","Partner network & catalogue",4,"Contracted partners and redeemable catalogue.")
el("res3","Resource","Member activity & clinical data feeds",5,"Wearable and clinical signal sources.")
el("res4","Resource","Sahatna Points reward economy",1,"The points currency as a managed asset.")

# Value Stream
el("vs1","ValueStream","Earn & Redeem Wellness Rewards",0,"Member value stream: Identify cohort -> Enrol -> Earn/Score -> Recognise -> Redeem -> Settle.")

# ---- Gap-accepted additive elements (gaps #4,#7,#8,#9; see 04-gaps-and-recommendations.md) ----
el("d9","Driver","Financial-services regulatory compliance (AML/SVF)",1,"Points redeemable for real value may constitute a CBUAE stored-value facility; AML & sanctions-screening obligations apply (gap #4).")
el("d10","Driver","ADHICS / health-data compliance",5,"Abu Dhabi Healthcare Information & Cyber Security standard governs clinical-data handling (gap #8).")
el("r13","Requirement","AML / Stored-Value controls",1,"Transaction monitoring, sanctions screening and stored-value-facility controls over the points economy (gap #4).")
el("r14","Requirement","PDPL data-subject rights",5,"Access, rectification, erasure, portability and objection over personal & clinical data (gap #7).")
el("p10","Principle","Minimal PII to partners",4,"Disclose the least PII necessary to partners on the redemption path; data minimisation (gap #9).")
el("p11","Principle","Erasure reconciled with the immutable ledger",2,"Right-to-erasure satisfied via crypto-shredding/tombstoning without breaking the append-only ledger (gap #7).")
el("c9","Constraint","Clinical signals handled as special-category data",5,"CLIN-SVC data classified and protected as special-category per ADHICS (gap #8).")
el("c10","Constraint","Data residency & cross-border-transfer controls",5,"Enforce UAE data residency; restrict/secure cross-border PII transfer to global partners (gap #9).")
# Title & Progression requirement (TITLE-SVC — the one ABB previously uncovered)
el("r15","Requirement","Title & Progression (recognition tiers)",0,"TITLE-SVC: member titles, levels and progression recognition.")
# Two extra Courses of Action so EVERY requirement is realized by one (consent/AML had none)
el("coa7","CourseOfAction","Privacy-by-design & consent governance (PDPL/ADHICS)",5,"Consent-driven, special-category-aware data governance realizing the data-protection requirements (gaps #7,#8).")
el("coa8","CourseOfAction","Treat points as regulated stored value (AML/KYC program)",1,"Operate the points economy under stored-value-facility / AML controls (gap #4).")

# ---- relationships: (source, target, type, modifier|None) -------------------
R = []
def rel(s,t,typ,mod=None): R.append((s,t,typ,mod))

# Stakeholder -assoc-> Driver
for s,ds in {"member":["d1","d2"],"doh":["d1","d5","d7"],"partner":["d6","d3"],
             "admin":["d7","d2"],"fraud":["d4","d3"],"ops":["d8","d7"]}.items():
    for d in ds: rel(s,d,"Association")
# Value -assoc-> Stakeholder
rel("val_member","member","Association"); rel("val_doh","doh","Association")
# Assessment -assoc-> Driver  and  -influence-> Goal
rel("a1","d7","Association"); rel("a1","g3","Influence","+")
rel("a2","d3","Association"); rel("a2","g2","Influence","+")
rel("a3","d4","Association"); rel("a3","g7","Influence","+")
rel("a4","d2","Association"); rel("a4","g8","Influence","+")
rel("a5","d6","Association"); rel("a5","g5","Influence","+")
rel("a6","d8","Association"); rel("a6","g4","Influence","+")
# Driver -influence(+)-> Goal
for d,gs in {"d1":["g1"],"d2":["g1","g8"],"d3":["g2","g5"],"d4":["g7"],
             "d5":["g6"],"d6":["g5"],"d7":["g2","g3"],"d8":["g4"]}.items():
    for g in gs: rel(d,g,"Influence","+")
# Outcome -realize-> Goal
for o,g in {"o1":"g3","o2":"g4","o3":"g3","o4":"g2","o5":"g5","o6":"g5","o7":"g7","o8":"g8","o9":"g3"}.items():
    rel(o,g,"Realization")
rel("o1","g1","Realization")
# Requirement -realize-> Goal
for r,g in {"r1":"g1","r2":"g3","r3":"g7","r4":"g1","r5":"g2","r6":"g5",
            "r7":"g5","r8":"g8","r9":"g6","r10":"g4","r11":"g4","r12":"g7"}.items():
    rel(r,g,"Realization")
# Principle -influence-> Requirement
for p,rs in {"p1":["r1","r2","r4"],"p2":["r5","r10","r11"],"p3":["r3","r4"],
             "p4":["r5"],"p5":["r6","r12"],"p6":["r10"],"p7":["r4"],
             "p8":["r6"],"p9":["r11","r1"]}.items():
    for r in rs: rel(p,r,"Influence","+")
# Principle -realize-> Goal (a few direct enablers)
rel("p1","g3","Realization"); rel("p2","g2","Realization"); rel("p9","g4","Realization")
# Constraint -realize-> Goal  and  -influence(-)-> Requirement (restricts)
rel("c1","g3","Realization"); rel("c1","r2","Influence","-")
rel("c2","g4","Realization"); rel("c2","r10","Influence","-")
rel("c3","g5","Realization"); rel("c3","r6","Influence","-")
rel("c4","g5","Realization"); rel("c4","r7","Influence","-")
rel("c5","g6","Realization"); rel("c5","r9","Influence","-")
rel("c6","g1","Realization"); rel("c6","r2","Influence","-")
rel("c7","g2","Realization"); rel("c7","r4","Influence","-")
rel("c8","doh","Association")
# Strategy chain (per the reference): Resource -assign-> Capability
#   Capability -realize-> Course of Action -realize-> Requirement ; Capability -serve-> Value Stream.
for r,caps in {"res1":["cap3"],"res2":["cap6","cap7"],"res3":["cap4","cap1"],"res4":["cap5"]}.items():
    for c in caps: rel(r,c,"Assignment")
# Capability -realize-> Course of Action
for coa,caps in {"coa1":["cap1","cap11","cap12"],"coa2":["cap2","cap8","cap11"],"coa3":["cap3"],
                 "coa4":["cap5"],"coa5":["cap6","cap7"],"coa6":["cap10","cap4"],
                 "coa7":["cap9"],"coa8":["cap5","cap10"]}.items():
    for c in caps: rel(c,coa,"Realization")
# Course of Action -realize-> Requirement  (every r1..r15 is realized by exactly one CoA)
for coa,reqs in {"coa1":["r1","r10","r11"],"coa2":["r2","r8"],"coa3":["r4","r15"],
                 "coa4":["r5"],"coa5":["r6","r7"],"coa6":["r3","r12"],
                 "coa7":["r9","r14"],"coa8":["r13"]}.items():
    for rq in reqs: rel(coa,rq,"Realization")
# Capability -serve-> ValueStream ; ValueStream -serve-> Member ; ValueStream -realize-> Value
for c in ["cap1","cap2","cap3","cap5","cap6","cap7"]: rel(c,"vs1","Serving")
rel("vs1","member","Serving"); rel("vs1","val_member","Realization")
# Title & Progression requirement realizes the engagement/recognition goal
rel("r15","g8","Realization")

# ---- Business-level rephrasing -------------------------------------------------
# The Motivation & Strategy layers MUST be technology-agnostic. The source is a
# solution-architecture document, so the first extraction leaked implementation
# detail (OLAP/OLTP seam, CDC, reverse-ETL, event spine, two-phase ledger, strategy
# registry, <50ms, ×10 …). Here we lift each element to its BUSINESS intent. IDs and
# relationships are unchanged; the implementation specifics remain in the rules
# catalogue (00-…md) and resurface correctly at the Application/Technology layers.
REPHRASE = {
 "a1": ("Scoring that can't be audited or replayed erodes trust",
        "If how a score was reached cannot be reproduced or explained, members and the sponsor cannot trust the rewards."),
 "a2": ("Letting analytics drive money or live state would jeopardise integrity",
        "Operational decisions and value must rest on authoritative records, not on derived analytical copies."),
 "a5": ("Fragmented partner coverage slows reward redemption",
        "Integrating each reward provider individually is slow and leaves gaps in coverage."),
 "a6": ("Coupling analytics to operations would slow the member experience and limit agility",
        "Tying the live member journey to analytical processing would harm responsiveness and the ability to change cohorts quickly."),
 "g4": ("Let analytics and operations evolve independently",
        "The insight/decisioning plane and the live member-experience plane can each change without disrupting the other."),
 "o1": ("Segments built (local) or consumed (clinical), reproducibly", "Local segments are built and version-pinned by the platform; clinical segments are consumed from the external builder; both reproducible."),
 "o2": ("Real-time, consistent enrolment eligibility", "Members are enrolled immediately against a stable, consistent eligibility basis."),
 "o3": ("Scores computed consistently and reproducibly", "Identical activity yields identical scores, every time, and can be re-derived."),
 "o4": ("Rewards earned are credited reliably and transparently", "Earned rewards reach the member's balance dependably and visibly."),
 "o5": ("Members redeem rewards reliably and promptly", "Redemption succeeds within the expected time and the reward is delivered."),
 "o6": ("Partner settlements reconcile accurately", "What partners are paid reconciles to what members redeemed, with discrepancies surfaced."),
 "o7": ("Only genuine, verified activity earns rewards", "Unverified or gamed activity does not earn rewards."),
 "o8": ("Members receive timely recognition and encouragement", "Recognition and nudges arrive at the moments that sustain engagement."),
 "o9": ("Past decisions are auditable and reproducible", "Any historical scoring or eligibility decision can be reconstructed for audit."),
 "r1":  ("Build local segments & consume external clinical segments", "DoH defines features; the platform builds versioned local (demographic/telemetry) segments and consumes externally-built clinical segments (Clinical Team/Malaffi)."),
 "r5":  ("Maintain the member rewards balance with reservations", "Keep an accurate member rewards balance, holding (reserving) amounts during redemption until confirmed."),
 "r10": ("Provide reliable information exchange between capabilities", "Capabilities exchange information dependably and in order, with no loss."),
 "r11": ("Provide analytics, warehousing & reporting", "Consolidated data for population analytics, insight and reporting."),
 "p1": ("Reproducibility by design", "Once a decision is published its basis is fixed, so the decision can always be reproduced."),
 "p2": ("Operational & financial records are authoritative", "The system of record governs live state and money; analytical copies are never the source of truth."),
 "p3": ("Rewards are earned only on verified activity", "Trust in the economy depends on rewarding genuine, verified behaviour."),
 "p4": ("Manage the reward economy to financial-grade integrity", "Balances are accurate, auditable and never silently lost or duplicated."),
 "p5": ("Check integrity before any value moves", "No value is transferred without an integrity check."),
 "p6": ("Information shared between capabilities is consistent & traceable", "Shared information has a known, evolvable meaning and can be traced end to end."),
 "p7": ("Scoring policy is business-owned and changeable without code", "The business defines and versions scoring rules as governed policy, not engineering changes."),
 "p8": ("No action is rewarded or charged twice", "Repeated or retried requests never double-credit or double-charge a member."),
 "p9": ("Loosely couple capabilities so each can change independently", "Capabilities depend on each other as little as possible to maximise evolvability."),
 "c1": ("Eligibility basis is fixed at publish", "A challenge's eligibility criteria are frozen when it is published, so enrolment is reproducible and auditable."),
 "c2": ("Live member reads resolve in real time from authoritative records", "Enrolment and earning reads meet the real-time latency budget and never depend on the analytics plane."),
 "c6": ("Withdrawal is irreversible: progress voided, no reward credited", "On withdrawal, accumulated progress is voided and no reward is credited."),
 "cap1": ("Local Segmentation (platform) & Clinical Segment Consumption (external)", "Build versioned local segments on the platform; consume clinical segments built externally by the Clinical Team on Malaffi."),
 "cap11":("Integration & Interoperability", "Reliable information exchange and integration between capabilities and partners."),
 "cap12":("Analytics & Insight", "Consolidated analytics, insight and reporting over programme data."),
 "coa1": ("Separate analytical insight from operational delivery", "Keep the live member experience fast and reliable while population analytics and decisioning evolve independently behind a clean boundary."),
 "coa2": ("Deliver as modular, independently-evolvable capability services", "Organise the platform as cohesive capabilities that can be changed and scaled independently."),
 "coa3": ("Govern scoring as versioned, business-owned policy", "Treat scoring rules as governed, versioned policy the business controls and can replay, rather than embedded code."),
 "coa4": ("Run rewards as financial-grade accounts", "Operate the points economy with the integrity, auditability and controls of financial accounting."),
 "coa5": ("Source rewards through aggregators for fast, broad coverage", "Partner via reward aggregators to obtain broad UAE coverage quickly, with direct integrations where warranted."),
 "coa6": ("Protect reward integrity at every transaction", "Guard every value-bearing transaction against fraud and double-processing."),
 "coa7": ("Adopt privacy-by-design, consent-led data governance", "Govern personal and health data by explicit consent and privacy-by-design, aligned to PDPL and ADHICS."),
 "coa8": ("Operate the points economy under financial-regulatory controls", "Treat the points economy as potentially regulated stored value, with AML/KYC-grade controls."),
 "res1": ("Scoring policy library", "The governed, versioned library of scoring rules and recognition criteria."),
 "res3": ("Member activity & clinical data", "Member-generated activity and clinical signals used to recognise wellness behaviour."),
 "d8":   ("Programme agility & evolvability", "The programme must adapt cohorts, scoring, rewards and partners without re-engineering."),
}
E = [(i,t, REPHRASE[i][0] if i in REPHRASE else n, theme, REPHRASE[i][1] if i in REPHRASE else doc)
     for (i,t,n,theme,doc) in E]

# ---- Gap-accepted additive relationships (gaps #4,#7,#8,#9) ----
# New Drivers: Stakeholder -assoc-> Driver, Driver -influence(+)-> Goal
rel("doh","d9","Association"); rel("fraud","d9","Association"); rel("doh","d10","Association")
rel("d9","g2","Influence","+"); rel("d9","g6","Influence","+"); rel("d10","g6","Influence","+")
# New Requirements -realize-> Goal
rel("r13","g6","Realization"); rel("r13","g2","Realization"); rel("r14","g6","Realization")
# New Principles -influence(+)-> Requirement, -realize-> Goal
rel("p10","r6","Influence","+"); rel("p10","r7","Influence","+"); rel("p10","g6","Realization")
rel("p11","r5","Influence","+"); rel("p11","r11","Influence","+"); rel("p11","r14","Influence","+"); rel("p11","g6","Realization")
# New Constraints -realize-> Goal, -influence(-)-> Requirement
rel("c9","g6","Realization"); rel("c9","r3","Influence","-"); rel("c9","r9","Influence","-")
rel("c10","g6","Realization"); rel("c10","r6","Influence","-")

# ---- layout: SWIMLANES — each element-type is a horizontal dashed Group lane
#               (label top-left), elements vertically aligned into theme columns so
#               causal chains read straight down. Empty lanes reserved at the bottom
#               for the Business / Application / Technology layers (later phases). ----
BAND_ORDER = ["Value","Stakeholder","Driver","Assessment","Goal","Outcome",
              "Requirement","Principle","Constraint",
              "CourseOfAction","ValueStream","Resource","Capability"]
BAND_LABEL = {
    "Value":"Values","Stakeholder":"Stakeholders","Driver":"Drivers","Assessment":"Assessments",
    "Goal":"Goals","Outcome":"Outcomes","Requirement":"Requirements","Principle":"Principles",
    "Constraint":"Constraints","CourseOfAction":"Strategy · Courses of Action",
    "ValueStream":"Strategy · Value Streams","Resource":"Strategy · Resources",
    "Capability":"Strategy · Capabilities"}
STRATEGY_BANDS = {"CourseOfAction","ValueStream","Resource","Capability"}
# reserved empty lanes (the rest of the layout, filled in later phases)
RESERVED = [
    ("Business Layer · Services / Processes / Functions / Objects / Events — Phase 3", 200),
    ("Application Layer · Components / Services / Data Objects — Phase 4", 170),
    ("Technology · OAM component realization (webservice / realtime-platform / postgresql …) — Phase 5", 150),
]
# Colour by ArchiMate LAYER (matching the reference): Motivation = purple, Strategy = tan.
MOTIVATION_BANDS = {"Value","Stakeholder","Driver","Assessment","Goal","Outcome",
                    "Requirement","Principle","Constraint"}
# ArchiMate standard layer colours: Motivation = purple, Strategy = tan/orange.
LAYER_FILL = {"motivation":"#E6E6FA","strategy":"#F5DEAA"}

W,H = 178,70        # element box (larger, like the reference)
SCW = 200           # column pitch (one causal column per theme)
LANE_GAP = 0        # lanes touch (contiguous dashed swimlanes)
LANE_PAD_TOP = 26   # room for the lane label at the lane's top-left
LANE_PAD_BOT = 14
LABEL_W = 150       # left gutter before the first column
TOP, LEFT = 30, 14

def rgb(hexs): return (int(hexs[1:3],16),int(hexs[3:5],16),int(hexs[5:7],16))

# theme columns: fixed x per theme so chains align vertically across lanes.
cell = {}
for (i,t,n,theme,doc) in E:
    cell.setdefault((t,theme),[]).append(i)
for k in cell: cell[k] = sorted(cell[k])
maxcells = {th: max([len(cell.get((b,th),[])) for b in BAND_ORDER]+[1]) for th in range(6)}
col_w = {th: maxcells[th]*SCW for th in range(6)}
col_x0 = {}; acc = LEFT + LABEL_W + 12
for th in range(6):
    col_x0[th] = acc; acc += col_w[th] + 30
CANVAS_W = acc + 20

# vertical cursor: stack each lane, remember its node-y and box geometry
lane_geom = {}      # band -> (box_y, box_h, node_y)
pos = {}
cur = TOP
for b in BAND_ORDER:
    box_y = cur
    node_y = box_y + LANE_PAD_TOP
    box_h = LANE_PAD_TOP + H + LANE_PAD_BOT
    lane_geom[b] = (box_y, box_h, node_y)
    for th in range(6):
        for kx,i in enumerate(cell.get((b,th),[])):
            pos[i] = (col_x0[th] + kx*SCW + (SCW-W)//2, node_y)
    cur = box_y + box_h + LANE_GAP
reserved_geom = []  # (label, box_y, box_h)
for label,h in RESERVED:
    reserved_geom.append((label, cur, h)); cur = cur + h + LANE_GAP
CANVAS_H = cur + 20

# ---- emit XML --------------------------------------------------------------
def L(s): return f'<name xml:lang="en">{escape(s)}</name>'
out = []
out.append('<?xml version="1.0" encoding="UTF-8"?>')
out.append(f'<model xmlns="{NS}" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           f'xsi:schemaLocation="{NS} {NS}archimate3_Diagram.xsd" identifier="id-wellness-motstrat">')
out.append(L("Wellness Platform — Motivation & Strategy"))
out.append('<documentation xml:lang="en">Motivation and Strategy layers derived from the wellness '
           'platform requirements/rules catalogue. Generated; see gen_motivation_strategy.py.</documentation>')
# elements
out.append("<elements>")
for (i,t,n,theme,doc) in E:
    out.append(f'<element identifier="{i}" xsi:type="{t}">')
    out.append(L(n))
    if doc: out.append(f'<documentation xml:lang="en">{escape(doc)}</documentation>')
    out.append('</element>')
out.append("</elements>")
# relationships
out.append("<relationships>")
relids = {}
for k,(s,t,typ,mod) in enumerate(R):
    rid = f"rel-{k+1}"; relids[k] = rid
    extra = f' modifier="{mod}"' if (typ=="Influence" and mod) else ""
    out.append(f'<relationship identifier="{rid}" source="{s}" target="{t}" xsi:type="{typ}"{extra}/>')
out.append("</relationships>")
# views
out.append("<views><diagrams>")
out.append('<view identifier="view-motstrat" xsi:type="Diagram">')
out.append(L("Motivation & Strategy View"))
nodeids = {}

def elem_node(i, fill):
    x,y = pos[i]; nid = f"node-{i}"; nodeids[i] = nid
    r,g,bl = rgb(fill)
    return (f'<node identifier="{nid}" elementRef="{i}" xsi:type="Element" x="{x}" y="{y}" w="{W}" h="{H}">'
            f'<style><fillColor r="{r}" g="{g}" b="{bl}"/><lineColor r="110" g="110" b="140"/>'
            f'<font name="Sans" size="8"><color r="0" g="0" b="0"/></font></style></node>')

# horizontal swimlane Group containers (label top-left), element nodes NESTED inside
elem_by_band = {b:[] for b in BAND_ORDER}
for (i,t,n,theme,doc) in E: elem_by_band[t].append((i,theme))
for b in BAND_ORDER:
    box_y,box_h,_ = lane_geom[b]
    gx = LEFT; gw = CANVAS_W - LEFT - 8
    fill = LAYER_FILL["strategy" if b in STRATEGY_BANDS else "motivation"]
    out.append(f'<node identifier="grp-{b}" xsi:type="Container" x="{gx}" y="{box_y}" w="{gw}" h="{box_h}">')
    out.append(f'<label xml:lang="en">{escape(BAND_LABEL[b])}</label>')
    out.append(f'<style><fillColor r="252" g="252" b="252" a="0"/><lineColor r="140" g="140" b="140"/>'
               f'<font name="Sans" size="9"><color r="80" g="80" b="80"/></font></style>')
    for (i,theme) in elem_by_band[b]:
        out.append(elem_node(i,fill))
    out.append('</node>')

# reserved empty lanes for the layers to come (Phases 3-5) — keeps space + intent
for ridx,(label,box_y,box_h) in enumerate(reserved_geom):
    out.append(f'<node identifier="grp-reserved{ridx}" xsi:type="Container" x="{LEFT}" y="{box_y}" '
               f'w="{CANVAS_W-LEFT-8}" h="{box_h}">')
    out.append(f'<label xml:lang="en">{escape(label)}</label>')
    out.append('<style><fillColor r="245" g="245" b="245" a="0"/><lineColor r="205" g="205" b="205"/>'
               '<font name="Sans" size="9"><color r="150" g="150" b="150"/></font></style>')
    out.append('</node>')

# connections (top level) — orthogonal (right-angled) routing via two bendpoints:
#   down/up from the source column, across at the mid-Y, then into the target column.
for k,(s,t,typ,mod) in enumerate(R):
    rid = relids[k]
    sx,sy = pos[s]; tx,ty = pos[t]
    scx,scy = sx+W//2, sy+H//2
    tcx,tcy = tx+W//2, ty+H//2
    midY = (scy+tcy)//2
    if scx==tcx:                      # same column -> straight vertical, no bendpoints
        out.append(f'<connection identifier="conn-{k+1}" relationshipRef="{rid}" '
                   f'source="{nodeids[s]}" target="{nodeids[t]}" xsi:type="Relationship"/>')
    else:                             # Z-route: vertical, horizontal at midY, vertical
        out.append(f'<connection identifier="conn-{k+1}" relationshipRef="{rid}" '
                   f'source="{nodeids[s]}" target="{nodeids[t]}" xsi:type="Relationship">'
                   f'<bendpoint x="{scx}" y="{midY}"/><bendpoint x="{tcx}" y="{midY}"/>'
                   f'</connection>')
out.append('</view>')
out.append("</diagrams></views>")
out.append("</model>")

xml = "\n".join(out)
path = "/Users/socrateshlapolosa/Development/health-service-idp/factory/docs/analysis/wellness-archimate/motivation-strategy.archimate.xml"
with open(path,"w") as f: f.write(xml)
print("elements:",len(E)," relationships:",len(R)," nodes:",len(E)," connections:",len(R))
from collections import Counter
print("by type:",dict(Counter(t for _,t,_,_,_ in E)))
print("rel types:",dict(Counter(typ for _,_,typ,_ in R)))
print("wrote:",path)
