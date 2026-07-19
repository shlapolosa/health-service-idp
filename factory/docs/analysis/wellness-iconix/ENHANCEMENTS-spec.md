# Architecture Enhancements — to propagate into ICONIX robustness + sequences

> These refinements were agreed while building the layered architecture. They are **model changes**, so they
> must land in the domain model, the **robustness** diagrams (`03-robustness/*`), the low-level ICONIX
> **sequences** (`04-sequences/*`) AND the high-level **architecture sequences** (`architecture/sequences/*`).
> Naming must match the C4 (`architecture/solution-c4.drawio`) exactly. **Mermaid hygiene (mandatory):** no `;`
> inside any sequenceDiagram message/note (use `,`), capital `Note`, balanced `alt/opt/loop … end`, no stray
> ``` fences or tool tags.

## E1 — Challenge Authoring: content-asset bucket + author-time clinical link  *(package: challenge-authoring)*
- **New entity** `ContentAsset` (image / icon / localized AR-EN media) persisted in **`challenge-content-store`**
  (object storage bucket). `challenge-db` keeps only **Content metadata + asset URIs** (refs, not blobs).
- **Boundary**: Content Authoring/Upload screen (Admin Portal).
- **Control**: `ContentAssetController` (writes assets to the bucket, URIs back to challenge-db),
  `ClinicalSegmentValidator` (author-time).
- **Author-time clinical link**: when the audience targets **clinical conditions**, the challenge-config flow
  calls `eligibility-svc` → **Malaffi** (segment **metadata** only — ACL, **no membership**) to confirm the
  clinical segment is valid **before** the `Draft` is accepted.
- Files: `03-robustness/challenge-authoring.md`, `04-sequences/challenge-authoring.md`.
  (`architecture/sequences/challenge-authoring.md` is ALREADY done — leave it, just keep names consistent.)

## E2 — Activity Ingestion: wearable telemetry via Health Connect SDK (frontend stream)  *(package: earn-scoring)*
- **Boundary**: `Health Connect SDK` — **on-device** (mobile) reader of Apple Health / Google Fit; it
  **streams** telemetry. It is **NOT** a server-side wearables-cloud integration; remove any "pull from
  wearables provider" framing.
- **Path**: `Mobile (Health Connect SDK) → APIM-north → BFF Wearable Ingest → APIM-south → ingestion-svc`,
  **async** stream. ingestion-svc verifies → emits `activity.verified` events.
- Files: `03-robustness/earn-scoring.md`, `04-sequences/earn-scoring.md`, `architecture/sequences/earn-scoring.md`.

## E3 — Surveys: Sahatna Survey API; survey responses stream like wearables  *(package: earn-scoring)*
- **New boundary**: `Surveys / Check-ins` (mobile) — fetch **survey info**, submit **survey responses**.
- **New BFF surface**: `Sahatna Survey API` — serves **survey info** (definitions/questions) read-side to the
  app, and **ingests survey responses**.
- **New entities**: `Survey` (definition), `SurveyResponse`.
- **Survey responses path = SAME as wearables**: `Mobile (Surveys) → APIM-north → Sahatna Survey API →
  APIM-south → ingestion-svc`, **async**. Responses are **self-reported activity (check-ins)** → feed scoring
  exactly like verified wearable metrics (cf. BRD mental / nutrition / sleep check-ins).
- **Survey info read** is **sync**: `Mobile → Sahatna Survey API`.
- Files: `03-robustness/earn-scoring.md`, `04-sequences/earn-scoring.md`, `architecture/sequences/earn-scoring.md`.

## E4 — Notifications: Sahatna Notifications API exposure  *(package: notification)*
- The **`Sahatna Notifications API`** (BFF) **owns outbound delivery** (push / email / in-app, consent-gated)
  AND **exposes a notifications API** (in-app feed) read-side to the app.
- Flow: `notification-svc` composes (consent-checked) → `Sahatna Notifications API` → Notification Provider
  (outbound); `Mobile → APIM-north → Sahatna Notifications API` (in-app feed read).
- Files: `03-robustness/notification.md`, `04-sequences/notification.md`, `architecture/sequences/notification.md`.

## Domain model  (`02-domain-model.md`)
- Add `ContentAsset` (owned by Challenge aggregate; stored in challenge-content-store), `Survey`,
  `SurveyResponse` (a SurveyResponse is an Activity-source — generalizes/relates to the activity ingested by
  ingestion-svc). Tag all "(added in architecture enhancements)". Do not remove existing classes.

## Index (`00-ICONIX-index.md`)
- Refresh traceability rows for challenge-authoring, earn-scoring, notification to mention the new
  boundary/control/entity objects; note the enhancements provenance.
