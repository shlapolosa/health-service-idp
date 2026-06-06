/**
 * profile-claims (CAFE identity wiring, 2026-06-06)
 * Copies the user's profile model (maintained by the identity-service in its
 * postgres, synced to app_metadata via the Management API) into token claims.
 * Same user + different active_profile => different claims in the token.
 */
exports.onExecutePostLogin = async (event, api) => {
  const ns = 'https://cafe.io/';
  const md = event.user.app_metadata || {};
  if (md.profiles) {
    api.accessToken.setCustomClaim(ns + 'profiles', md.profiles);
    api.idToken.setCustomClaim(ns + 'profiles', md.profiles);
  }
  if (md.active_profile) {
    api.accessToken.setCustomClaim(ns + 'active_profile', md.active_profile);
    api.idToken.setCustomClaim(ns + 'active_profile', md.active_profile);
  }
};
