# BRD Supplement — Marketplace: Reward Information & Data Model

> Supplemental requirement provided after the base BRD. ICONIX agents working the **Redeem / Marketplace**
> package and the **Domain Model** MUST treat this as authoritative for the `Reward` / `MarketplaceItem` entity.
> Scope note: for the **September Challenge**, reward **images are submitted manually to the Malaffi team**;
> CMS-managed image upload is a **later** increment (model the attribute now, the manual process as the Phase-1 flow).

## Intent
Better define the reward structure and the information partners provide. Key clarifications:
- A reward is **not title-only** — it carries a **discount value** modelled as **two separate attributes**:
  - **Reward Discount Type** — enum: `PERCENTAGE` | `CURRENCY_AMOUNT`.
  - **Reward Discount Amount** — the numeric value (a %age when type=PERCENTAGE; a money amount when type=CURRENCY_AMOUNT).
- **Partners provide reward images.** September Challenge: submitted **manually to the Malaffi team** (no upload UI).
  Later: incorporate into the existing **CMS**.

## Reward data model (authoritative attribute set)

### Required (from the BRD supplement)
| Attribute | Type | Notes |
|---|---|---|
| Reward name | string | display title |
| Description | string | long text |
| Reward image | image ref | partner-provided; Sept = manual to Malaffi, later = CMS |
| Reward Point cost | integer | points debited from wallet on redemption |
| Reward Discount Type | enum `PERCENTAGE` \| `CURRENCY_AMOUNT` | **separate attribute** |
| Reward Discount Amount | number | %age (if PERCENTAGE) or currency amount (if CURRENCY_AMOUNT) |
| Validity period | date range / duration | window the reward is offered in the marketplace |
| Redemption limit per user | integer | max times one member may redeem |
| Total inventory limit | integer (nullable) | cap on total redemptions; null = unlimited |
| Expiry rules (post-redemption validity) | duration / date | how long an issued voucher stays valid after redemption |

### Suggested additions (prevalent in comparable reward/loyalty marketplaces — confirm/prune)
| Attribute | Type | Why it's usually needed |
|---|---|---|
| Reward ID / SKU | string | stable identifier for ledger, reconciliation, partner mapping |
| Partner / provider ref | ref → Partner | who supplies & fulfils the reward |
| Reward category / type | enum (voucher · discount · physical good · experience · service) | filtering, marketplace browse, fulfilment routing |
| Currency | ISO-4217 code | required to interpret `CURRENCY_AMOUNT` discounts |
| Localized name & description | AR / EN | platform is bilingual (matches challenge content) |
| Status | enum (draft · active · paused · archived) | lifecycle / catalogue visibility control |
| Availability / go-live date | datetime | when it appears in the marketplace (≠ validity period) |
| Redemption method | enum (online code · QR · offline/manual contact) | drives the issue/fulfilment flow; offline = DoH contacts user |
| Voucher / code format | string/pattern | code, PIN or QR issued on redemption (encrypted at rest) |
| Inventory counters | int reserved / issued / remaining | enforce inventory limit under concurrency (reserve→issue saga) |
| Terms & conditions / fine print | string | partner conditions, exclusions ("avoid hidden conditions" per BRD) |
| Eligibility constraints | segment / tier / age | restrict who can redeem (if a reward is targeted) |
| Min points balance / cost tier | derived | sort/affordability display in marketplace |
| Featured / sort priority | int/bool | merchandising in the Track & Engage marketplace view |
| Tax / VAT applicability | bool/flag | partner invoicing (note: partner-financial settlement itself is out of BRD scope) |

## ICONIX impact (what the agents should update)
- **Domain model (`02-domain-model.md`)** — flesh out `Reward` / `MarketplaceItem` with the attributes above;
  `Reward Discount Type` + `Reward Discount Amount` are two attributes, not one; associate `Reward → Partner`,
  `Reward → Voucher` (1..*), `Reward → InventoryCounters`.
- **Use cases (`01-use-cases.md`)** — Redeem/Marketplace package: add/refine *Submit Reward (partner → manual to Malaffi)*,
  *Browse Marketplace*, *Redeem Reward*; note Sept-Challenge manual image path vs later CMS.
- **Robustness (`03-robustness/<redeem/marketplace>.md`)** — boundary: marketplace browse/detail/confirm screens +
  partner submission (manual/offline for Sept); control: reserve-inventory, validate-points, issue-voucher,
  apply-discount(type,amount); entity: Reward, Voucher, InventoryCounters, Wallet, Redemption.
- **Sequences (`04-sequences/<redeem/marketplace>.md`)** — show discount-type branching, inventory reserve→issue
  under the limit, per-user redemption-limit check, and post-redemption voucher expiry.
