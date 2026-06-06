# Auth0 tenant configuration (source of truth for out-of-cluster identity state)

Tenant: dev-4b4dzb0l6msa6iuh.uk.auth0.com (free tier - 10-app limit; reuse existing apps)

## Reproducible setup (auth0 CLI, user login)
1. API (audience): `https://identity.cafe.io/api` (scopes read:profiles, manage:profiles)
2. M2M app: reuse "Auth0 Management API (Test Application)" (oR8iCy...). Client grants:
   - Mgmt API (cgr_jToHAtS0abVMHZUN): read:users update:users create:users
     read:users_app_metadata update:users_app_metadata read:connections update:connections
   - identity API (cgr_aJN2ruBabFwhakWS): read:profiles manage:profiles
3. Post-login Action: deploy `profile-claims-action.js` as Action "profile-claims",
   bind to the post-login trigger. Maps app_metadata.profiles/active_profile ->
   https://cafe.io/profiles + active_profile claims (per-profile tokens).
4. Connection Username-Password-Authentication: requires_username=true,
   passwordPolicy good + password_complexity_options.min_length=12
   (gotcha: set both together - 'none' conflicts with min_length>1).
5. Key Vault kv-socrates-6706 secrets: auth0-domain, auth0-client-id,
   auth0-client-secret, auth0-audience, auth0-admin-password (generated 28-char).
6. Azure IAM: platform SP (5030f57a-...) needs "Key Vault Secrets User" on the
   vault and "API Management Service Contributor" on aigw-apim-dev-w4x7ibwk4e2is
   (for the expose-api trait's api import + policy write).

ROPG/password grant: intentionally NOT enabled (see identity-service-template
README-PATTERN-B.md).
