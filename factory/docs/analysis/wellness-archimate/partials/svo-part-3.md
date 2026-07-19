# SVO Grammatical Decomposition — Part 3

Source: `partials/part-3.md` (BR-201..BR-231, RULE-201..RULE-235). Subjects in *italics* are inferred (implicit in the source statement).

## S-V-O triples

| Triple# | Source ID | Subject | Action | Object |
|---------|-----------|---------|--------|--------|
| 1 | BR-201 | *Platform* | Provide (introduce) | Onboarding intro-carousel experience |
| 2 | BR-202 | *Platform* | Present | Host-home entry point |
| 3 | BR-203 | *Platform* | Display | Challenges dashboard |
| 4 | BR-204 | *Platform* | Show | Challenge details (pre-enrolment) |
| 5 | BR-205 | Member | Enrol in | Challenge |
| 6 | BR-205 | Member | Accept | Terms & Conditions |
| 7 | BR-206 | *Platform* | Provide | Challenge tracker |
| 8 | BR-207 | Member | Capture (submit) | Daily check-in |
| 9 | BR-208 | *Platform* | Acknowledge | Daily goal completion |
| 10 | BR-209 | *Platform* | Acknowledge | Week completion |
| 11 | BR-210 | *Platform* | Acknowledge | Challenge completion |
| 12 | BR-211 | Member | Withdraw from | Challenge |
| 13 | BR-212 | *Platform* | Provide | Rewards module |
| 14 | BR-213 | *Platform* | Show | Challenge-conclusion celebration |
| 15 | BR-214 | *Platform* | Onboard (intake) | Partner application |
| 16 | BR-215 | *Platform* | Perform (screen) | KYB due-diligence |
| 17 | BR-216 | *Platform* | Decide (gateway) | Partner approval |
| 18 | BR-217 | *Platform* | Provision | Sandbox partner credentials |
| 19 | BR-218 | Partner | Push | Catalogue item |
| 20 | BR-218 | *Platform* | Validate | Catalogue item |
| 21 | BR-219 | *Platform* | Release | Production credentials |
| 22 | BR-220 | Member | Redeem | Marketplace item |
| 23 | BR-220 | *Wallet SVC* | Reserve | Reservation (points) |
| 24 | BR-220 | Partner | Fulfil | Redemption |
| 25 | BR-221 | *Platform* | Release | Reservation |
| 26 | BR-221 | FRAUD-SVC | Log | Redemption incident |
| 27 | BR-222 | *Platform* | Run (aggregate) | Settlement |
| 28 | BR-222 | *Platform* | Reconcile | Ledger |
| 29 | BR-223 | *Platform* | Generate | VAT invoice |
| 30 | BR-223 | *Platform* | Route (pay) | Payment |
| 31 | BR-224 | *Platform* | Offboard | Partner |
| 32 | BR-225 | *Platform* | Depublish | Catalogue item |
| 33 | BR-225 | *Platform* | Honour | Voucher (unredeemed) |
| 34 | BR-226 | *Platform* | Source | Marketplace catalogue |
| 35 | BR-226 | PartnerAdapter | Integrate | Aggregator / Partner |
| 36 | BR-227 | *Platform* | Validate | KYB licence |
| 37 | BR-228 | Member | Browse / Redeem | Marketplace item |
| 38 | BR-228 | Member | View | Wallet balance / transaction / voucher |
| 39 | BR-229 | Platform Admin | Manage | Partner lifecycle |
| 40 | BR-229 | Platform Admin | Manage | Catalogue item |
| 41 | BR-229 | Platform Admin | Resolve | Uncertain redemption |
| 42 | BR-230 | *Wallet SVC* | Reserve | Reward points (reservation) |
| 43 | BR-230 | *Wallet SVC* | Credit | Reward points |
| 44 | BR-231 | *Platform* | Issue / Store | Voucher |
| 45 | RULE-201 | CMS (cms-service) | Own | Presentation content |
| 46 | RULE-201 | CHAL/SCORE/STREAK/WALLET contract | Own | Economics / eligibility / state |
| 47 | RULE-202 | Wallet SVC / Marketplace SVC | Apply | Reserve-then-confirm pattern |
| 48 | RULE-203 | Event consumer | Be idempotent on | source_event_id |
| 49 | RULE-204 | Eligibility / Consent resolution | Meet | Read-latency SLA |
| 50 | RULE-205 | Consent Resolver | Guarantee | Strong-consistency target |
| 51 | RULE-206 | *Platform* | Retain | Partner data |
| 52 | RULE-206 | *Platform* | Mask | PII |
| 53 | RULE-207 | *Partner* | Provide | KYB application (trade licence/VAT/signatory) |
| 54 | RULE-208 | *Platform* | Screen | AML watchlist / licence |
| 55 | RULE-209 | *Platform* | Validate | Catalogue item |
| 56 | RULE-210 | Wallet SVC | Expire | Reservation (300s TTL) |
| 57 | RULE-211 | Partner | Fulfil (10s timeout) | Redemption |
| 58 | RULE-212 | *Platform* | Release / Notify / Log | Reservation / Member / Incident |
| 59 | RULE-213 | Settlement timer | Trigger | Settlement |
| 60 | RULE-214 | *Platform* | Flag | Ledger discrepancy |
| 61 | RULE-215 | *Platform* | Release | Settlement holdback |
| 62 | RULE-216 | *Platform* | Route | Payment (by partner class) |
| 63 | RULE-217 | *Platform* | Revoke | Partner credentials |
| 64 | RULE-218 | *Platform* | Honour | Voucher (90-day wind-down) |
| 65 | RULE-219 | *Platform* | Enforce (>=0) | Wallet balance |
| 66 | RULE-220 | *Platform* | Enforce unique | WalletTransaction / WalletReservation key |
| 67 | RULE-221 | WalletReservation | Transition | Reservation state |
| 68 | RULE-222 | Platform Admin | Resolve (manual) | Uncertain redemption |
| 69 | RULE-223 | *Platform* | Snapshot | Redemption points_cost |
| 70 | RULE-224 | MarketplaceItem | Carry | Points-cost / AED-value mapping |
| 71 | RULE-225 | *Platform* | Store (as ref) | Partner credentials |
| 72 | RULE-226 | Partner | Sign | PDPL addendum |
| 73 | RULE-227 | *Platform* | Encrypt / Redact | Voucher / Redemption payload |
| 74 | RULE-228 | Client | Provide | Idempotency-Key header |
| 75 | RULE-229 | *Platform* | Authenticate | API request (JWT / mTLS) |
| 76 | RULE-230 | *Platform* | Soft-archive | Catalogue item |
| 77 | RULE-231 | *Platform* | Gate (precondition) | Redemption |
| 78 | RULE-232 | Aggregator (YouGotaGift/Reloadly/e&/Smiles) | Source | Marketplace catalogue |
| 79 | RULE-233 | Member / Platform Admin / Wallet SVC / Marketplace SVC / FRAUD-SVC / Partner | Participate in | Partner lifecycle |
| 80 | RULE-234 | Partner | Transition | Partner status |
| 81 | RULE-235 | Platform Token Service | Validate | Identity token |
| 82 | RULE-235 | User Profile Mirror | Cache | User profile |

## Active Structure elements

| Element name | ArchiMate type | Source IDs |
|--------------|----------------|------------|
| Member | Business Role | BR-205, BR-207, BR-211, BR-220, BR-228, RULE-212, RULE-233 |
| Partner | Business Actor (external) | BR-218, BR-220, RULE-207, RULE-211, RULE-226, RULE-234, RULE-233 |
| Platform Admin | Business Role | BR-229, RULE-222, RULE-233 |
| Platform / BFF | Business Collaboration | BR-201..204, BR-206, BR-208..210, BR-213..217, BR-219, BR-221..227, BR-230, BR-231, RULE-201, RULE-206, RULE-208..209, RULE-212, RULE-214..218, RULE-219, RULE-220, RULE-223, RULE-225, RULE-227, RULE-229..231, RULE-235 |
| Wallet SVC | Application Component | BR-220, BR-230, RULE-202, RULE-210, RULE-233 |
| Marketplace SVC | Application Component | BR-228, RULE-202, RULE-233 |
| FRAUD-SVC | Application Component | BR-221, RULE-212, RULE-233 |
| CMS (Strapi / cms-service) | Application Component | RULE-201 |
| CHAL/SCORE/STREAK contract | Application Component | RULE-201 |
| Event Consumer | Application Component | RULE-203 |
| Consent Resolver | Application Component | RULE-204, RULE-205 |
| Eligibility Resolver | Application Component | RULE-204, RULE-231 |
| Settlement Timer | Business Role (triggering) | RULE-213 |
| PartnerAdapter | Application Interface | BR-226 |
| Aggregator (YouGotaGift / Reloadly / e& / Smiles) | Business Actor (external) | BR-226, RULE-232 |
| Government API Marketplace | Business Actor (external) | BR-227, RULE-208 |
| Platform Token Service | Application Component | RULE-235 |
| User Profile Mirror | Application Component | RULE-235 |
| Client (API caller) | Application Component | RULE-228, RULE-229 |
| WalletReservation (state owner) | Data Object | RULE-221 |
| MarketplaceItem (state owner) | Data Object | RULE-224 |

## Behaviour elements

| Element name | ArchiMate type | Source IDs |
|--------------|----------------|------------|
| Onboarding intro experience | Business Service | BR-201, BR-202 |
| Browse challenges / catalogue | Business Service | BR-203, BR-204, BR-228 |
| Enrol in challenge | Business Process | BR-205 |
| Accept Terms & Conditions | Business Process | BR-205 |
| Track challenge / check-in | Business Process | BR-206, BR-207 |
| Acknowledge completion (goal/week/challenge) | Business Event | BR-208, BR-209, BR-210, BR-213 |
| Withdraw from challenge | Business Process | BR-211 |
| Provide rewards module | Business Service | BR-212 |
| Onboard partner (KYB intake) | Business Process | BR-214, RULE-207 |
| Perform KYB due-diligence | Business Function | BR-215, RULE-208, BR-227, RULE-227? |
| Decide partner approval | Business Process | BR-216 |
| Provision sandbox credentials | Business Process | BR-217 |
| Push & validate catalogue item | Business Process | BR-218, RULE-209, RULE-230 |
| Release production credentials | Business Process | BR-219 |
| Member redemption loop | Business Process | BR-220, BR-228, RULE-210, RULE-211, RULE-231 |
| Handle redemption failure | Business Process | BR-221, RULE-212, RULE-222 |
| Run settlement / reconcile | Business Process | BR-222, RULE-213, RULE-214 |
| Generate invoice & route payment | Business Process | BR-223, RULE-215, RULE-216 |
| Offboard partner | Business Process | BR-224, BR-225, RULE-217, RULE-218, RULE-206 |
| Source marketplace catalogue | Business Service | BR-226, RULE-232 |
| Manage partner lifecycle (admin) | Business Process | BR-229, RULE-233, RULE-234 |
| Reserve & credit points (two-phase) | Business Process | BR-230, RULE-202, RULE-219, RULE-220, RULE-221, RULE-223 |
| Issue / store voucher | Business Service | BR-231, RULE-227 |
| Resolve eligibility / consent | Application Service | RULE-204, RULE-205 |
| Enforce idempotency | Application Function | RULE-203, RULE-220, RULE-228 |
| Authenticate API request | Application Service | RULE-229 |
| Validate / mirror identity token | Application Service | RULE-235 |
| Snapshot points cost | Application Function | RULE-223, RULE-224 |
| Encrypt / redact at rest | Application Function | RULE-225, RULE-227 |
| Settlement trigger (monthly timer) | Business Event | RULE-213 |

## Passive Structure elements

| Element name | ArchiMate type | Source IDs |
|--------------|----------------|------------|
| Challenge | Business Object | BR-203, BR-204, BR-205, BR-206, BR-211 |
| Enrolment | Business Object | BR-205 |
| Terms & Conditions | Representation | BR-205 |
| Daily check-in | Business Object | BR-207 |
| Completion acknowledgement | Business Event (notification) | BR-208, BR-209, BR-210, BR-213 |
| Rewards module / Wallet | Business Object | BR-212, BR-230 |
| Partner application | Business Object | BR-214, RULE-207 |
| KYB record | Business Object | BR-215, BR-227, RULE-207, RULE-208 |
| Partner approval decision | Business Object | BR-216 |
| Partner credentials | Data Object | BR-217, BR-219, RULE-225 |
| Catalogue / MarketplaceItem | Business Object | BR-218, BR-225, BR-226, RULE-209, RULE-224, RULE-230 |
| Reservation (WalletReservation) | Data Object | BR-220, BR-221, RULE-210, RULE-219, RULE-220, RULE-221 |
| Redemption | Business Object | BR-220, BR-221, RULE-211, RULE-222, RULE-223, RULE-231 |
| Voucher | Business Object | BR-225, BR-231, RULE-218, RULE-227 |
| Settlement | Business Object | BR-222, RULE-213, RULE-214, RULE-215 |
| Ledger / WalletTransaction | Data Object | BR-222, RULE-214, RULE-219, RULE-220 |
| VAT invoice | Representation | BR-223 |
| Payment | Business Object | BR-223, RULE-216 |
| Reward points / WalletBalance | Business Object | BR-230, RULE-219 |
| Contract (PDPL addendum) | Contract | RULE-226 |
| Partner record (status) | Business Object | RULE-234, RULE-206, RULE-225 |
| Presentation content (CMS) | Representation | RULE-201 |
| source_event_id / Idempotency-Key | Data Object | RULE-203, RULE-220, RULE-228 |
| Consent / Eligibility record | Business Object | RULE-204, RULE-205, RULE-231 |
| Redemption incident / fraud log | Business Object | BR-221, RULE-212 |
| User profile (mirror) | Data Object | RULE-235 |
| Identity token | Data Object | RULE-229, RULE-235 |
