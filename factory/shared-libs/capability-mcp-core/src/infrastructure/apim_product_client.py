"""APIM Developer-Portal Product client — one product per OAM (APIM-PRODUCT-1 #161).

A product is a discovery/grouping surface in the APIM Developer Portal that links
ALL of an OAM app's externally-accessible APIs (the `svc/<name>` APIs the expose-api
trait / EVENT-2 already create). It is PURELY ADDITIVE: the per-service APIs and
their `validate-jwt` (Auth0) enforcement are untouched. The product carries
`subscriptionRequired:false` (JWT-only discovery model, mirrors the live
`mcp-external` product) — it adds NO sub-key requirement. Dual-auth (the live
`mcp-catalog <choose>` sub-key OR JWT pattern) is the documented v2 upgrade path;
not implemented here.

Mechanism (mirrors expose-api.yaml + ksvc-ready-apim-publish.yaml, EVENT-2):
the reconcile runs as a Kubernetes Job using `az rest` ARM calls, mounting the
`azure-credentials` secret to reuse the cluster service principal — NOT in-process
`az` (the MCP pod has no az/SP). The Job CONVERGES membership every run: create/
upsert the product, link desired APIs that exist, UNLINK APIs no longer desired,
ensure the `developers` group for portal visibility. All calls are PUT/DELETE-by-id
→ idempotent and safe to re-run on every submit/resubmit.

Day-0 ordering: the product reconcile may precede `svc/*` API creation (CI build +
ksvc-Ready precede EVENT-2 import). A link PUT for an api-id that doesn't exist yet
404s → the Job skip-tolerates it; the EVENT-2-sibling sensor
(ksvc-ready-apim-product-link.yaml) backfills the link when the ksvc goes Ready.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Platform products that must never be clobbered by an OAM-named product (§8 of
# the plan). OAM app names live in a disjoint namespace from these, but we guard
# anyway: refuse product creation if the app name matches.
_RESERVED_PRODUCT_RE = re.compile(r"^(mcp-|starter$|unlimited$)")

_APIM_NAME_DEFAULT = "aigw-apim-dev-w4x7ibwk4e2is"
_APIM_RG_DEFAULT = "rg-ai-gateway-dev-uae"
_API_VERSION = "2022-08-01"


class ApimProductClient:
    """Renders + creates the per-OAM APIM-product converge Job. Mirrors
    K8sClaimClient's load_incluster_config()/load_kube_config() fallback and Job-
    based-az pattern from EVENT-2."""

    def __init__(self, namespace: str = "default",
                 apim_name: str = _APIM_NAME_DEFAULT,
                 apim_rg: str = _APIM_RG_DEFAULT,
                 azure_secret: str = "azure-credentials"):
        self.namespace = namespace
        self.apim_name = apim_name
        self.apim_rg = apim_rg
        self.azure_secret = azure_secret
        self._batch = None

    # ------------------------------------------------------------------
    @staticmethod
    def is_reserved(app_name: str) -> bool:
        """True if `app_name` collides with a platform product (must skip)."""
        return bool(_RESERVED_PRODUCT_RE.match(app_name or ""))

    def _batch_api(self):
        if self._batch is None:
            from kubernetes import client, config
            try:
                config.load_incluster_config()
            except Exception:  # noqa: BLE001
                config.load_kube_config()
            self._batch = client.BatchV1Api()
        return self._batch

    # ------------------------------------------------------------------
    def reconcile_product(self, app_name: str, api_ids: list[str],
                          display_name: str | None = None,
                          description: str = "") -> tuple[bool, str]:
        """Create + converge the APIM product `app_name` to link exactly `api_ids`.

        Returns (ok, message). Idempotent. Reserved-prefix app names are skipped
        (ok=True, no-op — never a failure, so submit is never blocked by the guard).
        A product with no api_ids still gets created (an empty product is inert and
        the sensor/resubmit will link members later).
        """
        if self.is_reserved(app_name):
            msg = (f"skipped APIM product '{app_name}': collides with a reserved "
                   f"platform product (mcp-*/starter/unlimited)")
            logger.warning(msg)
            return True, msg

        body = self._build_job(app_name, api_ids, display_name or app_name, description)
        try:
            self._batch_api().create_namespaced_job(namespace=self.namespace, body=body)
        except Exception as e:  # noqa: BLE001
            logger.error("APIM product Job create failed for %s: %s", app_name, e)
            return False, f"APIM product Job create failed: {e}"
        logger.info("✅ APIM product reconcile Job created for %s (members=%s)",
                    app_name, ", ".join(api_ids) or "<none>")
        return True, f"APIM product '{app_name}' reconcile dispatched ({len(api_ids)} member(s))"

    # ------------------------------------------------------------------
    def build_product_properties(self, display_name: str, description: str) -> dict[str, Any]:
        """The §3.1 product payload `properties` block. JWT-only discovery product:
        subscriptionRequired:false (no sub-key enforcement), published to the portal."""
        return {
            "displayName": display_name,
            "description": description or display_name,
            "state": "published",            # what makes it visible in the Dev Portal
            "subscriptionRequired": False,    # JWT-only discovery (mirrors mcp-external)
            "approvalRequired": False,
            "terms": "",
        }

    def _build_job(self, app_name: str, api_ids: list[str],
                   display_name: str, description: str) -> dict[str, Any]:
        import json as _json

        props_json = _json.dumps({"properties":
                                  self.build_product_properties(display_name, description)})
        desired = " ".join(api_ids)  # space-separated list for the shell loop
        script = self._render_script(app_name, props_json, desired)
        return {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "generateName": f"apim-product-{app_name}-",
                "namespace": self.namespace,
                "labels": {
                    "app.kubernetes.io/component": "apim-product",
                    "app.kubernetes.io/managed-by": "capability-mcp",
                    "apim-product.cafe.io/app": app_name,
                },
            },
            "spec": {
                "ttlSecondsAfterFinished": 1800,
                "backoffLimit": 2,
                "template": {
                    "spec": {
                        "restartPolicy": "OnFailure",
                        "volumes": [{
                            "name": "azure-creds",
                            "secret": {"secretName": self.azure_secret},
                        }],
                        "containers": [{
                            "name": "apim-product",
                            "image": "mcr.microsoft.com/azure-cli:2.64.0",
                            "volumeMounts": [{
                                "name": "azure-creds",
                                "mountPath": "/azure",
                                "readOnly": True,
                            }],
                            "env": [
                                {"name": "APP", "value": app_name},
                                {"name": "APIM_NAME", "value": self.apim_name},
                                {"name": "APIM_RG", "value": self.apim_rg},
                                {"name": "DESIRED", "value": desired},
                            ],
                            "command": ["/bin/sh", "-c"],
                            "args": [script],
                        }],
                    },
                },
            },
        }

    def _render_script(self, app_name: str, props_json: str, desired: str) -> str:
        """The converge shell script (§3.1–3.5). Writes the product properties to a
        file to avoid shell-quoting the JSON. Skip-404 on link (day-0 ordering)."""
        # props_json is single-quoted-safe (it contains no single quotes — JSON
        # uses double quotes), so embed it directly in a heredoc-free echo via python.
        return f"""
set -e
CID=$(python3 -c "import json;print(json.load(open('/azure/azure-creds.json'))['clientId'])")
CSC=$(python3 -c "import json;print(json.load(open('/azure/azure-creds.json'))['clientSecret'])")
TEN=$(python3 -c "import json;print(json.load(open('/azure/azure-creds.json'))['tenantId'])")
SUB=$(python3 -c "import json;print(json.load(open('/azure/azure-creds.json'))['subscriptionId'])")
az login --service-principal -u "$CID" -p "$CSC" --tenant "$TEN" >/dev/null
az account set --subscription "$SUB"

B="https://management.azure.com/subscriptions/$SUB/resourceGroups/$APIM_RG/providers/Microsoft.ApiManagement/service/$APIM_NAME"

# §3.1 create/upsert the product (idempotent PUT)
cat > /tmp/product.json <<'PRODJSON'
{props_json}
PRODJSON
az rest --method PUT --url "$B/products/$APP?api-version={_API_VERSION}" --body @/tmp/product.json
echo "product upserted: $APP (published, subscriptionRequired=false)"

# §3.4 ensure portal discoverability via the developers group
az rest --method PUT --url "$B/products/$APP/groups/developers?api-version={_API_VERSION}" || true

# §3.2 link desired APIs that exist (skip-404 for day-0 ordering — the EVENT-2-
# sibling sensor backfills the link when the ksvc becomes Ready).
for ID in $DESIRED; do
  if az rest --method PUT --url "$B/products/$APP/apis/$ID?api-version={_API_VERSION}" 2>/tmp/err; then
    echo "linked: $ID"
  else
    if grep -qi 'NotFound\\|ResourceNotFound\\|404' /tmp/err; then
      echo "skip (api not yet created, sensor will backfill): $ID"
    else
      echo "ERROR linking $ID:"; cat /tmp/err; exit 1
    fi
  fi
done

# §3.3 + §3.5 CONVERGE: unlink members no longer desired (resubmit-removal case).
CURRENT=$(az rest --method GET --url "$B/products/$APP/apis?api-version={_API_VERSION}" \\
  --query "value[].name" -o tsv 2>/dev/null || echo "")
for CUR in $CURRENT; do
  KEEP=0
  for ID in $DESIRED; do [ "$CUR" = "$ID" ] && KEEP=1 && break; done
  if [ "$KEEP" = "0" ]; then
    echo "unlinking (no longer in OAM): $CUR"
    az rest --method DELETE --url "$B/products/$APP/apis/$CUR?api-version={_API_VERSION}" || true
  fi
done
echo "APIM product $APP converged"
"""
