# HARD-1 (#168): microservice-creator (mscv) image.
# Extracts the inline scaffold heredoc from application-claim-composition.yaml
# into a versioned, testable container. The composition Job now just runs
# /scripts/entrypoint.sh from this image.
#
# Tooling: the original Job ran `apk add --no-cache git curl jq` on alpine:3.18.
# We bake those in (plus bash, since the scripts are bash) so the Job no longer
# installs packages at runtime. Same base distro (alpine 3.18) for parity.
FROM alpine:3.18

# Same tools the original Job's `apk add` installed, plus bash for the scripts.
RUN apk add --no-cache git curl jq bash

COPY scripts/ /scripts/
RUN chmod +x /scripts/entrypoint.sh /scripts/lib/*.sh

# The composition Job sets command: [/scripts/entrypoint.sh] and passes the
# SERVICE_NAME/APP_CONTAINER/LANGUAGE/FRAMEWORK/SERVICE_FLAVOR/GITHUB_* env.
ENTRYPOINT ["/scripts/entrypoint.sh"]
